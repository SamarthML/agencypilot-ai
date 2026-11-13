"""Pure Pandas analytics for marketing CSVs: validation, KPIs, breakdowns and signals.

No database, HTTP or LLM here, so everything is unit-testable on small frames. A clean frame has
one row per (date, channel) with columns: date (datetime64), channel, sessions, conversions,
revenue, spend.
"""

import io
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from app.schemas.insights import (
    ChannelBreakdown,
    GoodWhen,
    InsightsSnapshot,
    Kpi,
    KpiUnit,
    Period,
    Signal,
    TimeSeriesPoint,
)
from app.schemas.reports import MonthPeriod, MonthSnapshot, ReportMonth

REQUIRED_COLUMNS = ("date", "channel", "sessions", "conversions", "revenue", "spend")
COUNT_COLUMNS = ("sessions", "conversions")
MONEY_COLUMNS = ("revenue", "spend")
METRICS = (*COUNT_COLUMNS, *MONEY_COLUMNS)
MAX_ROWS = 200_000
SIGNAL_MIN_DELTA_PCT = 15.0
SIGNAL_MIN_SHARE = 0.05  # ignore channels under 5% of previous-period sessions
MAX_SIGNALS = 5


class CsvValidationError(ValueError):
    """The uploaded file isn't a usable marketing CSV; the message is shown to the user."""


class NoDataForMonthError(CsvValidationError):
    """The requested report month has no rows in the client's dataset."""


@dataclass(frozen=True)
class CleanCsv:
    frame: pd.DataFrame
    warnings: list[str]


@dataclass(frozen=True)
class ClientFrame:
    client_id: str
    client_name: str
    frame: pd.DataFrame


# ---------------------------------------------------------------------------
# Parsing & validation
# ---------------------------------------------------------------------------


def client_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


def _normalise_column(name: object) -> str:
    return re.sub(r"\s+", "_", str(name).strip().lower())


def read_csv(content: bytes) -> pd.DataFrame:
    """Read raw bytes into an all-string frame with normalised column names."""
    if not content.strip():
        raise CsvValidationError("The file is empty.")
    try:
        frame = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig", dtype=str)
    except pd.errors.EmptyDataError as exc:
        raise CsvValidationError("The file is empty.") from exc
    except (pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise CsvValidationError(f"Couldn't read the file as a UTF-8 CSV ({exc}).") from exc
    frame.columns = [_normalise_column(c) for c in frame.columns]
    if frame.empty:
        raise CsvValidationError("The CSV has a header row but no data rows.")
    if len(frame) > MAX_ROWS:
        raise CsvValidationError(f"The CSV has {len(frame):,} rows; the limit is {MAX_ROWS:,}.")
    _check_columns(frame)
    return frame


def _check_columns(frame: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise CsvValidationError(
            f"Missing required column(s): {', '.join(missing)}. Expected columns: "
            f"{', '.join(REQUIRED_COLUMNS)} (plus an optional 'client' column)."
        )


def _row_number(index_label: object) -> int:
    """Spreadsheet row number of a frame index label (row 1 is the header)."""
    return int(str(index_label)) + 2


def _parse_dates(raw: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(raw.str.strip(), errors="coerce", format="mixed")
    bad = parsed.isna()
    if bad.any():
        first = bad.idxmax()
        raise CsvValidationError(
            f"Column 'date' has {int(bad.sum())} value(s) that aren't valid dates "
            f"(first at row {_row_number(first)}: {raw.loc[first]!r}). Use YYYY-MM-DD."
        )
    return parsed.dt.normalize()


def _parse_number(raw: pd.Series, column: str) -> tuple[pd.Series, int]:
    """Numbers may contain '$' or thousands separators; blanks count as 0 (and are reported)."""
    blanks = raw.isna() | (raw.str.strip() == "")
    cleaned = raw.where(~blanks, "0").str.replace(r"[,$\s]", "", regex=True)
    values = pd.to_numeric(cleaned, errors="coerce")
    bad = values.isna() | (values < 0)
    if bad.any():
        first = bad.idxmax()
        raise CsvValidationError(
            f"Column '{column}' has {int(bad.sum())} value(s) that aren't non-negative numbers "
            f"(first at row {_row_number(first)}: {raw.loc[first]!r})."
        )
    if column in COUNT_COLUMNS:
        values = values.round().astype("int64")
    return values, int(blanks.sum())


def _parse_channels(raw: pd.Series) -> pd.Series:
    channels = raw.fillna("").str.strip()
    if (channels == "").any():
        first = (channels == "").idxmax()
        raise CsvValidationError(f"Column 'channel' is empty at row {_row_number(first)}.")
    return channels


def clean_frame(raw: pd.DataFrame) -> CleanCsv:
    """Type-check a raw string frame and aggregate it to one row per (date, channel)."""
    frame = pd.DataFrame(
        {"date": _parse_dates(raw["date"]), "channel": _parse_channels(raw["channel"])}
    )
    warnings: list[str] = []
    for column in METRICS:
        frame[column], blanks = _parse_number(raw[column], column)
        if blanks:
            warnings.append(f"{blanks} blank '{column}' value(s) were treated as 0.")
    aggregated = frame.groupby(["date", "channel"], as_index=False)[list(METRICS)].sum()
    if len(aggregated) < len(frame):
        warnings.append(f"Combined {len(frame) - len(aggregated)} duplicate date/channel row(s).")
    return CleanCsv(aggregated.sort_values(["date", "channel"]).reset_index(drop=True), warnings)


def parse_client_csv(content: bytes, client_id: str, client_name: str) -> CleanCsv:
    """Parse an upload for one client. A 'client' column, if present, selects that client's rows."""
    raw = read_csv(content)
    if "client" in raw.columns:
        names = raw["client"].fillna("").astype(str)
        matched = raw[names.map(client_slug) == client_id]
        if matched.empty:
            found = ", ".join(sorted({n for n in names if n})[:5]) or "(none)"
            raise CsvValidationError(
                f"The file's 'client' column has no rows for {client_name}. Found: {found}."
            )
        raw = matched.reset_index(drop=True)
    return clean_frame(raw)


def parse_multi_client_csv(content: bytes) -> list[ClientFrame]:
    """Split a CSV with a 'client' column into one clean frame per client."""
    raw = read_csv(content)
    if "client" not in raw.columns:
        raise CsvValidationError("A multi-client CSV needs a 'client' column.")
    names = raw["client"].fillna("").str.strip()
    return [
        ClientFrame(client_slug(name), name, clean_frame(group.reset_index(drop=True)).frame)
        for name, group in raw.groupby(names, sort=True)
        if name
    ]


# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Totals:
    sessions: int
    conversions: int
    revenue: float
    spend: float

    def __add__(self, other: "Totals") -> "Totals":
        return Totals(
            self.sessions + other.sessions,
            self.conversions + other.conversions,
            self.revenue + other.revenue,
            self.spend + other.spend,
        )


ZERO_TOTALS = Totals(0, 0, 0.0, 0.0)


def totals(frame: pd.DataFrame) -> Totals:
    return Totals(
        sessions=int(frame["sessions"].sum()),
        conversions=int(frame["conversions"].sum()),
        revenue=float(frame["revenue"].sum()),
        spend=float(frame["spend"].sum()),
    )


def ratio(numerator: float, denominator: float, scale: float = 1.0) -> float | None:
    return None if not denominator else numerator / denominator * scale


def delta_pct(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None or previous == 0:
        return None
    return round((current - previous) / abs(previous) * 100, 1)


@dataclass(frozen=True)
class KpiDef:
    key: str
    label: str
    unit: KpiUnit
    good_when: GoodWhen
    compute: Callable[[Totals], float | None]


KPI_DEFS: tuple[KpiDef, ...] = (
    KpiDef("sessions", "Sessions", "count", "up", lambda t: t.sessions),
    KpiDef("conversions", "Conversions", "count", "up", lambda t: t.conversions),
    KpiDef(
        "conversion_rate", "Conversion rate", "percent", "up",
        lambda t: ratio(t.conversions, t.sessions, 100),
    ),
    KpiDef("revenue", "Revenue", "currency", "up", lambda t: t.revenue),
    KpiDef("spend", "Ad spend", "currency", "neutral", lambda t: t.spend),
    KpiDef("roas", "Blended ROAS", "ratio", "up", lambda t: ratio(t.revenue, t.spend)),
    KpiDef("cpa", "Cost / conversion", "currency", "down", lambda t: ratio(t.spend, t.conversions)),
    KpiDef("aov", "Avg. order value", "currency", "up", lambda t: ratio(t.revenue, t.conversions)),
)  # fmt: skip
KPI_BY_KEY = {kpi.key: kpi for kpi in KPI_DEFS}


def _round(value: float | None, unit: KpiUnit) -> float | None:
    if value is None:
        return None
    return float(round(value)) if unit == "count" else round(value, 2)


def build_kpi(definition: KpiDef, current: Totals, previous: Totals | None) -> Kpi:
    value = _round(definition.compute(current), definition.unit)
    prev = _round(definition.compute(previous), definition.unit) if previous else None
    return Kpi(
        key=definition.key,
        label=definition.label,
        value=value,
        previous=prev,
        delta_pct=delta_pct(value, prev),
        unit=definition.unit,
        good_when=definition.good_when,
    )


def build_kpis(current: Totals, previous: Totals | None) -> list[Kpi]:
    return [build_kpi(definition, current, previous) for definition in KPI_DEFS]


# ---------------------------------------------------------------------------
# Periods, breakdowns, timeseries
# ---------------------------------------------------------------------------


def resolve_period(frame: pd.DataFrame, days: int) -> Period:
    """The last `days` days of data, and the equally long window right before it."""
    end: date = frame["date"].max().date()
    start = end - timedelta(days=days - 1)
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=days - 1)
    return Period(
        days=days,
        start=start,
        end=end,
        previous_start=previous_start,
        previous_end=previous_end,
        has_previous=frame["date"].min().date() <= previous_start,
    )


def window(frame: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    dates = frame["date"].dt.date
    return frame[(dates >= start) & (dates <= end)]


def channel_breakdown(current: pd.DataFrame, previous: pd.DataFrame) -> list[ChannelBreakdown]:
    cur = current.groupby("channel")[list(METRICS)].sum()
    prev = previous.groupby("channel")[list(METRICS)].sum()
    channels = cur.index.union(prev.index)
    cur, prev = cur.reindex(channels, fill_value=0), prev.reindex(channels, fill_value=0)
    total_sessions = int(cur["sessions"].sum())
    rows = [
        _channel_row(str(name), cur.loc[name], prev.loc[name], total_sessions, not previous.empty)
        for name in channels
    ]
    return sorted(rows, key=lambda row: row.sessions, reverse=True)


def _channel_row(
    channel: str, cur: pd.Series, prev: pd.Series, total_sessions: int, has_previous: bool
) -> ChannelBreakdown:
    sessions, revenue, spend = int(cur["sessions"]), float(cur["revenue"]), float(cur["spend"])
    conversion_rate = ratio(int(cur["conversions"]), sessions, 100)
    roas = ratio(revenue, spend)
    return ChannelBreakdown(
        channel=channel,
        sessions=sessions,
        previous_sessions=int(prev["sessions"]),
        sessions_delta_pct=delta_pct(sessions, int(prev["sessions"])) if has_previous else None,
        sessions_share_pct=round(ratio(sessions, total_sessions, 100) or 0.0, 1),
        conversions=int(cur["conversions"]),
        revenue=round(revenue, 2),
        revenue_delta_pct=delta_pct(revenue, float(prev["revenue"])) if has_previous else None,
        spend=round(spend, 2),
        conversion_rate=None if conversion_rate is None else round(conversion_rate, 2),
        roas=None if roas is None else round(roas, 2),
    )


def build_timeseries(current: pd.DataFrame) -> list[TimeSeriesPoint]:
    daily = current.groupby("date")[list(METRICS)].sum()
    by_channel = current.pivot_table(
        index="date", columns="channel", values="sessions", aggfunc="sum", fill_value=0
    )
    return [
        TimeSeriesPoint(
            date=day.date(),
            sessions=int(row["sessions"]),
            conversions=int(row["conversions"]),
            revenue=round(float(row["revenue"]), 2),
            spend=round(float(row["spend"]), 2),
            by_channel={str(c): int(v) for c, v in by_channel.loc[day].items()},
        )
        for day, row in daily.iterrows()
    ]


# ---------------------------------------------------------------------------
# Signals (notable changes)
# ---------------------------------------------------------------------------

SIGNAL_KPIS = ("revenue", "conversion_rate", "roas", "cpa")


def format_value(value: float, unit: KpiUnit) -> str:
    if unit == "currency":
        return f"${value:,.2f}"
    if unit == "percent":
        return f"{value:.2f}%"
    if unit == "ratio":
        return f"{value:.2f}x"
    return f"{value:,.0f}"


def _sentiment(delta: float, good_when: GoodWhen) -> str:
    if good_when == "neutral":
        return "neutral"
    return "positive" if (delta > 0) == (good_when == "up") else "negative"


def _direction(delta: float) -> str:
    return "up" if delta > 0 else "down"


def channel_signals(
    channels: list[ChannelBreakdown], comparison: str, min_delta: float = SIGNAL_MIN_DELTA_PCT
) -> list[Signal]:
    previous_total = sum(c.previous_sessions for c in channels)
    signals: list[Signal] = []
    for c in channels:
        delta = c.sessions_delta_pct
        big_enough = previous_total and c.previous_sessions / previous_total >= SIGNAL_MIN_SHARE
        if delta is None or delta == 0 or abs(delta) < min_delta or not big_enough:
            continue
        message = (
            f"{c.channel} sessions {_direction(delta)} {abs(delta):.1f}% vs {comparison} "
            f"({c.previous_sessions:,} → {c.sessions:,})"
        )
        signals.append(
            Signal(
                kind="channel",
                metric="sessions",
                channel=c.channel,
                delta_pct=delta,
                current=c.sessions,
                previous=c.previous_sessions,
                sentiment=_sentiment(delta, "up"),
                message=message,
            )  # fmt: skip
        )
    return signals


def kpi_signals(
    kpis: list[Kpi], comparison: str, min_delta: float = SIGNAL_MIN_DELTA_PCT
) -> list[Signal]:
    signals: list[Signal] = []
    for kpi in kpis:
        delta = kpi.delta_pct
        if kpi.key not in SIGNAL_KPIS or delta is None or delta == 0 or abs(delta) < min_delta:
            continue
        assert kpi.value is not None and kpi.previous is not None  # delta implies both exist
        message = (
            f"{kpi.label} {_direction(delta)} {abs(delta):.1f}% vs {comparison} "
            f"({format_value(kpi.previous, kpi.unit)} → {format_value(kpi.value, kpi.unit)})"
        )
        signals.append(
            Signal(
                kind="kpi",
                metric=kpi.key,
                channel=None,
                delta_pct=delta,
                current=kpi.value,
                previous=kpi.previous,
                sentiment=_sentiment(delta, kpi.good_when),
                message=message,
            )  # fmt: skip
        )
    return signals


def find_signals(
    kpis: list[Kpi], channels: list[ChannelBreakdown], days: int, comparison: str | None = None
) -> list[Signal]:
    """Biggest movers; `comparison` names the baseline (default: "the previous N days")."""
    comparison = comparison or f"the previous {days} days"
    signals = channel_signals(channels, comparison) + kpi_signals(kpis, comparison)
    return sorted(signals, key=lambda s: abs(s.delta_pct), reverse=True)[:MAX_SIGNALS]


def top_movers(
    kpis: list[Kpi], channels: list[ChannelBreakdown], comparison: str, limit: int = MAX_SIGNALS
) -> list[Signal]:
    """The largest changes with no size threshold: a monthly report always names its movers."""
    signals = channel_signals(channels, comparison, 0.0) + kpi_signals(kpis, comparison, 0.0)
    return sorted(signals, key=lambda s: abs(s.delta_pct), reverse=True)[:limit]


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def build_snapshot(frame: pd.DataFrame, days: int) -> InsightsSnapshot:
    """Everything the dashboard shows for the last `days` days of one client's data."""
    if frame.empty:
        raise CsvValidationError("This dataset has no rows.")
    period = resolve_period(frame, days)
    current = window(frame, period.start, period.end)
    previous = (
        window(frame, period.previous_start, period.previous_end)
        if period.has_previous
        else frame.iloc[0:0]
    )
    kpis = build_kpis(totals(current), totals(previous) if period.has_previous else None)
    channels = channel_breakdown(current, previous)
    return InsightsSnapshot(
        period=period,
        kpis=kpis,
        timeseries=build_timeseries(current),
        channels=channels,
        signals=find_signals(kpis, channels, days),
    )


def period_totals(frame: pd.DataFrame, days: int) -> tuple[Totals, Totals | None]:
    """Current and previous-period totals for one client (previous is None if not covered)."""
    period = resolve_period(frame, days)
    current = totals(window(frame, period.start, period.end))
    if not period.has_previous:
        return current, None
    return current, totals(window(frame, period.previous_start, period.previous_end))


OVERVIEW_KPI_KEYS = ("spend", "roas", "conversions")


def build_overview_kpis(frames: list[pd.DataFrame], days: int) -> list[Kpi]:
    """Agency-wide KPIs across every client's latest dataset."""
    current, previous, with_previous = ZERO_TOTALS, ZERO_TOTALS, 0
    for frame in frames:
        cur, prev = period_totals(frame, days)
        current += cur
        if prev is not None:
            previous += prev
            with_previous += 1
    prev_totals = previous if with_previous else None
    clients = Kpi(
        key="active_clients", label="Active clients", value=float(len(frames)), previous=None,
        delta_pct=None, unit="count", good_when="up",
    )  # fmt: skip
    return [clients] + [
        build_kpi(KPI_BY_KEY[key], current, prev_totals) for key in OVERVIEW_KPI_KEYS
    ]


# ---------------------------------------------------------------------------
# Calendar months (monthly reports)
# ---------------------------------------------------------------------------


def month_bounds(month: str) -> tuple[date, date]:
    """First and last day of a "YYYY-MM" month."""
    first = date.fromisoformat(f"{month}-01")
    next_first = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    return first, next_first - timedelta(days=1)


def previous_month(month: str) -> str:
    first, _ = month_bounds(month)
    return (first - timedelta(days=1)).strftime("%Y-%m")


def month_label(month: str) -> str:
    return month_bounds(month)[0].strftime("%B %Y")


def _months_in(frame: pd.DataFrame) -> list[str]:
    return sorted(frame["date"].dt.strftime("%Y-%m").unique().tolist())


def available_months(frame: pd.DataFrame) -> list[ReportMonth]:
    """Months with data, newest first; `complete` when the data spans the whole month."""
    if frame.empty:
        return []
    first_day, last_day = frame["date"].min().date(), frame["date"].max().date()
    months = _months_in(frame)
    present = set(months)
    result = []
    for month in reversed(months):
        start, end = month_bounds(month)
        result.append(
            ReportMonth(
                month=month,
                label=month_label(month),
                complete=first_day <= start and last_day >= end,
                has_previous=previous_month(month) in present,
            )
        )
    return result


def month_period(frame: pd.DataFrame, month: str) -> MonthPeriod:
    start, end = month_bounds(month)
    prev = previous_month(month)
    previous_start, previous_end = month_bounds(prev)
    return MonthPeriod(
        month=month,
        label=month_label(month),
        start=start,
        end=end,
        previous_month=prev,
        previous_label=month_label(prev),
        previous_start=previous_start,
        previous_end=previous_end,
        has_previous=not window(frame, previous_start, previous_end).empty,
    )


def build_month_snapshot(frame: pd.DataFrame, month: str) -> MonthSnapshot:
    """KPIs, channels, daily series and top movers for one calendar month vs the one before."""
    period = month_period(frame, month)
    current = window(frame, period.start, period.end)
    if current.empty:
        raise NoDataForMonthError(f"There is no data for {period.label}.")
    previous = (
        window(frame, period.previous_start, period.previous_end)
        if period.has_previous
        else frame.iloc[0:0]
    )
    kpis = build_kpis(totals(current), totals(previous) if period.has_previous else None)
    channels = channel_breakdown(current, previous)
    return MonthSnapshot(
        period=period,
        kpis=kpis,
        channels=channels,
        timeseries=build_timeseries(current),
        top_movers=top_movers(kpis, channels, period.previous_label),
    )
