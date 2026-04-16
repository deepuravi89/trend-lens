"""Central scoring thresholds, weights, and app copy."""

from __future__ import annotations

SCORE_WEIGHTS = {
    "technical": 40,
    "fundamental": 40,
    "position": 20,
}

TECHNICAL_FACTORS = {
    "price_vs_200dma": 8,
    "price_vs_50dma": 7,
    "trend_alignment": 6,
    "rsi": 7,
    "macd": 5,
    "volume": 4,
    "distance_context": 3,
}

TECHNICAL_THRESHOLDS = {
    "rsi_oversold": 30,
    "rsi_neutral_low": 40,
    "rsi_neutral_high": 60,
    "rsi_extended": 70,
    "rsi_recovery_floor": 42,
    "rsi_weak_floor": 40,
    "volume_ratio_bullish": 1.1,
    "volume_ratio_weak": 0.9,
    "extended_above_50dma_pct": 0.08,
    "extended_above_200dma_pct": 0.18,
    "pullback_above_50dma_pct": -0.03,
}

FUNDAMENTAL_FACTORS = {
    "trailing_pe": 5,
    "forward_pe": 5,
    "peg_ratio": 4,
    "roe": 5,
    "debt_to_equity": 4,
    "revenue_growth": 4,
    "earnings_growth": 4,
    "cash_flow": 3,
    "margins": 4,
    "data_completeness": 2,
}

FUNDAMENTAL_THRESHOLDS = {
    "pe_low": 20,
    "pe_fair": 30,
    "forward_pe_low": 18,
    "forward_pe_fair": 28,
    "peg_good": 1.5,
    "peg_ok": 2.5,
    "roe_strong": 0.18,
    "roe_ok": 0.12,
    "debt_to_equity_low": 0.8,
    "debt_to_equity_ok": 1.5,
    "growth_strong": 0.15,
    "growth_ok": 0.05,
    "margin_strong": 0.2,
    "margin_ok": 0.1,
    "margin_floor": 0.0,
}

POSITION_THRESHOLDS = {
    "extended_rsi": 68,
    "extended_above_50dma_pct": 0.08,
    "trim_gain_pct": 0.2,
    "deep_drawdown_pct": -0.12,
    "small_add_fraction": 0.35,
    "min_add_score": 72,
    "strong_add_score": 82,
    "hold_floor": 58,
    "trim_floor": 45,
    "oversized_buffer_pct": 0.002,
    "near_target_buffer_pct": 0.85,
    "limited_room_pct_of_portfolio": 0.015,
}

CONFIDENCE_THRESHOLDS = {
    "high_alignment_ratio": 0.72,
    "medium_alignment_ratio": 0.5,
    "high_completeness_ratio": 0.8,
    "medium_completeness_ratio": 0.55,
}

VERDICT_BANDS = {
    "Strong Buy Zone": 85,
    "Buy on Pullback": 72,
    "Hold": 58,
    "Trim Watch": 45,
    "Avoid": 0,
}

APP_COPY = {
    "detailed_explainer": (
        "Trend Lens scores the current setup with explicit factor contributions so you can see "
        "where conviction comes from and where missing or noisy data lowers confidence."
    ),
    "position_help": (
        "Use total portfolio value and your max allocation limit to keep sizing grounded in your "
        "actual portfolio rather than a rough cash proxy. The position panel then estimates how "
        "much room you have to add before hitting your cap."
    ),
}
