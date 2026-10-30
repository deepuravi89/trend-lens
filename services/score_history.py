"""Score history: log what the model said each day, then check what happened next.

Each logged call uses the same neutral "new buyer" inputs (fixed portfolio, no
shares owned) so calls stay comparable over time, whatever your own holdings were.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Callable

import pandas as pd

from services.advisor import PositionInputs, base_quality_pct, build_position_advice
from services.market_data import StockSnapshot
from services.scoring import build_score_bundle, finalize_total_score

HISTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "score_history.csv"
COLUMNS = ["date", "ticker", "price", "total", "technical", "fundamental", "base_pct", "setup", "call", "confidence"]
HORIZONS = {"1M": 21, "3M": 63, "6M": 126}
SCORE_BANDS = [(80, "80+"), (65, "65–79"), (50, "50–64"), (0, "<50")]

NEUTRAL_INPUTS = PositionInputs(
    total_portfolio_value=100_000,
    shares_owned=0,
    average_cost_basis=0,
    max_portfolio_allocation_pct=10,
    cash_available_to_deploy=10_000,
    target_position_size_pct=None,
)


def build_record(snapshot: StockSnapshot, today: date | None = None) -> dict:
    """Score a snapshot with neutral inputs and return one history row."""
    scores = build_score_bundle(snapshot)
    advice = build_position_advice(snapshot, scores, NEUTRAL_INPUTS)
    final = finalize_total_score(scores, advice.score)
    return {
        "date": (today or date.today()).isoformat(),
        "ticker": snapshot.metadata.symbol,
        "price": round(float(snapshot.latest_price or 0.0), 4),
        "total": round(final.total_score, 2),
        "technical": round(scores.technical.score, 2),
        "fundamental": round(scores.fundamental.score, 2),
        "base_pct": round(base_quality_pct(scores), 2),
        "setup": advice.technical_setup.label,
        "call": advice.recommendation,
        "confidence": final.confidence,
    }


def load_history(path: Path = HISTORY_PATH) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)
    try:
        return pd.read_csv(path)
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return pd.DataFrame(columns=COLUMNS)


def record_score(snapshot: StockSnapshot, path: Path = HISTORY_PATH, today: date | None = None) -> dict:
    """Log today's call for a ticker, replacing any earlier entry for the same day."""
    record = build_record(snapshot, today)
    history = load_history(path)
    if not history.empty:
        same = (history["date"] == record["date"]) & (history["ticker"] == record["ticker"])
        history = history[~same]
    new_row = pd.DataFrame([record])
    history = new_row if history.empty else pd.concat([history, new_row], ignore_index=True)
    history = history.sort_values(["date", "ticker"])[COLUMNS]
    path.parent.mkdir(parents=True, exist_ok=True)
    history.to_csv(path, index=False)
    return record


def score_band(total: float) -> str:
    for floor, label in SCORE_BANDS:
        if total >= floor:
            return label
    return SCORE_BANDS[-1][1]


def forward_outcomes(
    history: pd.DataFrame,
    get_closes: Callable[[str], pd.Series],
    benchmark: str = "SPY",
    horizons: dict[str, int] = HORIZONS,
) -> pd.DataFrame:
    """For each logged call, the stock's and benchmark's return over each horizon.

    `get_closes(ticker)` returns daily closes indexed by date. A horizon is left
    empty until enough trading days have passed since the call.
    """
    if history.empty:
        return pd.DataFrame()
    bench = _daily(get_closes(benchmark))
    closes_by_ticker = {ticker: _daily(get_closes(ticker)) for ticker in history["ticker"].unique()}

    rows = []
    for record in history.to_dict("records"):
        closes = closes_by_ticker.get(record["ticker"])
        out = {**record, "band": score_band(float(record["total"]))}
        for label, days in horizons.items():
            stock_ret = _forward_return(closes, record["date"], days)
            bench_ret = _forward_return(bench, record["date"], days)
            out[f"ret_{label}"] = stock_ret
            out[f"excess_{label}"] = None if stock_ret is None or bench_ret is None else stock_ret - bench_ret
        rows.append(out)
    return pd.DataFrame(rows)


def summarize_outcomes(outcomes: pd.DataFrame, group_by: str, horizon: str) -> pd.DataFrame:
    """Average return, average excess vs benchmark and beat rate, per group."""
    column = f"excess_{horizon}"
    if outcomes.empty or column not in outcomes:
        return pd.DataFrame()
    done = outcomes.dropna(subset=[column])
    if done.empty:
        return pd.DataFrame()
    grouped = done.groupby(group_by)
    summary = pd.DataFrame(
        {
            "calls": grouped.size(),
            "avg_return": grouped[f"ret_{horizon}"].mean(),
            "avg_vs_spy": grouped[column].mean(),
            "beat_spy_rate": grouped[column].apply(lambda s: (s > 0).mean()),
        }
    )
    return summary.reset_index().sort_values("avg_vs_spy", ascending=False)


def _daily(series: pd.Series | None) -> pd.Series | None:
    if series is None or len(series) == 0:
        return None
    index = pd.DatetimeIndex(series.index)
    if index.tz is not None:
        index = index.tz_localize(None)
    return pd.Series(series.values, index=index.normalize()).sort_index().dropna()


def _forward_return(closes: pd.Series | None, start: str, days: int) -> float | None:
    if closes is None:
        return None
    after = closes[closes.index >= pd.Timestamp(start)]
    if len(after) <= days:
        return None
    base = float(after.iloc[0])
    return float(after.iloc[days]) / base - 1 if base else None
