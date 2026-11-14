"""Copilot persistence + pgvector retrieval against Postgres (fake embedder, no torch).

Skipped when the database isn't running.
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, check_db
from app.models.copilot import Chunk, CopilotFeedback, Document
from app.schemas.copilot import FeedbackRequest
from app.services import copilot, rag
from tests.fakes import FakeEmbedder

pytestmark = pytest.mark.skipif(not check_db(), reason="Postgres is not running")

CLIENT_A = "pytest-copilot-a"
CLIENT_B = "pytest-copilot-b"
SEED_CLIENT = "pytest-copilot-seed"
CLIENTS = (CLIENT_A, CLIENT_B, SEED_CLIENT)

SOURDOUGH = "Our sourdough loaves are baked at 5am with a 36 hour ferment."
BUDGET = "The Q4 marketing budget is 18000 dollars split across paid social and search."


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch) -> Iterator[Session]:
    embedder = FakeEmbedder()
    monkeypatch.setattr(rag, "get_embedder", lambda: embedder)
    with SessionLocal() as session:
        yield session
        session.execute(delete(Document).where(Document.client.in_(CLIENTS)))
        session.execute(delete(CopilotFeedback).where(CopilotFeedback.client.in_(CLIENTS)))
        session.commit()


def ingest(db: Session, client: str, filename: str, text: str) -> copilot.CopilotDocument:
    document = copilot.create_document(db, client, filename)
    copilot.ingest_document(document.id, filename, text.encode())
    return document


def test_ingest_marks_ready_and_counts_chunks(db: Session) -> None:
    ingest(db, CLIENT_A, "notes.md", f"{SOURDOUGH}\n\n{BUDGET}")

    [listed] = copilot.list_documents(db, CLIENT_A)

    assert (listed.status, listed.pages, listed.chunk_count, listed.error) == ("ready", 1, 1, None)


def test_retrieval_ranks_by_similarity_and_filters_by_client(db: Session) -> None:
    ingest(db, CLIENT_A, "bread.txt", SOURDOUGH)
    ingest(db, CLIENT_A, "budget.txt", BUDGET)
    ingest(db, CLIENT_B, "other-client.txt", SOURDOUGH)  # identical text, other client

    vector = FakeEmbedder().embed_query("how long is the sourdough ferment")
    hits = rag.retrieve(db, CLIENT_A, vector, top_k=5)
    db.rollback()  # end the SET LOCAL transaction

    assert [h.filename for h in hits] == ["bread.txt", "budget.txt"]
    assert hits[0].similarity > hits[1].similarity
    assert 0 < hits[0].similarity <= 1
    assert rag.retrieve(db, "pytest-copilot-nobody", vector, top_k=5) == []


def test_unreadable_file_is_marked_failed(db: Session) -> None:
    document = copilot.create_document(db, CLIENT_A, "latin1.txt")
    copilot.ingest_document(document.id, "latin1.txt", "café".encode("latin-1"))

    [listed] = copilot.list_documents(db, CLIENT_A)

    assert listed.status == "failed"
    assert listed.error is not None and "UTF-8" in listed.error
    assert listed.chunk_count == 0


def test_delete_removes_chunks_and_404s_twice(db: Session) -> None:
    document = ingest(db, CLIENT_A, "bread.txt", SOURDOUGH)

    copilot.delete_document(db, document.id)

    remaining = db.scalar(
        select(func.count()).select_from(Chunk).where(Chunk.document_id == document.id)
    )
    assert remaining == 0
    with pytest.raises(copilot.DocumentNotFoundError):
        copilot.delete_document(db, document.id)


def test_seed_runs_once_per_client(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(copilot, "SAMPLE_CLIENT", SEED_CLIENT)

    copilot.seed_sample_documents()
    copilot.seed_sample_documents()

    [listed] = copilot.list_documents(db, SEED_CLIENT)
    assert (listed.filename, listed.status, listed.pages) == ("bloom_bakery_brief.pdf", "ready", 3)
    assert listed.chunk_count >= 3


def test_feedback_round_trip(db: Session) -> None:
    body = FeedbackRequest(
        client=CLIENT_A,
        question="Q4 budget?",
        answer="$18,000",
        rating="down",
        comment="Missing split",
    )

    saved = copilot.save_feedback(db, body)

    row = db.get(CopilotFeedback, saved.id)
    assert row is not None
    assert (row.rating, row.comment, row.message_id) == ("down", "Missing split", None)
    assert saved.created_at is not None


def stored_brief(db: Session) -> tuple[str, str, list[str]]:
    document = db.scalars(select(Document).where(Document.client == SEED_CLIENT)).one()
    db.refresh(document)
    chunk_ids = db.scalars(select(Chunk.id).where(Chunk.document_id == document.id)).all()
    return document.embedding_backend, document.status, [str(i) for i in chunk_ids]


def test_seed_re_embeds_the_brief_after_a_backend_switch(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(copilot, "SAMPLE_CLIENT", SEED_CLIENT)
    copilot.seed_sample_documents()
    backend, _, first_chunks = stored_brief(db)
    assert backend == "sentence-transformers"

    monkeypatch.setattr(rag, "current_backend", lambda: "fastembed")
    copilot.seed_sample_documents()
    backend, status, new_chunks = stored_brief(db)

    assert (backend, status) == ("fastembed", "ready")
    assert new_chunks and not set(new_chunks) & set(first_chunks)

    copilot.seed_sample_documents()  # same backend again: nothing to do
    assert stored_brief(db)[2] == new_chunks
