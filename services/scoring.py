"""Transparent technical and fundamental scoring logic."""

from __future__ import annotations

from dataclasses import dataclass

from config.scoring_config import (
    CONFIDENCE_THRESHOLDS,
    FUNDAMENTAL_FACTORS,
    FUNDAMENTAL_THRESHOLDS,
    SCORE_WEIGHTS,
    TECHNICAL_FACTORS,
    TECHNICAL_THRESHOLDS,
    VERDICT_BANDS,
)
from services.market_data import StockSnapshot
from utils.formatters import format_currency, format_number, format_percent, format_points


@dataclass
class FactorScore:
    """A single factor contribution inside a section."""

    key: str
    label: str
    points: float
    max_points: float
    detail: str
    status: str
    available: bool = True

    @property
    def display_points(self) -> str:
        return format_points(self.points)


@dataclass
class SectionScore:
    """A score section with factors and confidence."""

    score: float
    max_score: float
    summary: str
    confidence: str
    completeness_ratio: float
    factors: list[FactorScore]
    setup: TechnicalSetup | None = None


@dataclass
class TechnicalSetup:
    """Readable classification for the current technical structure."""

    label: str
    summary: str
    reasoning_bullets: list[str]
    takeaway: str
    strength: str
    action_bias: str


@dataclass
class ScoreBundle:
    """Full score output for the dashboard."""

    technical: SectionScore
    fundamental: SectionScore
    total_score: float
    verdict: str
    quick_summary: str
    confidence: str
    position_score: float = 0.0


def build_score_bundle(snapshot: StockSnapshot) -> ScoreBundle:
    """Compute technical and fundamental scores before position overlay."""
    technical = score_technical(snapshot)
    fundamental = score_fundamental(snapshot)
    total_score = technical.score + fundamental.score
    confidence = merge_confidence([technical.confidence, fundamental.confidence])
    verdict = resolve_verdict(total_score)
    quick_summary = build_quick_summary(technical, fundamental)
    return ScoreBundle(
        technical=technical,
        fundamental=fundamental,
        total_score=total_score,
        verdict=verdict,
        quick_summary=quick_summary,
        confidence=confidence,
        position_score=0.0,
    )


def finalize_total_score(scores: ScoreBundle, position_score: float) -> ScoreBundle:
    """Fold the position advisor into the final 100-point score."""
    total_score = scores.technical.score + scores.fundamental.score + position_score
    return ScoreBundle(
        technical=scores.technical,
        fundamental=scores.fundamental,
        total_score=total_score,
        verdict=resolve_verdict(total_score),
        quick_summary=scores.quick_summary,
        confidence=merge_confidence([scores.technical.confidence, scores.fundamental.confidence]),
        position_score=position_score,
    )


def resolve_verdict(total_score: float) -> str:
    """Resolve total score into a simple verdict band."""
    for label, floor in VERDICT_BANDS.items():
        if total_score >= floor:
            return label
    return "Avoid"


def score_technical(snapshot: StockSnapshot) -> SectionScore:
    """Score price trend and momentum indicators out of 40."""
    latest = snapshot.history.iloc[-1]
    price = float(latest["Close"])
    sma50 = float(latest["SMA_50"])
    sma200 = float(latest["SMA_200"])
    rsi = float(latest["RSI_14"])
    macd = float(latest["MACD"])
    signal = float(latest["MACD_SIGNAL"])
    hist = float(latest["MACD_HIST"])
    volume = float(latest["Volume"])
    avg_volume = float(latest["AVG_VOLUME_20"])
    dist_50 = float(latest["DIST_FROM_50DMA"])
    dist_200 = float(latest["DIST_FROM_200DMA"])

    factors: list[FactorScore] = []

    factors.append(
        score_binary_factor(
            label="Price vs 200DMA",
            condition=price > sma200,
            max_points=TECHNICAL_FACTORS["price_vs_200dma"],
            positive_detail=f"Price is {format_percent(dist_200)} above the 200DMA, supporting the primary uptrend.",
            negative_detail=f"Price is {format_percent(dist_200)} versus the 200DMA, which weakens long-term trend confidence.",
        )
    )
    factors.append(
        score_binary_factor(
            label="Price vs 50DMA",
            condition=price > sma50,
            max_points=TECHNICAL_FACTORS["price_vs_50dma"],
            positive_detail=f"Price is {format_percent(dist_50)} above the 50DMA, so near-term control remains constructive.",
            negative_detail=f"Price is {format_percent(dist_50)} versus the 50DMA, showing short-term momentum has softened.",
        )
    )
    factors.append(
        score_binary_factor(
            label="50DMA vs 200DMA",
            condition=sma50 > sma200,
            max_points=TECHNICAL_FACTORS["trend_alignment"],
            positive_detail="The 50DMA is above the 200DMA, a classic uptrend alignment.",
            negative_detail="The 50DMA is below the 200DMA, so trend structure is not yet fully constructive.",
        )
    )
    factors.append(score_rsi_factor(rsi))
    factors.append(score_macd_factor(macd, signal, hist))
    factors.append(score_volume_factor(volume, avg_volume, price > sma50))
    factors.append(score_distance_factor(dist_50, dist_200, price > sma50, sma50 > sma200))

    score = min(sum(f.points for f in factors), SCORE_WEIGHTS["technical"])
    alignment_ratio = sum(1 for factor in factors if factor.points >= factor.max_points * 0.6) / len(factors)
    confidence = confidence_from_ratios(1.0, alignment_ratio)
    setup = classify_technical_setup(
        price=price,
        sma50=sma50,
        sma200=sma200,
        rsi=rsi,
        macd=macd,
        signal=signal,
        hist=hist,
        dist_50=dist_50,
        dist_200=dist_200,
    )

    return SectionScore(
        score=score,
        max_score=SCORE_WEIGHTS["technical"],
        summary=setup.summary,
        confidence=confidence,
        completeness_ratio=1.0,
        factors=factors,
        setup=setup,
    )


def score_fundamental(snapshot: StockSnapshot) -> SectionScore:
    """Score valuation, growth, quality, and balance sheet metrics out of 40."""
    fundamentals = snapshot.metadata.fundamentals
    factors = [
        score_pe_factor("Trailing P/E", fundamentals.get("trailingPE"), FUNDAMENTAL_FACTORS["trailing_pe"], trailing=True),
        score_pe_factor("Forward P/E", fundamentals.get("forwardPE"), FUNDAMENTAL_FACTORS["forward_pe"], trailing=False),
        score_peg_factor(fundamentals.get("pegRatio")),
        score_roe_factor(fundamentals.get("returnOnEquity")),
        score_debt_factor(fundamentals.get("debtToEquity")),
        score_growth_factor("Revenue growth", fundamentals.get("revenueGrowth")),
        score_growth_factor("EPS growth", fundamentals.get("earningsGrowth")),
        score_cash_flow_factor(fundamentals.get("freeCashflow"), fundamentals.get("operatingCashflow")),
        score_margin_factor(
            fundamentals.get("grossMargins"),
            fundamentals.get("operatingMargins"),
            fundamentals.get("profitMargins"),
        ),
    ]

    available_count = sum(1 for factor in factors if factor.available)
    completeness_ratio = available_count / len(factors)
    raw_score = sum(f.points for f in factors)

    completeness_factor = score_completeness_factor(completeness_ratio)
    factors.append(completeness_factor)

    if completeness_ratio < 0.45:
        adjusted_score = min(raw_score + completeness_factor.points, 20.0)
    elif completeness_ratio < 0.65:
        adjusted_score = min(raw_score + completeness_factor.points, 28.0)
    else:
        adjusted_score = raw_score + completeness_factor.points

    adjusted_score = min(adjusted_score, SCORE_WEIGHTS["fundamental"])
    alignment_ratio = sum(1 for factor in factors if factor.points >= max(factor.max_points * 0.6, 1)) / len(factors)
    confidence = confidence_from_ratios(completeness_ratio, alignment_ratio)

    if adjusted_score >= 30 and completeness_ratio >= 0.7:
        summary = "Fundamentals are broadly supportive, with useful coverage across valuation, quality, and growth."
    elif adjusted_score >= 22:
        summary = "Fundamentals are mixed or only partially complete, so conviction should stay measured."
    else:
        summary = "The fundamental picture is weak, expensive, or too sparse to support strong confidence."

    return SectionScore(
        score=adjusted_score,
        max_score=SCORE_WEIGHTS["fundamental"],
        summary=summary,
        confidence=confidence,
        completeness_ratio=completeness_ratio,
        factors=factors,
    )


def merge_confidence(labels: list[str]) -> str:
    """Merge section-level confidence values into a dashboard label."""
    if "Low" in labels:
        return "Low"
    if "Medium" in labels:
        return "Medium"
    return "High"


def confidence_from_ratios(completeness_ratio: float, alignment_ratio: float) -> str:
    """Resolve confidence from data completeness and signal alignment."""
    if (
        completeness_ratio >= CONFIDENCE_THRESHOLDS["high_completeness_ratio"]
        and alignment_ratio >= CONFIDENCE_THRESHOLDS["high_alignment_ratio"]
    ):
        return "High"
    if (
        completeness_ratio >= CONFIDENCE_THRESHOLDS["medium_completeness_ratio"]
        and alignment_ratio >= CONFIDENCE_THRESHOLDS["medium_alignment_ratio"]
    ):
        return "Medium"
    return "Low"


def build_quick_summary(technical: SectionScore, fundamental: SectionScore) -> str:
    """Create the above-the-fold summary line."""
    return (
        f"Technicals read as {technical.summary.lower()} "
        f"Fundamentals are {fundamental.summary.lower()}"
    )


def classify_technical_setup(
    *,
    price: float,
    sma50: float,
    sma200: float,
    rsi: float,
    macd: float,
    signal: float,
    hist: float,
    dist_50: float,
    dist_200: float,
) -> TechnicalSetup:
    """Classify the chart into a small, inspectable set of setup types."""
    price_above_50 = price > sma50
    price_above_200 = price > sma200
    trend_aligned = sma50 > sma200
    macd_improving = macd > signal or hist > 0
    macd_weak = macd <= signal and hist <= 0
    rsi_healthy = TECHNICAL_THRESHOLDS["rsi_neutral_low"] <= rsi <= TECHNICAL_THRESHOLDS["rsi_neutral_high"]
    rsi_extended = rsi >= TECHNICAL_THRESHOLDS["rsi_extended"]
    price_extended = dist_50 >= TECHNICAL_THRESHOLDS["extended_above_50dma_pct"]
    pullback_zone = dist_50 <= TECHNICAL_THRESHOLDS["pullback_above_50dma_pct"]
    recovery_rsi = rsi >= TECHNICAL_THRESHOLDS["rsi_recovery_floor"]
    weak_rsi = rsi < TECHNICAL_THRESHOLDS["rsi_weak_floor"]

    if price_above_200 and price_above_50 and trend_aligned and not (rsi_extended or price_extended) and macd_improving and rsi >= TECHNICAL_THRESHOLDS["rsi_neutral_low"]:
        return TechnicalSetup(
            label="Strong Uptrend",
            summary="Trend and momentum are aligned, and the stock is not obviously stretched.",
            reasoning_bullets=[
                "Price is holding above both the 50DMA and 200DMA.",
                "The 50DMA remains above the 200DMA, which keeps the broader trend pointed up.",
                "Momentum is supportive without looking overly heated.",
            ],
            takeaway="Usually the cleanest setup for building, as long as sizing still makes sense.",
            strength="High",
            action_bias="Add",
        )

    if price_above_200 and price_above_50 and trend_aligned and (rsi_extended or price_extended):
        extension_note = (
            f"RSI is elevated at {format_number(rsi)}."
            if rsi_extended
            else f"Price is stretched at {format_percent(dist_50)} above the 50DMA."
        )
        return TechnicalSetup(
            label="Constructive but Extended",
            summary="The stock still looks strong, but it is extended enough to make chasing less attractive.",
            reasoning_bullets=[
                "The broader trend is still healthy, with price above both moving averages.",
                extension_note,
                "Entry quality looks weaker here than stock quality.",
            ],
            takeaway="Usually better for patience than for chasing a fresh add.",
            strength="Medium",
            action_bias="Add on Pullback",
        )

    if (not price_above_200) and (price_above_50 or dist_50 >= TECHNICAL_THRESHOLDS["pullback_above_50dma_pct"]) and macd_improving and recovery_rsi:
        return TechnicalSetup(
            label="Recovery Setup",
            summary="Near-term action is improving, but the longer-term trend is still not fully repaired.",
            reasoning_bullets=[
                "Price is stabilizing around or above the 50DMA.",
                "Momentum is improving instead of continuing to break down.",
                "The stock is still below the 200DMA, so long-term confirmation is missing.",
            ],
            takeaway="Usually better for smaller, measured adds than for aggressive sizing.",
            strength="Medium",
            action_bias="Add Small",
        )

    if (not price_above_200) and (not price_above_50) and (not trend_aligned) and (weak_rsi or macd_weak):
        return TechnicalSetup(
            label="Weak Downtrend",
            summary="Trend and momentum are both weak, so the setup still looks fragile.",
            reasoning_bullets=[
                "Price is below both the 50DMA and 200DMA.",
                "The 50DMA is below the 200DMA, so trend structure is still working against the stock.",
                "Momentum remains weak rather than clearly stabilizing.",
            ],
            takeaway="Usually better for caution, defense, or trimming than for new buying.",
            strength="Low",
            action_bias="Avoid New Buy",
        )

    mixed_bullets = [
        "Signals are not fully aligned, so the chart does not offer a clean edge right now.",
        "Some pieces look workable, but the moving averages and momentum are not telling the same story yet.",
    ]
    if pullback_zone and trend_aligned and price_above_200:
        mixed_bullets.append("The stock is pulling back within a stronger structure, but confirmation is still incomplete.")
    elif rsi_healthy:
        mixed_bullets.append("Momentum is not badly overheated or broken, which keeps the setup watchable.")
    else:
        mixed_bullets.append("Momentum is neither clearly supportive nor clearly washed out, which argues for patience.")

    return TechnicalSetup(
        label="Mixed Setup",
        summary="Signals are mixed enough that patience is more useful than conviction here.",
        reasoning_bullets=mixed_bullets,
        takeaway="Usually better for waiting than for forcing a new decision.",
        strength="Medium",
        action_bias="Hold",
    )


def score_binary_factor(label: str, condition: bool, max_points: float, positive_detail: str, negative_detail: str) -> FactorScore:
    """Score a yes/no factor."""
    key_map = {
        "Price vs 200DMA": "price_vs_200dma",
        "Price vs 50DMA": "price_vs_50dma",
        "50DMA vs 200DMA": "trend_alignment",
    }
    return FactorScore(
        key=key_map.get(label, label.lower().replace(" ", "_")),
        label=label,
        points=max_points if condition else 0.0,
        max_points=max_points,
        detail=positive_detail if condition else negative_detail,
        status="Bullish" if condition else "Weak",
        available=True,
    )


def score_rsi_factor(rsi: float) -> FactorScore:
    """Score RSI with healthy, oversold, and extended interpretations."""
    max_points = TECHNICAL_FACTORS["rsi"]
    if rsi < TECHNICAL_THRESHOLDS["rsi_oversold"]:
        return FactorScore("rsi_14", "RSI (14)", 5.0, max_points, f"RSI is {format_number(rsi)}; oversold can be attractive if trend support holds.", "Oversold")
    if TECHNICAL_THRESHOLDS["rsi_neutral_low"] <= rsi <= TECHNICAL_THRESHOLDS["rsi_neutral_high"]:
        return FactorScore("rsi_14", "RSI (14)", max_points, max_points, f"RSI is {format_number(rsi)}; healthy momentum without obvious overheating.", "Healthy")
    if rsi < TECHNICAL_THRESHOLDS["rsi_extended"]:
        return FactorScore("rsi_14", "RSI (14)", 5.0, max_points, f"RSI is {format_number(rsi)}; constructive but not especially fresh.", "Constructive")
    return FactorScore("rsi_14", "RSI (14)", 2.0, max_points, f"RSI is {format_number(rsi)}; the stock looks extended and more vulnerable to a pullback.", "Extended")


def score_macd_factor(macd: float, signal: float, hist: float) -> FactorScore:
    """Score MACD trend and histogram confirmation."""
    max_points = TECHNICAL_FACTORS["macd"]
    if macd > signal and hist > 0:
        return FactorScore("macd", "MACD", max_points, max_points, "MACD is above signal with a positive histogram, supporting bullish trend continuation.", "Bullish")
    if macd > signal:
        return FactorScore("macd", "MACD", 3.0, max_points, "MACD is above signal, but the histogram confirmation is softer.", "Improving")
    if hist > 0:
        return FactorScore("macd", "MACD", 2.0, max_points, "MACD is still below signal even though histogram pressure is improving.", "Mixed")
    return FactorScore("macd", "MACD", 0.0, max_points, "MACD is below signal with weak histogram support.", "Weak")


def score_volume_factor(volume: float, avg_volume: float, trend_positive: bool) -> FactorScore:
    """Score current volume versus recent norms."""
    max_points = TECHNICAL_FACTORS["volume"]
    ratio = volume / avg_volume if avg_volume else 0
    if ratio >= TECHNICAL_THRESHOLDS["volume_ratio_bullish"] and trend_positive:
        return FactorScore("volume_ratio", "Volume vs 20D avg", max_points, max_points, f"Volume is running at {format_number(ratio)}x the 20-day average, confirming the move.", "Confirming")
    if ratio >= TECHNICAL_THRESHOLDS["volume_ratio_weak"]:
        return FactorScore("volume_ratio", "Volume vs 20D avg", 2.0, max_points, f"Volume is {format_number(ratio)}x average; participation is acceptable but not decisive.", "Neutral")
    return FactorScore("volume_ratio", "Volume vs 20D avg", 1.0, max_points, f"Volume is only {format_number(ratio)}x average, so conviction behind the move is lighter.", "Light")


def score_distance_factor(dist_50: float, dist_200: float, price_above_50: bool, trend_aligned: bool) -> FactorScore:
    """Score how extended price is from key moving averages."""
    max_points = TECHNICAL_FACTORS["distance_context"]
    if dist_50 >= TECHNICAL_THRESHOLDS["extended_above_50dma_pct"] or dist_200 >= TECHNICAL_THRESHOLDS["extended_above_200dma_pct"]:
        return FactorScore("dist_from_50dma", "Distance from trend", 1.0, max_points, f"Price is {format_percent(dist_50)} from the 50DMA and {format_percent(dist_200)} from the 200DMA; extension risk is elevated.", "Extended")
    if trend_aligned and dist_50 <= 0 and price_above_50:
        return FactorScore("dist_from_50dma", "Distance from trend", 2.0, max_points, f"Price is hugging the 50DMA at {format_percent(dist_50)}, which can be a healthier entry zone within the uptrend.", "Pullback")
    if trend_aligned and price_above_50:
        return FactorScore("dist_from_50dma", "Distance from trend", max_points, max_points, f"Price sits {format_percent(dist_50)} above the 50DMA and {format_percent(dist_200)} above the 200DMA; not overly stretched.", "Balanced")
    return FactorScore("dist_from_50dma", "Distance from trend", 1.0, max_points, f"Distance from the major averages does not yet support a strong timing edge.", "Mixed")


def score_pe_factor(label: str, value: float | None, max_points: float, trailing: bool) -> FactorScore:
    """Score trailing or forward P/E."""
    key = "trailing_pe" if trailing else "forward_pe"
    if value is None:
        return missing_factor(key, label, max_points, "Unavailable from the current data feed; confidence is reduced.")
    low = FUNDAMENTAL_THRESHOLDS["pe_low"] if trailing else FUNDAMENTAL_THRESHOLDS["forward_pe_low"]
    fair = FUNDAMENTAL_THRESHOLDS["pe_fair"] if trailing else FUNDAMENTAL_THRESHOLDS["forward_pe_fair"]
    if value <= low:
        return FactorScore(key, label, max_points, max_points, f"{label} is {format_number(value)}, which looks relatively efficient.", "Attractive")
    if value <= fair:
        return FactorScore(key, label, max_points - 1, max_points, f"{label} is {format_number(value)}, which looks fair but not clearly cheap.", "Fair")
    return FactorScore(key, label, 1.5, max_points, f"{label} is {format_number(value)}, so the market already expects continued execution.", "Expensive")


def score_peg_factor(value: float | None) -> FactorScore:
    """Score valuation relative to growth."""
    max_points = FUNDAMENTAL_FACTORS["peg_ratio"]
    if value is None:
        return missing_factor("peg_ratio", "PEG ratio", max_points, "Unavailable, so valuation-versus-growth is less certain.")
    if value <= FUNDAMENTAL_THRESHOLDS["peg_good"]:
        return FactorScore("peg_ratio", "PEG ratio", max_points, max_points, f"PEG ratio is {format_number(value)}, a good balance between valuation and growth.", "Attractive")
    if value <= FUNDAMENTAL_THRESHOLDS["peg_ok"]:
        return FactorScore("peg_ratio", "PEG ratio", 2.5, max_points, f"PEG ratio is {format_number(value)}, acceptable but not especially compelling.", "Okay")
    return FactorScore("peg_ratio", "PEG ratio", 1.0, max_points, f"PEG ratio is {format_number(value)}, suggesting growth may already be well priced in.", "Rich")


def score_roe_factor(value: float | None) -> FactorScore:
    """Score return on equity."""
    max_points = FUNDAMENTAL_FACTORS["roe"]
    if value is None:
        return missing_factor("return_on_equity", "ROE", max_points, "Unavailable, so capital efficiency confidence is reduced.")
    if value >= FUNDAMENTAL_THRESHOLDS["roe_strong"]:
        return FactorScore("return_on_equity", "ROE", max_points, max_points, f"ROE is {format_percent(value)}, a strong shareholder return profile.", "Strong")
    if value >= FUNDAMENTAL_THRESHOLDS["roe_ok"]:
        return FactorScore("return_on_equity", "ROE", 3.0, max_points, f"ROE is {format_percent(value)}, decent but not standout.", "Solid")
    return FactorScore("return_on_equity", "ROE", 1.5, max_points, f"ROE is {format_percent(value)}, which limits quality confidence.", "Soft")


def score_debt_factor(value: float | None) -> FactorScore:
    """Score balance-sheet leverage."""
    max_points = FUNDAMENTAL_FACTORS["debt_to_equity"]
    if value is None:
        return missing_factor("debt_to_equity", "Debt to equity", max_points, "Unavailable, so leverage risk is less visible.")
    if value <= FUNDAMENTAL_THRESHOLDS["debt_to_equity_low"]:
        return FactorScore("debt_to_equity", "Debt to equity", max_points, max_points, f"Debt to equity is {format_number(value)}, a healthy balance-sheet level.", "Healthy")
    if value <= FUNDAMENTAL_THRESHOLDS["debt_to_equity_ok"]:
        return FactorScore("debt_to_equity", "Debt to equity", 2.5, max_points, f"Debt to equity is {format_number(value)}, manageable but worth monitoring.", "Manageable")
    return FactorScore("debt_to_equity", "Debt to equity", 1.0, max_points, f"Debt to equity is {format_number(value)}, leaving less room if growth slows.", "Heavy")


def score_growth_factor(label: str, value: float | None) -> FactorScore:
    """Score revenue or earnings growth."""
    max_points = FUNDAMENTAL_FACTORS["revenue_growth"] if label == "Revenue growth" else FUNDAMENTAL_FACTORS["earnings_growth"]
    key = "revenue_growth" if label == "Revenue growth" else "earnings_growth"
    if value is None:
        return missing_factor(key, label, max_points, f"{label} is unavailable, which reduces conviction in the growth picture.")
    if value >= FUNDAMENTAL_THRESHOLDS["growth_strong"]:
        return FactorScore(key, label, max_points, max_points, f"{label} is {format_percent(value)}, a strong expansion rate.", "Strong")
    if value >= FUNDAMENTAL_THRESHOLDS["growth_ok"]:
        return FactorScore(key, label, 2.5, max_points, f"{label} is {format_percent(value)}, positive and supportive.", "Positive")
    return FactorScore(key, label, 1.0, max_points, f"{label} is {format_percent(value)}, which makes the growth case less compelling.", "Muted")


def score_cash_flow_factor(free_cash_flow: float | None, operating_cash_flow: float | None) -> FactorScore:
    """Score cash generation quality."""
    max_points = FUNDAMENTAL_FACTORS["cash_flow"]
    signal = free_cash_flow if free_cash_flow is not None else operating_cash_flow
    if signal is None:
        return missing_factor("free_cash_flow", "Cash flow", max_points, "Cash-flow fields are unavailable, so durability confidence is lower.")
    if signal > 0:
        return FactorScore("free_cash_flow", "Cash flow", max_points, max_points, f"Cash flow is positive at roughly {format_currency(signal)}, supporting durability.", "Positive")
    return FactorScore("free_cash_flow", "Cash flow", 0.5, max_points, f"Cash flow is negative at roughly {format_currency(signal)}, which trims quality confidence.", "Negative")


def score_margin_factor(gross: float | None, operating: float | None, profit: float | None) -> FactorScore:
    """Score margin quality using the best available margin fields."""
    max_points = FUNDAMENTAL_FACTORS["margins"]
    margin_values = [value for value in (gross, operating, profit) if value is not None]
    if not margin_values:
        return missing_factor("gross_margin", "Margins", max_points, "Margin fields are sparse, so profitability breadth is harder to judge.")
    average_margin = sum(margin_values) / len(margin_values)
    if average_margin >= FUNDAMENTAL_THRESHOLDS["margin_strong"]:
        return FactorScore("gross_margin", "Margins", max_points, max_points, f"Average margin profile is about {format_percent(average_margin)}, which is strong.", "Strong")
    if average_margin >= FUNDAMENTAL_THRESHOLDS["margin_ok"]:
        return FactorScore("gross_margin", "Margins", 2.5, max_points, f"Average margin profile is about {format_percent(average_margin)}, respectable but not elite.", "Solid")
    if average_margin >= FUNDAMENTAL_THRESHOLDS["margin_floor"]:
        return FactorScore("gross_margin", "Margins", 1.5, max_points, f"Average margin profile is about {format_percent(average_margin)}, which is thin.", "Thin")
    return FactorScore("gross_margin", "Margins", 0.5, max_points, f"Average margin profile is about {format_percent(average_margin)}, which is currently weak.", "Weak")


def score_completeness_factor(completeness_ratio: float) -> FactorScore:
    """Explicitly reflect data coverage inside the fundamental score."""
    max_points = FUNDAMENTAL_FACTORS["data_completeness"]
    if completeness_ratio >= 0.8:
        return FactorScore("data_completeness", "Data completeness", max_points, max_points, f"Fundamental coverage is {format_percent(completeness_ratio)}, so confidence stays stronger.", "High")
    if completeness_ratio >= 0.55:
        return FactorScore("data_completeness", "Data completeness", 1.0, max_points, f"Fundamental coverage is {format_percent(completeness_ratio)}; missing fields reduce confidence somewhat.", "Medium")
    return FactorScore("data_completeness", "Data completeness", 0.0, max_points, f"Fundamental coverage is only {format_percent(completeness_ratio)}; the model reduces conviction explicitly.", "Low")


def missing_factor(key: str, label: str, max_points: float, detail: str) -> FactorScore:
    """Create a missing-data factor entry."""
    return FactorScore(key, label, 0.0, max_points, detail, "Missing", available=False)
