"""Portfolio-aware position advisor logic."""

from __future__ import annotations

from dataclasses import dataclass

from config.scoring_config import POSITION_THRESHOLDS, SCORE_WEIGHTS
from services.market_data import StockSnapshot
from services.scoring import ScoreBundle
from utils.calculations import floor_shares
from utils.formatters import format_currency, format_currency_full, format_percent, format_percent_plain


@dataclass
class PositionInputs:
    """User-provided portfolio context for the position advisor."""

    total_portfolio_value: float
    shares_owned: float
    average_cost_basis: float
    max_portfolio_allocation_pct: float
    cash_available_to_deploy: float
    target_position_size_pct: float | None = None


@dataclass
class PositionMath:
    """Concrete portfolio math shown in the dashboard."""

    current_position_value: float
    current_allocation_pct: float | None
    target_max_position_value: float
    remaining_room_to_add: float
    unrealized_gain_loss_value: float | None
    unrealized_gain_loss_pct: float | None
    estimated_shares_can_add_with_cash: int
    estimated_shares_can_add_with_allocation_limit: int
    suggested_shares_to_add_now: int


@dataclass
class PositionAdvice:
    """Position sizing and action guidance."""

    score: float
    recommendation: str
    explanation: str
    bullets: list[str]
    math: PositionMath

    def render_bullets(self) -> str:
        return f'<ul class="explanation-list">{"".join(f"<li>{item}</li>" for item in self.bullets)}</ul>'


def build_position_advice(snapshot: StockSnapshot, scores: ScoreBundle, inputs: PositionInputs) -> PositionAdvice:
    """Convert scores and portfolio inputs into practical position guidance."""
    price = snapshot.latest_price or snapshot.metadata.current_price or 0.0
    latest = snapshot.history.iloc[-1]
    technical_score = scores.technical.score
    base_total = scores.total_score

    current_position_value = inputs.shares_owned * price
    current_allocation_pct = (
        current_position_value / inputs.total_portfolio_value
        if inputs.total_portfolio_value > 0
        else None
    )
    target_max_position_value = inputs.total_portfolio_value * (inputs.max_portfolio_allocation_pct / 100)
    remaining_room_to_add = max(0.0, target_max_position_value - current_position_value)

    unrealized_gain_loss_value = (
        inputs.shares_owned * (price - inputs.average_cost_basis)
        if inputs.shares_owned > 0 and inputs.average_cost_basis > 0
        else None
    )
    unrealized_gain_loss_pct = (
        (price / inputs.average_cost_basis) - 1
        if inputs.average_cost_basis > 0 and price > 0
        else None
    )

    cash_limited_shares = floor_shares(inputs.cash_available_to_deploy, price)
    allocation_limited_shares = floor_shares(remaining_room_to_add, price)

    is_extended = (
        latest["RSI_14"] >= POSITION_THRESHOLDS["extended_rsi"]
        or latest["DIST_FROM_50DMA"] >= POSITION_THRESHOLDS["extended_above_50dma_pct"]
    )
    under_max = current_allocation_pct is None or current_allocation_pct < (inputs.max_portfolio_allocation_pct / 100)

    score = 0.0
    if base_total >= POSITION_THRESHOLDS["strong_add_score"]:
        score += 9
    elif base_total >= POSITION_THRESHOLDS["min_add_score"]:
        score += 7
    elif base_total >= POSITION_THRESHOLDS["hold_floor"]:
        score += 5
    elif base_total >= POSITION_THRESHOLDS["trim_floor"]:
        score += 3
    else:
        score += 1

    if under_max and remaining_room_to_add > 0:
        score += 5
    elif remaining_room_to_add <= 0:
        score += 0
    else:
        score += 2

    if technical_score >= 30 and not is_extended:
        score += 4
    elif technical_score >= 26:
        score += 2
    elif technical_score < 20:
        score -= 1

    if unrealized_gain_loss_pct is not None and unrealized_gain_loss_pct >= POSITION_THRESHOLDS["trim_gain_pct"] and is_extended:
        score -= 2
    if unrealized_gain_loss_pct is not None and unrealized_gain_loss_pct <= POSITION_THRESHOLDS["deep_drawdown_pct"] and base_total < 60:
        score -= 1

    recommendation = "Avoid New Buy"
    explanation = "The setup lacks enough support for fresh capital right now."
    suggested_shares = 0

    if base_total >= POSITION_THRESHOLDS["strong_add_score"] and under_max and not is_extended and allocation_limited_shares > 0:
        recommendation = "Add"
        explanation = "The stock screens well overall, the chart is constructive, and your portfolio still has room under the cap."
        suggested_shares = suggested_share_count(inputs, price, remaining_room_to_add, full_add=True)
    elif base_total >= POSITION_THRESHOLDS["min_add_score"] and under_max and allocation_limited_shares > 0:
        if is_extended:
            recommendation = "Add on Pullback"
            explanation = "The stock screens well, but RSI and price extension suggest waiting for a better entry."
        else:
            recommendation = "Add Small"
            explanation = "The setup is good enough to build the position, but a smaller add keeps risk measured."
            suggested_shares = suggested_share_count(inputs, price, remaining_room_to_add, full_add=False)
    elif base_total >= POSITION_THRESHOLDS["hold_floor"]:
        recommendation = "Hold"
        explanation = "The setup is respectable, but the timing or sizing case is not strong enough to press aggressively."
    elif (
        base_total < POSITION_THRESHOLDS["hold_floor"]
        and unrealized_gain_loss_pct is not None
        and unrealized_gain_loss_pct > 0
    ) or not under_max:
        recommendation = "Trim"
        explanation = "Risk-reward is less favorable here, especially if the position is already large or the stock is extended."

    math = PositionMath(
        current_position_value=current_position_value,
        current_allocation_pct=current_allocation_pct,
        target_max_position_value=target_max_position_value,
        remaining_room_to_add=remaining_room_to_add,
        unrealized_gain_loss_value=unrealized_gain_loss_value,
        unrealized_gain_loss_pct=unrealized_gain_loss_pct,
        estimated_shares_can_add_with_cash=cash_limited_shares,
        estimated_shares_can_add_with_allocation_limit=allocation_limited_shares,
        suggested_shares_to_add_now=suggested_shares,
    )

    bullets = [
        allocation_bullet(current_allocation_pct, inputs.max_portfolio_allocation_pct),
        f"You have room to add approximately {format_currency_full(remaining_room_to_add)} before reaching your cap.",
        f"Cash on hand can fund about {cash_limited_shares} shares at the current price, while the allocation limit allows about {allocation_limited_shares} shares.",
    ]
    if unrealized_gain_loss_pct is not None and unrealized_gain_loss_value is not None:
        bullets.append(
            f"Your unrealized gain/loss is {format_currency_full(unrealized_gain_loss_value)} ({format_percent(unrealized_gain_loss_pct)})."
        )
    else:
        bullets.append("Cost basis is missing or zero, so unrealized gain/loss is not being used for recommendation pressure.")
    if is_extended:
        bullets.append("The stock is extended relative to its recent trend, which lowers the appeal of chasing here.")
    elif technical_score >= 28:
        bullets.append("Technicals are constructive without obvious extension, which helps the add case if sizing allows it.")
    else:
        bullets.append("Technical alignment is mixed, so the model leans toward patience instead of aggressive buying.")

    return PositionAdvice(
        score=max(0, min(score, SCORE_WEIGHTS["position"])),
        recommendation=recommendation,
        explanation=explanation,
        bullets=bullets,
        math=math,
    )


def allocation_bullet(current_allocation_pct: float | None, max_pct: float) -> str:
    """Generate a plain-English allocation sentence."""
    if current_allocation_pct is None:
        return "Portfolio allocation is unavailable until a total portfolio value is provided."
    return (
        f"You are currently at {format_percent_plain(current_allocation_pct)} allocation "
        f"versus a {max_pct:.1f}% max limit."
    )


def suggested_share_count(inputs: PositionInputs, price: float, remaining_room_to_add: float, full_add: bool) -> int:
    """Estimate a practical share add size bounded by cash, max allocation, and optional target size."""
    if price <= 0:
        return 0

    limit_room = remaining_room_to_add
    cash_room = inputs.cash_available_to_deploy

    if inputs.target_position_size_pct is not None and inputs.total_portfolio_value > 0:
        target_value = inputs.total_portfolio_value * (inputs.target_position_size_pct / 100)
        owned_value = inputs.shares_owned * price
        target_room = max(0.0, target_value - owned_value)
        sizing_room = min(limit_room, cash_room, target_room) if target_room > 0 else 0.0
    else:
        sizing_room = min(limit_room, cash_room)

    if not full_add:
        sizing_room *= POSITION_THRESHOLDS["small_add_fraction"]
    return floor_shares(sizing_room, price)
