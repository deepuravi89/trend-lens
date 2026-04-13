"""Calculation helpers for indicators and reusable signal math."""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Compute RSI with an EMA-like smoothing method."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def compute_macd(series: pd.Series) -> pd.DataFrame:
    """Compute MACD line, signal line, and histogram."""
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return pd.DataFrame({"MACD": macd, "MACD_SIGNAL": signal, "MACD_HIST": hist})


def add_indicators(history: pd.DataFrame) -> pd.DataFrame:
    """Add moving averages, RSI, MACD, and average volume to price history."""
    frame = history.copy()
    frame["SMA_50"] = frame["Close"].rolling(50, min_periods=1).mean()
    frame["SMA_200"] = frame["Close"].rolling(200, min_periods=1).mean()
    frame["AVG_VOLUME_20"] = frame["Volume"].rolling(20, min_periods=1).mean()
    frame["RSI_14"] = compute_rsi(frame["Close"], period=14)
    macd = compute_macd(frame["Close"])
    frame = pd.concat([frame, macd], axis=1)
    return frame.dropna(how="all")
