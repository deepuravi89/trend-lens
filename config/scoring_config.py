"""Central scoring thresholds and copy."""

from __future__ import annotations

SCORE_WEIGHTS = {
    "technical": 40,
    "fundamental": 40,
    "position": 20,
}

TECHNICAL_THRESHOLDS = {
    "rsi_oversold": 30,
    "rsi_caution": 70,
    "rsi_healthy_low": 40,
    "rsi_healthy_high": 60,
    "volume_ratio_bullish": 1.1,
    "volume_ratio_weak": 0.9,
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
}

VERDICT_BANDS = {
    "Strong Buy Zone": 85,
    "Buy on Pullback": 72,
    "Hold": 58,
    "Trim Watch": 45,
    "Avoid": 0,
}

POSITION_THRESHOLDS = {
    "extended_rsi": 68,
    "extended_above_50dma_pct": 0.08,
    "deep_drawdown_pct": -0.12,
    "target_buffer_pct": 0.9,
}

APP_COPY = {
    "detailed_explainer": (
        "The dashboard combines a simple, transparent rule set with live market data. "
        "Every section degrades gracefully when inputs are missing, so the app stays useful even "
        "when fundamentals are sparse."
    ),
}
