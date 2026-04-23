"""Input widgets for the Trend Lens app."""

from __future__ import annotations

import streamlit as st

from config.scoring_config import APP_COPY
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
                Screen a stock through trend, quality, valuation, and your own position sizing rules
                in one polished local workspace.
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


def render_position_inputs(key_prefix: str = "position") -> PositionInputs:
    """Render the portfolio-aware position input section."""
    st.markdown("")
    st.markdown('<div class="input-shell">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="section-title">Position Advisor Inputs</div>
        <div class="input-grid-note">
            Add your portfolio context once, then let Trend Lens translate the stock score into sizing-aware guidance.
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("How these fields are used", expanded=False):
        st.write(APP_COPY["position_help"])

    top = st.columns(3, gap="medium")
    with top[0]:
        total_portfolio_value = st.number_input(
            "Portfolio value used for sizing ($)",
            min_value=0.0,
            value=100000.0,
            step=1000.0,
            key=f"{key_prefix}_total_portfolio_value",
            help="Use the total value of the investable portfolio this position should be sized against. This is what makes the allocation math real.",
        )
    with top[1]:
        shares_owned = st.number_input(
            "Current shares owned",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key=f"{key_prefix}_shares_owned",
            help="How many shares you currently own. Use 0 if you are evaluating a new position.",
        )
    with top[2]:
        average_cost_basis = st.number_input(
            "Average cost per share ($)",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key=f"{key_prefix}_average_cost_basis",
            help="Your average purchase price per share. This is used to estimate unrealized gain or loss.",
        )

    bottom = st.columns(3, gap="medium")
    with bottom[0]:
        max_allocation_pct = st.number_input(
            "Max position cap (%)",
            min_value=1.0,
            max_value=100.0,
            value=10.0,
            step=0.5,
            key=f"{key_prefix}_max_allocation_pct",
            help="Your hard ceiling for this position as a percentage of total portfolio value.",
        )
    with bottom[1]:
        target_position_size_pct = st.number_input(
            "Target position size (%)",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=0.5,
            key=f"{key_prefix}_target_position_size_pct",
            help="Optional softer target if you are still building the position. Set to 0 to ignore it.",
        )
    with bottom[2]:
        cash_available = st.number_input(
            "Cash available now ($)",
            min_value=0.0,
            value=0.0,
            step=100.0,
            key=f"{key_prefix}_cash_available",
            help="Dry powder you would realistically be willing to use right now for this idea.",
        )
    st.markdown("</div>", unsafe_allow_html=True)

    return PositionInputs(
        total_portfolio_value=total_portfolio_value,
        shares_owned=shares_owned,
        average_cost_basis=average_cost_basis,
        max_portfolio_allocation_pct=max_allocation_pct,
        cash_available_to_deploy=cash_available,
        target_position_size_pct=target_position_size_pct if target_position_size_pct > 0 else None,
    )
