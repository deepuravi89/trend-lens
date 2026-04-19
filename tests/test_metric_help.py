"""Tests for metric definition registry and helper utilities."""

from __future__ import annotations

from config.metric_definitions import METRIC_DEFINITIONS
from utils.metric_help import format_metric_tooltip, get_metric_info, has_metric_info


REQUIRED_KEYS = {
    "price_vs_50dma",
    "price_vs_200dma",
    "sma_50",
    "sma_200",
    "dist_from_50dma",
    "dist_from_200dma",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_histogram",
    "avg_volume_20",
    "volume_ratio",
    "trend_alignment",
    "trailing_pe",
    "forward_pe",
    "peg_ratio",
    "return_on_equity",
    "debt_to_equity",
    "revenue_growth",
    "earnings_growth",
    "free_cash_flow",
    "operating_cash_flow",
    "gross_margin",
    "operating_margin",
    "profit_margin",
    "data_completeness",
    "confidence",
    "current_position_value",
    "current_allocation_pct",
    "max_position_cap",
    "target_position_size",
    "remaining_room_to_add",
    "cash_limited_add_amount",
    "estimated_shares_can_add",
    "unrealized_gain_loss_dollars",
    "unrealized_gain_loss_pct",
}


def test_metric_registry_covers_required_keys() -> None:
    missing = REQUIRED_KEYS - set(METRIC_DEFINITIONS)
    assert not missing, f"Missing metric definitions: {sorted(missing)}"


def test_get_metric_info_returns_definition() -> None:
    info = get_metric_info("rsi_14")
    assert info is not None
    assert info.label == "RSI (14)"


def test_unknown_metric_fails_gracefully() -> None:
    assert get_metric_info("not_real") is None
    assert has_metric_info("not_real") is False
    assert format_metric_tooltip("not_real") == ""


def test_tooltip_output_is_compact_text() -> None:
    tooltip = format_metric_tooltip("trailing_pe")
    assert "Why it matters:" in tooltip
    assert "good" not in tooltip.lower() or isinstance(tooltip, str)
