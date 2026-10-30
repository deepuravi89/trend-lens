"""Shared test fixtures."""

from __future__ import annotations

import pandas as pd

from services.market_data import StockMetadata, StockSnapshot


def strong_snapshot(price: float = 100.0) -> StockSnapshot:
    frame = pd.DataFrame(
        {
            "Open": [99.0, price],
            "Close": [99.0, price],
            "Volume": [1_000_000, 1_400_000],
            "SMA_50": [96.0, 97.0],
            "SMA_200": [85.0, 86.0],
            "AVG_VOLUME_20": [1_000_000, 1_000_000],
            "RSI_14": [55.0, 55.0],
            "MACD": [1.2, 1.6],
            "MACD_SIGNAL": [1.0, 1.2],
            "MACD_HIST": [0.2, 0.4],
            "DIST_FROM_50DMA": [0.02, price / 97.0 - 1],
            "DIST_FROM_200DMA": [0.16, price / 86.0 - 1],
        }
    )
    fundamentals = {
        "trailingPE": 18.0, "forwardPE": 17.0, "pegRatio": 1.2, "returnOnEquity": 0.2,
        "debtToEquity": 0.4, "revenueGrowth": 0.16, "earningsGrowth": 0.16,
        "freeCashflow": 1e9, "operatingCashflow": 1.2e9,
        "grossMargins": 0.45, "operatingMargins": 0.22, "profitMargins": 0.18,
    }
    metadata = StockMetadata(symbol="TEST", short_name="Test Corp", summary=None, exchange="NASDAQ",
                             current_price=price, fundamentals=fundamentals)
    return StockSnapshot(metadata=metadata, history=frame, latest_price=price)
