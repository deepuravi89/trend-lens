"""Score cards and summary sections."""

from __future__ import annotations

import streamlit as st

from services.advisor import PositionAdvice
from services.market_data import StockSnapshot
from services.scoring import ScoreBundle
from utils.formatters import format_currency, format_percent, truncate_text


VERDICT_CLASSES = {
    "Strong Buy Zone": "green",
    "Buy on Pullback": "blue",
    "Hold": "amber",
    "Trim Watch": "amber",
    "Avoid": "red",
    "Add": "green",
    "Add on Pullback": "blue",
    "Trim": "amber",
    "Avoid New Buy": "red",
}


def render_header() -> None:
    """Render the app header spacing anchor."""
    st.markdown("", unsafe_allow_html=True)


def _metric_card(label: str, value: str, caption: str, pill_text: str | None = None) -> str:
    pill_markup = ""
    if pill_text:
        pill_class = VERDICT_CLASSES.get(pill_text, "blue")
        pill_markup = f'<div class="pill {pill_class}">{pill_text}</div>'
    return (
        '<div class="metric-card">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f"{pill_markup}"
        f'<div class="metric-caption">{caption}</div>'
        "</div>"
    )


def render_score_section(snapshot: StockSnapshot, scores: ScoreBundle, advice: PositionAdvice) -> None:
    """Render the top metrics and the three main analysis cards."""
    current_price = snapshot.latest_price or snapshot.metadata.current_price
    daily_change = snapshot.metadata.day_change_pct
    price_caption = (
        f"{format_percent(daily_change)} today • {snapshot.metadata.exchange or 'Exchange N/A'}"
        if daily_change is not None
        else f"{snapshot.metadata.exchange or 'Exchange N/A'}"
    )

    total_col, price_col, verdict_col, company_col = st.columns(4, gap="medium")
    with total_col:
        st.markdown(
            _metric_card(
                "Total Score",
                f"{scores.total_score:.0f} / 100",
                "Weighted blend of technical setup, fundamentals, and position context.",
                scores.verdict,
            ),
            unsafe_allow_html=True,
        )
    with price_col:
        st.markdown(
            _metric_card(
                "Current Price",
                format_currency(current_price),
                price_caption,
            ),
            unsafe_allow_html=True,
        )
    with verdict_col:
        st.markdown(
            _metric_card(
                "Position Advisor",
                f"{advice.score:.0f} / 20",
                "Practical action based on your sizing inputs, cost basis, and current setup.",
                advice.recommendation,
            ),
            unsafe_allow_html=True,
        )
    with company_col:
        st.markdown(
            _metric_card(
                snapshot.metadata.symbol,
                snapshot.metadata.short_name or snapshot.metadata.symbol,
                truncate_text(snapshot.metadata.summary or "Company summary unavailable.", 170),
            ),
            unsafe_allow_html=True,
        )

    st.markdown("")
    tech_col, fund_col, advisor_col = st.columns(3, gap="large")

    with tech_col:
        _render_detail_card(
            "Technical Score",
            f"{scores.technical.score:.0f} / 40",
            scores.technical.summary,
            scores.technical.explanations,
        )
    with fund_col:
        _render_detail_card(
            "Fundamental Score",
            f"{scores.fundamental.score:.0f} / 40",
            scores.fundamental.summary,
            scores.fundamental.explanations,
        )
    with advisor_col:
        _render_detail_card(
            "Position Advisor",
            f"{advice.score:.0f} / 20",
            advice.explanation,
            advice.bullets,
            pill_text=advice.recommendation,
        )


def _render_detail_card(
    title: str,
    value: str,
    summary: str,
    bullets: list[str],
    pill_text: str | None = None,
) -> None:
    card = (
        '<div class="detail-card">'
        f'<div class="metric-label">{title}</div>'
        f'<div class="metric-value">{value}</div>'
    )
    if pill_text:
        pill_class = VERDICT_CLASSES.get(pill_text, "blue")
        card += f'<div class="pill {pill_class}">{pill_text}</div>'
    card += (
        f'<div class="section-subtitle" style="margin-top: 0.85rem;">{summary}</div>'
        '<ul class="explanation-list">'
        f"{''.join(f'<li>{bullet}</li>' for bullet in bullets[:5])}"
        "</ul>"
        "</div>"
    )
    st.markdown(card, unsafe_allow_html=True)
