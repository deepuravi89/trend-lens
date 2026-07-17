"""Tests for the Strategy Lab backtesting service."""

from __future__ import annotations

from datetime import date

import pandas as pd

from services.backtesting import (
    BacktestConfig,
    calculate_max_drawdown,
    generate_strategy_signals,
    prepare_backtest_frame,
    run_backtest,
    validate_backtest_config,
)


def make_history(rows: list[dict[str, float]]) -> pd.DataFrame:
    index = pd.date_range("2024-01-02", periods=len(rows), freq="B")
    frame = pd.DataFrame(rows, index=index)
    frame["DIST_FROM_50DMA"] = frame["Close"] / frame["SMA_50"] - 1
    frame["DIST_FROM_200DMA"] = frame["Close"] / frame["SMA_200"] - 1
    return frame


def strong_row(close: float = 110.0, open_: float = 110.0, high: float = 112.0, low: float = 109.0) -> dict[str, float]:
    return {
        "Open": open_,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": 1_000_000,
        "SMA_50": 105.0,
        "SMA_200": 100.0,
        "RSI_14": 55.0,
        "MACD": 1.2,
        "MACD_SIGNAL": 0.8,
        "MACD_HIST": 0.4,
    }


def weak_row(close: float = 90.0, open_: float = 90.0, high: float = 91.0, low: float = 88.0) -> dict[str, float]:
    return {
        "Open": open_,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": 1_000_000,
        "SMA_50": 95.0,
        "SMA_200": 100.0,
        "RSI_14": 35.0,
        "MACD": -1.0,
        "MACD_SIGNAL": -0.4,
        "MACD_HIST": -0.6,
    }


def make_config(strategy_name: str = "Strong Uptrend", **overrides) -> BacktestConfig:
    config = BacktestConfig(
        ticker="TEST",
        strategy_name=strategy_name,
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 31),
        holding_period_days=2,
        initial_capital=10000.0,
        trade_size_pct=100.0,
        stop_loss_pct=None,
        take_profit_pct=None,
        slippage_pct=0.0,
    )
    for key, value in overrides.items():
        setattr(config, key, value)
    return config


def test_validate_backtest_config_flags_invalid_values() -> None:
    issues = validate_backtest_config(
        BacktestConfig(
            ticker="",
            strategy_name="Strong Uptrend",
            start_date=date(2024, 2, 1),
            end_date=date(2024, 1, 1),
            holding_period_days=0,
            initial_capital=0.0,
            trade_size_pct=120.0,
            slippage_pct=-1.0,
        )
    )
    assert len(issues) >= 5


def test_strong_uptrend_signal_generation() -> None:
    frame = prepare_backtest_frame(make_history([strong_row(), strong_row(), strong_row()]), date(2024, 1, 2), date(2024, 1, 31))
    signals = generate_strategy_signals(frame, "Strong Uptrend")
    assert signals.any()


def test_holding_period_exit_generates_trade() -> None:
    history = make_history([strong_row(), strong_row(111), strong_row(112), strong_row(113), strong_row(114)])
    result = run_backtest(make_config(), history=history)
    assert result.error is None
    assert result.trades
    assert result.trades[0].exit_reason == "Time Exit"


def test_stop_loss_exit() -> None:
    history = make_history(
        [
            strong_row(),
            strong_row(open_=110, high=111, low=107, close=108),
            strong_row(open_=108, high=109, low=100, close=101),
            strong_row(open_=101, high=102, low=99, close=100),
        ]
    )
    result = run_backtest(make_config(stop_loss_pct=2.0, holding_period_days=5), history=history)
    assert result.trades
    assert result.trades[0].exit_reason == "Stop Loss"


def test_take_profit_exit() -> None:
    history = make_history(
        [
            strong_row(),
            strong_row(open_=110, high=115, low=109, close=114),
            strong_row(open_=114, high=116, low=113, close=115),
            strong_row(open_=115, high=116, low=114, close=115),
        ]
    )
    result = run_backtest(make_config(take_profit_pct=3.0, holding_period_days=5), history=history)
    assert result.trades
    assert result.trades[0].exit_reason == "Take Profit"


def test_max_drawdown_calculation() -> None:
    curve = pd.DataFrame({"Date": pd.date_range("2024-01-01", periods=4), "Equity": [10000, 11000, 9000, 9500]})
    assert round(calculate_max_drawdown(curve), 4) == -0.1818


def test_no_trade_scenario() -> None:
    history = make_history([weak_row(), weak_row(), weak_row(), weak_row()])
    result = run_backtest(make_config(strategy_name="Momentum Confirmation"), history=history)
    assert result.error is None
    assert result.trades == []


def test_missing_data_is_handled_gracefully() -> None:
    history = pd.DataFrame({"Close": [1, 2, 3]}, index=pd.date_range("2024-01-01", periods=3))
    result = run_backtest(make_config(), history=history)
    assert result.error is not None
