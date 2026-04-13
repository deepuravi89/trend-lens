"""Formatting helpers used throughout the UI."""

from __future__ import annotations


def format_currency(value: float | None) -> str:
    """Format numeric currency values with compact millions/billions support."""
    if value is None:
        return "N/A"
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if abs_value >= 1_000:
        return f"${value:,.0f}"
    return f"${value:,.2f}"


def format_percent(value: float | None) -> str:
    """Format percentages from decimal values."""
    if value is None:
        return "N/A"
    return f"{value * 100:+.1f}%"


def format_number(value: float | None) -> str:
    """Format generic numeric values."""
    if value is None:
        return "N/A"
    if abs(value) >= 100:
        return f"{value:,.0f}"
    return f"{value:.2f}"


def truncate_text(value: str, max_length: int = 180) -> str:
    """Truncate long text for compact card layouts."""
    if len(value) <= max_length:
        return value
    return value[: max_length - 1].rstrip() + "…"
