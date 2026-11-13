"""A fake LLM provider so tests never construct an SDK client or touch the network."""

from collections.abc import AsyncIterator

import pytest

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
