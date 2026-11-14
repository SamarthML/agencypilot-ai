"""Both real embedding backends produce the same kind of vector (skipped if not installed).

These load the actual BGE model (downloaded once into the HF / fastembed cache), so they are
the only tests that touch a real model; everything else uses tests/fakes.FakeEmbedder.
"""

import math
from collections.abc import Callable
from functools import cache

import pytest

from app.core.config import EmbeddingBackend
from app.models.copilot import EMBEDDING_DIM
from app.services import rag

MODEL = "BAAI/bge-small-en-v1.5"
PASSAGE = "Bloom Bakery wants to grow catering orders by 30% in the third quarter."
QUESTION = "What is the catering growth target?"
UNRELATED = "The ferry timetable changes every winter in northern Norway."
# Each backend's heavy dependency; ImportError or a blocked DLL (OSError) means "not installed".
BACKEND_MODULES: dict[EmbeddingBackend, str] = {
    "sentence-transformers": "sentence_transformers",
    "fastembed": "fastembed",
}


@cache
def load(backend: EmbeddingBackend) -> rag.Embedder | None:
    try:
        __import__(BACKEND_MODULES[backend])
    except (ImportError, OSError):
        return None
    return rag.EMBEDDER_CLASSES[backend](MODEL)


def embedder_or_skip(backend: EmbeddingBackend) -> rag.Embedder:
    embedder = load(backend)
    if embedder is None:
        pytest.skip(f"{backend} is not installed")
    return embedder


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


@pytest.mark.parametrize("backend", list(BACKEND_MODULES))
def test_backend_returns_normalised_384_dim_vectors(backend: EmbeddingBackend) -> None:
    embedder = embedder_or_skip(backend)

    passage, unrelated = embedder.embed_documents([PASSAGE, UNRELATED])
    query = embedder.embed_query(QUESTION)

    for vector in (passage, unrelated, query):
        assert len(vector) == EMBEDDING_DIM
        assert math.isclose(math.sqrt(dot(vector, vector)), 1.0, abs_tol=1e-4)
    assert dot(query, passage) > dot(query, unrelated)
    assert embedder.max_tokens == rag.BGE_MAX_TOKENS


@pytest.mark.parametrize("backend", list(BACKEND_MODULES))
def test_backend_counts_tokens_without_truncating(backend: EmbeddingBackend) -> None:
    embedder = embedder_or_skip(backend)

    assert embedder.count_tokens("word " * 900) == 900
    with pytest.raises(rag.ChunkTooLongError):
        embedder.embed_documents(["word " * 600])


def test_backends_agree() -> None:
    torch_backend = embedder_or_skip("sentence-transformers")
    onnx_backend = embedder_or_skip("fastembed")
    encode: list[Callable[[rag.Embedder], list[float]]] = [
        lambda e: e.embed_documents([PASSAGE])[0],
        lambda e: e.embed_query(QUESTION),
    ]

    for embed in encode:
        assert dot(embed(torch_backend), embed(onnx_backend)) > 0.99
    assert torch_backend.count_tokens(PASSAGE) == onnx_backend.count_tokens(PASSAGE)
