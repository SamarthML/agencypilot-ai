from decimal import Decimal

import pytest

from app.services import pricing


def test_known_model_cost_uses_per_million_prices() -> None:
    # openai/gpt-oss-120b on Groq: $0.15 in / $0.60 out per 1M tokens
    cost = pricing.estimate_cost("openai/gpt-oss-120b", 1_000_000, 1_000_000)

    assert cost == Decimal("0.750000")


def test_small_call_is_rounded_to_six_places() -> None:
    cost = pricing.estimate_cost("gpt-4o-mini", 1234, 567)

    # (1234 * 0.15 + 567 * 0.60) / 1e6 = 0.0005253
    assert cost == Decimal("0.000525")


def test_zero_tokens_cost_zero() -> None:
    assert pricing.estimate_cost("claude-haiku-5-5", 0, 0) == Decimal("0")


def test_unknown_model_costs_zero_and_warns(caplog: pytest.LogCaptureFixture) -> None:
    cost = pricing.estimate_cost("mystery-model", 1000, 1000)

    assert cost == Decimal("0")
    assert "mystery-model" in caplog.text


def test_negative_tokens_rejected() -> None:
    with pytest.raises(ValueError):
        pricing.estimate_cost("gpt-4o-mini", -1, 0)


def test_every_default_model_has_a_price() -> None:
    for model in ("openai/gpt-oss-120b", "gpt-4o-mini", "claude-haiku-5-5"):
        assert pricing.get_price(model) is not None
