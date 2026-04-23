"""Watchlist ranking and row assembly for Trend Lens."""

from __future__ import annotations

from dataclasses import dataclass

from services.advisor import PositionInputs, build_position_advice
from services.catalysts import CatalystSummary, get_catalyst_summary
from services.market_data import StockSnapshot, get_stock_snapshot
from services.scoring import build_score_bundle, finalize_total_score


@dataclass
class WatchlistEntry:
    """A lightweight user-managed watchlist item."""

    ticker: str
    note: str = ""
    shares_owned: float = 0.0
    average_cost_basis: float = 0.0


@dataclass
class WatchlistRow:
    """A ranked watchlist row with dashboard-ready fields."""

    ticker: str
    company_name: str
    current_price: float | None
    total_score: float
    technical_score: float
    fundamental_score: float
    setup_type: str
    recommendation: str
    confidence: str
    catalyst_bias: str
    note: str
    shares_owned: float
    current_allocation_pct: float | None
    room_to_add: float | None


RECOMMENDATION_PRIORITY = {
    "Add": 6,
    "Add on Pullback": 5,
    "Add Small": 4,
    "Hold": 3,
    "Trim": 2,
    "Avoid New Buy": 1,
}

CONFIDENCE_PRIORITY = {
    "High": 3,
    "Medium": 2,
    "Low": 1,
}

CATALYST_PRIORITY = {
    "Positive": 3,
    "Neutral": 2,
    "Caution": 1,
}


def build_watchlist_row(entry: WatchlistEntry, base_inputs: PositionInputs) -> WatchlistRow | None:
    """Build a single watchlist row by reusing the main scoring and advisor pipeline."""
    snapshot = get_stock_snapshot(entry.ticker)
    if snapshot.error:
        return None

    effective_inputs = PositionInputs(
        total_portfolio_value=base_inputs.total_portfolio_value,
        shares_owned=entry.shares_owned,
        average_cost_basis=entry.average_cost_basis,
        max_portfolio_allocation_pct=base_inputs.max_portfolio_allocation_pct,
        cash_available_to_deploy=base_inputs.cash_available_to_deploy,
        target_position_size_pct=base_inputs.target_position_size_pct,
    )
    scores = build_score_bundle(snapshot)
    advice = build_position_advice(snapshot, scores, effective_inputs)
    scores = finalize_total_score(scores, advice.score)
    catalyst = get_catalyst_summary(entry.ticker, snapshot)
    return _row_from_pipeline(entry, snapshot, scores, advice, catalyst)


def _row_from_pipeline(entry: WatchlistEntry, snapshot: StockSnapshot, scores, advice, catalyst: CatalystSummary) -> WatchlistRow:
    return WatchlistRow(
        ticker=snapshot.metadata.symbol,
        company_name=snapshot.metadata.short_name or snapshot.metadata.symbol,
        current_price=snapshot.latest_price or snapshot.metadata.current_price,
        total_score=scores.total_score,
        technical_score=scores.technical.score,
        fundamental_score=scores.fundamental.score,
        setup_type=scores.technical.setup.label if scores.technical.setup else "Mixed Setup",
        recommendation=advice.recommendation,
        confidence=scores.confidence,
        catalyst_bias=catalyst.bias,
        note=entry.note,
        shares_owned=entry.shares_owned,
        current_allocation_pct=advice.metrics.current_allocation_pct,
        room_to_add=advice.metrics.remaining_room_to_add,
    )


def rank_watchlist_rows(rows: list[WatchlistRow]) -> list[WatchlistRow]:
    """Default ranking for actionable watchlist review."""
    return sorted(
        rows,
        key=lambda row: (
            row.total_score,
            RECOMMENDATION_PRIORITY.get(row.recommendation, 0),
            CONFIDENCE_PRIORITY.get(row.confidence, 0),
            CATALYST_PRIORITY.get(row.catalyst_bias, 0),
        ),
        reverse=True,
    )
