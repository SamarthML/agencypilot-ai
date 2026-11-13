"""Client Copilot: document upload/list/delete, streaming RAG chat (SSE) and feedback."""

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.sse import EventSourceResponse, ServerSentEvent
from sqlalchemy.orm import Session

from app.api.deps import LlmProviderDep
from app.core.config import get_settings
from app.core.db import get_db
from app.schemas.common import ClientId
from app.schemas.copilot import ChatRequest, CopilotDocument, FeedbackRequest, FeedbackResponse
from app.services import copilot

router = APIRouter(prefix="/api/copilot", tags=["copilot"])

DbDep = Annotated[Session, Depends(get_db)]


async def _read_upload(file: UploadFile) -> bytes:
    limit_mb = get_settings().copilot_max_upload_mb
    max_bytes = int(limit_mb * 1024 * 1024)
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"The file is larger than {limit_mb:g} MB.",
        )
    return content


@router.post("/upload", response_model=CopilotDocument, status_code=status.HTTP_202_ACCEPTED)
async def upload(
    db: DbDep,
    background: BackgroundTasks,
    client: Annotated[ClientId, Form()],
    file: Annotated[UploadFile, File(description="PDF, .txt or .md, up to 10 MB")],
) -> CopilotDocument:
    """Store the document as `processing`; chunking + embedding run in a background task."""
    content = await _read_upload(file)
    filename = copilot.validate_upload(file.filename or "", content)
    document = copilot.create_document(db, client, filename)
    background.add_task(copilot.ingest_document, document.id, filename, content)
    return document


@router.get("/documents", response_model=list[CopilotDocument])
def documents(db: DbDep, client: Annotated[ClientId, Query()]) -> list[CopilotDocument]:
    return copilot.list_documents(db, client)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: uuid.UUID, db: DbDep) -> None:
    copilot.delete_document(db, document_id)


@router.post("/chat/stream", response_class=EventSourceResponse)
async def chat_stream(
    body: ChatRequest, provider: LlmProviderDep
) -> AsyncIterator[ServerSentEvent]:
    """SSE: `token`* → `citations` → `done` (or `error`). Answers only from the client's docs."""
    async for event in copilot.chat(body, provider):
        yield ServerSentEvent(event=event.event, data=event.data)


@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def feedback(body: FeedbackRequest, db: DbDep) -> FeedbackResponse:
    return copilot.save_feedback(db, body)
