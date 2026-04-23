"""Lightweight catalyst extraction and summarization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import streamlit as st
import yfinance as yf

from services.market_data import StockSnapshot
from config.catalyst_config import (
    CATALYST_CATEGORY_KEYWORDS,
    CATALYST_RECENCY_DAYS,
    CAUTION_KEYWORDS,
    POSITIVE_KEYWORDS,
    SOURCE_CONFIDENCE,
)


@dataclass
class CatalystEvent:
    """A recent catalyst item normalized for the dashboard."""

    ticker: str
    title: str
    source: str
    published_at: str
    category: str
    polarity: str
    confidence: str
    summary: str


@dataclass
class CatalystSummary:
    """Compact catalyst layer for a ticker."""

    bias: str
    positive_points: list[str]
    risk_points: list[str]
    freshness_label: str
    top_events: list[CatalystEvent]
    asset_context: str = "Stock context"
    context_note: str | None = None


def detect_asset_type(snapshot: StockSnapshot | None) -> str:
    """Infer whether the snapshot looks like a stock or ETF."""
    if snapshot is None:
        return "unknown"

    metadata = snapshot.metadata
    quote_type = (metadata.quote_type or "").upper()
    if quote_type == "ETF":
        return "etf"
    if quote_type == "EQUITY":
        return "stock"
    if metadata.fund_family or metadata.category:
        return "etf"
    if metadata.short_name:
        name = metadata.short_name.lower()
        if any(token in name for token in ("etf", "index fund", "select sector", "trust", "s&p 500", "nasdaq-100", "nasdaq 100")):
            return "etf"
    return "stock"


def classify_freshness(days_old: int | None) -> str:
    """Resolve a freshness label from age in days."""
    if days_old is None:
        return "Stale"
    if days_old <= CATALYST_RECENCY_DAYS["fresh"]:
        return "Fresh"
    if days_old <= CATALYST_RECENCY_DAYS["recent"]:
        return "Recent"
    return "Stale"


def categorize_event(title: str) -> str:
    """Infer a lightweight category from a headline."""
    normalized = title.lower()
    for category, keywords in CATALYST_CATEGORY_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return category
    return "generic_news"


def classify_polarity(title: str) -> str:
    """Infer simple polarity from a headline."""
    normalized = title.lower()
    positive_hits = sum(keyword in normalized for keyword in POSITIVE_KEYWORDS)
    caution_hits = sum(keyword in normalized for keyword in CAUTION_KEYWORDS)
    if caution_hits > positive_hits:
        return "caution"
    if positive_hits > caution_hits:
        return "positive"
    return "neutral"


def summarize_headline(title: str, category: str, polarity: str) -> str:
    """Create a short plain-English line from a headline classification."""
    category_phrase = {
        "earnings": "Earnings news",
        "guidance": "Guidance news",
        "analyst": "Analyst activity",
        "product": "Product or demand news",
        "regulation": "Regulatory news",
        "sector": "Sector context",
        "generic_news": "Company news",
    }.get(category, "Company news")
    polarity_phrase = {
        "positive": "looks supportive",
        "neutral": "looks mixed",
        "caution": "looks cautionary",
    }[polarity]
    return f"{category_phrase} {polarity_phrase.lower()}."


def resolve_source_confidence(source: str) -> str:
    """Map known news sources to rough confidence labels."""
    return SOURCE_CONFIDENCE.get(source.strip().lower(), "Low")


def build_catalyst_summary(events: list[CatalystEvent], snapshot: StockSnapshot | None = None) -> CatalystSummary:
    """Summarize recent events into a compact catalyst view."""
    asset_type = detect_asset_type(snapshot)
    if asset_type == "etf":
        return build_etf_catalyst_summary(events, snapshot)
    return build_stock_catalyst_summary(events, snapshot)


def build_stock_catalyst_summary(events: list[CatalystEvent], snapshot: StockSnapshot | None = None) -> CatalystSummary:
    """Summarize recent events into a compact stock catalyst view."""
    fallback_positive, fallback_risks = _build_fallback_context(snapshot)
    if not events:
        return CatalystSummary(
            bias="Neutral",
            positive_points=fallback_positive or ["No clearly supportive recent catalyst stood out in the current feed."],
            risk_points=fallback_risks or ["Recent catalyst coverage is sparse, so this read should carry less weight."],
            freshness_label="Stale",
            top_events=[],
            asset_context="Stock context",
        )

    positive_points = [event.summary for event in events if event.polarity == "positive"][:3]
    risk_points = [event.summary for event in events if event.polarity == "caution"][:3]
    top_events = events[:5]

    parsed_dates = [parsed for event in top_events if (parsed := _parse_published_at(event.published_at)) is not None]
    latest_date = max(parsed_dates) if parsed_dates else None
    days_old = None
    if latest_date is not None:
        days_old = (datetime.now(timezone.utc) - latest_date).days
    freshness_label = classify_freshness(days_old)

    if positive_points and not risk_points:
        bias = "Positive"
    elif risk_points and not positive_points:
        bias = "Caution"
    elif positive_points and risk_points:
        bias = "Neutral"
    else:
        bias = "Neutral"

    if not positive_points:
        positive_points = fallback_positive or ["No clearly supportive recent catalyst stood out."]
    if not risk_points:
        risk_points = fallback_risks or ["No clear near-term risk item stood out."]

    if freshness_label == "Stale":
        if positive_points:
            positive_points[0] = f"{positive_points[0]} Fresh supporting news is limited."
        if risk_points:
            risk_points[0] = f"{risk_points[0]} The recent-news read is getting stale."

    return CatalystSummary(
        bias=bias,
        positive_points=positive_points,
        risk_points=risk_points,
        freshness_label=freshness_label,
        top_events=top_events,
        asset_context="Stock context",
    )


def build_etf_catalyst_summary(events: list[CatalystEvent], snapshot: StockSnapshot | None = None) -> CatalystSummary:
    """Summarize recent events into an ETF-aware catalyst view."""
    positive_points, risk_points, bias = _build_etf_context(snapshot)
    context_note = "Because this is an ETF, this read leans more on index, sector, and trend context than on company headlines."

    if events:
        positive_points.extend(event.summary for event in events if event.polarity == "positive")
        risk_points.extend(event.summary for event in events if event.polarity == "caution")
        parsed_dates = [parsed for event in events[:5] if (parsed := _parse_published_at(event.published_at)) is not None]
        latest_date = max(parsed_dates) if parsed_dates else None
        days_old = (datetime.now(timezone.utc) - latest_date).days if latest_date is not None else None
        freshness_label = classify_freshness(days_old)
        if freshness_label == "Fresh":
            if bias == "Neutral" and any(event.polarity == "positive" for event in events):
                bias = "Positive"
            elif bias == "Neutral" and any(event.polarity == "caution" for event in events):
                bias = "Caution"
    else:
        freshness_label = "Stale"

    if not positive_points:
        positive_points = ["No clear ETF-specific positive catalyst stood out, so this read leans more on market and trend context."]
    if not risk_points:
        risk_points = ["No single ETF-specific risk event stood out, so this read leans more on backdrop and trend context."]

    if freshness_label == "Stale":
        positive_points[0] = f"{positive_points[0]} Fresh ETF-specific coverage is limited, so treat this more as backdrop than as a fresh event read."

    return CatalystSummary(
        bias=bias,
        positive_points=positive_points[:3],
        risk_points=risk_points[:3],
        freshness_label=freshness_label,
        top_events=events[:5],
        asset_context="ETF context",
        context_note=context_note,
    )


def _build_fallback_context(snapshot: StockSnapshot | None) -> tuple[list[str], list[str]]:
    """Use the latest available company context when news is sparse."""
    if snapshot is None:
        return [], []

    fundamentals = snapshot.metadata.fundamentals
    positive_points: list[str] = []
    risk_points: list[str] = []

    revenue_growth = fundamentals.get("revenueGrowth")
    earnings_growth = fundamentals.get("earningsGrowth")
    roe = fundamentals.get("returnOnEquity")
    forward_pe = fundamentals.get("forwardPE")
    trailing_pe = fundamentals.get("trailingPE")
    debt_to_equity = fundamentals.get("debtToEquity")

    if isinstance(revenue_growth, (int, float)) and revenue_growth >= 0.1:
        positive_points.append("Latest reported revenue growth still looks supportive.")
    if isinstance(earnings_growth, (int, float)) and earnings_growth >= 0.1:
        positive_points.append("Latest reported earnings growth still supports the story.")
    if isinstance(roe, (int, float)) and roe >= 0.18:
        positive_points.append("Underlying business quality still looks solid based on return on equity.")

    valuation = forward_pe if isinstance(forward_pe, (int, float)) else trailing_pe
    if isinstance(valuation, (int, float)) and valuation >= 30:
        risk_points.append("Valuation still leaves less room for execution misses.")
    if isinstance(debt_to_equity, (int, float)) and debt_to_equity >= 1.5:
        risk_points.append("Balance-sheet leverage still deserves monitoring.")

    return positive_points[:2], risk_points[:2]


def _build_etf_context(snapshot: StockSnapshot | None) -> tuple[list[str], list[str], str]:
    """Build ETF-aware context from trend and fund style when news is sparse."""
    if snapshot is None or snapshot.history.empty:
        return (
            ["ETF context is limited because current market data was not available."],
            ["ETF-specific recent news is sparse, so this read should stay lightweight."],
            "Neutral",
        )

    latest = snapshot.history.iloc[-1]
    price = float(latest["Close"])
    sma50 = float(latest["SMA_50"])
    sma200 = float(latest["SMA_200"])
    rsi = float(latest["RSI_14"])
    metadata = snapshot.metadata
    context_style = _infer_etf_style(snapshot)

    trend_positive = price > sma50 and price > sma200 and sma50 > sma200
    trend_weak = price < sma50 and price < sma200 and sma50 < sma200
    trend_mixed = not trend_positive and not trend_weak

    positive_points: list[str] = []
    risk_points: list[str] = []

    if trend_positive:
        positive_points.append(_positive_etf_trend_line(context_style))
        bias = "Positive"
    elif trend_weak:
        risk_points.append(_negative_etf_trend_line(context_style))
        bias = "Caution"
    else:
        positive_points.append(_mixed_etf_line(context_style))
        bias = "Neutral"

    if context_style == "broad_market":
        positive_points.append("Broad large-cap tone remains the main support for this ETF." if trend_positive else "Broad market tone is still the main context to watch here.")
        risk_points.append("If broad market leadership narrows, this ETF can lose momentum quickly.")
    elif context_style == "large_cap_growth":
        positive_points.append("Growth-heavy leadership remains the main support if the trend keeps holding.")
        risk_points.append("This ETF stays sensitive to rate pressure and any loss of mega-cap leadership.")
    elif context_style == "technology":
        positive_points.append("Technology leadership matters more here than any single-company headline.")
        risk_points.append("Tech leadership can unwind quickly if sentiment or rates turn against the group.")
    elif context_style == "financials":
        positive_points.append("Financial sector tone improves when the group starts to reclaim trend support.")
        risk_points.append("Rate expectations and credit worries can swing this sector quickly.")
    else:
        positive_points.append("This ETF is best read through sector or index tone rather than company-specific news.")
        risk_points.append("Without a strong trend, ETF context is useful but not decisive.")

    if rsi >= 70:
        risk_points.append("Momentum looks extended, which can weaken short-term entry quality.")
        if bias == "Positive":
            bias = "Neutral"
    elif rsi < 40 and trend_weak:
        risk_points.append("Momentum remains soft, which keeps the ETF backdrop cautious.")

    return positive_points[:3], risk_points[:3], bias


def _infer_etf_style(snapshot: StockSnapshot) -> str:
    """Infer a lightweight ETF style bucket."""
    metadata = snapshot.metadata
    text = " ".join(
        filter(
            None,
            [
                metadata.symbol,
                metadata.short_name,
                metadata.summary,
                metadata.fund_family,
                metadata.category,
            ],
        )
    ).lower()
    if any(token in text for token in ("s&p 500", "voo", "spy", "ivv", "large blend")):
        return "broad_market"
    if any(token in text for token in ("nasdaq", "qqq", "qqqm", "growth")):
        return "large_cap_growth"
    if any(token in text for token in ("technology", "xlk", "tech")):
        return "technology"
    if any(token in text for token in ("financial", "xlf", "bank")):
        return "financials"
    return "generic_etf"


def _positive_etf_trend_line(style: str) -> str:
    if style == "broad_market":
        return "Broad market trend remains constructive above key moving averages."
    if style == "large_cap_growth":
        return "Large-cap growth leadership remains constructive above key moving averages."
    if style == "technology":
        return "Technology sector momentum remains constructive above key moving averages."
    if style == "financials":
        return "Financial sector momentum is acting constructively above key moving averages."
    return "ETF trend remains constructive above key moving averages."


def _negative_etf_trend_line(style: str) -> str:
    if style == "broad_market":
        return "Broad market trend is below key moving averages, so the backdrop still looks weak."
    if style == "large_cap_growth":
        return "Growth-heavy leadership is below key moving averages, so the backdrop still looks weak."
    if style == "technology":
        return "Technology sector trend is below key moving averages, so the backdrop still looks weak."
    if style == "financials":
        return "Financial sector trend is below key moving averages, so the backdrop still looks weak."
    return "ETF trend is below key moving averages, so the backdrop still looks weak."


def _mixed_etf_line(style: str) -> str:
    if style == "broad_market":
        return "Broad market context is still usable, but the trend read is mixed rather than decisive."
    if style == "large_cap_growth":
        return "Growth-led context is still relevant, but the trend read is mixed."
    if style == "technology":
        return "Technology context is still relevant, but the trend read is mixed."
    if style == "financials":
        return "Financial sector context matters here, but the trend read is mixed."
    return "ETF context is usable, but the trend read is mixed rather than decisive."


def _parse_published_at(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _normalize_event(ticker: str, raw_item: dict[str, object]) -> CatalystEvent | None:
    title = str(raw_item.get("title") or "").strip()
    if not title:
        return None

    source = str(raw_item.get("publisher") or raw_item.get("source") or "Unknown").strip()
    published_ts = raw_item.get("providerPublishTime")
    published_at = ""
    if isinstance(published_ts, (int, float)):
        published_at = datetime.fromtimestamp(published_ts, tz=timezone.utc).isoformat()
    else:
        published_at = str(raw_item.get("published_at") or "")

    category = categorize_event(title)
    polarity = classify_polarity(title)
    return CatalystEvent(
        ticker=ticker,
        title=title,
        source=source,
        published_at=published_at,
        category=category,
        polarity=polarity,
        confidence=resolve_source_confidence(source),
        summary=summarize_headline(title, category, polarity),
    )


@st.cache_data(ttl=1800, show_spinner=False)
def get_catalyst_events(ticker: str) -> list[CatalystEvent]:
    """Fetch recent company-specific items for catalyst analysis."""
    symbol = ticker.strip().upper()
    if not symbol:
        return []

    try:
        raw_news = yf.Ticker(symbol).news or []
        events = [
            event
            for item in raw_news[:8]
            if (event := _normalize_event(symbol, item)) is not None
        ]
        events.sort(key=lambda event: event.published_at, reverse=True)
        return events
    except Exception:
        return []


def get_catalyst_summary(ticker: str, snapshot: StockSnapshot | None = None) -> CatalystSummary:
    """Fetch recent company-specific items and summarize them into a catalyst layer."""
    return build_catalyst_summary(get_catalyst_events(ticker), snapshot)
