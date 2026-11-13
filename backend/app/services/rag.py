"""RAG primitives for the Client Copilot: extract → chunk → embed → retrieve.

Chunk sizes are measured with the embedding model's own tokenizer, and anything longer than
the model's input window raises instead of being silently truncated by sentence-transformers
(BGE reads at most 512 tokens; text past that would simply never be embedded).
"""

import io
import logging
import re
import threading
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import PurePath
from typing import Protocol

from pypdf import PdfReader
from pypdf.errors import PyPdfError
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.copilot import Chunk, Document

logger = logging.getLogger(__name__)

TEXT_EXTENSIONS = (".txt", ".md")
SUPPORTED_EXTENSIONS = (".pdf", *TEXT_EXTENSIONS)
# Measured on the sample brief with bge-small: whole ~450-token pages put the right page on top
# for 4/10 questions; 250-token chunks for 8/10 and separate off-topic questions far better.
# Smaller chunks gave no further gain. The model's hard limit (510) is enforced separately.
CHUNK_TOKENS = 250
OVERLAP_TOKENS = 40
# BGE v1.5 is trained with this instruction on queries only; passages are embedded as-is.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
EMBED_BATCH_SIZE = 32

TokenCounter = Callable[[str], int]


class DocumentParseError(ValueError):
    """The file has no readable text (corrupt, encrypted, scanned, or not UTF-8)."""


class ChunkTooLongError(ValueError):
    """Text would exceed the embedding model's input window and be silently truncated."""


@dataclass(frozen=True)
class PageText:
    page: int
    text: str


@dataclass(frozen=True)
class ExtractedDocument:
    page_count: int
    pages: list[PageText]  # 1-based page numbers; pages without text are left out


@dataclass(frozen=True)
class TextChunk:
    page: int
    chunk_index: int
    text: str
    token_count: int


@dataclass(frozen=True)
class RetrievedChunk:
    document_id: uuid.UUID
    filename: str
    page: int
    text: str
    similarity: float


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def extract_document(filename: str, content: bytes) -> ExtractedDocument:
    """Text per page with pypdf; a .txt/.md file is a single page."""
    suffix = PurePath(filename).suffix.lower()
    if suffix == ".pdf":
        pages = _pdf_pages(content)
    elif suffix in TEXT_EXTENSIONS:
        pages = [PageText(1, clean_text(_decode_utf8(content)))]
    else:
        raise DocumentParseError(f"Unsupported file type '{suffix}'.")
    with_text = [page for page in pages if page.text]
    if not with_text:
        raise DocumentParseError("No extractable text found (is it a scanned PDF?).")
    return ExtractedDocument(page_count=len(pages), pages=with_text)


def _pdf_pages(content: bytes) -> list[PageText]:
    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted and not reader.decrypt(""):
            raise DocumentParseError("The PDF is password-protected.")
        return [
            PageText(number, clean_text(page.extract_text() or ""))
            for number, page in enumerate(reader.pages, start=1)
        ]
    except DocumentParseError:
        raise
    except (PyPdfError, ValueError, KeyError, TypeError, NotImplementedError) as exc:
        # pypdf raises a mix of its own and builtin errors on malformed files.
        raise DocumentParseError(f"The PDF could not be read ({type(exc).__name__}).") from exc


def _decode_utf8(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DocumentParseError("Text files must be UTF-8 encoded.") from exc


def clean_text(raw: str) -> str:
    """Collapse runs of spaces, trim lines, keep paragraph breaks. Postgres rejects NUL."""
    lines = [re.sub(r"[ \t ]+", " ", line).strip() for line in raw.replace("\x00", "").splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

_UNIT_BOUNDARY = re.compile(r"(?<=[.!?])\s+|\n+")


def chunk_pages(
    pages: Sequence[PageText],
    count_tokens: TokenCounter,
    max_tokens: int = CHUNK_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[TextChunk]:
    """Split each page into ≤ max_tokens chunks; a page never spans chunks, so pages stay exact."""
    chunks: list[TextChunk] = []
    for page in pages:
        for piece in split_text(page.text, count_tokens, max_tokens, overlap_tokens):
            chunks.append(TextChunk(page.page, len(chunks), piece, count_tokens(piece)))
    return chunks


def split_text(
    text_: str, count_tokens: TokenCounter, max_tokens: int, overlap_tokens: int
) -> list[str]:
    """Pages that fit are kept verbatim; longer ones are packed sentence by sentence."""
    if count_tokens(text_) <= max_tokens:
        return [text_]
    units = [
        piece
        for unit in _UNIT_BOUNDARY.split(text_)
        if unit.strip()
        for piece in _fit_unit(unit.strip(), count_tokens, max_tokens)
    ]
    return _pack(units, count_tokens, max_tokens, overlap_tokens)


def _pack(
    units: list[str], count_tokens: TokenCounter, max_tokens: int, overlap_tokens: int
) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    for unit in units:
        if current and count_tokens(" ".join([*current, unit])) > max_tokens:
            chunks.append(" ".join(current))
            current = _overlap_tail(current, count_tokens, overlap_tokens)
            while current and count_tokens(" ".join([*current, unit])) > max_tokens:
                current.pop(0)
        current.append(unit)
    if current:
        chunks.append(" ".join(current))
    return chunks


def _overlap_tail(units: list[str], count_tokens: TokenCounter, overlap_tokens: int) -> list[str]:
    """The last whole sentences of a chunk that fit in the overlap budget."""
    tail: list[str] = []
    for unit in reversed(units):
        if count_tokens(" ".join([unit, *tail])) > overlap_tokens:
            break
        tail.insert(0, unit)
    return tail


def _fit_unit(unit: str, count_tokens: TokenCounter, max_tokens: int) -> list[str]:
    """Split a sentence longer than max_tokens on word boundaries (or inside a huge word)."""
    if count_tokens(unit) <= max_tokens:
        return [unit]
    pieces: list[str] = []
    current: list[str] = []
    for word in unit.split():
        for part in _fit_word(word, count_tokens, max_tokens):
            if current and count_tokens(" ".join([*current, part])) > max_tokens:
                pieces.append(" ".join(current))
                current = []
            current.append(part)
    if current:
        pieces.append(" ".join(current))
    return pieces


def _fit_word(word: str, count_tokens: TokenCounter, max_tokens: int) -> list[str]:
    if count_tokens(word) <= max_tokens:
        return [word]
    # Assume ≤ 4 tokens per character (byte-level worst case); verified again before embedding.
    step = max(1, max_tokens // 4)
    return [word[i : i + step] for i in range(0, len(word), step)]


def check_token_limit(texts: Sequence[str], count_tokens: TokenCounter, limit: int) -> None:
    for index, item in enumerate(texts):
        tokens = count_tokens(item)
        if tokens > limit:
            raise ChunkTooLongError(
                f"Text #{index} is {tokens} tokens; the embedding model reads at most {limit}."
            )


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------


class Embedder(Protocol):
    max_tokens: int

    def count_tokens(self, text: str) -> int: ...

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class BgeEmbedder:
    """sentence-transformers BGE model on CPU, producing L2-normalised vectors."""

    def __init__(self, model_name: str) -> None:
        # Imported here: torch + transformers take ~25 s to import cold, so only pay when used.
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name, device="cpu")
        self._tokenizer = self._model.tokenizer
        # [CLS] and [SEP] take two of the model's positions.
        self.max_tokens: int = self._model.max_seq_length - 2

    def count_tokens(self, text_: str) -> int:
        return len(self._tokenizer.encode(text_, add_special_tokens=False, verbose=False))

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        check_token_limit(texts, self.count_tokens, self.max_tokens)
        return self._encode(list(texts))

    def embed_query(self, text_: str) -> list[float]:
        query = QUERY_PREFIX + text_
        check_token_limit([query], self.count_tokens, self.max_tokens)
        return self._encode([query])[0]

    def _encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(
            texts,
            batch_size=EMBED_BATCH_SIZE,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vectors.tolist()


_embedder: Embedder | None = None
_embedder_lock = threading.Lock()


def get_embedder() -> Embedder:
    """The process-wide model, loaded once (thread-safe: warm-up and requests may race)."""
    global _embedder
    if _embedder is None:
        with _embedder_lock:
            if _embedder is None:
                model_name = get_settings().embedding_model
                logger.info("Loading embedding model %s", model_name)
                _embedder = BgeEmbedder(model_name)
                logger.info("Embedding model ready")
    return _embedder


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def retrieve(
    db: Session, client: str, query_embedding: Sequence[float], top_k: int
) -> list[RetrievedChunk]:
    """The client's top_k chunks by cosine similarity (1 - cosine distance), best first."""
    distance = Chunk.embedding.cosine_distance(query_embedding)
    stmt = (
        select(Chunk.document_id, Document.filename, Chunk.page, Chunk.text, distance)
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.client == client, Document.status == "ready")
        .order_by(distance)
        .limit(top_k)
    )
    # A filtered HNSW scan can return fewer than top_k rows when other clients' chunks crowd
    # the candidate list; iterative scans (pgvector >= 0.8) keep searching until enough match.
    db.execute(text("SET LOCAL hnsw.iterative_scan = strict_order"))
    rows = db.execute(stmt).all()
    return [
        RetrievedChunk(doc_id, filename, page, chunk_text, round(1.0 - float(dist), 4))
        for doc_id, filename, page, chunk_text, dist in rows
    ]


def is_grounded(chunks: Sequence[RetrievedChunk], min_similarity: float) -> bool:
    """True when the best chunk is similar enough to answer from; otherwise skip the LLM."""
    return bool(chunks) and max(chunk.similarity for chunk in chunks) >= min_similarity
