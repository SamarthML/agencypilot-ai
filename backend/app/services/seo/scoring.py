"""Severity-weighted 0-100 SEO score. Computed in code, never by the LLM."""

from collections.abc import Sequence

from app.schemas.seo import CheckStatus, SeoCheck

STATUS_FACTOR: dict[CheckStatus, float] = {"pass": 1.0, "warn": 0.5, "fail": 0.0}


def score(checks: Sequence[SeoCheck]) -> int:
    """round(100 * Σ weight·factor / Σ weight); 0 when there are no weighted checks."""
    total_weight = sum(c.weight for c in checks)
    if total_weight <= 0:
        return 0
    earned = sum(c.weight * STATUS_FACTOR[c.status] for c in checks)
    return round(100 * earned / total_weight)
