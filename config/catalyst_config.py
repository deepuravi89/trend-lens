"""Configuration for catalyst recency and lightweight news classification."""

from __future__ import annotations

CATALYST_RECENCY_DAYS = {
    "fresh": 3,
    "recent": 10,
    "stale": 21,
}

CATALYST_CATEGORY_KEYWORDS = {
    "earnings": ["earnings", "revenue", "eps", "beat", "miss", "quarter", "results"],
    "guidance": ["guidance", "outlook", "forecast", "raises outlook", "cuts outlook"],
    "analyst": ["analyst", "upgrade", "downgrade", "price target", "rating"],
    "product": ["launch", "product", "shipment", "demand", "adoption", "volume", "delivery", "order"],
    "regulation": ["regulation", "antitrust", "probe", "lawsuit", "approval", "ban", "recall", "investigation", "legal"],
    "m_and_a_contract": ["contract", "deal", "partnership", "acquisition", "merger", "award", "customer", "supply agreement"],
    "sector": ["sector", "industry", "peer", "market demand", "industrywide", "industry-wide"],
}

POSITIVE_KEYWORDS = [
    "beat",
    "raises",
    "raise",
    "strong",
    "growth",
    "upgrade",
    "surge",
    "wins",
    "win",
    "approval",
    "record",
    "expands",
    "accelerates",
    "bullish",
    "outperform",
    "rebound",
    "stronger",
]

CAUTION_KEYWORDS = [
    "miss",
    "cut",
    "cuts",
    "warns",
    "warning",
    "downgrade",
    "probe",
    "lawsuit",
    "slowdown",
    "pressure",
    "weak",
    "delay",
    "decline",
    "cuts outlook",
    "underperform",
    "slumps",
    "falling",
    "cuts guidance",
]

SOURCE_CONFIDENCE = {
    "reuters": "High",
    "bloomberg": "High",
    "associated press": "High",
    "ap": "High",
    "marketwatch": "Medium",
    "yahoo finance": "Medium",
    "benzinga": "Medium",
    "seeking alpha": "Medium",
}

CATALYST_BIAS_PRIORITY = {
    "Positive": 3,
    "Neutral": 2,
    "Caution": 1,
}
