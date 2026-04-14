"""Streamlit entry point for the Trend Lens stock dashboard."""

from __future__ import annotations

import streamlit as st

from components.charts import render_chart_suite
from components.inputs import render_position_inputs, render_ticker_input
from components.score_cards import render_header, render_score_section
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
                --panel: rgba(12, 23, 43, 0.84);
                --panel-strong: rgba(16, 30, 56, 0.96);
                --panel-soft: rgba(8, 16, 30, 0.45);
                --border: rgba(148, 163, 184, 0.17);
                --text: #e6eefc;
                --muted: #8ca2c3;
                --muted-strong: #b7c8e3;
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

            [data-testid="stHeader"] { background: transparent; }
            [data-testid="stToolbar"] { right: 1rem; }

            .block-container {
                padding-top: 1.5rem;
                padding-bottom: 2.8rem;
                max-width: 1360px;
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
                padding: 1.8rem 1.8rem 1.55rem 1.8rem;
                margin-bottom: 1rem;
                background:
                    radial-gradient(circle at top right, rgba(96, 165, 250, 0.14), transparent 32%),
                    linear-gradient(180deg, rgba(16, 30, 56, 0.92), rgba(11, 21, 40, 0.86));
            }
            .detail-card { padding: 1.3rem 1.35rem; height: 100%; }
            .metric-card { padding: 1.2rem; min-height: 156px; }

            .hero-eyebrow,
            .metric-label {
                color: var(--muted);
                text-transform: uppercase;
                letter-spacing: 0.16em;
                font-size: 0.72rem;
                margin-bottom: 0.7rem;
            }

            .hero-title {
                font-size: 2.45rem;
                font-weight: 700;
                margin: 0;
                color: var(--text);
                letter-spacing: -0.03em;
            }

            .hero-subtitle,
            .section-subtitle,
            .metric-caption {
                color: var(--muted);
                line-height: 1.6;
            }

            .hero-subtitle {
                max-width: 56rem;
                font-size: 1rem;
            }

            .metric-value {
                font-size: 2.15rem;
                font-weight: 700;
                color: var(--text);
                line-height: 1.1;
                letter-spacing: -0.03em;
            }

            .pill {
                display: inline-flex;
                align-items: center;
                border-radius: 999px;
                padding: 0.35rem 0.82rem;
                font-size: 0.8rem;
                font-weight: 600;
                margin-top: 0.75rem;
                white-space: nowrap;
                letter-spacing: 0.01em;
            }

            .pill.green { background: rgba(61, 217, 164, 0.16); color: #aaf2d8; }
            .pill.amber { background: rgba(255, 182, 72, 0.14); color: #ffd38c; }
            .pill.red { background: rgba(255, 107, 122, 0.14); color: #ffc2cb; }
            .pill.blue { background: rgba(96, 165, 250, 0.14); color: #c7e1ff; }

            .section-kicker {
                color: var(--muted-strong);
                font-size: 0.92rem;
                line-height: 1.6;
                margin-top: 0.35rem;
            }

            .section-title {
                color: var(--text);
                font-weight: 700;
                font-size: 1.05rem;
                margin-bottom: 0.75rem;
                letter-spacing: -0.01em;
            }

            .factor-table {
                display: grid;
                gap: 0.68rem;
                margin-top: 1.05rem;
            }

            .factor-row {
                display: flex;
                justify-content: space-between;
                gap: 1rem;
                padding: 0.92rem 0.98rem;
                border-radius: 18px;
                border: 1px solid rgba(148, 163, 184, 0.12);
                background: rgba(7, 14, 27, 0.4);
            }

            .factor-row.positive,
            .math-row.positive {
                border-color: rgba(61, 217, 164, 0.18);
                background: linear-gradient(180deg, rgba(12, 31, 33, 0.65), rgba(7, 14, 27, 0.45));
            }

            .factor-row.caution,
            .math-row.caution {
                border-color: rgba(255, 182, 72, 0.2);
                background: linear-gradient(180deg, rgba(36, 26, 12, 0.45), rgba(7, 14, 27, 0.45));
            }

            .factor-row.negative,
            .math-row.negative {
                border-color: rgba(255, 107, 122, 0.2);
                background: linear-gradient(180deg, rgba(36, 17, 24, 0.5), rgba(7, 14, 27, 0.45));
            }

            .factor-main { min-width: 0; }
            .factor-name { color: var(--text); font-weight: 600; margin-bottom: 0.22rem; }
            .factor-detail { color: var(--muted); font-size: 0.9rem; line-height: 1.45; }
            .factor-meta { display: flex; flex-direction: column; align-items: flex-end; min-width: 92px; }
            .factor-points { color: var(--text); font-size: 1.02rem; font-weight: 700; }

            .math-grid {
                display: grid;
                gap: 0.64rem;
                margin-top: 0.95rem;
            }

            .math-row {
                display: flex;
                justify-content: space-between;
                gap: 1rem;
                align-items: center;
                padding: 0.82rem 0.98rem;
                border-radius: 16px;
                background: rgba(7, 14, 27, 0.42);
                border: 1px solid rgba(148, 163, 184, 0.12);
            }

            .math-row span { color: var(--muted); }
            .math-row strong { color: var(--text); text-align: right; }

            .mini-stat {
                min-width: 132px;
                padding: 0.75rem 0.9rem;
                border-radius: 18px;
                background: rgba(7, 14, 27, 0.42);
                border: 1px solid rgba(148, 163, 184, 0.12);
            }

            .mini-stat span {
                display: block;
                color: var(--muted);
                font-size: 0.74rem;
                text-transform: uppercase;
                letter-spacing: 0.12em;
                margin-bottom: 0.38rem;
            }

            .mini-stat strong {
                color: var(--text);
                font-size: 1.15rem;
            }

            .explanation-list {
                margin: 0;
                padding-left: 1.15rem;
                color: var(--text);
            }
            .explanation-list li { margin-bottom: 0.52rem; line-height: 1.5; color: #d8e3f7; }

            .input-shell {
                background: rgba(10, 20, 37, 0.55);
                border: 1px solid rgba(148, 163, 184, 0.12);
                border-radius: 22px;
                padding: 1.2rem 1.2rem 0.5rem 1.2rem;
                margin-bottom: 1.1rem;
            }

            .input-grid-note {
                color: var(--muted);
                font-size: 0.92rem;
                margin-bottom: 0.95rem;
            }

            .stTextInput input,
            .stNumberInput input,
            .stSelectbox div[data-baseweb="select"] > div {
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

            .stExpander {
                border: 1px solid rgba(148, 163, 184, 0.12);
                border-radius: 16px;
                background: rgba(7, 14, 27, 0.3);
            }

            .chart-shell { padding: 1rem 1rem 0.35rem 1rem; }

            @media (max-width: 1080px) {
                .hero-title { font-size: 2.05rem; }
                .metric-value { font-size: 1.9rem; }
                .factor-row,
                .math-row { flex-direction: column; align-items: flex-start; }
                .factor-meta { align-items: flex-start; min-width: 0; }
                .mini-stat { min-width: calc(50% - 0.5rem); }
            }

            @media (max-width: 760px) {
                .block-container { padding-top: 1rem; padding-left: 0.9rem; padding-right: 0.9rem; }
                .hero-card, .detail-card, .metric-card { border-radius: 20px; }
                .hero-card { padding: 1.35rem; }
                .hero-title { font-size: 1.85rem; }
                .mini-stat { min-width: 100%; }
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
    st.caption("Trend Lens is a local decision-support tool for personal investing research. It is not financial advice.")


if __name__ == "__main__":
    main()
