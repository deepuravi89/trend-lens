"""Extra context shown next to the score: earnings timing and strength vs the S&P 500.

Neither feeds into the score. They are shown separately so the score stays
comparable over time in the score history.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd
import streamlit as st
import yfinance as yf

from config.scoring_config import MARKET_CONTEXT
from services.market_data import get_history_with_indicators


@dataclass
class MarketContext:
    next_earnings_date: date | None
    days_to_earnings: int | None
    return_3m: float | None
    return_6m: float | None
    relative_3m: float | None
    relative_6m: float | None

    @property
    def earnings_soon(self) -> bool:
        return self.days_to_earnings is not None and 0 <= self.days_to_earnings <= MARKET_CONTEXT["earnings_warning_days"]

    @property
    def earnings_label(self) -> str:
        if self.next_earnings_date is None or self.days_to_earnings is None:
            return "N/A"
        when = self.next_earnings_date.strftime("%b %d")
        if self.days_to_earnings < 0:
            return f"Reported {when}"
        if self.days_to_earnings == 0:
            return "Today"
        return f"{when} ({self.days_to_earnings}d)"


@st.cache_data(ttl=21600, show_spinner=False)
def get_next_earnings_date(ticker: str) -> date | None:
    """Next scheduled earnings date from Yahoo, or None (ETFs and gaps in the feed)."""
    try:
        calendar = yf.Ticker(ticker.strip().upper()).calendar
    except Exception:
        return None
    if not isinstance(calendar, dict):
        return None
    dates = calendar.get("Earnings Date") or []
    dates = [d for d in dates if isinstance(d, date)]
    return min(dates) if dates else None


def trailing_return(close: pd.Series, trading_days: int) -> float | None:
    close = close.dropna()
    if len(close) <= trading_days:
        return None
    start = float(close.iloc[-1 - trading_days])
    return float(close.iloc[-1]) / start - 1 if start else None


def relative_return(stock_close: pd.Series, benchmark_close: pd.Series, trading_days: int) -> float | None:
    """Stock return minus benchmark return over the same dates."""
    frame = pd.concat(
        [_by_day(stock_close).rename("stock"), _by_day(benchmark_close).rename("bench")],
        axis=1,
        join="inner",
    )
    stock = trailing_return(frame["stock"], trading_days)
    bench = trailing_return(frame["bench"], trading_days)
    if stock is None or bench is None:
        return None
    return stock - bench


def _by_day(series: pd.Series) -> pd.Series:
    index = pd.DatetimeIndex(series.index)
    if index.tz is not None:
        index = index.tz_localize(None)
    return pd.Series(series.values, index=index.normalize())


def build_market_context(ticker: str, history: pd.DataFrame, today: date | None = None) -> MarketContext:
    today = today or date.today()
    earnings = get_next_earnings_date(ticker)
    days = (earnings - today).days if earnings else None

    close = history["Close"] if "Close" in history else pd.Series(dtype=float)
    benchmark = get_history_with_indicators(MARKET_CONTEXT["benchmark"], period="1y")
    bench_close = benchmark["Close"] if not benchmark.empty else None

    short, long = MARKET_CONTEXT["relative_days_short"], MARKET_CONTEXT["relative_days_long"]
    return MarketContext(
        next_earnings_date=earnings,
        days_to_earnings=days,
        return_3m=trailing_return(close, short),
        return_6m=trailing_return(close, long),
        relative_3m=relative_return(close, bench_close, short) if bench_close is not None else None,
        relative_6m=relative_return(close, bench_close, long) if bench_close is not None else None,
    )
