"""RAG primitives: extraction, token-aware chunking, the token-limit guard, the threshold."""

import uuid

import pytest

from app.services import copilot, rag
from app.services.rag import PageText, RetrievedChunk


def words(text: str) -> int:
    """Token counter for tests: one token per whitespace-separated word."""
    return len(text.split())


def sentences(count: int, words_each: int = 10, tag: str = "s") -> str:
    return " ".join(
        " ".join(f"{tag}{i}w{j}" for j in range(words_each - 1)) + f" end{i}." for i in range(count)
    )


# --- extraction -------------------------------------------------------------------------------


def test_text_file_is_one_cleaned_page() -> None:
    content = "﻿Hello   world\n\n\n\nSecond\t para\x00".encode()

    extracted = rag.extract_document("notes.md", content)

    assert extracted.page_count == 1
    assert extracted.pages == [PageText(1, "Hello world\n\nSecond para")]


def test_non_utf8_text_file_is_rejected() -> None:
    with pytest.raises(rag.DocumentParseError, match="UTF-8"):
        rag.extract_document("notes.txt", "café".encode("latin-1"))


def test_whitespace_only_file_has_no_text() -> None:
    with pytest.raises(rag.DocumentParseError, match="No extractable text"):
        rag.extract_document("notes.txt", b"   \n\n ")


def test_pdf_pages_keep_their_numbers() -> None:
    extracted = rag.extract_document("brief.pdf", copilot.SAMPLE_BRIEF.read_bytes())

    assert extracted.page_count == 3
    assert [page.page for page in extracted.pages] == [1, 2, 3]
    assert "Brand voice" in extracted.pages[0].text
    assert "$18,000" in extracted.pages[1].text
    assert "Mother's Day Brunch" in extracted.pages[2].text


def test_corrupt_pdf_raises_parse_error() -> None:
    with pytest.raises(rag.DocumentParseError, match="could not be read"):
        rag.extract_document("broken.pdf", b"%PDF-1.7\nthis is not really a pdf")


# --- chunking ---------------------------------------------------------------------------------


def test_page_that_fits_is_one_verbatim_chunk() -> None:
    text = "Line one.\nLine two keeps its newline."

    chunks = rag.chunk_pages([PageText(4, text)], words, max_tokens=50)

    assert [(c.page, c.chunk_index, c.text) for c in chunks] == [(4, 0, text)]
    assert chunks[0].token_count == words(text)


def test_long_page_splits_under_limit_with_sentence_overlap() -> None:
    text = sentences(30)  # 300 tokens

    chunks = rag.chunk_pages([PageText(1, text)], words, max_tokens=50, overlap_tokens=10)

    assert len(chunks) > 6
    assert all(c.token_count <= 50 for c in chunks)
    for previous, current in zip(chunks, chunks[1:], strict=False):
        last_sentence = previous.text.rsplit(". ", 1)[-1]
        assert current.text.startswith(last_sentence)  # one 10-token sentence carried over
    covered = " ".join(c.text for c in chunks)
    assert all(f"end{i}." in covered for i in range(30))


def test_page_numbers_and_chunk_indexes_across_pages() -> None:
    pages = [
        PageText(1, sentences(12, tag="a")),
        PageText(2, "Short page."),
        PageText(5, sentences(12, tag="c")),
    ]

    chunks = rag.chunk_pages(pages, words, max_tokens=50, overlap_tokens=0)

    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert {c.page for c in chunks} == {1, 2, 5}
    assert all("a0w0" not in c.text for c in chunks if c.page != 1)
    assert [c.text for c in chunks if c.page == 2] == ["Short page."]


def test_sentence_longer_than_limit_is_split_on_words() -> None:
    giant = " ".join(f"w{i}" for i in range(120)) + "."

    chunks = rag.chunk_pages([PageText(1, giant)], words, max_tokens=50, overlap_tokens=0)

    assert [c.token_count for c in chunks] == [50, 50, 20]
    assert " ".join(c.text for c in chunks) == giant


def test_single_huge_word_is_split_by_characters() -> None:
    def chars(text: str) -> int:  # worst case: one token per character
        return len(text.replace(" ", ""))

    chunks = rag.chunk_pages([PageText(1, "x" * 1000)], chars, max_tokens=100, overlap_tokens=0)

    assert all(c.token_count <= 100 for c in chunks)
    assert "".join(c.text.replace(" ", "") for c in chunks) == "x" * 1000


def test_brief_chunks_fit_the_embedding_window() -> None:
    extracted = rag.extract_document("brief.pdf", copilot.SAMPLE_BRIEF.read_bytes())

    chunks = rag.chunk_pages(extracted.pages, words)

    rag.check_token_limit([c.text for c in chunks], words, rag.CHUNK_TOKENS)
    assert {c.page for c in chunks} == {1, 2, 3}


# --- token-limit guard ------------------------------------------------------------------------


def test_token_limit_raises_instead_of_truncating() -> None:
    rag.check_token_limit(["a b c", "d e"], words, limit=3)

    with pytest.raises(rag.ChunkTooLongError, match="Text #1 is 4 tokens"):
        rag.check_token_limit(["a b", "a b c d"], words, limit=3)


# --- threshold --------------------------------------------------------------------------------


def hit(similarity: float) -> RetrievedChunk:
    return RetrievedChunk(uuid.uuid4(), "brief.pdf", 1, "text", similarity)


@pytest.mark.parametrize(
    ("similarities", "grounded"),
    [([], False), ([0.42, 0.59], False), ([0.6], True), ([0.31, 0.83], True)],
)
def test_is_grounded_uses_best_similarity(similarities: list[float], grounded: bool) -> None:
    assert rag.is_grounded([hit(s) for s in similarities], 0.6) is grounded
