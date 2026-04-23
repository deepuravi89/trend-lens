"""Market data fetching and normalization via yfinance."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st
import yfinance as yf

from utils.calculations import add_indicators


@dataclass
class StockMetadata:
    """Company summary and quote fields used by the dashboard."""

    symbol: str
    short_name: str | None
    summary: str | None
    exchange: str | None
    quote_type: str | None = None
    fund_family: str | None = None
    category: str | None = None
    current_price: float | None = None
    market_cap: float | None = None
    day_change_pct: float | None = None
    fundamentals: dict[str, float | str | None] | None = None


@dataclass
class StockSnapshot:
    """Normalized market snapshot used across the app."""

    metadata: StockMetadata
    history: pd.DataFrame
    latest_price: float | None
    error: str | None = None


@dataclass
class SearchMatch:
    """Resolved ticker search result for the input experience."""

    symbol: str
    name: str
    exchange: str | None = None
    quote_type: str | None = None

    @property
    def label(self) -> str:
        exchange = f" • {self.exchange}" if self.exchange else ""
        return f"{self.symbol} — {self.name}{exchange}"


def _coerce_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _is_equity_like(quote_type: str | None) -> bool:
    return (quote_type or "").upper() in {"EQUITY", "ETF"}


def _score_match(query: str, symbol: str, name: str) -> tuple[int, int, int]:
    normalized_query = query.strip().lower()
    symbol_l = symbol.lower()
    name_l = name.lower()
    exact_symbol = int(symbol_l == normalized_query)
    starts_symbol = int(symbol_l.startswith(normalized_query))
    name_contains = int(normalized_query in name_l)
    return (exact_symbol, starts_symbol, name_contains)


@st.cache_data(ttl=900, show_spinner=False)
def search_tickers(query: str) -> list[SearchMatch]:
    """Return likely ticker matches for a company name or symbol query."""
    normalized_query = query.strip()
    if not normalized_query:
        return []

    try:
        search = yf.Search(
            normalized_query,
            max_results=8,
            news_count=0,
            lists_count=0,
            enable_fuzzy_query=True,
            raise_errors=False,
        )
        quotes = getattr(search, "quotes", None) or []
        matches: list[SearchMatch] = []
        for item in quotes:
            symbol = _safe_text(item.get("symbol"))
            name = _safe_text(item.get("shortname")) or _safe_text(item.get("longname"))
            quote_type = _safe_text(item.get("quoteType"))
            exchange = _safe_text(item.get("exchange"))
            if not symbol or not name or not _is_equity_like(quote_type):
                continue
            matches.append(
                SearchMatch(
                    symbol=symbol.upper(),
                    name=name,
                    exchange=exchange,
                    quote_type=quote_type,
                )
            )

        unique_by_symbol: dict[str, SearchMatch] = {}
        for match in matches:
            unique_by_symbol.setdefault(match.symbol, match)

        ranked = sorted(
            unique_by_symbol.values(),
            key=lambda match: _score_match(normalized_query, match.symbol, match.name),
            reverse=True,
        )
        return ranked[:5]
    except Exception:
        return []


@st.cache_data(ttl=900, show_spinner=False)
def get_stock_snapshot(ticker: str) -> StockSnapshot:
    """Fetch price history, quote fields, and core fundamentals for a ticker."""
    symbol = ticker.strip().upper()
    if not symbol:
        return StockSnapshot(
            metadata=StockMetadata(symbol="", short_name=None, summary=None, exchange=None, quote_type=None, fund_family=None, category=None, current_price=None, market_cap=None, day_change_pct=None, fundamentals={}),
            history=pd.DataFrame(),
            latest_price=None,
            error="Please enter a stock ticker.",
        )

    try:
        stock = yf.Ticker(symbol)
        history = stock.history(period="1y", auto_adjust=False)
        if history.empty:
            return StockSnapshot(
                metadata=StockMetadata(symbol=symbol, short_name=None, summary=None, exchange=None, quote_type=None, fund_family=None, category=None, current_price=None, market_cap=None, day_change_pct=None, fundamentals={}),
                history=pd.DataFrame(),
                latest_price=None,
                error=f"No price history was returned for {symbol}. Check the ticker and try again.",
            )

        history = add_indicators(history)
        info = stock.info or {}

        latest_close = _coerce_float(history["Close"].iloc[-1])
        prev_close = _coerce_float(history["Close"].iloc[-2]) if len(history) > 1 else None
        day_change_pct = ((latest_close / prev_close) - 1) if latest_close and prev_close else None

        fundamentals = {
            "trailingPE": _coerce_float(info.get("trailingPE")),
            "forwardPE": _coerce_float(info.get("forwardPE")),
            "pegRatio": _coerce_float(info.get("pegRatio")),
            "returnOnEquity": _coerce_float(info.get("returnOnEquity")),
            "debtToEquity": _coerce_float(info.get("debtToEquity")),
            "revenueGrowth": _coerce_float(info.get("revenueGrowth")),
            "earningsGrowth": _coerce_float(info.get("earningsGrowth")),
            "freeCashflow": _coerce_float(info.get("freeCashflow")),
            "operatingCashflow": _coerce_float(info.get("operatingCashflow")),
            "grossMargins": _coerce_float(info.get("grossMargins")),
            "operatingMargins": _coerce_float(info.get("operatingMargins")),
            "profitMargins": _coerce_float(info.get("profitMargins")),
        }

        metadata = StockMetadata(
            symbol=symbol,
            short_name=_safe_text(info.get("shortName")) or _safe_text(info.get("longName")),
            summary=_safe_text(info.get("longBusinessSummary")),
            exchange=_safe_text(info.get("exchange")),
            quote_type=_safe_text(info.get("quoteType")),
            fund_family=_safe_text(info.get("fundFamily")),
            category=_safe_text(info.get("category")),
            current_price=_coerce_float(info.get("currentPrice")) or latest_close,
            market_cap=_coerce_float(info.get("marketCap")),
            day_change_pct=day_change_pct,
            fundamentals=fundamentals,
        )
        return StockSnapshot(metadata=metadata, history=history, latest_price=latest_close, error=None)
    except Exception as exc:  # pragma: no cover - yfinance failures vary by ticker/network state.
        return StockSnapshot(
            metadata=StockMetadata(symbol=symbol, short_name=None, summary=None, exchange=None, quote_type=None, fund_family=None, category=None, current_price=None, market_cap=None, day_change_pct=None, fundamentals={}),
            history=pd.DataFrame(),
            latest_price=None,
            error=f"Unable to fetch market data for {symbol}: {exc}",
        )
