"""Score History tab: what the model said, and how those calls turned out."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.score_cards import mini_stat
from services.market_data import get_history_with_indicators, get_stock_snapshot
from services.score_history import HISTORY_PATH, HORIZONS, forward_outcomes, load_history, record_score, summarize_outcomes


def _closes_since(start: str):
    def get_closes(ticker: str) -> pd.Series:
        frame = get_history_with_indicators(ticker, start=start)
        return frame["Close"] if not frame.empty else pd.Series(dtype=float)

    return get_closes


def _format_summary(summary: pd.DataFrame, label: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            label: summary.iloc[:, 0],
            "Calls": summary["calls"],
            "Avg return": summary["avg_return"].map(lambda v: f"{v * 100:+.1f}%"),
            "Avg vs S&P 500": summary["avg_vs_spy"].map(lambda v: f"{v * 100:+.1f}%"),
            "Beat S&P 500": summary["beat_spy_rate"].map(lambda v: f"{v * 100:.0f}%"),
        }
    )


def render_score_history() -> None:
    st.markdown('<div class="section-title">Score History</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="input-grid-note">Every stock you open in Deep Dive or the Watchlist is logged once a day with a neutral '
        '"new buyer" call (fixed $100k portfolio, no shares owned). Once enough time has passed, this tab checks whether '
        "higher scores and Add calls actually beat the S&amp;P 500. Expect a few months before the numbers mean much.</div>",
        unsafe_allow_html=True,
    )

    history = load_history()

    with st.expander("Log tickers now", expanded=history.empty):
        raw = st.text_input("Tickers (comma separated)", value="", key="history_log_tickers", placeholder="AAPL, MSFT, KO")
        if st.button("Log today's calls", key="history_log_button"):
            tickers = [t.strip().upper() for t in raw.split(",") if t.strip()]
            for ticker in tickers:
                snapshot = get_stock_snapshot(ticker)
                if snapshot.error:
                    st.warning(f"{ticker}: {snapshot.error}")
                else:
                    record_score(snapshot)
            history = load_history()
        st.caption(f"Saved locally to {HISTORY_PATH.relative_to(HISTORY_PATH.parent.parent)}. For a daily log without opening the app, run scripts/log_scores.py.")

    if history.empty:
        st.info("No calls logged yet. Open a few stocks in Deep Dive or log some tickers above.")
        return

    st.markdown(
        '<div style="display:flex; flex-wrap:wrap; gap:0.75rem; margin:0.4rem 0 1rem 0;">'
        f'{mini_stat("Calls logged", str(len(history)))}'
        f'{mini_stat("Tickers", str(history["ticker"].nunique()))}'
        f'{mini_stat("Days covered", str(history["date"].nunique()))}'
        "</div>",
        unsafe_allow_html=True,
    )

    horizon = st.radio("Look-ahead window", list(HORIZONS), horizontal=True, index=1, key="history_horizon")
    with st.spinner("Checking what happened after each call..."):
        outcomes = forward_outcomes(history, _closes_since(str(history["date"].min())))

    by_call = summarize_outcomes(outcomes, "call", horizon)
    if by_call.empty:
        days = HORIZONS[horizon]
        st.info(f"No calls are old enough yet for the {horizon} window ({days} trading days). Keep logging and check back.")
    else:
        left, right = st.columns(2, gap="large")
        with left:
            st.markdown("**By call**")
            st.dataframe(_format_summary(by_call, "Call"), hide_index=True, use_container_width=True)
        with right:
            st.markdown("**By total score**")
            st.dataframe(_format_summary(summarize_outcomes(outcomes, "band", horizon), "Score"), hide_index=True, use_container_width=True)
        st.caption("If Add calls and high scores don't beat the S&P 500 here over time, the scoring rules need rethinking.")

    st.markdown("**Recent calls**")
    recent = history.sort_values(["date", "ticker"], ascending=[False, True]).head(50)
    st.dataframe(recent, hide_index=True, use_container_width=True)
