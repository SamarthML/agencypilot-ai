import pytest

from app.schemas.seo import CheckStatus, SeoCheck
from app.services.seo.scoring import score


def check(status: CheckStatus, weight: int) -> SeoCheck:
    return SeoCheck(id="x", name="X", status=status, value="v", recommendation="r", weight=weight)


def test_all_pass_is_100() -> None:
    assert score([check("pass", 60), check("pass", 40)]) == 100


def test_all_fail_is_0() -> None:
    assert score([check("fail", 60), check("fail", 40)]) == 0


def test_warn_earns_half_the_weight() -> None:
    assert score([check("warn", 100)]) == 50


@pytest.mark.parametrize(
    ("checks", "expected"),
    [
        ([check("pass", 15), check("fail", 12), check("warn", 10)], 54),  # (15 + 5) / 37
        ([check("pass", 6), check("warn", 8), check("fail", 86)], 10),  # (6 + 4) / 100
    ],
)
def test_weighted_math(checks: list[SeoCheck], expected: int) -> None:
    assert score(checks) == expected


def test_no_checks_scores_zero() -> None:
    assert score([]) == 0
