"""Helpers for working with centralized metric definitions."""

from __future__ import annotations

from html import escape

from config.metric_definitions import METRIC_DEFINITIONS, MetricDefinition


def get_metric_info(key: str) -> MetricDefinition | None:
    """Return a metric definition or None when it is unknown."""
    return METRIC_DEFINITIONS.get(key)


def has_metric_info(key: str) -> bool:
    """Check whether a metric key exists in the registry."""
    return key in METRIC_DEFINITIONS


def format_metric_tooltip(key: str) -> str:
    """Return compact tooltip text suitable for hover help."""
    info = get_metric_info(key)
    if info is None:
        return ""
    lead_range = info.interpretation_ranges[0] if info.interpretation_ranges else ""
    parts = [
        info.plain_english_definition,
        f"Why it matters: {info.why_it_matters}",
        lead_range,
    ]
    return " ".join(part for part in parts if part).strip()


def format_metric_inline_label(key: str, fallback_label: str) -> str:
    """Render an HTML label with a lightweight tooltip affordance."""
    info = get_metric_info(key)
    if info is None:
        return escape(fallback_label)
    short = f' <span class="metric-inline-note">{escape(info.short_label)}</span>' if info.short_label else ""
    tooltip = escape(format_metric_tooltip(key), quote=True)
    return (
        f'<span class="metric-help-label" title="{tooltip}">'
        f"{escape(fallback_label)}{short}"
        '<span class="metric-help-dot">?</span>'
        "</span>"
    )


def render_metric_guide_html(keys: list[str]) -> str:
    """Render grouped glossary HTML for a list of metric keys."""
    items: list[str] = []
    for key in keys:
        info = get_metric_info(key)
        if info is None:
            continue
        ranges = "".join(f"<li>{escape(entry)}</li>" for entry in info.interpretation_ranges[:3])
        items.append(
            '<div class="metric-guide-item">'
            f'<div class="factor-name">{escape(info.label)}</div>'
            f'<div class="factor-detail">{escape(info.plain_english_definition)}</div>'
            f'<div class="metric-guide-why">{escape(info.why_it_matters)}</div>'
            f'<ul class="metric-guide-ranges">{ranges}</ul>'
            "</div>"
        )
    return "".join(items)
