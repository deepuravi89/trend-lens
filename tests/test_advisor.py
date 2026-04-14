"""Tests for portfolio-aware position advisor math."""

from __future__ import annotations

import pandas as pd

from services.advisor import PositionInputs, build_position_advice
from services.market_data import StockMetadata, StockSnapshot
from services.scoring import build_score_bundle


def make_snapshot(price: float = 100.0) -> StockSnapshot:
    frame = pd.DataFrame(
        {
            "Open": [98.0, 99.0, price],
            "Close": [99.0, 101.0, price],
            "Volume": [1_000_000, 1_100_000, 1_400_000],
            "SMA_50": [90.0, 92.0, 95.0],
            "SMA_200": [80.0, 81.0, 85.0],
            "AVG_VOLUME_20": [1_000_000, 1_000_000, 1_000_000],
            "RSI_14": [55.0, 58.0, 57.0],
            "MACD": [1.0, 1.2, 1.6],
            "MACD_SIGNAL": [0.8, 1.0, 1.2],
            "MACD_HIST": [0.2, 0.2, 0.4],
            "DIST_FROM_50DMA": [0.10, 0.10, (price / 95.0) - 1],
            "DIST_FROM_200DMA": [0.23, 0.24, (price / 85.0) - 1],
        }
    )
    metadata = StockMetadata(
        symbol="TEST",
        short_name="Test Corp",
        summary="Test summary",
        exchange="NASDAQ",
        current_price=price,
        market_cap=None,
        day_change_pct=0.01,
        fundamentals={
            "trailingPE": 18.0,
            "forwardPE": 17.0,
            "pegRatio": 1.2,
            "returnOnEquity": 0.2,
            "debtToEquity": 0.4,
            "revenueGrowth": 0.12,
            "earningsGrowth": 0.14,
            "freeCashflow": 1_000_000_000,
            "operatingCashflow": 1_200_000_000,
            "grossMargins": 0.45,
            "operatingMargins": 0.22,
            "profitMargins": 0.18,
        },
    )
    return StockSnapshot(metadata=metadata, history=frame, latest_price=price)


def test_position_advisor_uses_total_portfolio_value() -> None:
    snapshot = make_snapshot(price=100.0)
    scores = build_score_bundle(snapshot)
    advice = build_position_advice(
        snapshot,
        scores,
        PositionInputs(
            total_portfolio_value=100_000,
            shares_owned=20,
            average_cost_basis=80,
            max_portfolio_allocation_pct=10,
            cash_available_to_deploy=5_000,
            target_position_size_pct=8,
        ),
    )

    assert advice.math.current_position_value == 2_000
    assert advice.math.current_allocation_pct == 0.02
    assert advice.math.target_max_position_value == 10_000
    assert advice.math.remaining_room_to_add == 8_000
    assert advice.math.estimated_shares_can_add_with_cash == 50
    assert advice.math.estimated_shares_can_add_with_allocation_limit == 80


def test_position_advisor_suggests_small_add_under_target() -> None:
    snapshot = make_snapshot(price=100.0)
    scores = build_score_bundle(snapshot)
    advice = build_position_advice(
        snapshot,
        scores,
        PositionInputs(
            total_portfolio_value=100_000,
            shares_owned=20,
            average_cost_basis=90,
            max_portfolio_allocation_pct=10,
            cash_available_to_deploy=2_000,
            target_position_size_pct=6,
        ),
    )

    assert advice.recommendation in {"Add", "Add Small", "Add on Pullback"}
    assert advice.math.suggested_shares_to_add_now >= 0
