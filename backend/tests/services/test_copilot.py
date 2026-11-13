"""Copilot chat orchestration and upload validation. Retrieval and the LLM are faked."""

import uuid

import pytest

from app.schemas.copilot import ChatRequest, ChatTurn, CitationsEvent, DoneEvent, TokenEvent
from app.services import copilot, llm
from app.services.llm import Usage
from app.services.pricing import estimate_cost
from app.services.rag import RetrievedChunk
from tests.fakes import FakeProvider, TransientError, ok, use_provider

BRIEF = "bloom_bakery_brief.pdf"
MODEL = "openai/gpt-oss-120b"


def hit(page: int, similarity: float, text: str = "Q4 budget: $18,000 total.") -> RetrievedChunk:
    return RetrievedChunk(uuid.uuid4(), BRIEF, page, text, similarity)


class FakeSearch:
    """Stands in for embed + pgvector retrieval; records every (client, query)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.result = [hit(2, 0.82), hit(3, 0.55, "Past campaign results.")]

    def __call__(self, client: str, query: str) -> list[RetrievedChunk]:
        self.calls.append((client, query))
        return self.result


@pytest.fixture
def search(monkeypatch: pytest.MonkeyPatch) -> FakeSearch:
    fake = FakeSearch()
    monkeypatch.setattr(copilot, "search", fake)
    return fake


async def run(request: ChatRequest) -> list[copilot.ChatEvent]:
    return [event async for event in copilot.chat(request, "groq")]


def request(
    question: str = "What is the Q4 budget?", history: list[ChatTurn] | None = None
) -> ChatRequest:
    return ChatRequest(client="bloom-bakery", question=question, history=history or [])


# --- chat -------------------------------------------------------------------------------------


async def test_grounded_answer_streams_tokens_then_citations_then_done(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord], search: FakeSearch
) -> None:
    provider = use_provider(
        monkeypatch,
        FakeProvider(stream_items=["The Q4 budget is $18,000 ", f"[{BRIEF} p.2].", Usage(900, 60)]),
    )

    events = await run(request())

    assert [e.event for e in events] == ["token", "token", "citations", "done"]
    assert isinstance(events[0].data, TokenEvent) and events[0].data.text.startswith("The Q4")
    citations = events[2].data
    assert isinstance(citations, CitationsEvent)
    assert [(c.filename, c.page, c.similarity) for c in citations.citations] == [(BRIEF, 2, 0.82)]
    done = events[3].data
    assert isinstance(done, DoneEvent)
    assert (done.provider, done.model, done.input_tokens, done.output_tokens) == (
        "groq",
        MODEL,
        900,
        60,
    )
    assert done.cost_usd == float(estimate_cost(MODEL, 900, 60))
    assert done.grounded is True and done.rewritten_query is None
    assert search.calls == [("bloom-bakery", "What is the Q4 budget?")]
    assert [row.feature for row in usage_rows] == ["copilot"]
    [sent] = provider.requests
    assert f"Source [{BRIEF} p.2]\nQ4 budget: $18,000 total." in sent.messages[0].content
    assert sent.messages[0].content.endswith("Question: What is the Q4 budget?")
    assert "ONLY" in (sent.system or "")


async def test_weak_retrieval_skips_the_llm_and_costs_nothing(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord], search: FakeSearch
) -> None:
    provider = use_provider(monkeypatch, FakeProvider())
    search.result = [hit(1, 0.41), hit(2, 0.38)]

    events = await run(request("Who won the 1998 World Cup?"))

    assert [e.event for e in events] == ["token", "citations", "done"]
    assert isinstance(events[0].data, TokenEvent)
    assert "couldn't find this in Bloom Bakery's documents" in events[0].data.text
    assert events[1].data == CitationsEvent(citations=[])
    done = events[2].data
    assert isinstance(done, DoneEvent)
    assert (done.grounded, done.cost_usd, done.input_tokens, done.output_tokens) == (False, 0, 0, 0)
    assert provider.requests == []
    # Logged as a guardrail skip: no provider call, no tokens, no cost.
    assert [(r.feature, r.skipped, r.cached, r.cost_usd, r.input_tokens) for r in usage_rows] == [
        ("copilot", True, False, 0, 0)
    ]


async def test_no_documents_at_all_also_hits_the_guardrail(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord], search: FakeSearch
) -> None:
    use_provider(monkeypatch, FakeProvider())
    search.result = []

    events = await run(request())

    assert [e.event for e in events] == ["token", "citations", "done"]


async def test_follow_up_is_rewritten_from_the_last_four_turns(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord], search: FakeSearch
) -> None:
    standalone = "What was the ROAS of the Mother's Day Brunch Boxes campaign?"
    provider = use_provider(
        monkeypatch,
        FakeProvider(
            outcomes=[ok(f'"{standalone}"', tokens_in=120, tokens_out=30)],
            stream_items=[f"It was 5.0 [{BRIEF} p.3].", Usage(800, 40)],
        ),
    )
    history = [
        ChatTurn(role="user", content="old question one"),
        ChatTurn(role="assistant", content="old answer one"),
        ChatTurn(role="user", content="What was our best campaign?"),
        ChatTurn(role="assistant", content="Mother's Day Brunch Boxes."),
        ChatTurn(role="user", content="And the worst?"),
        ChatTurn(role="assistant", content="The Summer TikTok Test."),
    ]

    events = await run(request("What was the ROAS of the best one?", history))

    rewrite, answer = provider.requests
    prompt = rewrite.messages[0].content
    assert "old question one" not in prompt and "old answer one" not in prompt
    assert "What was our best campaign?" in prompt and "Summer TikTok Test" in prompt
    assert prompt.endswith("Latest question: What was the ROAS of the best one?")
    assert search.calls == [("bloom-bakery", standalone)]
    assert answer.messages[0].content.endswith(f"Question: {standalone}")
    assert [row.feature for row in usage_rows] == ["copilot_rewrite", "copilot"]
    done = events[-1].data
    assert isinstance(done, DoneEvent)
    assert (done.input_tokens, done.output_tokens, done.rewritten_query) == (920, 70, standalone)
    expected = estimate_cost(MODEL, 120, 30) + estimate_cost(MODEL, 800, 40)
    assert done.cost_usd == pytest.approx(float(expected))


async def test_llm_failure_ends_with_an_error_event(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord], search: FakeSearch
) -> None:
    use_provider(monkeypatch, FakeProvider(stream_items=[RuntimeError("boom")]))

    events = await run(request())

    assert [e.event for e in events] == ["error"]
    assert "Groq request failed" in events[0].data.detail  # type: ignore[attr-defined]
    assert usage_rows[0].success is False


async def test_mid_stream_failure_keeps_tokens_then_errors(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord], search: FakeSearch
) -> None:
    use_provider(monkeypatch, FakeProvider(stream_items=["Partial ", TransientError("drop")]))

    events = await run(request())

    assert [e.event for e in events] == ["token", "error"]


async def test_unexpected_failure_gives_a_generic_error(
    monkeypatch: pytest.MonkeyPatch, usage_rows: list[llm.UsageRecord]
) -> None:
    def broken_search(client: str, query: str) -> list[RetrievedChunk]:
        raise ConnectionError("database is down")

    monkeypatch.setattr(copilot, "search", broken_search)

    events = await run(request())

    assert [e.event for e in events] == ["error"]
    assert "database" not in events[0].data.detail  # type: ignore[attr-defined]


# --- citations --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("Budget is $18,000 [brief.pdf p.2].", [("brief.pdf", 2)]),
        ("A [brief.pdf p. 3] and B [brief.pdf p.1].", [("brief.pdf", 3), ("brief.pdf", 1)]),
        ("Both [brief.pdf p.2, p.3].", [("brief.pdf", 2), ("brief.pdf", 3)]),
        ("Mixed [brief.pdf p.2; notes.md p.1].", [("brief.pdf", 2), ("notes.md", 1)]),
        ("Repeated [brief.pdf p.2] twice [brief.pdf p.2].", [("brief.pdf", 2)]),
        ("Page word [brief.pdf page 4].", [("brief.pdf", 4)]),
        ("Unknown file [other.pdf p.2] and a [link](x).", []),
        ("No citations at all.", []),
        # Regression: gpt-oss on Groq cites with fullwidth brackets, which returned no citations.
        (
            "Budget **$18,000**【brief.pdf p.2】 and【notes.md p.1】",
            [("brief.pdf", 2), ("notes.md", 1)],
        ),
    ],
)
def test_citation_refs(answer: str, expected: list[tuple[str, int]]) -> None:
    assert copilot.citation_refs(answer, ["brief.pdf", "notes.md"]) == expected


def test_page_like_text_inside_a_filename_is_not_a_page() -> None:
    assert copilot.citation_refs("[p2.pdf p.7]", ["p2.pdf"]) == [("p2.pdf", 7)]


def test_cited_sources_only_include_retrieved_pages() -> None:
    chunks = [hit(2, 0.7, "first " * 100), hit(2, 0.9, "Budget text."), hit(3, 0.6)]

    citations = copilot.cited_sources(f"[{BRIEF} p.2] [{BRIEF} p.9]", chunks)

    assert [(c.page, c.similarity, c.snippet) for c in citations] == [(2, 0.9, "Budget text.")]


def test_snippet_is_flattened_and_capped() -> None:
    snippet = copilot._snippet("word\n" * 200)

    assert len(snippet) == copilot.SNIPPET_CHARS and snippet.endswith("…")
    assert "\n" not in snippet


# --- upload validation ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("filename", "stored"),
    [
        ("brief.PDF", "brief.PDF"),
        ("notes.md", "notes.md"),
        ("C:\\Users\\me\\..\\plan.txt", "plan.txt"),
    ],
)
def test_valid_uploads_keep_a_safe_base_name(filename: str, stored: str) -> None:
    content = b"%PDF-1.7 ..." if filename.lower().endswith(".pdf") else b"hello"

    assert copilot.validate_upload(filename, content) == stored


@pytest.mark.parametrize(
    ("filename", "content", "error"),
    [
        ("deck.docx", b"PK...", copilot.UnsupportedDocumentError),
        ("noextension", b"hello", copilot.UnsupportedDocumentError),
        ("notes.txt", b"  \n ", copilot.InvalidDocumentError),
        ("fake.pdf", b"<html>not a pdf</html>", copilot.InvalidDocumentError),
    ],
)
def test_invalid_uploads_are_rejected(
    filename: str, content: bytes, error: type[Exception]
) -> None:
    with pytest.raises(error):
        copilot.validate_upload(filename, content)
