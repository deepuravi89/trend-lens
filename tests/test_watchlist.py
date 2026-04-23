"""Tests for watchlist ranking behavior."""

from __future__ import annotations

from services.watchlist import WatchlistRow, rank_watchlist_rows


def make_row(
    ticker: str,
    *,
    total_score: float,
    recommendation: str,
    confidence: str,
    catalyst_bias: str,
) -> WatchlistRow:
    return WatchlistRow(
        ticker=ticker,
        company_name=ticker,
        current_price=100.0,
        total_score=total_score,
        technical_score=30.0,
        fundamental_score=30.0,
        setup_type="Strong Uptrend",
        recommendation=recommendation,
        confidence=confidence,
        catalyst_bias=catalyst_bias,
        note="",
        shares_owned=0.0,
        current_allocation_pct=None,
        room_to_add=None,
    )


def test_rank_watchlist_rows_prefers_higher_score_then_action_quality() -> None:
    rows = [
        make_row("AAA", total_score=82, recommendation="Add Small", confidence="High", catalyst_bias="Neutral"),
        make_row("BBB", total_score=84, recommendation="Hold", confidence="High", catalyst_bias="Positive"),
        make_row("CCC", total_score=84, recommendation="Add on Pullback", confidence="Medium", catalyst_bias="Neutral"),
    ]
    ranked = rank_watchlist_rows(rows)
    assert [row.ticker for row in ranked] == ["CCC", "BBB", "AAA"]


def test_rank_watchlist_rows_uses_confidence_and_catalyst_as_tiebreakers() -> None:
    rows = [
        make_row("AAA", total_score=80, recommendation="Hold", confidence="Medium", catalyst_bias="Neutral"),
        make_row("BBB", total_score=80, recommendation="Hold", confidence="High", catalyst_bias="Neutral"),
        make_row("CCC", total_score=80, recommendation="Hold", confidence="High", catalyst_bias="Positive"),
    ]
    ranked = rank_watchlist_rows(rows)
    assert [row.ticker for row in ranked] == ["CCC", "BBB", "AAA"]
