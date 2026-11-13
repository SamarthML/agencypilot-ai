"""Calendar-month analytics for reports (pure Pandas, no DB)."""

from datetime import date

import pytest

from app.services import analytics
from tests.report_data import report_frame


@pytest.mark.parametrize(
    ("month", "first", "last"),
    [
        ("2026-02", date(2026, 2, 1), date(2026, 2, 28)),
        ("2028-02", date(2028, 2, 1), date(2028, 2, 29)),
        ("2026-12", date(2026, 12, 1), date(2026, 12, 31)),
    ],
)
def test_month_bounds(month: str, first: date, last: date) -> None:
    assert analytics.month_bounds(month) == (first, last)


def test_previous_month_crosses_year() -> None:
    assert analytics.previous_month("2026-01") == "2025-12"
    assert analytics.month_label("2026-10") == "October 2026"


def test_available_months_flags_partial_and_previous() -> None:
    months = analytics.available_months(report_frame())

    assert [(m.month, m.complete, m.has_previous) for m in months] == [
        ("2026-10", True, True),
        ("2026-09", True, True),
        ("2026-08", False, False),  # data starts on Aug 15
    ]
    assert months[0].label == "October 2026"


def test_month_snapshot_compares_calendar_months() -> None:
    snapshot = analytics.build_month_snapshot(report_frame(), "2026-10")
    kpis = {k.key: k for k in snapshot.kpis}

    assert snapshot.period.previous_label == "September 2026"
    assert (kpis["sessions"].value, kpis["sessions"].previous) == (4340, 4500)  # 31 vs 30 days
    assert kpis["sessions"].delta_pct == -3.6
    assert (kpis["revenue"].value, kpis["revenue"].previous) == (10230.0, 9000.0)
    assert kpis["revenue"].delta_pct == 13.7
    assert len(snapshot.timeseries) == 31


def test_top_movers_name_channels_against_the_previous_month() -> None:
    snapshot = analytics.build_month_snapshot(report_frame(), "2026-10")
    messages = [s.message for s in snapshot.top_movers]

    assert "Paid Search sessions up 24.0% vs September 2026 (1,500 → 1,860)" in messages
    assert "Organic sessions down 17.3% vs September 2026 (3,000 → 2,480)" in messages
    deltas = [abs(s.delta_pct) for s in snapshot.top_movers]
    assert deltas == sorted(deltas, reverse=True)


def test_month_without_data_is_rejected() -> None:
    with pytest.raises(analytics.NoDataForMonthError, match="no data for July 2026"):
        analytics.build_month_snapshot(report_frame(), "2026-07")


def test_first_month_has_no_previous_comparison() -> None:
    snapshot = analytics.build_month_snapshot(report_frame(), "2026-08")

    assert snapshot.period.has_previous is False
    assert all(k.previous is None and k.delta_pct is None for k in snapshot.kpis)
