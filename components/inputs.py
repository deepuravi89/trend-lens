"""Input widgets for the Trend Lens app."""

from __future__ import annotations

import streamlit as st
from services.advisor import PositionInputs
from services.market_data import SearchMatch, search_tickers


def render_ticker_input() -> str:
    """Render the hero header input row and return the ticker."""
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-eyebrow">Personal Stock Dashboard</div>
            <h1 class="hero-title">Trend Lens</h1>
            <div class="hero-subtitle">
                Screen a stock through price trend, quality, valuation, and your own position sizing
                rules in one polished local workspace.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([3, 1], gap="medium")
    with left:
        query = st.text_input(
            "Search ticker or company",
            value=st.session_state.get("ticker_query", "MSFT"),
            max_chars=40,
            help="Type a ticker like MSFT or a company name like Microsoft.",
        ).strip()
        st.session_state["ticker_query"] = query
    with right:
        st.markdown("<div style='height: 1.9rem;'></div>", unsafe_allow_html=True)
        if st.button("Refresh Snapshot", use_container_width=True):
            st.cache_data.clear()

    matches = search_tickers(query)
    if matches:
        selected_ticker = _render_match_selector(matches)
    else:
        selected_ticker = query.upper()
        if query:
            st.caption("No search matches found. Using your input as the ticker symbol directly.")
    return selected_ticker


def _render_match_selector(matches: list[SearchMatch]) -> str:
    """Render match selection UI and return the chosen ticker symbol."""
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

    options = [match.label for match in matches]
    selected_label = st.selectbox(
        "Choose match",
        options=options,
        index=0,
        help="Pick a different symbol if the top match is not the one you meant.",
    )
    selected_match = next(match for match in matches if match.label == selected_label)
    return selected_match.symbol


def render_position_inputs() -> PositionInputs:
    """Render the sidebar-style portfolio inputs."""
    st.markdown("")
    st.markdown(
        """
        <div class="section-title">Position Advisor Inputs</div>
        <div class="section-subtitle" style="margin-bottom: 0.9rem;">
            These settings personalize the buy, hold, or trim guidance without turning the app into
            a trading system.
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2, col3, col4 = st.columns(4, gap="medium")
    with col1:
        shares_owned = st.number_input("Shares owned", min_value=0.0, value=0.0, step=1.0)
    with col2:
        average_cost_basis = st.number_input("Average cost basis ($)", min_value=0.0, value=0.0, step=1.0)
    with col3:
        max_allocation_pct = st.number_input(
            "Max portfolio allocation (%)",
            min_value=1.0,
            max_value=100.0,
            value=10.0,
            step=1.0,
        )
    with col4:
        cash_available = st.number_input("Cash available to deploy ($)", min_value=0.0, value=0.0, step=100.0)
    return PositionInputs(
        shares_owned=shares_owned,
        average_cost_basis=average_cost_basis,
        max_allocation_pct=max_allocation_pct,
        cash_available=cash_available,
    )
