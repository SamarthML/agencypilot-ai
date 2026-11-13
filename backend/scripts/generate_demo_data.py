"""Generate the deterministic demo marketing CSV used by the Insights dashboard.

Three clients x six channels x N days of daily sessions, conversions, revenue and spend, with
one scripted story per client so the AI summary has something real to find:

- Bloom Bakery: a Paid Social campaign lifts traffic over the last 25 days.
- Apex Fitness: Organic traffic drops ~45% over the last 24 days (a site redesign lost rankings).
- Nova Dental: Paid Search CPCs rise ~35% over the last 30 days (competitor bidding), so CPA rises.

Usage (from backend/):
    .\\.venv\\Scripts\\python.exe scripts/generate_demo_data.py
"""

import argparse
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger("generate_demo_data")

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUT = BACKEND_DIR / "sample_data" / "marketing_demo.csv"
DEFAULT_END = date(2026, 11, 12)
DEFAULT_DAYS = 180
DEFAULT_SEED = 42

# Monday..Sunday traffic multipliers.
WEEKDAY_FACTOR = np.array([1.05, 1.08, 1.06, 1.02, 0.95, 0.85, 0.88])
DAILY_GROWTH = 0.0005


@dataclass(frozen=True)
class Channel:
    name: str
    base_sessions: float
    cvr: float
    cpc: float = 0.0  # 0 for unpaid channels


@dataclass(frozen=True)
class Event:
    """Multiply a channel's sessions (or CPC) by `factor` for the last `days` days."""

    channel: str
    days: int
    factor: float
    target: str = "sessions"  # "sessions" or "cpc"
    ramp_days: int = 3


@dataclass(frozen=True)
class Client:
    name: str
    aov: float
    channels: tuple[Channel, ...]
    events: tuple[Event, ...] = field(default_factory=tuple)


CLIENTS: tuple[Client, ...] = (
    Client(
        "Bloom Bakery",
        aov=32.0,
        channels=(
            Channel("Organic", 420, 0.030),
            Channel("Paid Search", 160, 0.045, cpc=0.90),
            Channel("Paid Social", 220, 0.020, cpc=0.55),
            Channel("Email", 90, 0.070),
            Channel("Referral", 50, 0.030),
            Channel("Direct", 180, 0.050),
        ),
        events=(Event("Paid Social", days=25, factor=1.6),),
    ),
    Client(
        "Apex Fitness",
        aov=79.0,
        channels=(
            Channel("Organic", 650, 0.025),
            Channel("Paid Search", 240, 0.040, cpc=1.60),
            Channel("Paid Social", 300, 0.018, cpc=0.80),
            Channel("Email", 110, 0.060),
            Channel("Referral", 70, 0.025),
            Channel("Direct", 210, 0.035),
        ),
        events=(Event("Organic", days=24, factor=0.55),),
    ),
    Client(
        "Nova Dental",
        aov=210.0,
        channels=(
            Channel("Organic", 260, 0.030),
            Channel("Paid Search", 140, 0.050, cpc=3.20),
            Channel("Paid Social", 90, 0.012, cpc=1.10),
            Channel("Email", 40, 0.050),
            Channel("Referral", 60, 0.060),
            Channel("Direct", 120, 0.040),
        ),
        events=(Event("Paid Search", days=30, factor=1.35, target="cpc"),),
    ),
)


def event_multiplier(
    events: tuple[Event, ...], channel: str, target: str, n_days: int
) -> np.ndarray:
    """Per-day multiplier: 1.0, then a linear ramp to `factor` at the start of the event."""
    multiplier = np.ones(n_days)
    for event in events:
        if event.channel != channel or event.target != target:
            continue
        start = n_days - event.days
        ramp = np.linspace(1.0, event.factor, event.ramp_days + 1)[1:]
        multiplier[start : start + len(ramp)] *= ramp
        multiplier[start + len(ramp) :] *= event.factor
    return multiplier


def channel_rows(
    client: Client, channel: Channel, dates: pd.DatetimeIndex, rng: np.random.Generator
) -> pd.DataFrame:
    n = len(dates)
    trend = (1 + DAILY_GROWTH) ** np.arange(n)
    sessions_mult = event_multiplier(client.events, channel.name, "sessions", n)
    expected = channel.base_sessions * WEEKDAY_FACTOR[dates.day_of_week] * trend * sessions_mult
    sessions = np.maximum(0, np.round(expected * rng.lognormal(0, 0.07, n))).astype(int)
    conversions = rng.binomial(sessions, np.clip(channel.cvr * rng.lognormal(0, 0.05, n), 0, 1))
    revenue = conversions * client.aov * rng.lognormal(0, 0.10, n)
    cpc = channel.cpc * event_multiplier(client.events, channel.name, "cpc", n)
    spend = sessions * cpc * rng.lognormal(0, 0.05, n)
    return pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "client": client.name,
            "channel": channel.name,
            "sessions": sessions,
            "conversions": conversions,
            "revenue": revenue.round(2),
            "spend": spend.round(2),
        }
    )


def generate(end: date, days: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end=pd.Timestamp(end), periods=days, freq="D")
    frames = [
        channel_rows(client, channel, dates, rng)
        for client in CLIENTS
        for channel in client.channels
    ]
    return pd.concat(frames).sort_values(["client", "date", "channel"]).reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--end", type=date.fromisoformat, default=DEFAULT_END)
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args()
    frame = generate(args.end, args.days, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.out, index=False, lineterminator="\n")
    start = args.end - timedelta(days=args.days - 1)
    logger.info("Wrote %d rows (%s to %s) to %s", len(frame), start, args.end, args.out)


if __name__ == "__main__":
    main()
