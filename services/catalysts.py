"""Lightweight catalyst extraction and summarization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import streamlit as st
import yfinance as yf

from config.catalyst_config import (
    CATALYST_CATEGORY_KEYWORDS,
    CATALYST_RECENCY_DAYS,
    CAUTION_KEYWORDS,
    POSITIVE_KEYWORDS,
    SOURCE_CONFIDENCE,
)
from services.market_data import StockSnapshot


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
    primary_read: str | None = None


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
    category_phrases = {
        "earnings": {
            "positive": "Earnings-related coverage appears supportive.",
            "neutral": "Earnings-related coverage looks mixed.",
            "caution": "Earnings-related coverage looks cautionary.",
        },
        "guidance": {
            "positive": "Guidance and outlook headlines appear supportive.",
            "neutral": "Guidance headlines look mixed.",
            "caution": "Guidance and outlook headlines are a risk to watch.",
        },
        "analyst": {
            "positive": "Analyst activity appears supportive.",
            "neutral": "Analyst commentary looks mixed.",
            "caution": "Analyst activity leans cautionary.",
        },
        "product": {
            "positive": "Product or demand coverage appears supportive.",
            "neutral": "Product and demand coverage looks mixed.",
            "caution": "Product or demand coverage is a risk to watch.",
        },
        "regulation": {
            "positive": "Regulatory coverage looks manageable for now.",
            "neutral": "Regulatory and legal coverage looks mixed.",
            "caution": "Regulatory or legal headlines are a risk to watch.",
        },
        "m_and_a_contract": {
            "positive": "Contract or deal flow appears supportive.",
            "neutral": "Contract and deal flow looks mixed.",
            "caution": "Contract or deal headlines deserve caution.",
        },
        "sector": {
            "positive": "Sector context looks supportive.",
            "neutral": "Sector context looks mixed.",
            "caution": "Sector context looks cautionary.",
        },
        "generic_news": {
            "positive": "Company-specific coverage appears supportive.",
            "neutral": "Company-specific coverage looks mixed.",
            "caution": "Company-specific coverage looks cautionary.",
        },
    }
    return category_phrases.get(category, category_phrases["generic_news"])[polarity]


def resolve_source_confidence(source: str) -> str:
    """Map known news sources to rough confidence labels."""
    return SOURCE_CONFIDENCE.get(source.strip().lower(), "Low")


def format_event_date(value: str) -> str:
    """Format a catalyst timestamp for compact UI display."""
    parsed = _parse_published_at(value)
    if parsed is None:
        return "Date unavailable"
    return parsed.astimezone(timezone.utc).strftime("%b %d, %Y")


def build_catalyst_summary(events: list[CatalystEvent], snapshot: StockSnapshot | None = None) -> CatalystSummary:
    """Summarize recent events into a compact catalyst view."""
    asset_type = detect_asset_type(snapshot)
    if asset_type == "etf":
        return build_etf_catalyst_summary(events, snapshot)
    return build_stock_catalyst_summary(events, snapshot)


def build_stock_catalyst_summary(events: list[CatalystEvent], snapshot: StockSnapshot | None = None) -> CatalystSummary:
    """Summarize recent events into a compact stock catalyst view."""
    fallback_positive, fallback_risks = _build_fallback_context(snapshot)
    top_events = events[:5]
    freshness_label = _freshness_from_events(top_events)

    positive_points = _event_bullets(top_events, "positive")
    risk_points = _event_bullets(top_events, "caution")

    if positive_points and not risk_points:
        bias = "Positive"
    elif risk_points and not positive_points:
        bias = "Caution"
    else:
        bias = "Neutral"

    if not positive_points:
        positive_points = fallback_positive or ["No clear supportive company item stood out in the current feed."]
    if not risk_points:
        risk_points = fallback_risks or ["No clear company-specific risk item stood out in the current feed."]

    if not top_events:
        primary_read = "Recent company-specific flow is light, so lean more on the score and setup than on fresh event flow."
    else:
        primary_read = _build_stock_primary_read(top_events, bias, freshness_label)

    return CatalystSummary(
        bias=bias,
        positive_points=positive_points[:3],
        risk_points=risk_points[:3],
        freshness_label=freshness_label,
        top_events=top_events,
        asset_context="Stock context",
        primary_read=primary_read,
    )


def build_etf_catalyst_summary(events: list[CatalystEvent], snapshot: StockSnapshot | None = None) -> CatalystSummary:
    """Summarize recent events into an ETF-aware catalyst view."""
    positive_points, risk_points, bias = _build_etf_context(snapshot)
    event_positive = _event_bullets(events[:5], "positive")
    event_risks = _event_bullets(events[:5], "caution")
    freshness_label = _freshness_from_events(events[:5])
    context_note = "Because this is an ETF, this read leans more on index, sector, and trend context than on company headlines."

    if event_positive:
        positive_points = _merge_unique(positive_points, event_positive)
    if event_risks:
        risk_points = _merge_unique(risk_points, event_risks)

    if freshness_label == "Fresh":
        if bias == "Neutral" and event_positive and not event_risks:
            bias = "Positive"
        elif bias == "Neutral" and event_risks and not event_positive:
            bias = "Caution"

    primary_read = _build_etf_primary_read(snapshot, freshness_label, bool(events))

    return CatalystSummary(
        bias=bias,
        positive_points=positive_points[:3],
        risk_points=risk_points[:3],
        freshness_label=freshness_label,
        top_events=events[:5],
        asset_context="ETF context",
        context_note=context_note,
        primary_read=primary_read,
    )


def _build_fallback_context(snapshot: StockSnapshot | None) -> tuple[list[str], list[str]]:
    """Use the latest available company context when news is sparse."""
    if snapshot is None:
        return [], []

    fundamentals = snapshot.metadata.fundamentals or {}
    positive_points: list[str] = []
    risk_points: list[str] = []

    revenue_growth = fundamentals.get("revenueGrowth")
    earnings_growth = fundamentals.get("earningsGrowth")
    roe = fundamentals.get("returnOnEquity")
    forward_pe = fundamentals.get("forwardPE")
    trailing_pe = fundamentals.get("trailingPE")
    debt_to_equity = fundamentals.get("debtToEquity")

    if isinstance(revenue_growth, (int, float)) and revenue_growth >= 0.1:
        positive_points.append("Reported revenue growth still looks supportive.")
    if isinstance(earnings_growth, (int, float)) and earnings_growth >= 0.1:
        positive_points.append("Reported earnings growth still supports the story.")
    if isinstance(roe, (int, float)) and roe >= 0.18:
        positive_points.append("Business quality still looks solid based on return on equity.")

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
            ["Market context is limited because current ETF price data was not available."],
            ["ETF-specific item flow is light, so this read should stay lightweight."],
            "Neutral",
        )

    latest = snapshot.history.iloc[-1]
    price = float(latest["Close"])
    sma50 = float(latest["SMA_50"])
    sma200 = float(latest["SMA_200"])
    rsi = float(latest["RSI_14"])
    context_style = _infer_etf_style(snapshot)

    trend_positive = price > sma50 and price > sma200 and sma50 > sma200
    trend_weak = price < sma50 and price < sma200 and sma50 < sma200

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
        positive_points.append("Broad market tone is still the main support behind this ETF.")
        risk_points.append("If leadership narrows or index breadth weakens, momentum can fade quickly.")
    elif context_style == "large_cap_growth":
        positive_points.append("Growth-heavy leadership remains the key support when the trend holds together.")
        risk_points.append("This ETF stays sensitive to rate pressure and any crack in mega-cap leadership.")
    elif context_style == "technology":
        positive_points.append("Technology leadership is the main backdrop here, more than any one company headline.")
        risk_points.append("Tech momentum can unwind quickly if rates or sentiment turn against the group.")
    elif context_style == "financials":
        positive_points.append("Financial sector tone improves most when the group reclaims trend support.")
        risk_points.append("Rate expectations and credit worries can swing this sector quickly.")
    else:
        positive_points.append("This ETF is better read through sector or index tone than through company-specific headlines.")
        risk_points.append("Without a stronger trend, ETF context is useful but not decisive.")

    if rsi >= 70:
        risk_points.append("Momentum looks extended, which can weaken short-term entry quality.")
        if bias == "Positive":
            bias = "Neutral"
    elif rsi < 40 and trend_weak:
        risk_points.append("Momentum remains soft, which keeps the backdrop cautious.")

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
    if any(token in text for token in ("technology", "xlk", "vgt", "tech")):
        return "technology"
    if any(token in text for token in ("financial", "xlf", "bank")):
        return "financials"
    return "generic_etf"


def _positive_etf_trend_line(style: str) -> str:
    if style == "broad_market":
        return "Broad large-cap trend remains constructive above key moving averages."
    if style == "large_cap_growth":
        return "Growth-heavy leadership remains constructive above key moving averages."
    if style == "technology":
        return "Technology leadership remains constructive above key moving averages."
    if style == "financials":
        return "Financial sector momentum looks constructive above key moving averages."
    return "ETF trend remains constructive above key moving averages."


def _negative_etf_trend_line(style: str) -> str:
    if style == "broad_market":
        return "Broad large-cap trend sits below key moving averages, so the backdrop still looks weak."
    if style == "large_cap_growth":
        return "Growth-heavy leadership is below key moving averages, so the backdrop still looks weak."
    if style == "technology":
        return "Technology sector trend is below key moving averages, so the backdrop still looks weak."
    if style == "financials":
        return "Financial sector trend is below key moving averages, so the backdrop still looks weak."
    return "ETF trend is below key moving averages, so the backdrop still looks weak."


def _mixed_etf_line(style: str) -> str:
    if style == "broad_market":
        return "Broad market context is still constructive enough to watch, but the trend read is mixed."
    if style == "large_cap_growth":
        return "Growth leadership still matters here, but the trend read is mixed."
    if style == "technology":
        return "Technology context still matters here, but the trend read is mixed."
    if style == "financials":
        return "Financial sector context matters here, but the trend read is mixed."
    return "ETF context is usable, but the trend read is mixed rather than decisive."


def _parse_published_at(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _freshness_from_events(events: list[CatalystEvent]) -> str:
    parsed_dates = [parsed for event in events if (parsed := _parse_published_at(event.published_at)) is not None]
    latest_date = max(parsed_dates) if parsed_dates else None
    days_old = (datetime.now(timezone.utc) - latest_date).days if latest_date is not None else None
    return classify_freshness(days_old)


def _event_bullets(events: list[CatalystEvent], polarity: str) -> list[str]:
    bullets: list[str] = []
    seen_categories: set[str] = set()
    for event in events:
        if event.polarity != polarity or event.category in seen_categories:
            continue
        bullets.append(event.summary)
        seen_categories.add(event.category)
    return bullets[:3]


def _build_stock_primary_read(events: list[CatalystEvent], bias: str, freshness_label: str) -> str:
    categories = [event.category for event in events]
    dominant = max(set(categories), key=categories.count) if categories else "generic_news"
    category_label = {
        "earnings": "earnings-related",
        "guidance": "guidance-related",
        "analyst": "analyst",
        "product": "product and demand",
        "regulation": "regulatory or legal",
        "m_and_a_contract": "deal and contract",
        "sector": "sector",
        "generic_news": "company-specific",
    }.get(dominant, "company-specific")
    if bias == "Positive":
        lead = f"Recent {category_label} flow is supportive and broadly lines up with the current setup."
    elif bias == "Caution":
        lead = f"Recent {category_label} flow is cautionary and deserves respect against the current setup."
    else:
        lead = "Recent company-specific flow is mixed, so this read adds context more than conviction."

    if freshness_label == "Stale":
        return f"{lead} The available items are getting older, so keep the read lighter."
    return lead


def _build_etf_primary_read(snapshot: StockSnapshot | None, freshness_label: str, has_events: bool) -> str:
    style = _infer_etf_style(snapshot) if snapshot is not None and not snapshot.history.empty else "generic_etf"
    if style == "broad_market":
        lead = "This ETF is mainly driven by the broad market backdrop rather than by company-specific events."
    elif style == "large_cap_growth":
        lead = "This ETF is mainly driven by growth leadership, rate sensitivity, and mega-cap trend support."
    elif style == "technology":
        lead = "This ETF is mainly driven by technology leadership and sector momentum."
    elif style == "financials":
        lead = "This ETF is mainly driven by financial-sector tone, rates, and credit sentiment."
    else:
        lead = "This ETF is best read through market and sector context rather than company-specific headlines."

    if not has_events or freshness_label == "Stale":
        return f"{lead} Treat this more as backdrop than as a fresh event read."
    return f"{lead} Recent items add context, but the market backdrop still does most of the work."


def _merge_unique(base: list[str], additions: list[str]) -> list[str]:
    merged = list(base)
    for item in additions:
        if item not in merged:
            merged.append(item)
    return merged


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
    """Fetch recent items and summarize them into a catalyst layer."""
    return build_catalyst_summary(get_catalyst_events(ticker), snapshot)
