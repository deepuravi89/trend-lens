"""Configuration for catalyst recency and lightweight news classification."""

from __future__ import annotations

CATALYST_RECENCY_DAYS = {
    "fresh": 3,
    "recent": 10,
    "stale": 21,
}

CATALYST_CATEGORY_KEYWORDS = {
    "earnings": ["earnings", "revenue", "eps", "beat", "miss", "guidance"],
    "guidance": ["guidance", "outlook", "forecast"],
    "analyst": ["analyst", "upgrade", "downgrade", "price target", "rating"],
    "product": ["launch", "product", "shipment", "demand", "adoption", "contract", "deal"],
    "regulation": ["regulation", "antitrust", "probe", "lawsuit", "approval", "ban"],
    "sector": ["sector", "industry", "peer", "market demand"],
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
