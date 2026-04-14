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
    summary_state = VERDICT_CLASSES.get(scores.verdict, "blue")
    summary_card = (
        '<div class="detail-card" style="margin-bottom:1.1rem;">'
        '<div style="display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; flex-wrap:wrap;">'
        '<div style="min-width:260px; flex:1 1 480px;">'
        f'<div class="hero-eyebrow">{snapshot.metadata.symbol}</div>'
        f'<div class="hero-title" style="font-size:2.6rem;">{snapshot.metadata.short_name or snapshot.metadata.symbol}</div>'
        f'<div class="section-kicker">{truncate_text(snapshot.metadata.summary or "Live market snapshot and scoring overview.", 150)}</div>'
        f'<div class="section-subtitle" style="margin-top:0.65rem; max-width: 48rem;">{truncate_text(scores.quick_summary, 190)}</div>'
        "</div>"
        '<div style="min-width:220px; flex:0 1 280px;">'
        f'<div class="metric-label">Immediate Takeaway</div>'
        f'<div class="pill {summary_state}" style="margin-top:0;">{scores.verdict}</div>'
        f'<div class="pill {VERDICT_CLASSES.get(scores.confidence, "blue")}" style="margin-left:0.45rem; margin-top:0;">{scores.confidence} Confidence</div>'
        f'<div class="metric-value" style="margin-top:0.85rem;">{scores.total_score:.0f} / 100</div>'
        '<div class="metric-caption" style="margin-top:0.55rem;">Verdict, confidence, and score are designed to be readable at a glance before you dive into the factor cards below.</div>'
        "</div>"
        "</div>"
        '<div style="display:flex; flex-wrap:wrap; gap:0.75rem; margin-top:1.15rem;">'
        f'{mini_stat("Current Price", format_currency(price))}'
        f'{mini_stat("Daily Move", format_percent(move))}'
        f'{mini_stat("Ticker", snapshot.metadata.symbol)}'
        f'{mini_stat("Score Mix", f"{scores.technical.score:.0f}T / {scores.fundamental.score:.0f}F / {scores.position_score:.0f}P")}'
        "</div>"
        "</div>"
    )
    st.markdown(summary_card, unsafe_allow_html=True)


def render_section_card(title: str, score: float, max_score: float, summary: str, confidence: str, factors: list[FactorScore]) -> None:
    """Render a factor-by-factor section card."""
    confidence_key = confidence.split(" • ")[0]
    st.markdown(
        (
            '<div class="detail-card">'
            f'<div class="metric-label">{title}</div>'
            f'<div class="metric-value">{score:.0f} / {max_score:.0f}</div>'
            f'<div class="pill {VERDICT_CLASSES.get(confidence_key, "blue")}">{confidence}</div>'
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
    deployable_amount = advice.metrics.cash_limited_add_amount or 0.0
    suggested = (
        f"Capacity now: about {advice.metrics.estimated_shares_can_add} shares / {format_currency_full(deployable_amount)}"
        if advice.metrics.estimated_shares_can_add > 0
        else "No immediate add capacity under your current inputs"
    )
    drivers_html = "".join(
        f"<li><strong>{driver.label}</strong>: {driver.detail}</li>"
        for driver in advice.score_drivers[:4]
    )
    st.markdown(
        (
            '<div class="detail-card">'
            '<div class="metric-label">Position Advisor</div>'
            f'<div class="metric-value">{advice.score:.0f} / 20</div>'
            f'<div class="pill {VERDICT_CLASSES.get(advice.recommendation, "blue")}">{advice.recommendation}</div>'
            f'<div class="section-kicker">{suggested}</div>'
            f'<div class="section-subtitle" style="margin-top:0.65rem;">{advice.explanation}</div>'
            '<div class="metric-label" style="margin-top:0.9rem;">What This Means</div>'
            '<ul class="explanation-list">'
            f'{"".join(f"<li>{bullet}</li>" for bullet in advice.bullets[:3])}'
            "</ul>"
            '<div class="metric-label" style="margin-top:0.95rem;">Why The Advisor Scored It This Way</div>'
            f'<ul class="explanation-list">{drivers_html}</ul>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_position_math_panel(advice: PositionAdvice) -> None:
    """Render the portfolio math panel."""
    metrics = advice.metrics
    allocation_display = format_percent_plain(metrics.current_allocation_pct) if metrics.current_allocation_pct is not None else "N/A"
    gain_loss_value = format_currency_full(metrics.unrealized_gain_loss_dollars) if metrics.unrealized_gain_loss_dollars is not None else "N/A"
    gain_loss_pct = format_percent(metrics.unrealized_gain_loss_pct) if metrics.unrealized_gain_loss_pct is not None else "N/A"
    target_value = format_currency_full(metrics.target_position_value) if metrics.target_position_value is not None else "N/A"
    target_gap = format_currency_full(metrics.gap_to_target_value) if metrics.gap_to_target_value is not None else "N/A"
    max_position_value = format_currency_full(metrics.target_max_position_value) if metrics.target_max_position_value is not None else "N/A"
    room_left = format_currency_full(metrics.remaining_room_to_add) if metrics.remaining_room_to_add is not None else "N/A"
    cash_limited_add = format_currency_full(metrics.cash_limited_add_amount) if metrics.cash_limited_add_amount is not None else "N/A"
    summary_html = (
        '<div style="display:flex; flex-wrap:wrap; gap:0.65rem; margin-top:0.85rem; margin-bottom:0.3rem;">'
        f'{mini_stat("Allocation", allocation_display)}'
        f'{mini_stat("Room Left", room_left)}'
        f'{mini_stat("Can Add Now", f"{metrics.estimated_shares_can_add} sh")}'
        "</div>"
    )

    rows = [
        ("Current allocation", allocation_display),
        ("Current position value", format_currency_full(metrics.current_position_value)),
        ("Average cost basis", format_currency_full(metrics.average_cost_basis) if metrics.average_cost_basis > 0 else "N/A"),
        ("Unrealized gain/loss $", gain_loss_value),
        ("Unrealized gain/loss %", gain_loss_pct),
        ("Max allowed position value", max_position_value),
        ("Remaining room before cap", room_left),
        ("Cash-limited add amount", cash_limited_add),
        ("Estimated shares can add now", f"{metrics.estimated_shares_can_add} shares"),
    ]
    if metrics.target_position_size_pct is not None:
        rows.extend(
            [
                ("Target position value", target_value),
                ("Gap to target", target_gap),
            ]
        )
    rows.append(("Suggested action", advice.recommendation))
    rows_html = "".join(render_math_row(label, value) for label, value in rows)
    st.markdown(
        (
            '<div class="detail-card">'
            '<div class="section-title">Position Math</div>'
            '<div class="section-subtitle">A clean sizing snapshot based on portfolio value, allocation cap, available cash, and your optional target size.</div>'
            f"{summary_html}"
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
    tone = factor_tone(factor.status)
    status_class = VERDICT_CLASSES.get("High" if tone == "positive" else "Medium" if tone == "caution" else "Low", "blue")
    return (
        f'<div class="factor-row {tone}">'
        f'<div class="factor-main"><div class="factor-name">{factor.label}</div><div class="factor-detail">{factor.detail}</div></div>'
        f'<div class="factor-meta"><span class="factor-points">{factor.display_points}</span><span class="pill {status_class}" style="margin-top:0.35rem;">{factor.status}</span></div>'
        "</div>"
    )


def mini_stat(label: str, value: str) -> str:
    """Render a small inline summary stat."""
    return f'<div class="mini-stat"><span>{label}</span><strong>{value}</strong></div>'


def factor_tone(status: str) -> str:
    """Map a factor status to a UI tone."""
    if status in {"Bullish", "Strong", "Attractive", "Healthy", "Positive", "Balanced"}:
        return "positive"
    if status in {"Fair", "Constructive", "Okay", "Solid", "Manageable", "Neutral", "Pullback", "Improving", "Medium", "Oversold"}:
        return "caution"
    return "negative"


def render_math_row(label: str, value: str) -> str:
    """Render a math row with light semantic emphasis."""
    tone = "positive"
    if any(word in label.lower() for word in {"unrealized gain/loss", "suggested action"}):
        if "-" in value or "Avoid" in value or "Trim" in value:
            tone = "negative"
        elif "Hold" in value or "Add on Pullback" in value:
            tone = "caution"
    elif "allocation" in label.lower() or "room" in label.lower() or "target" in label.lower():
        tone = "caution"
    return (
        f'<div class="math-row {tone}">'
        f'<span>{label}</span>'
        f'<strong>{value}</strong>'
        "</div>"
    )
