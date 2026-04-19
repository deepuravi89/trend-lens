"""Portfolio-aware position advisor logic."""

from __future__ import annotations

from dataclasses import dataclass

from config.scoring_config import POSITION_THRESHOLDS, SCORE_WEIGHTS
from services.market_data import StockSnapshot
from services.scoring import ScoreBundle, TechnicalSetup
from utils.calculations import floor_shares
from utils.formatters import format_currency_full, format_percent, format_percent_plain


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
class PositionDerivedMetrics:
    """Derived portfolio math used for recommendations and UI display."""

    current_price: float
    current_position_value: float
    current_allocation_pct: float | None
    max_portfolio_allocation_pct: float
    target_max_position_value: float | None
    remaining_room_to_add: float | None
    cash_limited_add_amount: float | None
    estimated_shares_can_add: int
    unrealized_gain_loss_dollars: float | None
    unrealized_gain_loss_pct: float | None
    target_position_size_pct: float | None
    target_position_value: float | None
    gap_to_target_value: float | None
    average_cost_basis: float
    has_valid_portfolio_value: bool
    is_new_position: bool
    target_was_clamped: bool = False


@dataclass
class AdvisorScoreDriver:
    """A single reason the advisor score moved up or down."""

    label: str
    points: float
    detail: str


@dataclass
class PositionAdvice:
    """Position sizing and action guidance."""

    score: float
    recommendation: str
    explanation: str
    decision_basis: str
    bullets: list[str]
    metrics: PositionDerivedMetrics
    score_drivers: list[AdvisorScoreDriver]
    technical_setup: TechnicalSetup

    def render_bullets(self) -> str:
        return f'<ul class="explanation-list">{"".join(f"<li>{item}</li>" for item in self.bullets)}</ul>'


def build_position_advice(snapshot: StockSnapshot, scores: ScoreBundle, inputs: PositionInputs) -> PositionAdvice:
    """Convert scores and portfolio inputs into practical position guidance."""
    price = snapshot.latest_price or snapshot.metadata.current_price or 0.0
    latest = snapshot.history.iloc[-1]
    base_total = scores.total_score
    technical_score = scores.technical.score
    fundamental_score = scores.fundamental.score
    technical_setup = scores.technical.setup or TechnicalSetup(
        label="Mixed Setup",
        summary="Technical signals are incomplete, so the chart is being treated as mixed.",
        reasoning_bullets=["The classifier could not resolve a cleaner setup type from the available signals."],
        takeaway="Usually better for waiting than for forcing a new decision.",
        strength="Low",
        action_bias="Hold",
    )

    metrics = derive_position_metrics(price, inputs)

    is_extended = (
        latest["RSI_14"] >= POSITION_THRESHOLDS["extended_rsi"]
        or latest["DIST_FROM_50DMA"] >= POSITION_THRESHOLDS["extended_above_50dma_pct"]
    )
    strong_total = base_total >= POSITION_THRESHOLDS["strong_add_score"]
    decent_total = base_total >= POSITION_THRESHOLDS["min_add_score"]
    weak_total = base_total < POSITION_THRESHOLDS["trim_floor"]

    score_drivers: list[AdvisorScoreDriver] = []
    score = 0.0

    if not metrics.has_valid_portfolio_value:
        score_drivers.append(AdvisorScoreDriver("Missing portfolio value", 1.0, "Allocation math is unavailable until total portfolio value is provided."))
        score = 1.0
    else:
        if technical_setup.label == "Strong Uptrend":
            score += 4
            score_drivers.append(AdvisorScoreDriver("Setup read", 4.0, "Strong Uptrend: the trend is aligned and the stock is not obviously overstretched."))
        elif technical_setup.label == "Constructive but Extended":
            score += 1
            score_drivers.append(AdvisorScoreDriver("Setup read", 1.0, "Constructive but Extended: the stock still looks strong, but entry quality is less attractive here."))
        elif technical_setup.label == "Recovery Setup":
            score += 2
            score_drivers.append(AdvisorScoreDriver("Setup read", 2.0, "Recovery Setup: momentum is improving, but the longer-term trend is still not fully repaired."))
        elif technical_setup.label == "Mixed Setup":
            score += 2
            score_drivers.append(AdvisorScoreDriver("Setup read", 2.0, "Mixed Setup: signals are usable, but not aligned well enough for high conviction."))
        else:
            score += 0
            score_drivers.append(AdvisorScoreDriver("Setup read", 0.0, "Weak Downtrend: the trend and momentum picture still argues for caution."))

        if strong_total:
            score += 8
            score_drivers.append(AdvisorScoreDriver("Score quality", 8.0, "The overall score is strong enough to support adding if sizing allows it."))
        elif decent_total:
            score += 6
            score_drivers.append(AdvisorScoreDriver("Score quality", 6.0, "The overall score is decent, but conviction is not at the top end."))
        elif base_total >= POSITION_THRESHOLDS["hold_floor"]:
            score += 4
            score_drivers.append(AdvisorScoreDriver("Score quality", 4.0, "The overall score is good enough to hold, but not strong enough to press."))
        else:
            score += 1
            score_drivers.append(AdvisorScoreDriver("Score quality", 1.0, "The overall score is weak, so fresh buying should stay cautious."))

        if metrics.remaining_room_to_add is not None and metrics.remaining_room_to_add > 0:
            if metrics.current_allocation_pct is not None and metrics.current_allocation_pct * 100 < inputs.max_portfolio_allocation_pct:
                score += 5
                score_drivers.append(AdvisorScoreDriver("Sizing room", 5.0, "You still have real room under your max allocation cap."))
        else:
            score -= 2
            score_drivers.append(AdvisorScoreDriver("Sizing room", -2.0, "The position is already at or above your max allocation cap."))

        if metrics.current_allocation_pct is not None and metrics.current_allocation_pct > (inputs.max_portfolio_allocation_pct / 100) + POSITION_THRESHOLDS["oversized_buffer_pct"]:
            score -= 2
            score_drivers.append(AdvisorScoreDriver("Current sizing", -2.0, "The position is already above the max allocation you set."))

        if metrics.unrealized_gain_loss_pct is not None and metrics.unrealized_gain_loss_pct >= POSITION_THRESHOLDS["trim_gain_pct"] and is_extended:
            score -= 2
            score_drivers.append(AdvisorScoreDriver("Reward vs. risk", -2.0, "A large gain plus extension tilts the setup toward protecting capital."))

        if metrics.unrealized_gain_loss_pct is not None and metrics.unrealized_gain_loss_pct <= POSITION_THRESHOLDS["deep_drawdown_pct"] and weak_total:
            score -= 1
            score_drivers.append(AdvisorScoreDriver("Reward vs. risk", -1.0, "A deep drawdown and weak setup reduce the case for averaging down."))

        if metrics.target_was_clamped:
            score_drivers.append(AdvisorScoreDriver("Target size", 0.0, "Target position size exceeded the max cap, so the model capped it at the max allocation."))

    recommendation, explanation = recommend_action(
        base_total=base_total,
        is_extended=is_extended,
        weak_total=weak_total,
        technical_score=technical_score,
        fundamental_score=fundamental_score,
        setup=technical_setup,
        metrics=metrics,
    )

    bullets = build_position_bullets(metrics, recommendation, is_extended, technical_setup)
    decision_basis = build_decision_basis(
        setup=technical_setup,
        recommendation=recommendation,
        base_total=base_total,
        fundamental_score=fundamental_score,
        is_extended=is_extended,
        metrics=metrics,
    )

    return PositionAdvice(
        score=max(0, min(score, SCORE_WEIGHTS["position"])),
        recommendation=recommendation,
        explanation=explanation,
        decision_basis=decision_basis,
        bullets=bullets,
        metrics=metrics,
        score_drivers=score_drivers,
        technical_setup=technical_setup,
    )


def derive_position_metrics(price: float, inputs: PositionInputs) -> PositionDerivedMetrics:
    """Compute portfolio-based position metrics safely."""
    current_position_value = inputs.shares_owned * price
    has_valid_portfolio_value = inputs.total_portfolio_value > 0
    current_allocation_pct = (
        current_position_value / inputs.total_portfolio_value
        if has_valid_portfolio_value
        else None
    )

    target_max_position_value = (
        inputs.total_portfolio_value * inputs.max_portfolio_allocation_pct / 100
        if has_valid_portfolio_value
        else None
    )
    remaining_room_to_add = (
        max(0.0, target_max_position_value - current_position_value)
        if target_max_position_value is not None
        else None
    )
    cash_limited_add_amount = (
        min(inputs.cash_available_to_deploy, remaining_room_to_add)
        if remaining_room_to_add is not None
        else None
    )
    estimated_shares_can_add = floor_shares(cash_limited_add_amount, price)

    unrealized_gain_loss_dollars = (
        inputs.shares_owned * (price - inputs.average_cost_basis)
        if inputs.shares_owned > 0 and inputs.average_cost_basis > 0
        else None
    )
    unrealized_gain_loss_pct = (
        (price / inputs.average_cost_basis) - 1
        if inputs.shares_owned > 0 and inputs.average_cost_basis > 0 and price > 0
        else None
    )

    target_was_clamped = False
    target_position_size_pct = inputs.target_position_size_pct
    if target_position_size_pct is not None and target_position_size_pct > inputs.max_portfolio_allocation_pct:
        target_position_size_pct = inputs.max_portfolio_allocation_pct
        target_was_clamped = True

    target_position_value = (
        inputs.total_portfolio_value * target_position_size_pct / 100
        if has_valid_portfolio_value and target_position_size_pct is not None
        else None
    )
    gap_to_target_value = (
        max(0.0, target_position_value - current_position_value)
        if target_position_value is not None
        else None
    )

    return PositionDerivedMetrics(
        current_price=price,
        current_position_value=current_position_value,
        current_allocation_pct=current_allocation_pct,
        max_portfolio_allocation_pct=inputs.max_portfolio_allocation_pct,
        target_max_position_value=target_max_position_value,
        remaining_room_to_add=remaining_room_to_add,
        cash_limited_add_amount=cash_limited_add_amount,
        estimated_shares_can_add=estimated_shares_can_add,
        unrealized_gain_loss_dollars=unrealized_gain_loss_dollars,
        unrealized_gain_loss_pct=unrealized_gain_loss_pct,
        target_position_size_pct=target_position_size_pct,
        target_position_value=target_position_value,
        gap_to_target_value=gap_to_target_value,
        average_cost_basis=inputs.average_cost_basis,
        has_valid_portfolio_value=has_valid_portfolio_value,
        is_new_position=inputs.shares_owned <= 0,
        target_was_clamped=target_was_clamped,
    )


def recommend_action(
    *,
    base_total: float,
    is_extended: bool,
    weak_total: bool,
    technical_score: float,
    fundamental_score: float,
    setup: TechnicalSetup,
    metrics: PositionDerivedMetrics,
) -> tuple[str, str]:
    """Resolve the recommendation label and explanation."""
    if not metrics.has_valid_portfolio_value:
        if weak_total:
            return "Avoid New Buy", f"{setup.label} with missing portfolio value is not strong enough to support a fresh buy."
        return "Hold", f"{setup.label}, but the sizing call stays limited until you provide portfolio value."

    oversized = (
        metrics.current_allocation_pct is not None
        and metrics.current_allocation_pct * 100 > metrics.max_portfolio_allocation_pct + POSITION_THRESHOLDS["oversized_buffer_pct"] * 100
    )
    near_target = (
        metrics.target_position_value is not None
        and metrics.current_position_value >= metrics.target_position_value * POSITION_THRESHOLDS["near_target_buffer_pct"]
    )
    limited_room = (
        metrics.remaining_room_to_add is not None
        and metrics.target_max_position_value is not None
        and metrics.remaining_room_to_add <= metrics.target_max_position_value * POSITION_THRESHOLDS["limited_room_pct_of_portfolio"]
    )
    can_add_now = metrics.estimated_shares_can_add > 0

    if oversized and (setup.label == "Weak Downtrend" or weak_total or is_extended):
        return "Trim", "The position is above your size limit, and the current setup does not justify staying that large."

    if setup.label == "Weak Downtrend":
        if oversized:
            return "Trim", "Weak Downtrend plus oversized positioning makes trimming the cleaner risk decision here."
        return "Avoid New Buy", "Weak Downtrend means the trend and momentum picture still does not justify fresh buying."

    if setup.label == "Constructive but Extended":
        if (
            (base_total >= POSITION_THRESHOLDS["min_add_score"] or (technical_score >= 30 and fundamental_score >= 30))
            and can_add_now
        ):
            return "Add on Pullback", "Constructive but Extended means the stock still looks strong, but entry quality should improve on a pullback."
        if base_total >= POSITION_THRESHOLDS["hold_floor"]:
            return "Hold", "The setup still has some strength, but extension and current sizing do not support adding here."
        return "Avoid New Buy", "The stock has some underlying strength, but not enough overall support to justify chasing an extended move."

    if setup.label == "Strong Uptrend":
        if (
            base_total >= POSITION_THRESHOLDS["min_add_score"]
            and technical_score >= 30
            and fundamental_score >= 30
            and can_add_now
            and not near_target
            and not limited_room
        ):
            return "Add", "Strong Uptrend, solid score quality, and room under your cap all support building here."
        if base_total >= POSITION_THRESHOLDS["strong_add_score"] and can_add_now and not near_target:
            return "Add", "Strong Uptrend and room under your cap support building here."
        if base_total >= POSITION_THRESHOLDS["min_add_score"] and can_add_now:
            if limited_room or near_target:
                return "Add Small", "Strong Uptrend, but your remaining room or target gap argues for a measured add rather than a full one."
            return "Add Small", "The trend is healthy, but the edge is not strong enough to justify pressing harder."
        if base_total >= POSITION_THRESHOLDS["hold_floor"]:
            return "Hold", "The trend is still supportive, but current sizing or score quality does not call for a new add."
        return "Avoid New Buy", "The chart looks better than the full score mix, but not enough to justify a fresh buy here."

    if setup.label == "Recovery Setup":
        if (
            base_total >= POSITION_THRESHOLDS["min_add_score"]
            and fundamental_score >= 22
            and technical_score >= 20
            and can_add_now
            and not near_target
        ):
            return "Add Small", "Recovery Setup means near-term action is improving, but the unconfirmed long-term trend still argues for measured sizing."
        if base_total >= POSITION_THRESHOLDS["hold_floor"]:
            return "Hold", "The stock is stabilizing, but the longer-term trend is not repaired enough to justify a larger add yet."
        return "Avoid New Buy", "The stock is trying to recover, but the overall support is still too thin for fresh capital."

    if setup.label == "Mixed Setup":
        if oversized and weak_total:
            return "Trim", "Mixed Setup plus oversized positioning makes the current holding harder to justify."
        if base_total >= POSITION_THRESHOLDS["hold_floor"] or near_target:
            return "Hold", "Mixed Setup means the edge is limited, so holding steady makes more sense than forcing a new decision."
        return "Avoid New Buy", "Mixed Setup means the chart does not offer a clean enough edge for fresh buying."

    if oversized or (is_extended and weak_total):
        return "Trim", "The position is either too large for your rules or too stretched for a weakening setup."
    if base_total >= POSITION_THRESHOLDS["hold_floor"] or near_target:
        return "Hold", "The stock is reasonable to keep, but timing or position sizing does not support pressing harder here."
    return "Avoid New Buy", "The setup does not offer enough technical or fundamental support for fresh buying right now."


def build_position_bullets(
    metrics: PositionDerivedMetrics,
    recommendation: str,
    is_extended: bool,
    setup: TechnicalSetup,
) -> list[str]:
    """Generate plain-English explanation bullets."""
    bullets: list[str] = []

    if metrics.current_allocation_pct is None:
        bullets.append("Allocation math is unavailable because portfolio value was not provided or is zero.")
    else:
        bullets.append(
            f"You are currently at {format_percent_plain(metrics.current_allocation_pct)} allocation versus a {metrics.max_portfolio_allocation_pct:.1f}% max cap."
        )

    bullets.append(
        f"Setup read: {setup.label}. {setup.summary}"
    )

    if metrics.remaining_room_to_add is not None:
        bullets.append(
            f"You have room to add about {format_currency_full(metrics.remaining_room_to_add)} before reaching your allocation limit."
        )

    if metrics.cash_limited_add_amount is not None:
        bullets.append(
            f"Based on available cash, you could deploy about {format_currency_full(metrics.cash_limited_add_amount)} and add roughly {metrics.estimated_shares_can_add} shares at the current price."
        )

    if metrics.target_position_value is not None and metrics.gap_to_target_value is not None:
        bullets.append(
            f"Your target position value is {format_currency_full(metrics.target_position_value)}, leaving about {format_currency_full(metrics.gap_to_target_value)} left to reach it."
        )
    elif metrics.target_was_clamped:
        bullets.append("Your target size was above the max cap, so the advisor treated the cap as the effective target.")

    if metrics.is_new_position:
        bullets.append("You do not currently hold shares, so this is being treated as a fresh position candidate.")
    elif metrics.unrealized_gain_loss_dollars is not None and metrics.unrealized_gain_loss_pct is not None:
        bullets.append(
            f"Your unrealized gain/loss is {format_currency_full(metrics.unrealized_gain_loss_dollars)} ({format_percent(metrics.unrealized_gain_loss_pct)})."
        )
    else:
        bullets.append("Gain/loss math is unavailable because shares are held without a usable average cost basis.")

    if is_extended:
        bullets.append("The stock is technically extended, so waiting for a pullback may improve entry quality.")
    elif recommendation in {"Add", "Add Small"}:
        bullets.append("The stock is not obviously extended, which makes a staged add easier to justify if the rest of the setup holds.")

    return bullets


def build_decision_basis(
    *,
    setup: TechnicalSetup,
    recommendation: str,
    base_total: float,
    fundamental_score: float,
    is_extended: bool,
    metrics: PositionDerivedMetrics,
) -> str:
    """Build a compact user-facing summary of the recommendation basis."""
    parts = [setup.label]

    if recommendation == "Add":
        parts.append("good overall score")
        if metrics.remaining_room_to_add:
            parts.append("room under cap")
        if fundamental_score >= 30:
            parts.append("supportive fundamentals")
    elif recommendation == "Add Small":
        if setup.label == "Recovery Setup":
            parts.append("improving momentum")
            parts.append("long-term trend still unconfirmed")
        else:
            parts.append("supportive setup")
            if metrics.target_position_value is not None:
                parts.append("measured sizing")
    elif recommendation == "Add on Pullback":
        parts.append("strong stock quality")
        parts.append("entry quality is weaker here")
    elif recommendation == "Hold":
        parts.append("limited edge")
        if metrics.target_position_value is not None and metrics.current_position_value >= metrics.target_position_value * POSITION_THRESHOLDS["near_target_buffer_pct"]:
            parts.append("already near target")
        elif is_extended:
            parts.append("not a clean entry")
    elif recommendation == "Trim":
        parts.append("current sizing is heavy")
        if is_extended:
            parts.append("extension raises risk")
        else:
            parts.append("setup does not justify the size")
    else:
        parts.append("no clean reason for fresh buying")
        if is_extended:
            parts.append("entry quality is weak")

    return " + ".join(parts[:3])
