"""Fakes so tests never construct an SDK client, load an embedding model or touch the network."""

import math
import re
import zlib
from collections.abc import AsyncIterator, Sequence

import pytest

from app.models.copilot import EMBEDDING_DIM
from app.services import llm
from app.services.llm import Completion, CompletionRequest, StreamItem, Usage


class TransientError(Exception):
    """Stands in for a provider rate-limit/timeout error (retryable)."""


class FakeProvider:
    name = "groq"
    retryable_errors: tuple[type[BaseException], ...] = (TransientError,)

    def __init__(
        self,
        outcomes: list[Completion | Exception] | None = None,
        stream_items: list[StreamItem | Exception] | None = None,
    ) -> None:
        self.outcomes = outcomes or []
        self.stream_items = stream_items or []
        self.requests: list[CompletionRequest] = []

    async def complete(self, request: CompletionRequest) -> Completion:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamItem]:
        self.requests.append(request)
        for item in self.stream_items:
            if isinstance(item, Exception):
                raise item
            yield item


def use_provider(monkeypatch: pytest.MonkeyPatch, provider: FakeProvider) -> FakeProvider:
    monkeypatch.setattr(llm, "build_provider", lambda name, settings: provider)
    return provider


def ok(text: str = "All good.", tokens_in: int = 1000, tokens_out: int = 200) -> Completion:
    return Completion(text=text, usage=Usage(tokens_in, tokens_out))


class FakeEmbedder:
    """Deterministic stand-in for BGE: hashed bag-of-words, L2-normalised, 384 dims.

    Texts sharing words get a high cosine similarity, which is enough to test retrieval
    ranking and client filtering without loading torch. "Tokens" are whitespace words.
    """

    max_tokens = 510

    def __init__(self) -> None:
        self.queries: list[str] = []

    def count_tokens(self, text: str) -> int:
        return len(text.split())

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        return self._vector(text)

    @staticmethod
    def _vector(text: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIM
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            vector[zlib.crc32(word.encode()) % EMBEDDING_DIM] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]
