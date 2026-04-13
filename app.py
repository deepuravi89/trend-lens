"""Streamlit entry point for the Trend Lens stock dashboard."""

from __future__ import annotations

import streamlit as st

from components.charts import render_chart_suite
from components.inputs import render_position_inputs, render_ticker_input
from components.score_cards import render_header, render_score_section
from config.scoring_config import APP_COPY
from services.advisor import build_position_advice
from services.market_data import get_stock_snapshot
from services.scoring import build_score_bundle, finalize_total_score


st.set_page_config(
    page_title="Trend Lens",
    page_icon="TL",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def inject_styles() -> None:
    """Apply the premium dashboard theme."""
    st.markdown(
        """
        <style>
            :root {
                --bg: #09111f;
                --panel: rgba(13, 24, 44, 0.82);
                --panel-strong: rgba(18, 32, 59, 0.95);
                --border: rgba(148, 163, 184, 0.18);
                --text: #e6eefc;
                --muted: #8fa5c5;
                --green: #3dd9a4;
                --amber: #ffb648;
                --red: #ff6b7a;
                --blue: #60a5fa;
            }

            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(96, 165, 250, 0.14), transparent 32%),
                    radial-gradient(circle at top right, rgba(61, 217, 164, 0.12), transparent 25%),
                    linear-gradient(180deg, #08101c 0%, #09111f 55%, #070d18 100%);
                color: var(--text);
            }

            [data-testid="stHeader"] {
                background: rgba(0, 0, 0, 0);
            }

            [data-testid="stToolbar"] {
                right: 1rem;
            }

            .block-container {
                padding-top: 2rem;
                padding-bottom: 2.5rem;
                max-width: 1320px;
            }

            .hero-card,
            .metric-card,
            .detail-card {
                background: var(--panel);
                border: 1px solid var(--border);
                border-radius: 24px;
                backdrop-filter: blur(18px);
                box-shadow: 0 20px 45px rgba(3, 9, 20, 0.35);
            }

            .hero-card {
                padding: 1.75rem 1.75rem 1.2rem 1.75rem;
                margin-bottom: 1.2rem;
            }

            .hero-eyebrow {
                letter-spacing: 0.18em;
                text-transform: uppercase;
                color: var(--muted);
                font-size: 0.72rem;
                margin-bottom: 0.65rem;
            }

            .hero-title {
                font-size: 2.2rem;
                font-weight: 700;
                margin: 0;
                color: var(--text);
            }

            .hero-subtitle {
                margin-top: 0.55rem;
                font-size: 1rem;
                color: var(--muted);
                max-width: 58rem;
                line-height: 1.6;
            }

            .metric-card {
                padding: 1.3rem 1.25rem;
                min-height: 162px;
            }

            .metric-label {
                color: var(--muted);
                text-transform: uppercase;
                letter-spacing: 0.14em;
                font-size: 0.72rem;
                margin-bottom: 0.7rem;
            }

            .metric-value {
                font-size: 2rem;
                font-weight: 700;
                color: var(--text);
                line-height: 1.1;
            }

            .metric-caption {
                color: var(--muted);
                font-size: 0.94rem;
                margin-top: 0.7rem;
                line-height: 1.5;
            }

            .pill {
                display: inline-flex;
                align-items: center;
                border-radius: 999px;
                padding: 0.3rem 0.8rem;
                font-size: 0.86rem;
                font-weight: 600;
                margin-top: 0.85rem;
            }

            .pill.green { background: rgba(61, 217, 164, 0.16); color: #aaf2d8; }
            .pill.amber { background: rgba(255, 182, 72, 0.14); color: #ffd38c; }
            .pill.red { background: rgba(255, 107, 122, 0.14); color: #ffc2cb; }
            .pill.blue { background: rgba(96, 165, 250, 0.14); color: #c7e1ff; }

            .detail-card {
                padding: 1.25rem 1.3rem;
                height: 100%;
            }

            .section-title {
                color: var(--text);
                font-weight: 700;
                font-size: 1.02rem;
                margin-bottom: 0.85rem;
            }

            .section-subtitle {
                color: var(--muted);
                line-height: 1.6;
                margin-bottom: 1rem;
            }

            .explanation-list {
                margin: 0;
                padding-left: 1.1rem;
                color: var(--text);
            }

            .explanation-list li {
                margin-bottom: 0.55rem;
                line-height: 1.5;
                color: #d8e3f7;
            }

            .stTextInput > div > div,
            .stNumberInput > div > div > input {
                background: rgba(11, 19, 36, 0.95);
                color: var(--text);
                border-radius: 14px;
                border: 1px solid rgba(148, 163, 184, 0.18);
            }

            .stButton button {
                width: 100%;
                border-radius: 14px;
                border: 1px solid rgba(96, 165, 250, 0.28);
                background: linear-gradient(135deg, rgba(43, 104, 219, 0.95), rgba(36, 182, 152, 0.82));
                color: white;
                font-weight: 700;
                padding: 0.72rem 1rem;
            }

            .chart-shell {
                padding: 1rem 1rem 0.35rem 1rem;
            }

            .footer-note {
                color: var(--muted);
                font-size: 0.88rem;
                line-height: 1.5;
                margin-top: 0.75rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    """Render the full Streamlit experience."""
    inject_styles()
    render_header()

    ticker = render_ticker_input()
    position_inputs = render_position_inputs()

    if not ticker:
        st.info("Enter a ticker to load the dashboard.")
        return

    with st.spinner(f"Loading {ticker.upper()}..."):
        snapshot = get_stock_snapshot(ticker)

    if snapshot.error:
        st.error(snapshot.error)
        return

    scores = build_score_bundle(snapshot)
    advice = build_position_advice(snapshot, scores, position_inputs)
    scores = finalize_total_score(scores, advice.score)

    render_score_section(snapshot, scores, advice)
    render_chart_suite(snapshot)

    lower_left, lower_right = st.columns([1.2, 1], gap="large")

    with lower_left:
        st.markdown('<div class="detail-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Why The Model Landed Here</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="section-subtitle">{APP_COPY["detailed_explainer"]}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(scores.render_full_explanation(), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with lower_right:
        st.markdown('<div class="detail-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Position Context</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="section-subtitle">{advice.explanation}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(advice.render_bullets(), unsafe_allow_html=True)
        st.markdown(
            '<div class="footer-note">This dashboard is a personal decision-support tool. '
            "It is not a trading bot and not financial advice.</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
