"""HTTP contract of /api/copilot. Services are patched: no DB, embedding model or LLM."""

import json
import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.main import create_app
from app.schemas.copilot import CopilotDocument, FeedbackRequest, FeedbackResponse
from app.services import copilot
from app.services.llm import Usage
from app.services.rag import RetrievedChunk
from tests.fakes import FakeProvider, use_provider

DOC_ID = uuid.UUID("00000000-0000-0000-0000-0000000000d1")


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def document(client_id: str = "bloom-bakery", filename: str = "brief.pdf") -> CopilotDocument:
    return CopilotDocument(
        id=DOC_ID, client=client_id, filename=filename, pages=0, status="processing",
        error=None, created_at=datetime.now(UTC),
    )  # fmt: skip


@pytest.fixture
def ingested(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, bytes]]:
    """Patch document creation + the background ingest; record what would be ingested."""
    calls: list[tuple[str, str, bytes]] = []
    monkeypatch.setattr(copilot, "create_document", lambda db, c, f: document(c, f))
    monkeypatch.setattr(
        copilot,
        "ingest_document",
        lambda doc_id, f, content: calls.append((str(doc_id), f, content)),
    )
    return calls


def parse_sse(body: str) -> list[tuple[str, dict[str, object]]]:
    events = []
    for block in body.strip().split("\n\n"):
        fields = dict(
            line.split(": ", 1) for line in block.splitlines() if not line.startswith(":")
        )
        events.append((fields["event"], json.loads(fields["data"])))
    return events


# --- upload -----------------------------------------------------------------------------------


def test_upload_returns_processing_and_ingests_in_background(
    client: TestClient, ingested: list[tuple[str, str, bytes]]
) -> None:
    result = client.post(
        "/api/copilot/upload",
        data={"client": "bloom-bakery"},
        files={"file": ("brief.pdf", b"%PDF-1.7 fake", "application/pdf")},
    )

    assert result.status_code == 202
    assert result.json()["status"] == "processing"
    assert ingested == [(str(DOC_ID), "brief.pdf", b"%PDF-1.7 fake")]


@pytest.mark.parametrize(
    ("filename", "content", "status"),
    [
        ("deck.docx", b"PK..", 415),
        ("empty.txt", b"", 422),
        ("fake.pdf", b"<html></html>", 422),
    ],
)
def test_upload_rejects_bad_files(
    client: TestClient,
    ingested: list[tuple[str, str, bytes]],
    filename: str,
    content: bytes,
    status: int,
) -> None:
    result = client.post(
        "/api/copilot/upload", data={"client": "bloom-bakery"}, files={"file": (filename, content)}
    )

    assert result.status_code == status
    assert result.json()["detail"]
    assert ingested == []


def test_upload_over_size_limit_is_413(
    client: TestClient, ingested: list[tuple[str, str, bytes]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "copilot_max_upload_mb", 0.001)  # ~1 KB

    result = client.post(
        "/api/copilot/upload",
        data={"client": "bloom-bakery"},
        files={"file": ("a.txt", b"x" * 2000)},
    )

    assert result.status_code == 413
    assert "larger than" in result.json()["detail"]
    assert ingested == []


@pytest.mark.parametrize("data", [{}, {"client": "Not A Slug"}])
def test_upload_needs_a_valid_client(
    client: TestClient, ingested: list[tuple[str, str, bytes]], data: dict[str, str]
) -> None:
    result = client.post("/api/copilot/upload", data=data, files={"file": ("a.txt", b"hello")})

    assert result.status_code == 422


# --- documents --------------------------------------------------------------------------------


def test_documents_are_listed_per_client(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def list_documents(db: Session, client_id: str) -> list[CopilotDocument]:
        calls.append(client_id)
        return [document(client_id)]

    monkeypatch.setattr(copilot, "list_documents", list_documents)

    assert (
        client.get("/api/copilot/documents?client=apex-fitness").json()[0]["client"]
        == "apex-fitness"
    )
    assert client.get("/api/copilot/documents").status_code == 422
    assert calls == ["apex-fitness"]


def test_delete_document_204_and_404(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def delete(db: Session, document_id: uuid.UUID) -> None:
        if document_id != DOC_ID:
            raise copilot.DocumentNotFoundError(f"No document with id {document_id}.")

    monkeypatch.setattr(copilot, "delete_document", delete)

    assert client.delete(f"/api/copilot/documents/{DOC_ID}").status_code == 204
    missing = client.delete(f"/api/copilot/documents/{uuid.uuid4()}")
    assert missing.status_code == 404
    assert "No document" in missing.json()["detail"]


# --- chat (SSE) -------------------------------------------------------------------------------


def test_chat_stream_wire_format_and_event_order(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, usage_rows: list[object]
) -> None:
    chunk = RetrievedChunk(uuid.uuid4(), "brief.pdf", 2, "Q4 budget: $18,000 total.", 0.81)
    monkeypatch.setattr(copilot, "search", lambda client_id, query: [chunk])
    use_provider(
        monkeypatch, FakeProvider(stream_items=["$18,000 ", "[brief.pdf p.2]", Usage(10, 5)])
    )

    result = client.post(
        "/api/copilot/chat/stream", json={"client": "bloom-bakery", "question": "Q4 budget?"}
    )

    assert result.status_code == 200
    assert result.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(result.text)
    assert [name for name, _ in events] == ["token", "token", "citations", "done"]
    assert "".join(str(data["text"]) for name, data in events if name == "token") == (
        "$18,000 [brief.pdf p.2]"
    )
    assert events[2][1]["citations"] == [
        {
            "filename": "brief.pdf",
            "page": 2,
            "snippet": "Q4 budget: $18,000 total.",
            "similarity": 0.81,
        }
    ]
    assert events[3][1]["grounded"] is True


@pytest.mark.parametrize(
    "body",
    [
        {"client": "bloom-bakery"},
        {"client": "bloom-bakery", "question": ""},
        {"client": "bloom-bakery", "question": "x" * 1001},
        {"client": "BAD", "question": "hi"},
        {
            "client": "bloom-bakery",
            "question": "hi",
            "history": [{"role": "system", "content": "x"}],
        },
    ],
)
def test_chat_rejects_invalid_bodies(client: TestClient, body: dict[str, object]) -> None:
    assert client.post("/api/copilot/chat/stream", json=body).status_code == 422


def test_chat_rejects_unknown_provider(client: TestClient) -> None:
    result = client.post(
        "/api/copilot/chat/stream",
        json={"client": "bloom-bakery", "question": "hi"},
        headers={"X-LLM-Provider": "gemini"},
    )

    assert result.status_code == 400


# --- feedback ---------------------------------------------------------------------------------


def test_feedback_is_saved(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    saved: list[FeedbackRequest] = []

    def save(db: Session, body: FeedbackRequest) -> FeedbackResponse:
        saved.append(body)
        return FeedbackResponse(id=uuid.uuid4(), created_at=datetime.now(UTC))

    monkeypatch.setattr(copilot, "save_feedback", save)
    message_id = str(uuid.uuid4())

    result = client.post(
        "/api/copilot/feedback",
        json={"message_id": message_id, "answer": "It was $18,000.", "rating": "up"},
    )

    assert result.status_code == 201
    assert str(saved[0].message_id) == message_id and saved[0].rating == "up"


@pytest.mark.parametrize(
    "body",
    [
        {"answer": "a", "rating": "up"},  # neither message_id nor question
        {"question": "q", "answer": "a", "rating": "meh"},
        {"question": "q", "answer": "", "rating": "down"},
    ],
)
def test_feedback_validation(client: TestClient, body: dict[str, str]) -> None:
    assert client.post("/api/copilot/feedback", json=body).status_code == 422
