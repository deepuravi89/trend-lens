"""Watchlist management and display UI."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from services.advisor import PositionInputs
from services.market_data import SearchMatch, search_tickers
from services.watchlist import WatchlistEntry, WatchlistRow, build_watchlist_row, rank_watchlist_rows
from utils.formatters import format_currency, format_currency_full, format_percent_plain


STARTER_WATCHLIST = [
    WatchlistEntry("MSFT", "Quality compounder"),
    WatchlistEntry("AAPL", "Platform + services"),
    WatchlistEntry("NVDA", "AI leadership"),
]


def ensure_watchlist_state() -> None:
    """Initialize a small local watchlist in session state."""
    st.session_state.setdefault(
        "watchlist_entries",
        [
            {
                "ticker": entry.ticker,
                "note": entry.note,
                "shares_owned": entry.shares_owned,
                "average_cost_basis": entry.average_cost_basis,
            }
            for entry in STARTER_WATCHLIST
        ],
    )


def render_watchlist_section(position_inputs: PositionInputs) -> None:
    """Render the ranked watchlist dashboard."""
    ensure_watchlist_state()
    st.markdown(
        """
        <div class="detail-card" style="margin-bottom:1rem;">
            <div class="section-title">Watchlist</div>
            <div class="section-subtitle">
                Rank the stocks you care about by current opportunity, setup quality, recommendation, and catalyst bias.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_watchlist_manager()
    rows = _build_rows(position_inputs)
    if not rows:
        st.info("Add at least one ticker to build the ranked watchlist.")
        return

    ranked = rank_watchlist_rows(rows)
    _render_watchlist_priority_strip(ranked)
    st.caption("Default ranking favors total score first, then recommendation quality, confidence, and catalyst context.")
    st.dataframe(_rows_to_frame(ranked), use_container_width=True, hide_index=True)

    open_options = [row.ticker for row in ranked]
    selected = st.selectbox(
        "Open a watchlist name in the deep dive view",
        options=open_options,
        index=0,
        help="Pick a ranked watchlist name and switch back to the Deep Dive tab to review the full dashboard.",
    )
    if st.button("Open In Deep Dive", use_container_width=True, key="watchlist_open_deep_dive"):
        st.session_state["ticker_query"] = selected
        st.success(f"{selected} loaded into the Deep Dive search box.")


def _render_watchlist_manager() -> None:
    left, right = st.columns([2.2, 1], gap="large")
    with left:
        query = st.text_input(
            "Add watchlist ticker",
            value="",
            max_chars=40,
            help="Type a ticker like TSLA or a company name like Tesla.",
            key="watchlist_query",
        ).strip()
        matches = search_tickers(query)
        if matches:
            ticker = _render_watchlist_match_selector(matches)
        else:
            ticker = query.upper()
            if query:
                st.caption("No search matches found. Trend Lens will try your input as a ticker symbol directly.")
        note = st.text_input("Optional note / thesis", value="", max_chars=80, help="Keep a short reminder of why the stock is on your list.")
        row_a, row_b = st.columns(2, gap="medium")
        with row_a:
            shares_owned = st.number_input("Shares owned (optional)", min_value=0.0, value=0.0, step=1.0, key="watchlist_shares")
        with row_b:
            average_cost_basis = st.number_input("Average cost (optional)", min_value=0.0, value=0.0, step=1.0, key="watchlist_cost")
        if st.button("Add To Watchlist", use_container_width=True, key="watchlist_add") and ticker:
            entries = st.session_state["watchlist_entries"]
            if any(item["ticker"] == ticker for item in entries):
                st.info(f"{ticker} is already in your watchlist.")
            else:
                entries.append(
                    {
                        "ticker": ticker,
                        "note": note,
                        "shares_owned": shares_owned,
                        "average_cost_basis": average_cost_basis,
                    }
                )
                st.session_state["watchlist_entries"] = entries
                st.success(f"Added {ticker} to the watchlist.")
    with right:
        entries = st.session_state["watchlist_entries"]
        options = [item["ticker"] for item in entries]
        if options:
            remove_ticker = st.selectbox("Remove ticker", options=options, index=0)
            if st.button("Remove From Watchlist", use_container_width=True, key="watchlist_remove"):
                st.session_state["watchlist_entries"] = [item for item in entries if item["ticker"] != remove_ticker]
        if st.button("Reset Starter Watchlist", use_container_width=True, key="watchlist_reset"):
            st.session_state["watchlist_entries"] = [
                {
                    "ticker": entry.ticker,
                    "note": entry.note,
                    "shares_owned": entry.shares_owned,
                    "average_cost_basis": entry.average_cost_basis,
                }
                for entry in STARTER_WATCHLIST
            ]


def _render_watchlist_match_selector(matches: list[SearchMatch]) -> str:
    """Render the best-match selector for watchlist additions."""
    best = matches[0]
    st.markdown(
        (
            '<div class="section-subtitle" style="margin: 0.35rem 0 0.65rem 0;">'
            f'Best match: <strong style="color:#e6eefc;">{best.symbol}</strong> — {best.name}'
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    if len(matches) == 1:
        return best.symbol

    selected_label = st.selectbox(
        "Choose watchlist match",
        options=[match.label for match in matches],
        index=0,
        key="watchlist_match_selector",
        help="Pick a different symbol if the top match is not the one you meant.",
    )
    selected_match = next(match for match in matches if match.label == selected_label)
    return selected_match.symbol


def _build_rows(position_inputs: PositionInputs) -> list[WatchlistRow]:
    rows: list[WatchlistRow] = []
    for raw in st.session_state.get("watchlist_entries", []):
        row = build_watchlist_row(
            WatchlistEntry(
                ticker=raw["ticker"],
                note=raw.get("note", ""),
                shares_owned=float(raw.get("shares_owned", 0.0)),
                average_cost_basis=float(raw.get("average_cost_basis", 0.0)),
            ),
            position_inputs,
        )
        if row is not None:
            rows.append(row)
    return rows


def _rows_to_frame(rows: list[WatchlistRow]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Rank": index + 1,
                "Ticker": row.ticker,
                "Company": row.company_name,
                "Price": format_currency(row.current_price),
                "Total": f"{row.total_score:.0f}",
                "Tech": f"{row.technical_score:.0f}",
                "Fund": f"{row.fundamental_score:.0f}",
                "Setup": row.setup_type,
                "Action": row.recommendation,
                "Confidence": row.confidence,
                "Catalyst": row.catalyst_bias,
                "Own?": "Yes" if row.shares_owned > 0 else "No",
                "Alloc %": format_percent_plain(row.current_allocation_pct) if row.current_allocation_pct is not None and row.shares_owned > 0 else "—",
                "Add Room": format_currency_full(row.room_to_add) if row.room_to_add is not None and row.shares_owned > 0 else "—",
                "Thesis": row.note or "—",
            }
            for index, row in enumerate(rows)
        ]
    )


def _render_watchlist_priority_strip(rows: list[WatchlistRow]) -> None:
    """Render a compact at-a-glance strip for the most actionable names."""
    leaders = rows[:3]
    cols = st.columns(len(leaders), gap="medium")
    for rank, (col, row) in enumerate(zip(cols, leaders), start=1):
        with col:
            st.markdown(
                (
                    '<div class="detail-card">'
                    f'<div class="metric-label">#{rank} Priority</div>'
                    f'<div class="factor-name" style="font-size:1.1rem; margin-bottom:0.4rem;">{row.ticker}</div>'
                    f'<div class="section-kicker" style="margin-top:0;">{row.company_name}</div>'
                    f'<div class="metric-value" style="font-size:1.8rem; margin-top:0.7rem;">{row.total_score:.0f}</div>'
                    '<div style="display:flex; gap:0.4rem; flex-wrap:wrap; margin-top:0.65rem;">'
                    f'<div class="pill blue" style="margin-top:0;">{row.setup_type}</div>'
                    f'<div class="pill {"green" if row.recommendation == "Add" else "blue" if row.recommendation in {"Add Small", "Add on Pullback"} else "amber" if row.recommendation in {"Hold", "Trim"} else "red"}" style="margin-top:0;">{row.recommendation}</div>'
                    f'<div class="pill {"green" if row.catalyst_bias == "Positive" else "amber" if row.catalyst_bias == "Caution" else "blue"}" style="margin-top:0;">Catalyst: {row.catalyst_bias}</div>'
                    "</div>"
                    f'<div class="metric-caption" style="margin-top:0.7rem;">{row.note or "No note added yet."}</div>'
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
