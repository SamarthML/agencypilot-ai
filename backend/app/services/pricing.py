"""Per-model token prices used to estimate the cost of every LLM call.

These are EDITABLE ESTIMATES in USD per 1M tokens, taken from public pricing pages
(last checked 2026-11). Providers change prices; update this table rather than
hardcoding prices at call sites. Unknown models are costed at 0 and logged.
"""

import logging
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

logger = logging.getLogger(__name__)

PER_MILLION = Decimal(1_000_000)
COST_QUANTUM = Decimal("0.000001")


@dataclass(frozen=True)
class ModelPrice:
    input_per_mtok: Decimal
    output_per_mtok: Decimal


def _price(input_usd: str, output_usd: str) -> ModelPrice:
    return ModelPrice(Decimal(input_usd), Decimal(output_usd))


PRICES: dict[str, ModelPrice] = {
    # Groq (Llama 3.x models were retired from GroqCloud in 2026)
    "openai/gpt-oss-120b": _price("0.15", "0.60"),
    # OpenAI
    "gpt-4o-mini": _price("0.15", "0.60"),
    "gpt-4o": _price("2.50", "10.00"),
    # Anthropic (Claude Haiku 5.5 price applies to prompts up to 100K tokens)
    "claude-haiku-5-5": _price("0.10", "0.50"),
    "claude-sonnet-5-5": _price("2.00", "10.00"),
    "claude-opus-5-5": _price("4.00", "20.00"),
}


def get_price(model: str) -> ModelPrice | None:
    return PRICES.get(model)


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    """Estimated USD cost of one call, rounded to 6 decimal places."""
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("Token counts cannot be negative")
    price = get_price(model)
    if price is None:
        logger.warning("No price configured for model %r; cost recorded as 0", model)
        return Decimal("0").quantize(COST_QUANTUM)
    cost = (
        Decimal(input_tokens) * price.input_per_mtok
        + Decimal(output_tokens) * price.output_per_mtok
    ) / PER_MILLION
    return cost.quantize(COST_QUANTUM, rounding=ROUND_HALF_UP)
