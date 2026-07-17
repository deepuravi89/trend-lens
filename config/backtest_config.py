"""Configuration for the Strategy Lab / Backtest Lab."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyTemplate:
    """A simple backtest strategy definition for the lab."""

    key: str
    label: str
    description: str


STRATEGY_TEMPLATES = [
    StrategyTemplate(
        key="strong_uptrend",
        label="Strong Uptrend",
        description="Enter when the chart is classified as Strong Uptrend.",
    ),
    StrategyTemplate(
        key="recovery_setup",
        label="Recovery Setup",
        description="Enter when the chart is classified as Recovery Setup.",
    ),
    StrategyTemplate(
        key="pullback_in_uptrend",
        label="Pullback in Uptrend",
        description="Enter when long-term trend is strong and price pulls back near the 50DMA without looking broken.",
    ),
    StrategyTemplate(
        key="momentum_confirmation",
        label="Momentum Confirmation",
        description="Enter when price is above the 50DMA with healthy RSI and bullish MACD confirmation.",
    ),
    StrategyTemplate(
        key="avoid_weakness_baseline",
        label="Avoid Weakness Baseline",
        description="Measure what usually happened next after Weak Downtrend setups for comparison.",
    ),
]


DEFAULT_BACKTESTS = {
    "years": 5,
    "holding_period_days": 20,
    "initial_capital": 10000.0,
    "trade_size_pct": 100.0,
    "slippage_pct": 0.1,
    "warmup_days": 320,
}


BACKTEST_THRESHOLDS = {
    "pullback_near_50dma_pct": 0.03,
    "extended_above_50dma_pct": 0.08,
}


BACKTEST_COPY = {
    "assumptions": (
        "Assumes next-day entries after a signal, long-only trades, no taxes, and simplified slippage and exit handling. "
        "Use the lab as historical context for research and education, not as a forecast."
    ),
    "warnings": [
        "Backtests can make a strategy look cleaner than real life.",
        "Past results are not a prediction of future performance.",
        "Daily-bar exits and simplified slippage do not capture every real-world trading detail.",
    ],
}
