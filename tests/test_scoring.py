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
    assert scores.technical.setup is not None
    assert scores.technical.setup.label == "Constructive but Extended"
    assert any(factor.status == "Extended" for factor in scores.technical.factors)


def test_setup_classifies_strong_uptrend() -> None:
    snapshot = make_snapshot(
        price=120,
        sma50=112,
        sma200=100,
        rsi=56,
        macd=2.2,
        signal=1.6,
        hist=0.6,
        volume=1_250_000,
        avg_volume=1_000_000,
        fundamentals={"trailingPE": 20},
    )
    scores = build_score_bundle(snapshot)

    assert scores.technical.setup is not None
    assert scores.technical.setup.label == "Strong Uptrend"


def test_setup_classifies_recovery_setup() -> None:
    snapshot = make_snapshot(
        price=98,
        sma50=96,
        sma200=110,
        rsi=46,
        macd=0.6,
        signal=0.4,
        hist=0.2,
        volume=1_050_000,
        avg_volume=1_000_000,
        fundamentals={"trailingPE": 20},
    )
    scores = build_score_bundle(snapshot)

    assert scores.technical.setup is not None
    assert scores.technical.setup.label == "Recovery Setup"


def test_setup_classifies_mixed_setup() -> None:
    snapshot = make_snapshot(
        price=99,
        sma50=101,
        sma200=95,
        rsi=52,
        macd=0.1,
        signal=0.2,
        hist=-0.1,
        volume=900_000,
        avg_volume=1_000_000,
        fundamentals={"trailingPE": 20},
    )
    scores = build_score_bundle(snapshot)

    assert scores.technical.setup is not None
    assert scores.technical.setup.label == "Mixed Setup"


def test_setup_classifies_weak_downtrend() -> None:
    snapshot = make_snapshot(
        price=82,
        sma50=90,
        sma200=104,
        rsi=34,
        macd=-1.0,
        signal=-0.6,
        hist=-0.4,
        volume=850_000,
        avg_volume=1_000_000,
        fundamentals={"trailingPE": 20},
    )
    scores = build_score_bundle(snapshot)

    assert scores.technical.setup is not None
    assert scores.technical.setup.label == "Weak Downtrend"


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


# --- v5 regressions -------------------------------------------------------

from services.market_data import _debt_to_equity_ratio  # noqa: E402
from services.scoring import score_debt_factor, score_peg_factor, score_pe_factor  # noqa: E402


def test_yahoo_debt_to_equity_percent_is_converted_to_ratio() -> None:
    # Yahoo returns MSFT as ~12.2, meaning 0.122x.
    assert round(_debt_to_equity_ratio(12.157), 5) == 0.12157
    assert _debt_to_equity_ratio(None) is None
    assert score_debt_factor(_debt_to_equity_ratio(12.157)).status == "Healthy"
    assert score_debt_factor(_debt_to_equity_ratio(107.4)).status == "Manageable"


def test_negative_pe_and_peg_do_not_score_as_cheap() -> None:
    forward = score_pe_factor("Forward P/E", -7.0, 5, trailing=False)
    peg = score_peg_factor(-0.5)

    assert forward.points == 0
    assert forward.status == "Unprofitable"
    assert peg.points == 0
    assert peg.status == "Not meaningful"


def test_negative_equity_is_flagged() -> None:
    factor = score_debt_factor(-2.0)
    assert factor.points == 0
    assert factor.status == "Negative equity"
