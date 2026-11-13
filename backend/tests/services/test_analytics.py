"""KPI math and CSV validation on small fixtures (no DB, no LLM)."""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from app.services import analytics
from app.services.analytics import CsvValidationError

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SAMPLE_CSV = Path(__file__).resolve().parents[2] / "sample_data" / "marketing_demo.csv"
HEADER = "date,channel,sessions,conversions,revenue,spend\n"


@pytest.fixture
def small_frame() -> pd.DataFrame:
    content = (FIXTURES / "marketing_small.csv").read_bytes()
    return analytics.parse_client_csv(content, "test-co", "Test Co").frame


def kpi_map(snapshot: analytics.InsightsSnapshot) -> dict[str, analytics.Kpi]:
    return {kpi.key: kpi for kpi in snapshot.kpis}


# --- KPI math -----------------------------------------------------------------


def test_period_splits_into_current_and_previous_windows(small_frame: pd.DataFrame) -> None:
    period = analytics.build_snapshot(small_frame, 2).period

    assert (period.start, period.end) == (date(2026, 1, 3), date(2026, 1, 4))
    assert (period.previous_start, period.previous_end) == (date(2026, 1, 1), date(2026, 1, 2))
    assert period.has_previous is True


def test_kpi_values_and_deltas(small_frame: pd.DataFrame) -> None:
    kpis = kpi_map(analytics.build_snapshot(small_frame, 2))

    # Current: 220 sessions, 10 conv, $1000 revenue, $60 spend. Previous: 300, 6, $600, $50.
    assert (kpis["sessions"].value, kpis["sessions"].previous) == (220, 300)
    assert kpis["sessions"].delta_pct == -26.7
    assert kpis["conversions"].delta_pct == 66.7
    assert (kpis["conversion_rate"].value, kpis["conversion_rate"].previous) == (4.55, 2.0)
    assert (kpis["revenue"].value, kpis["spend"].value) == (1000.0, 60.0)
    assert kpis["spend"].delta_pct == 20.0
    assert (kpis["roas"].value, kpis["roas"].previous) == (16.67, 12.0)
    assert (kpis["cpa"].value, kpis["cpa"].previous) == (6.0, 8.33)
    assert kpis["cpa"].good_when == "down"
    assert kpis["aov"].delta_pct == 0.0


def test_no_previous_period_means_no_deltas(small_frame: pd.DataFrame) -> None:
    snapshot = analytics.build_snapshot(small_frame, 3)

    assert snapshot.period.has_previous is False
    assert all(kpi.delta_pct is None and kpi.previous is None for kpi in snapshot.kpis)
    assert snapshot.signals == []


def test_ratios_are_none_when_denominator_is_zero() -> None:
    frame = analytics.clean_frame(
        pd.DataFrame(
            [
                {
                    "date": "2026-01-01",
                    "channel": "Organic",
                    "sessions": "0",
                    "conversions": "0",
                    "revenue": "0",
                    "spend": "0",
                }
            ]
        )  # fmt: skip
    ).frame

    kpis = kpi_map(analytics.build_snapshot(frame, 7))

    assert kpis["conversion_rate"].value is None
    assert kpis["roas"].value is None
    assert kpis["cpa"].value is None


def test_channel_breakdown(small_frame: pd.DataFrame) -> None:
    channels = analytics.build_snapshot(small_frame, 2).channels

    organic, paid = channels[0], channels[1]
    assert organic.channel == "Organic"
    assert (organic.sessions, organic.previous_sessions) == (120, 200)
    assert organic.sessions_delta_pct == -40.0
    assert organic.sessions_share_pct == 54.5
    assert organic.roas is None  # no spend
    assert paid.roas == 6.67
    assert paid.conversion_rate == 4.0


def test_timeseries_is_daily_with_channel_split(small_frame: pd.DataFrame) -> None:
    points = analytics.build_snapshot(small_frame, 2).timeseries

    assert [p.date for p in points] == [date(2026, 1, 3), date(2026, 1, 4)]
    assert points[0].sessions == 110
    assert points[0].by_channel == {"Organic": 60, "Paid Search": 50}


def test_signals_flag_big_channel_and_kpi_changes(small_frame: pd.DataFrame) -> None:
    signals = analytics.build_snapshot(small_frame, 2).signals

    organic = next(s for s in signals if s.channel == "Organic")
    assert organic.sentiment == "negative"
    assert organic.message == "Organic sessions down 40.0% vs the previous 2 days (200 → 120)"
    assert all(abs(s.delta_pct) >= analytics.SIGNAL_MIN_DELTA_PCT for s in signals)
    assert [abs(s.delta_pct) for s in signals] == sorted(
        (abs(s.delta_pct) for s in signals), reverse=True
    )
    cpa = next(s for s in signals if s.metric == "cpa")
    assert cpa.sentiment == "positive"  # CPA going down is good


def test_overview_sums_clients(small_frame: pd.DataFrame) -> None:
    kpis = {k.key: k for k in analytics.build_overview_kpis([small_frame, small_frame], 2)}

    assert kpis["active_clients"].value == 2
    assert kpis["spend"].value == 120.0
    assert kpis["conversions"].value == 20
    assert kpis["roas"].value == 16.67


def test_demo_data_tells_the_apex_organic_story() -> None:
    clients = {c.client_id: c for c in analytics.parse_multi_client_csv(SAMPLE_CSV.read_bytes())}

    assert set(clients) == {"apex-fitness", "bloom-bakery", "nova-dental"}
    signals = analytics.build_snapshot(clients["apex-fitness"].frame, 30).signals
    assert signals[0].channel == "Organic"
    assert signals[0].delta_pct < -25


# --- Validation -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"", "empty"),
        (b"   \n", "empty"),
        (HEADER.encode(), "no data rows"),
        (b"date,channel,sessions\n2026-01-01,Organic,1\n", "conversions, revenue, spend"),
        (f"{HEADER}2026-13-45,Organic,1,0,0,0\n".encode(), "row 2"),
        (f"{HEADER}2026-01-01,Organic,-5,0,0,0\n".encode(), "sessions"),
        (f"{HEADER}2026-01-01,Organic,1,0,lots,0\n".encode(), "revenue"),
        (f"{HEADER}2026-01-01,,1,0,0,0\n".encode(), "channel"),
        (b"\xff\xfe\x00garbage", "UTF-8"),
    ],
)
def test_invalid_csv_is_rejected_with_a_clear_message(content: bytes, message: str) -> None:
    with pytest.raises(CsvValidationError, match=message):
        analytics.parse_client_csv(content, "x", "X")


def test_messy_but_valid_csv_is_cleaned() -> None:
    content = (
        b" Date , Channel ,Sessions,Conversions,Revenue,Spend\n"
        b'2026-01-01,Organic,"1,200",3,"$1,000.50",\n'
        b"2026-01-01,Organic,100,1,10,0\n"
    )

    parsed = analytics.parse_client_csv(content, "x", "X")

    [row] = parsed.frame.to_dict("records")
    assert (row["sessions"], row["revenue"], row["spend"]) == (1300, 1010.5, 0.0)
    assert any("blank 'spend'" in w for w in parsed.warnings)
    assert any("duplicate" in w for w in parsed.warnings)


def test_client_column_selects_matching_rows() -> None:
    content = (FIXTURES / "marketing_small.csv").read_bytes()

    parsed = analytics.parse_client_csv(content, "other-co", "Other Co")

    assert parsed.frame["sessions"].tolist() == [999]


def test_client_column_without_matching_rows_is_rejected() -> None:
    content = (FIXTURES / "marketing_small.csv").read_bytes()

    with pytest.raises(CsvValidationError, match="no rows for Nova Dental. Found: Other Co, Test"):
        analytics.parse_client_csv(content, "nova-dental", "Nova Dental")


def test_client_slug() -> None:
    assert analytics.client_slug("  Apex Fitness & Co. ") == "apex-fitness-co"
