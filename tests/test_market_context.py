"""Tests for earnings timing and relative strength vs the S&P 500."""

from __future__ import annotations

from datetime import date

import pandas as pd

from services.market_context import MarketContext, relative_return, trailing_return


def closes(values: list[float], tz: str | None = None) -> pd.Series:
    index = pd.bdate_range("2026-01-01", periods=len(values), tz=tz)
    return pd.Series(values, index=index)


def test_trailing_return() -> None:
    series = closes([100.0] * 10 + [110.0])
    assert round(trailing_return(series, 10), 4) == 0.10
    assert trailing_return(series, 50) is None


def test_relative_return_aligns_dates_across_timezones() -> None:
    stock = closes([100.0] * 10 + [120.0], tz="America/New_York")
    bench = closes([100.0] * 10 + [105.0])
    assert round(relative_return(stock, bench, 10), 4) == 0.15


def make_context(days: int | None) -> MarketContext:
    when = date(2026, 11, 3) if days is not None else None
    return MarketContext(when, days, None, None, None, None)


def test_earnings_soon_window() -> None:
    assert make_context(3).earnings_soon
    assert make_context(0).earnings_label == "Today"
    assert not make_context(12).earnings_soon
    assert not make_context(-2).earnings_soon
    assert make_context(-2).earnings_label.startswith("Reported")
    assert make_context(None).earnings_label == "N/A"
