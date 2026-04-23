"""Tests for catalyst summarization and freshness logic."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from services.catalysts import CatalystEvent, build_catalyst_summary, classify_freshness, detect_asset_type
from services.market_data import StockMetadata, StockSnapshot


def make_event(*, polarity: str, days_old: int, summary: str) -> CatalystEvent:
    published_at = (datetime.now(timezone.utc) - timedelta(days=days_old)).isoformat()
    return CatalystEvent(
        ticker="TEST",
        title="Sample headline",
        source="Reuters",
        published_at=published_at,
        category="earnings",
        polarity=polarity,
        confidence="High",
        summary=summary,
    )


def test_classify_freshness_windows() -> None:
    assert classify_freshness(1) == "Fresh"
    assert classify_freshness(7) == "Recent"
    assert classify_freshness(15) == "Stale"


def test_catalyst_summary_resolves_positive_bias() -> None:
    summary = build_catalyst_summary(
        [
            make_event(polarity="positive", days_old=1, summary="Recent earnings context leans supportive."),
            make_event(polarity="positive", days_old=2, summary="Recent analyst activity leans supportive."),
        ]
    )
    assert summary.bias == "Positive"
    assert summary.freshness_label == "Fresh"
    assert summary.positive_points


def test_catalyst_summary_resolves_caution_bias() -> None:
    summary = build_catalyst_summary(
        [make_event(polarity="caution", days_old=4, summary="Recent guidance language leans cautionary.")]
    )
    assert summary.bias == "Caution"
    assert summary.freshness_label == "Recent"
    assert summary.risk_points


def test_catalyst_summary_handles_missing_events() -> None:
    summary = build_catalyst_summary([])
    assert summary.bias == "Neutral"
    assert summary.freshness_label == "Stale"
    assert summary.top_events == []


def test_catalyst_summary_uses_snapshot_context_when_news_is_sparse() -> None:
    snapshot = StockSnapshot(
        metadata=StockMetadata(
            symbol="TEST",
            short_name="Test Inc",
            summary=None,
            exchange="NASDAQ",
            current_price=100.0,
            market_cap=None,
            day_change_pct=None,
            fundamentals={
                "revenueGrowth": 0.18,
                "earningsGrowth": 0.16,
                "returnOnEquity": 0.22,
                "forwardPE": 34.0,
                "trailingPE": 36.0,
                "debtToEquity": 0.6,
            },
        ),
        history=pd.DataFrame(),
        latest_price=100.0,
    )
    summary = build_catalyst_summary([], snapshot)

    assert summary.bias == "Neutral"
    assert summary.freshness_label == "Stale"
    assert any("growth" in item.lower() or "quality" in item.lower() for item in summary.positive_points)
    assert any("valuation" in item.lower() for item in summary.risk_points)


def make_snapshot(*, symbol: str, quote_type: str | None, short_name: str, category: str | None, fund_family: str | None, price: float, sma50: float, sma200: float, rsi: float) -> StockSnapshot:
    return StockSnapshot(
        metadata=StockMetadata(
            symbol=symbol,
            short_name=short_name,
            summary=None,
            exchange="NASDAQ",
            quote_type=quote_type,
            fund_family=fund_family,
            category=category,
            current_price=price,
            market_cap=None,
            day_change_pct=None,
            fundamentals={},
        ),
        history=pd.DataFrame(
            {
                "Close": [price],
                "SMA_50": [sma50],
                "SMA_200": [sma200],
                "RSI_14": [rsi],
            }
        ),
        latest_price=price,
    )


def test_detect_asset_type_identifies_etf() -> None:
    snapshot = make_snapshot(
        symbol="VOO",
        quote_type="ETF",
        short_name="Vanguard S&P 500 ETF",
        category="Large Blend",
        fund_family="Vanguard",
        price=500,
        sma50=490,
        sma200=470,
        rsi=58,
    )
    assert detect_asset_type(snapshot) == "etf"


def test_etf_catalyst_summary_constructive_broad_etf() -> None:
    snapshot = make_snapshot(
        symbol="VOO",
        quote_type="ETF",
        short_name="Vanguard S&P 500 ETF",
        category="Large Blend",
        fund_family="Vanguard",
        price=500,
        sma50=490,
        sma200=470,
        rsi=58,
    )
    summary = build_catalyst_summary([], snapshot)
    assert summary.asset_context == "ETF context"
    assert summary.bias == "Positive"
    assert any("broad market" in item.lower() for item in summary.positive_points)


def test_etf_catalyst_summary_mixed_growth_etf() -> None:
    snapshot = make_snapshot(
        symbol="QQQM",
        quote_type="ETF",
        short_name="Invesco NASDAQ 100 ETF",
        category="Large Growth",
        fund_family="Invesco",
        price=200,
        sma50=202,
        sma200=185,
        rsi=55,
    )
    summary = build_catalyst_summary([], snapshot)
    assert summary.asset_context == "ETF context"
    assert summary.bias == "Neutral"
    assert any("growth" in item.lower() for item in summary.positive_points + summary.risk_points)


def test_etf_catalyst_summary_weak_sector_etf() -> None:
    snapshot = make_snapshot(
        symbol="XLF",
        quote_type="ETF",
        short_name="Financial Select Sector SPDR Fund",
        category="Financial",
        fund_family="State Street",
        price=40,
        sma50=42,
        sma200=45,
        rsi=35,
    )
    summary = build_catalyst_summary([], snapshot)
    assert summary.asset_context == "ETF context"
    assert summary.bias == "Caution"
    assert any("financial" in item.lower() for item in summary.positive_points + summary.risk_points)


def test_stock_catalyst_summary_still_uses_stock_logic() -> None:
    snapshot = make_snapshot(
        symbol="MSFT",
        quote_type="EQUITY",
        short_name="Microsoft Corporation",
        category=None,
        fund_family=None,
        price=420,
        sma50=410,
        sma200=380,
        rsi=60,
    )
    summary = build_catalyst_summary([], snapshot)
    assert summary.asset_context == "Stock context"


def test_uncertain_asset_type_defaults_gracefully() -> None:
    snapshot = make_snapshot(
        symbol="TEST",
        quote_type=None,
        short_name="Test Company",
        category=None,
        fund_family=None,
        price=100,
        sma50=98,
        sma200=96,
        rsi=55,
    )
    assert detect_asset_type(snapshot) == "stock"
