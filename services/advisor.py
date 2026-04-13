"""Personalized position advisor logic."""

from __future__ import annotations

from dataclasses import dataclass

from config.scoring_config import POSITION_THRESHOLDS, SCORE_WEIGHTS
from services.market_data import StockSnapshot
from services.scoring import ScoreBundle
from utils.formatters import format_currency, format_percent


@dataclass
class PositionInputs:
    """User-provided portfolio context for the position advisor."""

    shares_owned: float
    average_cost_basis: float
    max_allocation_pct: float
    cash_available: float


@dataclass
class PositionAdvice:
    """Position sizing and action guidance."""

    score: float
    recommendation: str
    explanation: str
    bullets: list[str]

    def render_bullets(self) -> str:
        return f'<ul class="explanation-list">{"".join(f"<li>{item}</li>" for item in self.bullets)}</ul>'


def build_position_advice(snapshot: StockSnapshot, scores: ScoreBundle, inputs: PositionInputs) -> PositionAdvice:
    """Convert scores and user sizing inputs into practical position guidance."""
    price = snapshot.latest_price or snapshot.metadata.current_price or 0.0
    tech = scores.technical.score
    total = scores.total_score
    latest = snapshot.history.iloc[-1]
    position_value = inputs.shares_owned * price
    portfolio_proxy = position_value + inputs.cash_available
    allocation_pct = (position_value / portfolio_proxy * 100) if portfolio_proxy > 0 else 0.0
    pct_from_cost = ((price / inputs.average_cost_basis) - 1) if inputs.average_cost_basis > 0 and price > 0 else None

    is_extended = (
        latest["RSI_14"] >= POSITION_THRESHOLDS["extended_rsi"]
        or ((price / latest["SMA_50"]) - 1) >= POSITION_THRESHOLDS["extended_above_50dma_pct"]
    )
    under_target = allocation_pct < (inputs.max_allocation_pct * POSITION_THRESHOLDS["target_buffer_pct"])

    score = 0.0
    bullets = [
        f"Current position value is about {format_currency(position_value)} at {format_currency(price)} per share.",
        f"Portfolio proxy allocation is {allocation_pct:.1f}% versus your {inputs.max_allocation_pct:.1f}% max target.",
    ]

    if pct_from_cost is not None:
        bullets.append(f"Your unrealized gain/loss versus cost basis is {format_percent(pct_from_cost)}.")
    else:
        bullets.append("No active cost basis was provided, so gain/loss context is neutral.")

    if total >= 80:
        score += 9
    elif total >= 68:
        score += 7
    elif total >= 55:
        score += 5
    else:
        score += 2

    if tech >= 28 and not is_extended:
        score += 5
        bullets.append("Technical conditions are constructive without looking overly stretched.")
    elif tech >= 28:
        score += 3
        bullets.append("The chart is strong, but the stock looks a bit extended from a fresh-entry perspective.")
    elif tech >= 20:
        score += 2
        bullets.append("Technicals are mixed, which argues for patience rather than aggressive buying.")
    else:
        bullets.append("Technicals are soft enough that protecting capital matters more than adding.")

    if under_target:
        score += 4
        bullets.append("Your current allocation is still below the limit you set, leaving room to add selectively.")
    else:
        score += 1
        bullets.append("Sizing is already near or above your target band, so new buying should be more selective.")

    if pct_from_cost is not None and pct_from_cost <= POSITION_THRESHOLDS["deep_drawdown_pct"] and total < 60:
        score -= 1
        bullets.append("The position is underwater and the overall score is weak, which raises trim risk rather than averaging down.")

    if total >= 78 and under_target and not is_extended:
        recommendation = "Add"
        explanation = "The stock screens well overall, the chart is supportive, and your current sizing leaves room to build."
    elif total >= 72 and under_target and is_extended:
        recommendation = "Add on Pullback"
        explanation = "The overall setup is strong, but the near-term price action looks stretched enough to wait for a cleaner entry."
    elif total >= 55 and tech >= 20:
        recommendation = "Hold"
        explanation = "The setup is good enough to keep, but not clean enough to press hard right here."
    elif total >= 45 or (pct_from_cost is not None and pct_from_cost > 0.15 and is_extended):
        recommendation = "Trim"
        explanation = "Risk-reward is getting less favorable, especially if the stock is extended or your position is already doing the heavy lifting."
    else:
        recommendation = "Avoid New Buy"
        explanation = "The setup lacks enough technical and fundamental support for fresh capital right now."

    return PositionAdvice(score=max(0, min(score, SCORE_WEIGHTS["position"])), recommendation=recommendation, explanation=explanation, bullets=bullets)
