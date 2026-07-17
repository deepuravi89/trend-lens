"""Simple historical strategy testing for Trend Lens."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

import pandas as pd

from config.backtest_config import BACKTEST_THRESHOLDS
from services.market_data import get_history_with_indicators
from services.scoring import TechnicalSetup, classify_technical_setup_from_row


@dataclass
class BacktestConfig:
    """User-configurable backtest inputs."""

    ticker: str
    strategy_name: str
    start_date: date
    end_date: date
    holding_period_days: int
    initial_capital: float
    trade_size_pct: float
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None
    slippage_pct: float = 0.1


@dataclass
class TradeResult:
    """One completed historical trade."""

    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_price: float
    exit_price: float
    return_pct: float
    pnl: float
    exit_reason: str
    setup_label: str
    holding_days: int


@dataclass
class BacktestResult:
    """Aggregate result for a backtest run."""

    strategy_name: str
    trades: list[TradeResult]
    win_rate: float
    average_return: float
    median_return: float
    max_drawdown: float
    best_trade: float
    worst_trade: float
    average_holding_days: float
    profit_factor: float | None
    final_equity: float
    benchmark_return: float | None
    equity_curve: pd.DataFrame
    signal_frame: pd.DataFrame
    error: str | None = None


def validate_backtest_config(config: BacktestConfig) -> list[str]:
    """Return user-facing validation issues for a backtest request."""
    issues: list[str] = []
    if not config.ticker.strip():
        issues.append("Enter a ticker before running the Strategy Lab.")
    if config.end_date <= config.start_date:
        issues.append("End date must be after the start date.")
    if config.holding_period_days <= 0:
        issues.append("Holding period must be at least 1 trading day.")
    if config.initial_capital <= 0:
        issues.append("Initial capital must be greater than zero.")
    if config.trade_size_pct <= 0 or config.trade_size_pct > 100:
        issues.append("Trade size must be between 0 and 100 percent.")
    if config.stop_loss_pct is not None and config.stop_loss_pct <= 0:
        issues.append("Stop loss must be positive when enabled.")
    if config.take_profit_pct is not None and config.take_profit_pct <= 0:
        issues.append("Take profit must be positive when enabled.")
    if config.slippage_pct < 0:
        issues.append("Slippage cannot be negative.")
    return issues


def run_backtest(config: BacktestConfig, history: pd.DataFrame | None = None) -> BacktestResult:
    """Run a simple long-only backtest over daily bars."""
    issues = validate_backtest_config(config)
    if issues:
        return BacktestResult(
            strategy_name=config.strategy_name,
            trades=[],
            win_rate=0.0,
            average_return=0.0,
            median_return=0.0,
            max_drawdown=0.0,
            best_trade=0.0,
            worst_trade=0.0,
            average_holding_days=0.0,
            profit_factor=None,
            final_equity=config.initial_capital,
            benchmark_return=None,
            equity_curve=pd.DataFrame(),
            signal_frame=pd.DataFrame(),
            error=" ".join(issues),
        )

    if history is None:
        fetch_start = (config.start_date - timedelta(days=320)).isoformat()
        fetch_end = (config.end_date + timedelta(days=1)).isoformat()
        history = get_history_with_indicators(config.ticker, start=fetch_start, end=fetch_end)

    frame = prepare_backtest_frame(history, config.start_date, config.end_date)
    if frame.empty or len(frame) < 3:
        return _empty_backtest_result(config, "Not enough daily history was available for this backtest range.")

    signal_series = generate_strategy_signals(frame, config.strategy_name)
    cash = config.initial_capital
    active_trade: dict[str, object] | None = None
    trades: list[TradeResult] = []
    equity_rows: list[dict[str, object]] = []

    for idx, (trade_date, row) in enumerate(frame.iterrows()):
        if active_trade is None and idx > 0 and bool(signal_series.iloc[idx - 1]):
            active_trade = _enter_trade(config, frame.iloc[idx], trade_date, cash)
            cash = float(active_trade["cash_reserve"])

        if active_trade is not None:
            exit_payload = _maybe_exit_trade(config, row, trade_date, active_trade)
            if exit_payload is not None:
                trade = _finalize_trade(active_trade, exit_payload)
                trades.append(trade)
                cash = float(exit_payload["cash_after_exit"])
                active_trade = None

        equity_value = cash
        if active_trade is not None:
            equity_value += float(active_trade["shares"]) * float(row["Close"])
            active_trade["bars_held"] = int(active_trade["bars_held"]) + 1

        equity_rows.append({"Date": trade_date, "Equity": equity_value})

    if active_trade is not None:
        final_row = frame.iloc[-1]
        exit_payload = {
            "exit_date": frame.index[-1],
            "exit_price": float(final_row["Close"]) * (1 - config.slippage_pct / 100),
            "exit_reason": "End of Test",
            "cash_after_exit": cash + float(active_trade["shares"]) * float(final_row["Close"]) * (1 - config.slippage_pct / 100),
        }
        trades.append(_finalize_trade(active_trade, exit_payload))
        cash = float(exit_payload["cash_after_exit"])
        equity_rows[-1]["Equity"] = cash

    equity_curve = pd.DataFrame(equity_rows)
    signal_frame = build_signal_frame(frame, signal_series, trades)
    return summarize_backtest(config, trades, equity_curve, frame, signal_frame)


def prepare_backtest_frame(history: pd.DataFrame, start_date: date, end_date: date) -> pd.DataFrame:
    """Prepare a filtered frame with setup labels for the requested test window."""
    if history is None or history.empty:
        return pd.DataFrame()

    frame = history.copy()
    required = {"Open", "High", "Low", "Close", "Volume", "SMA_50", "SMA_200", "RSI_14", "MACD", "MACD_SIGNAL", "MACD_HIST", "DIST_FROM_50DMA", "DIST_FROM_200DMA"}
    if not required.issubset(frame.columns):
        return pd.DataFrame()

    frame = frame.sort_index().copy()
    frame["SETUP_LABEL"] = frame.apply(lambda row: classify_technical_setup_from_row(row).label, axis=1)
    mask = (frame.index.date >= start_date) & (frame.index.date <= end_date)
    return frame.loc[mask].copy()


def generate_strategy_signals(frame: pd.DataFrame, strategy_name: str) -> pd.Series:
    """Generate a daily entry signal series for a named strategy template."""
    if frame.empty:
        return pd.Series(dtype=bool)

    if strategy_name == "Strong Uptrend":
        return frame["SETUP_LABEL"].eq("Strong Uptrend")
    if strategy_name == "Recovery Setup":
        return frame["SETUP_LABEL"].eq("Recovery Setup")
    if strategy_name == "Avoid Weakness baseline":
        return frame["SETUP_LABEL"].eq("Weak Downtrend")
    if strategy_name == "Pullback in Uptrend":
        return (
            (frame["Close"] > frame["SMA_200"])
            & (frame["SMA_50"] > frame["SMA_200"])
            & (frame["DIST_FROM_50DMA"].abs() <= BACKTEST_THRESHOLDS["pullback_near_50dma_pct"])
            & (frame["RSI_14"] < 70)
        )
    if strategy_name == "Momentum Confirmation":
        return (
            (frame["Close"] > frame["SMA_50"])
            & (frame["MACD"] > frame["MACD_SIGNAL"])
            & (frame["RSI_14"].between(40, 60))
        )
    return pd.Series(False, index=frame.index)


def build_signal_frame(frame: pd.DataFrame, signals: pd.Series, trades: list[TradeResult]) -> pd.DataFrame:
    """Attach entry and exit markers for Strategy Lab charts."""
    chart = frame[["Close", "SMA_50", "SMA_200"]].copy()
    chart["Signal"] = signals.astype(bool)
    chart["Entry"] = pd.NA
    chart["Exit"] = pd.NA
    for trade in trades:
        if trade.entry_date in chart.index:
            chart.loc[trade.entry_date, "Entry"] = trade.entry_price
        if trade.exit_date in chart.index:
            chart.loc[trade.exit_date, "Exit"] = trade.exit_price
    return chart


def calculate_max_drawdown(equity_curve: pd.DataFrame) -> float:
    """Calculate maximum drawdown from an equity curve."""
    if equity_curve.empty:
        return 0.0
    running_peak = equity_curve["Equity"].cummax()
    drawdown = equity_curve["Equity"] / running_peak - 1
    return float(drawdown.min())


def summarize_backtest(
    config: BacktestConfig,
    trades: list[TradeResult],
    equity_curve: pd.DataFrame,
    frame: pd.DataFrame,
    signal_frame: pd.DataFrame,
) -> BacktestResult:
    """Turn raw trades and equity into user-facing summary stats."""
    returns = [trade.return_pct for trade in trades]
    pnl_positive = sum(trade.pnl for trade in trades if trade.pnl > 0)
    pnl_negative = abs(sum(trade.pnl for trade in trades if trade.pnl < 0))
    benchmark_return = None
    if not frame.empty:
        benchmark_return = float(frame["Close"].iloc[-1] / frame["Close"].iloc[0] - 1)

    return BacktestResult(
        strategy_name=config.strategy_name,
        trades=trades,
        win_rate=(sum(1 for trade in trades if trade.return_pct > 0) / len(trades)) if trades else 0.0,
        average_return=float(pd.Series(returns).mean()) if returns else 0.0,
        median_return=float(pd.Series(returns).median()) if returns else 0.0,
        max_drawdown=calculate_max_drawdown(equity_curve),
        best_trade=max(returns) if returns else 0.0,
        worst_trade=min(returns) if returns else 0.0,
        average_holding_days=float(pd.Series([trade.holding_days for trade in trades]).mean()) if trades else 0.0,
        profit_factor=(pnl_positive / pnl_negative) if pnl_negative > 0 else None,
        final_equity=float(equity_curve["Equity"].iloc[-1]) if not equity_curve.empty else config.initial_capital,
        benchmark_return=benchmark_return,
        equity_curve=equity_curve,
        signal_frame=signal_frame,
    )


def _empty_backtest_result(config: BacktestConfig, error: str) -> BacktestResult:
    return BacktestResult(
        strategy_name=config.strategy_name,
        trades=[],
        win_rate=0.0,
        average_return=0.0,
        median_return=0.0,
        max_drawdown=0.0,
        best_trade=0.0,
        worst_trade=0.0,
        average_holding_days=0.0,
        profit_factor=None,
        final_equity=config.initial_capital,
        benchmark_return=None,
        equity_curve=pd.DataFrame(),
        signal_frame=pd.DataFrame(),
        error=error,
    )


def _enter_trade(config: BacktestConfig, row: pd.Series, trade_date: pd.Timestamp, cash_balance: float) -> dict[str, object]:
    entry_price = float(row["Open"]) * (1 + config.slippage_pct / 100)
    allocation = cash_balance * (config.trade_size_pct / 100)
    shares = allocation / entry_price if entry_price > 0 else 0.0
    setup = classify_technical_setup_from_row(row)
    return {
        "entry_date": trade_date,
        "entry_price": entry_price,
        "shares": shares,
        "allocated_capital": allocation,
        "cash_reserve": cash_balance - allocation,
        "bars_held": 0,
        "setup_label": setup.label,
        "stop_price": entry_price * (1 - config.stop_loss_pct / 100) if config.stop_loss_pct is not None else None,
        "take_profit_price": entry_price * (1 + config.take_profit_pct / 100) if config.take_profit_pct is not None else None,
    }


def _maybe_exit_trade(config: BacktestConfig, row: pd.Series, trade_date: pd.Timestamp, active_trade: dict[str, object]) -> dict[str, object] | None:
    low = float(row["Low"])
    high = float(row["High"])
    close = float(row["Close"])
    shares = float(active_trade["shares"])
    cash_reserve = float(active_trade["cash_reserve"])
    stop_price = active_trade["stop_price"]
    take_profit_price = active_trade["take_profit_price"]

    if stop_price is not None and low <= float(stop_price):
        exit_price = float(stop_price) * (1 - config.slippage_pct / 100)
        return {
            "exit_date": trade_date,
            "exit_price": exit_price,
            "exit_reason": "Stop Loss",
            "cash_after_exit": cash_reserve + shares * exit_price,
        }

    if take_profit_price is not None and high >= float(take_profit_price):
        exit_price = float(take_profit_price) * (1 - config.slippage_pct / 100)
        return {
            "exit_date": trade_date,
            "exit_price": exit_price,
            "exit_reason": "Take Profit",
            "cash_after_exit": cash_reserve + shares * exit_price,
        }

    if int(active_trade["bars_held"]) + 1 >= config.holding_period_days:
        exit_price = close * (1 - config.slippage_pct / 100)
        return {
            "exit_date": trade_date,
            "exit_price": exit_price,
            "exit_reason": "Time Exit",
            "cash_after_exit": cash_reserve + shares * exit_price,
        }

    return None


def _finalize_trade(active_trade: dict[str, object], exit_payload: dict[str, object]) -> TradeResult:
    entry_price = float(active_trade["entry_price"])
    exit_price = float(exit_payload["exit_price"])
    shares = float(active_trade["shares"])
    pnl = shares * (exit_price - entry_price)
    return TradeResult(
        entry_date=pd.Timestamp(active_trade["entry_date"]),
        exit_date=pd.Timestamp(exit_payload["exit_date"]),
        entry_price=entry_price,
        exit_price=exit_price,
        return_pct=(exit_price / entry_price) - 1 if entry_price else 0.0,
        pnl=pnl,
        exit_reason=str(exit_payload["exit_reason"]),
        setup_label=str(active_trade["setup_label"]),
        holding_days=int(active_trade["bars_held"]) + 1,
    )
