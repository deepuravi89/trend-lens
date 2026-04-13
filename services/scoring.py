"""Scoring engine for technical and fundamental analysis."""

from __future__ import annotations

from dataclasses import dataclass

from config.scoring_config import FUNDAMENTAL_THRESHOLDS, SCORE_WEIGHTS, TECHNICAL_THRESHOLDS, VERDICT_BANDS
from services.market_data import StockSnapshot
from utils.formatters import format_currency, format_number, format_percent


@dataclass
class SectionScore:
    """A score with supporting explanation."""

    score: float
    summary: str
    explanations: list[str]


@dataclass
class ScoreBundle:
    """Full score output for the dashboard."""

    technical: SectionScore
    fundamental: SectionScore
    total_score: float
    verdict: str
    position_score: float = 0.0

    def render_full_explanation(self) -> str:
        """Render section bullets as HTML."""
        return (
            '<div class="section-title">Technical Read</div>'
            f'<ul class="explanation-list">{"".join(f"<li>{item}</li>" for item in self.technical.explanations)}</ul>'
            '<div class="section-title" style="margin-top: 1rem;">Fundamental Read</div>'
            f'<ul class="explanation-list">{"".join(f"<li>{item}</li>" for item in self.fundamental.explanations)}</ul>'
        )


def build_score_bundle(snapshot: StockSnapshot) -> ScoreBundle:
    """Compute technical, fundamental, and total score bundle."""
    technical = score_technical(snapshot)
    fundamental = score_fundamental(snapshot)
    total_score = technical.score + fundamental.score
    verdict = resolve_verdict(total_score)
    return ScoreBundle(technical=technical, fundamental=fundamental, position_score=0.0, total_score=total_score, verdict=verdict)


def finalize_total_score(scores: ScoreBundle, position_score: float) -> ScoreBundle:
    """Fold the position advisor into the final 100-point score."""
    total_score = scores.technical.score + scores.fundamental.score + position_score
    return ScoreBundle(
        technical=scores.technical,
        fundamental=scores.fundamental,
        position_score=position_score,
        total_score=total_score,
        verdict=resolve_verdict(total_score),
    )


def resolve_verdict(total_score: float) -> str:
    """Resolve total score into a simple verdict band."""
    for label, floor in VERDICT_BANDS.items():
        if total_score >= floor:
            return label
    return "Avoid"


def score_technical(snapshot: StockSnapshot) -> SectionScore:
    """Score price trend and momentum indicators out of 40."""
    frame = snapshot.history
    latest = frame.iloc[-1]
    price = latest["Close"]
    sma50 = latest["SMA_50"]
    sma200 = latest["SMA_200"]
    rsi = latest["RSI_14"]
    macd = latest["MACD"]
    signal = latest["MACD_SIGNAL"]
    volume = latest["Volume"]
    avg_volume = latest["AVG_VOLUME_20"]

    score = 0.0
    explanations: list[str] = []

    if price > sma200:
        score += 8
        explanations.append(f"Price is above the 200-day average ({format_currency(price)} vs {format_currency(sma200)}), which supports the long-term uptrend.")
    else:
        explanations.append(f"Price is below the 200-day average ({format_currency(price)} vs {format_currency(sma200)}), which weakens the long-term trend.")

    if price > sma50:
        score += 7
        explanations.append(f"Price is above the 50-day average ({format_currency(price)} vs {format_currency(sma50)}), showing near-term momentum is still intact.")
    else:
        explanations.append(f"Price is below the 50-day average ({format_currency(price)} vs {format_currency(sma50)}), so short-term trend leadership is fading.")

    if sma50 > sma200:
        score += 7
        explanations.append("The 50-day average remains above the 200-day average, a constructive trend alignment.")
    else:
        explanations.append("The 50-day average is below the 200-day average, which points to weaker trend structure.")

    if rsi < TECHNICAL_THRESHOLDS["rsi_oversold"]:
        score += 5
        explanations.append(f"RSI is {format_number(rsi)}, which is oversold and can signal a more attractive entry if the trend stabilizes.")
    elif TECHNICAL_THRESHOLDS["rsi_healthy_low"] <= rsi <= TECHNICAL_THRESHOLDS["rsi_healthy_high"]:
        score += 7
        explanations.append(f"RSI is {format_number(rsi)}, a healthy momentum range without obvious overheating.")
    elif rsi < TECHNICAL_THRESHOLDS["rsi_caution"]:
        score += 5
        explanations.append(f"RSI is {format_number(rsi)}, still constructive but no longer as fresh as a neutral setup.")
    else:
        score += 2
        explanations.append(f"RSI is {format_number(rsi)}, which looks extended and raises pullback risk.")

    if macd > signal and latest["MACD_HIST"] > 0:
        score += 7
        explanations.append("MACD is above its signal line with a positive histogram, supporting bullish momentum.")
    elif macd > signal:
        score += 5
        explanations.append("MACD is above its signal line, though the momentum thrust is less decisive.")
    else:
        explanations.append("MACD is below its signal line, which suggests momentum has cooled.")

    volume_ratio = (volume / avg_volume) if avg_volume else None
    if volume_ratio is not None and volume_ratio >= TECHNICAL_THRESHOLDS["volume_ratio_bullish"] and price > sma50:
        score += 4
        explanations.append(f"Volume is running at {format_number(volume_ratio)}x the 20-day average, giving the current move better participation.")
    elif volume_ratio is not None and volume_ratio >= TECHNICAL_THRESHOLDS["volume_ratio_weak"]:
        score += 3
        explanations.append(f"Volume is near normal at {format_number(volume_ratio)}x average, which is acceptable but not especially powerful.")
    else:
        score += 1
        explanations.append("Volume is light relative to recent trading, so the move has less confirmation behind it.")

    summary = (
        "Trend and momentum are working together well."
        if score >= 30
        else "The setup is mixed, with some constructive signals but not a fully clean trend."
        if score >= 22
        else "Technical conditions are fragile or extended, so timing risk is elevated."
    )
    return SectionScore(score=min(score, SCORE_WEIGHTS["technical"]), summary=summary, explanations=explanations)


def score_fundamental(snapshot: StockSnapshot) -> SectionScore:
    """Score valuation, growth, quality, and balance sheet metrics out of 40."""
    f = snapshot.metadata.fundamentals
    explanations: list[str] = []
    score = 0.0
    metrics_seen = 0

    trailing_pe = f.get("trailingPE")
    if trailing_pe is not None:
        metrics_seen += 1
        if trailing_pe <= FUNDAMENTAL_THRESHOLDS["pe_low"]:
            score += 6
            explanations.append(f"Trailing P/E is {format_number(trailing_pe)}, which screens as relatively efficient.")
        elif trailing_pe <= FUNDAMENTAL_THRESHOLDS["pe_fair"]:
            score += 4
            explanations.append(f"Trailing P/E is {format_number(trailing_pe)}, which looks fair rather than outright cheap.")
        else:
            score += 2
            explanations.append(f"Trailing P/E is {format_number(trailing_pe)}, so valuation already expects quite a bit.")
    else:
        explanations.append("Trailing P/E is unavailable, so the valuation read leans on other metrics.")

    forward_pe = f.get("forwardPE")
    if forward_pe is not None:
        metrics_seen += 1
        if forward_pe <= FUNDAMENTAL_THRESHOLDS["forward_pe_low"]:
            score += 5
            explanations.append(f"Forward P/E is {format_number(forward_pe)}, suggesting next-year expectations are still reasonable.")
        elif forward_pe <= FUNDAMENTAL_THRESHOLDS["forward_pe_fair"]:
            score += 4
            explanations.append(f"Forward P/E is {format_number(forward_pe)}, a workable but not deeply discounted level.")
        else:
            score += 2
            explanations.append(f"Forward P/E is {format_number(forward_pe)}, so the market is pricing in continued execution.")
    else:
        explanations.append("Forward P/E is missing, which is common for some sectors and early-stage names.")

    peg_ratio = f.get("pegRatio")
    if peg_ratio is not None:
        metrics_seen += 1
        if peg_ratio <= FUNDAMENTAL_THRESHOLDS["peg_good"]:
            score += 5
            explanations.append(f"PEG ratio is {format_number(peg_ratio)}, a good balance between valuation and growth.")
        elif peg_ratio <= FUNDAMENTAL_THRESHOLDS["peg_ok"]:
            score += 3.5
            explanations.append(f"PEG ratio is {format_number(peg_ratio)}, acceptable but not especially compelling.")
        else:
            score += 1.5
            explanations.append(f"PEG ratio is {format_number(peg_ratio)}, which suggests growth may already be fully priced.")
    else:
        explanations.append("PEG ratio is unavailable, so the model cannot judge valuation versus growth as directly.")

    roe = f.get("returnOnEquity")
    if roe is not None:
        metrics_seen += 1
        if roe >= FUNDAMENTAL_THRESHOLDS["roe_strong"]:
            score += 6
            explanations.append(f"ROE is {format_percent(roe)}, which points to strong shareholder returns.")
        elif roe >= FUNDAMENTAL_THRESHOLDS["roe_ok"]:
            score += 4
            explanations.append(f"ROE is {format_percent(roe)}, a decent but not standout profitability level.")
        else:
            score += 2
            explanations.append(f"ROE is {format_percent(roe)}, which limits quality points.")
    else:
        explanations.append("ROE is unavailable, so capital efficiency is harder to assess.")

    debt_to_equity = f.get("debtToEquity")
    if debt_to_equity is not None:
        metrics_seen += 1
        if debt_to_equity <= FUNDAMENTAL_THRESHOLDS["debt_to_equity_low"]:
            score += 5
            explanations.append(f"Debt to equity is {format_number(debt_to_equity)}, a healthy balance-sheet level.")
        elif debt_to_equity <= FUNDAMENTAL_THRESHOLDS["debt_to_equity_ok"]:
            score += 3
            explanations.append(f"Debt to equity is {format_number(debt_to_equity)}, manageable but worth monitoring.")
        else:
            score += 1
            explanations.append(f"Debt to equity is {format_number(debt_to_equity)}, which reduces flexibility if growth slows.")
    else:
        explanations.append("Debt to equity is missing, so leverage is not fully visible in this snapshot.")

    revenue_growth = f.get("revenueGrowth")
    if revenue_growth is not None:
        metrics_seen += 1
        if revenue_growth >= FUNDAMENTAL_THRESHOLDS["growth_strong"]:
            score += 5
            explanations.append(f"Revenue growth is {format_percent(revenue_growth)}, a strong top-line expansion rate.")
        elif revenue_growth >= FUNDAMENTAL_THRESHOLDS["growth_ok"]:
            score += 3.5
            explanations.append(f"Revenue growth is {format_percent(revenue_growth)}, positive and supportive.")
        else:
            score += 1.5
            explanations.append(f"Revenue growth is {format_percent(revenue_growth)}, so top-line momentum is modest.")
    else:
        explanations.append("Revenue growth data is unavailable from the current feed.")

    eps_growth = f.get("earningsGrowth")
    if eps_growth is not None:
        metrics_seen += 1
        if eps_growth >= FUNDAMENTAL_THRESHOLDS["growth_strong"]:
            score += 5
            explanations.append(f"EPS growth is {format_percent(eps_growth)}, showing earnings are compounding at a healthy clip.")
        elif eps_growth >= FUNDAMENTAL_THRESHOLDS["growth_ok"]:
            score += 3.5
            explanations.append(f"EPS growth is {format_percent(eps_growth)}, positive but not explosive.")
        else:
            score += 1.5
            explanations.append(f"EPS growth is {format_percent(eps_growth)}, which weakens the growth case.")
    else:
        explanations.append("EPS growth is unavailable, so the earnings trend is only partially visible.")

    free_cashflow = f.get("freeCashflow")
    operating_cashflow = f.get("operatingCashflow")
    cash_flow_signal = free_cashflow if free_cashflow is not None else operating_cashflow
    if cash_flow_signal is not None:
        metrics_seen += 1
        if cash_flow_signal > 0:
            score += 3
            explanations.append(f"Cash flow is positive at roughly {format_currency(cash_flow_signal)}, which supports business durability.")
        else:
            score += 1
            explanations.append(f"Cash flow is negative at roughly {format_currency(cash_flow_signal)}, which trims financial quality.")
    else:
        explanations.append("Cash flow data is unavailable, so the score reduces reliance on this factor.")

    if metrics_seen <= 3:
        score = min(score, 22)
        explanations.append("Several fundamental fields are missing, so this section intentionally caps conviction instead of over-scoring sparse data.")

    summary = (
        "Fundamentals look sturdy, with a healthy mix of valuation support, growth, and balance-sheet quality."
        if score >= 30
        else "Fundamentals are usable but mixed, with some strengths offset by either valuation pressure or missing data."
        if score >= 22
        else "The fundamental picture is either weak, expensive, or too incomplete to build strong conviction."
    )
    return SectionScore(score=min(score, SCORE_WEIGHTS["fundamental"]), summary=summary, explanations=explanations)
