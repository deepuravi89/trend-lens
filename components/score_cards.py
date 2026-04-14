"""Score cards and summary sections."""

from __future__ import annotations

import streamlit as st

from services.advisor import PositionAdvice
from services.market_data import StockSnapshot
from services.scoring import FactorScore, ScoreBundle
from utils.formatters import (
    format_currency,
    format_currency_full,
    format_percent,
    format_percent_plain,
    truncate_text,
)


VERDICT_CLASSES = {
    "Strong Buy Zone": "green",
    "Buy on Pullback": "blue",
    "Hold": "amber",
    "Trim Watch": "amber",
    "Avoid": "red",
    "Add": "green",
    "Add Small": "blue",
    "Add on Pullback": "blue",
    "Trim": "amber",
    "Avoid New Buy": "red",
    "High": "green",
    "Medium": "amber",
    "Low": "red",
}


def render_header() -> None:
    """Render the app header spacing anchor."""
    st.markdown("", unsafe_allow_html=True)


def render_score_section(snapshot: StockSnapshot, scores: ScoreBundle, advice: PositionAdvice) -> None:
    """Render the upgraded summary, factor cards, and position math panel."""
    render_top_summary(snapshot, scores)

    left, right = st.columns([1.8, 1], gap="large")
    with left:
        tech_col, fund_col = st.columns(2, gap="large")
        with tech_col:
            render_section_card("Technical Score", scores.technical.score, scores.technical.max_score, scores.technical.summary, scores.technical.confidence, scores.technical.factors)
        with fund_col:
            render_section_card(
                "Fundamental Score",
                scores.fundamental.score,
                scores.fundamental.max_score,
                scores.fundamental.summary,
                f"{scores.fundamental.confidence} • {format_percent_plain(scores.fundamental.completeness_ratio)} data completeness",
                scores.fundamental.factors,
            )
    with right:
        render_position_advisor_card(advice)

    st.markdown("")
    math_col, explain_col = st.columns([1, 1.2], gap="large")
    with math_col:
        render_position_math_panel(advice)
    with explain_col:
        render_detail_explainer(scores)


def render_top_summary(snapshot: StockSnapshot, scores: ScoreBundle) -> None:
    """Render the above-the-fold summary area."""
    price = snapshot.latest_price or snapshot.metadata.current_price
    move = snapshot.metadata.day_change_pct
    summary_card = (
        '<div class="detail-card" style="margin-bottom:1.1rem;">'
        f'<div class="hero-eyebrow">{snapshot.metadata.symbol}</div>'
        f'<div class="hero-title" style="font-size:2.6rem;">{snapshot.metadata.short_name or snapshot.metadata.symbol}</div>'
        f'<div class="section-subtitle" style="margin-top:0.5rem; max-width: 48rem;">{truncate_text(scores.quick_summary, 190)}</div>'
        '<div style="display:flex; flex-wrap:wrap; gap:0.75rem; margin-top:1rem;">'
        f'{mini_stat("Current Price", format_currency(price))}'
        f'{mini_stat("Daily Move", format_percent(move))}'
        f'{mini_stat("Overall Score", f"{scores.total_score:.0f} / 100")}'
        f'{mini_pill_stat("Verdict", scores.verdict)}'
        f'{mini_pill_stat("Confidence", scores.confidence)}'
        "</div>"
        "</div>"
    )
    st.markdown(summary_card, unsafe_allow_html=True)


def render_section_card(title: str, score: float, max_score: float, summary: str, confidence: str, factors: list[FactorScore]) -> None:
    """Render a factor-by-factor section card."""
    st.markdown(
        (
            '<div class="detail-card">'
            f'<div class="metric-label">{title}</div>'
            f'<div class="metric-value">{score:.0f} / {max_score:.0f}</div>'
            f'<div class="pill {VERDICT_CLASSES.get(confidence.split(" • ")[0], "blue")}">{confidence}</div>'
            f'<div class="section-subtitle" style="margin-top:0.85rem;">{summary}</div>'
            '<div class="factor-table">'
            f'{"".join(render_factor_row(factor) for factor in factors)}'
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_position_advisor_card(advice: PositionAdvice) -> None:
    """Render the position advisor summary card."""
    st.markdown(
        (
            '<div class="detail-card">'
            '<div class="metric-label">Position Advisor</div>'
            f'<div class="metric-value">{advice.score:.0f} / 20</div>'
            f'<div class="pill {VERDICT_CLASSES.get(advice.recommendation, "blue")}">{advice.recommendation}</div>'
            f'<div class="section-subtitle" style="margin-top:0.85rem;">{advice.explanation}</div>'
            '<ul class="explanation-list">'
            f'{"".join(f"<li>{bullet}</li>" for bullet in advice.bullets[:4])}'
            "</ul>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_position_math_panel(advice: PositionAdvice) -> None:
    """Render the portfolio math panel."""
    math = advice.math
    allocation_display = format_percent_plain(math.current_allocation_pct) if math.current_allocation_pct is not None else "N/A"
    gain_loss_value = format_currency_full(math.unrealized_gain_loss_value) if math.unrealized_gain_loss_value is not None else "N/A"
    gain_loss_pct = format_percent(math.unrealized_gain_loss_pct) if math.unrealized_gain_loss_pct is not None else "N/A"

    rows = [
        ("Current position value", format_currency_full(math.current_position_value)),
        ("Current allocation", allocation_display),
        ("Unrealized gain/loss $", gain_loss_value),
        ("Unrealized gain/loss %", gain_loss_pct),
        ("Room before max allocation", format_currency_full(math.remaining_room_to_add)),
        ("Cash-limited add amount", f"{math.estimated_shares_can_add_with_cash} shares"),
        ("Allocation-limited add amount", f"{math.estimated_shares_can_add_with_allocation_limit} shares"),
        ("Suggested action", advice.recommendation if math.suggested_shares_to_add_now == 0 else f"{advice.recommendation} • {math.suggested_shares_to_add_now} shares"),
    ]
    rows_html = "".join(f'<div class="math-row"><span>{label}</span><strong>{value}</strong></div>' for label, value in rows)
    st.markdown(
        (
            '<div class="detail-card">'
            '<div class="section-title">Position Math</div>'
            '<div class="section-subtitle">Sizing, allocation, and add-capacity math based on your actual portfolio inputs.</div>'
            '<div class="math-grid">'
            f"{rows_html}"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_detail_explainer(scores: ScoreBundle) -> None:
    """Render the combined detailed explanation card."""
    st.markdown(
        (
            '<div class="detail-card">'
            '<div class="section-title">Why The Model Landed Here</div>'
            '<div class="section-subtitle">Each factor shows its point contribution and a short interpretation so the score stays inspectable.</div>'
            '<div class="metric-label" style="margin-top:0.5rem;">Technical Drivers</div>'
            '<ul class="explanation-list">'
            f'{"".join(f"<li>{factor.label}: {factor.display_points} points. {factor.detail}</li>" for factor in scores.technical.factors)}'
            "</ul>"
            '<div class="metric-label" style="margin-top:1rem;">Fundamental Drivers</div>'
            '<ul class="explanation-list">'
            f'{"".join(f"<li>{factor.label}: {factor.display_points} points. {factor.detail}</li>" for factor in scores.fundamental.factors)}'
            "</ul>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_factor_row(factor: FactorScore) -> str:
    """Render a compact factor row."""
    status_class = VERDICT_CLASSES.get("High" if factor.status in {"Bullish", "Strong", "Attractive", "Healthy", "Positive", "Balanced"} else "Medium" if factor.status in {"Fair", "Constructive", "Okay", "Solid", "Manageable", "Neutral", "Pullback", "Improving", "Medium"} else "Low", "blue")
    return (
        '<div class="factor-row">'
        f'<div class="factor-main"><div class="factor-name">{factor.label}</div><div class="factor-detail">{factor.detail}</div></div>'
        f'<div class="factor-meta"><span class="factor-points">{factor.display_points}</span><span class="pill {status_class}" style="margin-top:0.35rem;">{factor.status}</span></div>'
        "</div>"
    )


def mini_stat(label: str, value: str) -> str:
    """Render a small inline summary stat."""
    return f'<div class="mini-stat"><span>{label}</span><strong>{value}</strong></div>'


def mini_pill_stat(label: str, value: str) -> str:
    """Render an inline summary stat with a pill value."""
    pill_class = VERDICT_CLASSES.get(value, "blue")
    return f'<div class="mini-stat"><span>{label}</span><div class="pill {pill_class}" style="margin-top:0.4rem;">{value}</div></div>'
