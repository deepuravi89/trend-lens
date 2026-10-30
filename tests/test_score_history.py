"""Tests for logging calls and measuring what happened next."""

from __future__ import annotations

from datetime import date

import pandas as pd

from services.score_history import forward_outcomes, load_history, record_score, score_band, summarize_outcomes
from tests_helpers import strong_snapshot


def test_record_score_keeps_one_row_per_ticker_per_day(tmp_path) -> None:
    path = tmp_path / "history.csv"
    snapshot = strong_snapshot()

    record_score(snapshot, path=path, today=date(2026, 10, 1))
    record_score(snapshot, path=path, today=date(2026, 10, 1))
    record_score(snapshot, path=path, today=date(2026, 10, 2))

    history = load_history(path)
    assert len(history) == 2
    assert set(history["ticker"]) == {"TEST"}
    assert history.iloc[0]["call"] in {"Add", "Add Small"}


def test_load_history_handles_missing_file(tmp_path) -> None:
    assert load_history(tmp_path / "nope.csv").empty


def test_forward_outcomes_and_summary() -> None:
    dates = pd.bdate_range("2026-01-01", periods=30)
    prices = {
        "WIN": pd.Series([100.0 + i for i in range(30)], index=dates),  # +21% over 21 days
        "LOSE": pd.Series([100.0 - i for i in range(30)], index=dates),
        "SPY": pd.Series([100.0 + i * 0.1 for i in range(30)], index=dates),
    }
    history = pd.DataFrame(
        [
            {"date": "2026-01-01", "ticker": "WIN", "total": 85, "call": "Add"},
            {"date": "2026-01-01", "ticker": "LOSE", "total": 40, "call": "Avoid New Buy"},
            {"date": "2026-02-10", "ticker": "WIN", "total": 85, "call": "Add"},  # too recent for 1M
        ]
    )

    outcomes = forward_outcomes(history, lambda t: prices[t], horizons={"1M": 21})
    assert round(outcomes.loc[0, "ret_1M"], 4) == 0.21
    assert round(outcomes.loc[0, "excess_1M"], 4) == round(0.21 - 0.021, 4)
    assert pd.isna(outcomes.loc[2, "excess_1M"])

    summary = summarize_outcomes(outcomes, "call", "1M").set_index("call")
    assert summary.loc["Add", "calls"] == 1
    assert summary.loc["Add", "beat_spy_rate"] == 1.0
    assert summary.loc["Avoid New Buy", "beat_spy_rate"] == 0.0


def test_score_band() -> None:
    assert score_band(91) == "80+"
    assert score_band(70) == "65–79"
    assert score_band(12) == "<50"
