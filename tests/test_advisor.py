"""Tests for portfolio-aware position advisor math."""

from __future__ import annotations

import pandas as pd

from services.advisor import PositionInputs, base_quality_pct, build_position_advice, derive_position_metrics
from services.market_data import StockMetadata, StockSnapshot
from services.scoring import build_score_bundle


def make_snapshot(price: float = 100.0, rsi: float = 57.0, dist_from_50: float | None = None) -> StockSnapshot:
    if dist_from_50 is None:
        dist_from_50 = (price / 95.0) - 1
    frame = pd.DataFrame(
        {
            "Open": [98.0, 99.0, price],
            "Close": [99.0, 101.0, price],
            "Volume": [1_000_000, 1_100_000, 1_400_000],
            "SMA_50": [90.0, 92.0, 95.0],
            "SMA_200": [80.0, 81.0, 85.0],
            "AVG_VOLUME_20": [1_000_000, 1_000_000, 1_000_000],
            "RSI_14": [55.0, 58.0, rsi],
            "MACD": [1.0, 1.2, 1.6],
            "MACD_SIGNAL": [0.8, 1.0, 1.2],
            "MACD_HIST": [0.2, 0.2, 0.4],
            "DIST_FROM_50DMA": [0.10, 0.10, dist_from_50],
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


def make_inputs(**overrides: float | None) -> PositionInputs:
    base = dict(
        total_portfolio_value=100_000,
        shares_owned=20,
        average_cost_basis=80,
        max_portfolio_allocation_pct=10,
        cash_available_to_deploy=5_000,
        target_position_size_pct=8,
    )
    base.update(overrides)
    return PositionInputs(**base)


def test_current_allocation_math() -> None:
    metrics = derive_position_metrics(100.0, make_inputs())
    assert metrics.current_position_value == 2_000
    assert metrics.current_allocation_pct == 0.02


def test_remaining_room_and_cash_limited_add() -> None:
    metrics = derive_position_metrics(100.0, make_inputs())
    assert metrics.target_max_position_value == 10_000
    assert metrics.remaining_room_to_add == 8_000
    assert metrics.cash_limited_add_amount == 5_000
    assert metrics.estimated_shares_can_add == 50


def test_gain_loss_calculations() -> None:
    metrics = derive_position_metrics(100.0, make_inputs())
    assert metrics.unrealized_gain_loss_dollars == 400
    assert round(metrics.unrealized_gain_loss_pct or 0, 4) == 0.25


def test_recommendation_for_strong_underweight_setup() -> None:
    snapshot = make_snapshot(price=100.0, rsi=55.0, dist_from_50=0.03)
    scores = build_score_bundle(snapshot)
    advice = build_position_advice(snapshot, scores, make_inputs(shares_owned=5, target_position_size_pct=6))

    assert advice.technical_setup.label == "Strong Uptrend"
    assert advice.recommendation == "Add"
    assert advice.metrics.estimated_shares_can_add > 0
    assert "Strong Uptrend" in advice.decision_basis
    assert "room" in advice.explanation.lower()


def test_recommendation_for_extended_but_strong_setup() -> None:
    snapshot = make_snapshot(price=110.0, rsi=74.0, dist_from_50=0.12)
    scores = build_score_bundle(snapshot)
    advice = build_position_advice(snapshot, scores, make_inputs(shares_owned=5, average_cost_basis=90))

    assert advice.technical_setup.label == "Constructive but Extended"
    assert advice.recommendation == "Add on Pullback"
    assert "entry quality" in advice.explanation.lower()
    assert "Constructive but Extended" in advice.decision_basis


def test_recommendation_for_recovery_setup() -> None:
    snapshot = make_snapshot(price=98.0, rsi=47.0, dist_from_50=0.01)
    snapshot.history.loc[:, "SMA_50"] = [94.0, 95.0, 97.0]
    snapshot.history.loc[:, "SMA_200"] = [105.0, 104.0, 103.0]
    scores = build_score_bundle(snapshot)
    advice = build_position_advice(snapshot, scores, make_inputs(shares_owned=5, average_cost_basis=92))

    assert advice.technical_setup.label == "Recovery Setup"
    assert advice.recommendation in {"Add Small", "Hold"}
    assert "Recovery Setup" in advice.decision_basis


def test_recommendation_for_oversized_weak_setup() -> None:
    snapshot = make_snapshot(price=82.0, rsi=34.0, dist_from_50=-0.09)
    snapshot.history.loc[:, "SMA_50"] = [92.0, 91.0, 90.0]
    snapshot.history.loc[:, "SMA_200"] = [108.0, 106.0, 104.0]
    snapshot.history.loc[:, "MACD"] = [-0.6, -0.8, -1.0]
    snapshot.history.loc[:, "MACD_SIGNAL"] = [-0.4, -0.5, -0.7]
    snapshot.history.loc[:, "MACD_HIST"] = [-0.2, -0.3, -0.3]
    scores = build_score_bundle(snapshot)
    advice = build_position_advice(snapshot, scores, make_inputs(shares_owned=150, average_cost_basis=95))

    assert advice.technical_setup.label == "Weak Downtrend"
    assert advice.recommendation == "Trim"
    assert "oversized" in advice.explanation.lower() or "size" in advice.explanation.lower()
    assert "Weak Downtrend" in advice.decision_basis


def test_missing_portfolio_value_limits_allocation_math() -> None:
    snapshot = make_snapshot(price=100.0)
    scores = build_score_bundle(snapshot)
    advice = build_position_advice(snapshot, scores, make_inputs(total_portfolio_value=0))

    assert advice.metrics.current_allocation_pct is None
    assert "Allocation math is unavailable" in advice.bullets[0]
    assert advice.score <= 5


def test_target_position_is_clamped_to_max_cap() -> None:
    metrics = derive_position_metrics(100.0, make_inputs(target_position_size_pct=15, max_portfolio_allocation_pct=10))
    assert metrics.target_position_size_pct == 10
    assert metrics.target_was_clamped is True


# --- v5 regressions -------------------------------------------------------


def with_fundamental_score(scores, value: float):
    from dataclasses import replace

    return replace(scores, fundamental=replace(scores.fundamental, score=value))


def test_add_threshold_uses_80_point_base() -> None:
    # 36 technical + 29 fundamental = 65 of 80 (81%). Before v5 this was compared
    # against 72 "out of 100" and always came back Hold.
    snapshot = make_snapshot(price=100.0, rsi=55.0, dist_from_50=0.03)
    scores = with_fundamental_score(build_score_bundle(snapshot), 29.0)
    scores = replace_technical(scores, 36.0)
    advice = build_position_advice(snapshot, scores, make_inputs(shares_owned=0, average_cost_basis=0, target_position_size_pct=None))

    assert base_quality_pct(scores) == 81.25
    assert advice.technical_setup.label == "Strong Uptrend"
    assert advice.recommendation in {"Add", "Add Small"}


def replace_technical(scores, value: float):
    from dataclasses import replace

    return replace(scores, technical=replace(scores.technical, score=value))


def test_position_score_does_not_double_count_stock_quality() -> None:
    snapshot = make_snapshot(price=100.0, rsi=55.0, dist_from_50=0.03)
    base = build_score_bundle(snapshot)
    inputs = make_inputs(shares_owned=5, target_position_size_pct=6)

    strong = build_position_advice(snapshot, with_fundamental_score(base, 38.0), inputs)
    weak = build_position_advice(snapshot, with_fundamental_score(base, 12.0), inputs)

    assert strong.score == weak.score
    assert strong.score <= 20
    assert all(driver.label != "Score quality" for driver in strong.score_drivers)


def test_trim_large_gain_at_full_size_when_extended() -> None:
    snapshot = make_snapshot(price=110.0, rsi=74.0, dist_from_50=0.12)
    scores = build_score_bundle(snapshot)
    # 70 shares x $110 = 7.7% of the portfolio against an 8% target, up 37%.
    advice = build_position_advice(snapshot, scores, make_inputs(shares_owned=70, average_cost_basis=80))

    assert advice.recommendation == "Trim"
    assert "gain" in advice.explanation.lower()


def make_weak_snapshot() -> StockSnapshot:
    snapshot = make_snapshot(price=82.0, rsi=34.0, dist_from_50=-0.09)
    snapshot.history.loc[:, "SMA_50"] = [92.0, 91.0, 90.0]
    snapshot.history.loc[:, "SMA_200"] = [108.0, 106.0, 104.0]
    snapshot.history.loc[:, "MACD"] = [-0.6, -0.8, -1.0]
    snapshot.history.loc[:, "MACD_SIGNAL"] = [-0.4, -0.5, -0.7]
    snapshot.history.loc[:, "MACD_HIST"] = [-0.2, -0.3, -0.3]
    return snapshot


def test_trim_holder_when_trend_and_fundamentals_are_weak() -> None:
    snapshot = make_weak_snapshot()
    scores = with_fundamental_score(build_score_bundle(snapshot), 15.0)

    holder = build_position_advice(snapshot, scores, make_inputs(shares_owned=10, average_cost_basis=95))
    newcomer = build_position_advice(snapshot, scores, make_inputs(shares_owned=0, average_cost_basis=0))

    assert holder.recommendation == "Trim"
    assert newcomer.recommendation == "Avoid New Buy"


def test_weak_trend_with_solid_fundamentals_is_not_trimmed() -> None:
    snapshot = make_weak_snapshot()
    scores = with_fundamental_score(build_score_bundle(snapshot), 30.0)
    advice = build_position_advice(snapshot, scores, make_inputs(shares_owned=10, average_cost_basis=95))

    assert advice.recommendation == "Avoid New Buy"
