"""Tests for technical and fundamental scoring edge cases."""

from __future__ import annotations

import pandas as pd

from services.market_data import StockMetadata, StockSnapshot
from services.scoring import build_score_bundle


def make_snapshot(
    *,
    price: float,
    sma50: float,
    sma200: float,
    rsi: float,
    macd: float,
    signal: float,
    hist: float,
    volume: float,
    avg_volume: float,
    fundamentals: dict[str, float | None],
) -> StockSnapshot:
    frame = pd.DataFrame(
        {
            "Open": [price],
            "Close": [price],
            "Volume": [volume],
            "SMA_50": [sma50],
            "SMA_200": [sma200],
            "AVG_VOLUME_20": [avg_volume],
            "RSI_14": [rsi],
            "MACD": [macd],
            "MACD_SIGNAL": [signal],
            "MACD_HIST": [hist],
            "DIST_FROM_50DMA": [(price / sma50) - 1],
            "DIST_FROM_200DMA": [(price / sma200) - 1],
        }
    )
    metadata = StockMetadata(
        symbol="EDGE",
        short_name="Edge Inc",
        summary=None,
        exchange="NASDAQ",
        current_price=price,
        market_cap=None,
        day_change_pct=None,
        fundamentals=fundamentals,
    )
    return StockSnapshot(metadata=metadata, history=frame, latest_price=price)


def test_technical_score_flags_extended_conditions() -> None:
    snapshot = make_snapshot(
        price=120,
        sma50=100,
        sma200=90,
        rsi=75,
        macd=2,
        signal=1,
        hist=1,
        volume=1_200_000,
        avg_volume=1_000_000,
        fundamentals={"trailingPE": 20},
    )
    scores = build_score_bundle(snapshot)

    assert "extended" in scores.technical.summary.lower()
    assert any(factor.status == "Extended" for factor in scores.technical.factors)


def test_sparse_fundamental_data_reduces_confidence() -> None:
    snapshot = make_snapshot(
        price=100,
        sma50=98,
        sma200=90,
        rsi=55,
        macd=1,
        signal=0.5,
        hist=0.5,
        volume=1_100_000,
        avg_volume=1_000_000,
        fundamentals={
            "trailingPE": None,
            "forwardPE": None,
            "pegRatio": None,
            "returnOnEquity": None,
            "debtToEquity": None,
            "revenueGrowth": None,
            "earningsGrowth": None,
            "freeCashflow": None,
            "operatingCashflow": None,
            "grossMargins": None,
            "operatingMargins": None,
            "profitMargins": None,
        },
    )
    scores = build_score_bundle(snapshot)

    assert scores.fundamental.confidence == "Low"
    assert scores.fundamental.completeness_ratio == 0
    assert scores.fundamental.score <= 2
