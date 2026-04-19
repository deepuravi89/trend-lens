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


def format_currency_full(value: float | None) -> str:
    """Format currency with full thousands separators."""
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


def format_percent(value: float | None) -> str:
    """Format percentages from decimal values."""
    if value is None:
        return "N/A"
    return f"{value * 100:+.1f}%"


def format_percent_plain(value: float | None) -> str:
    """Format percentages without forcing a sign."""
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def format_number(value: float | None) -> str:
    """Format generic numeric values."""
    if value is None:
        return "N/A"
    if abs(value) >= 100:
        return f"{value:,.0f}"
    return f"{value:.2f}"


def format_points(value: float) -> str:
    """Format point contributions for factor display."""
    return f"{value:+.1f}".replace(".0", "")


def format_shares(value: float | None) -> str:
    """Format share counts for position math."""
    if value is None:
        return "N/A"
    if abs(value - int(value)) < 1e-9:
        return f"{int(value):,}"
    return f"{value:,.2f}"


def truncate_text(value: str, max_length: int = 180) -> str:
    """Truncate long text for compact card layouts."""
    if len(value) <= max_length:
        return value
    return value[: max_length - 1].rstrip() + "..."
