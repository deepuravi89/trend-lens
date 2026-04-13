"""Chart rendering utilities."""

from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from services.market_data import StockSnapshot

__all__ = ["render_chart_suite", "render_chart_suit", "build_chart"]


def render_chart_suite(snapshot: StockSnapshot) -> None:
    """Render the main price and indicator chart suite."""
    chart = build_chart(snapshot)
    st.markdown('<div class="detail-card chart-shell">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Trend & Momentum</div>', unsafe_allow_html=True)
    st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)


def render_chart_suit(snapshot: StockSnapshot) -> None:
    """Compatibility alias for older import/session state."""
    render_chart_suite(snapshot)


def build_chart(snapshot: StockSnapshot) -> go.Figure:
    """Construct the multi-panel chart layout."""
    frame = snapshot.history.copy()

    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.035,
        row_heights=[0.52, 0.15, 0.16, 0.17],
        specs=[[{"secondary_y": False}], [{"secondary_y": False}], [{"secondary_y": False}], [{"secondary_y": False}]],
    )

    fig.add_trace(
        go.Scatter(
            x=frame.index,
            y=frame["Close"],
            name="Price",
            mode="lines",
            line={"color": "#e6eefc", "width": 2.4},
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=frame.index,
            y=frame["SMA_50"],
            name="50D MA",
            mode="lines",
            line={"color": "#60a5fa", "width": 1.8},
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=frame.index,
            y=frame["SMA_200"],
            name="200D MA",
            mode="lines",
            line={"color": "#3dd9a4", "width": 1.8},
        ),
        row=1,
        col=1,
    )

    bar_colors = ["#3dd9a4" if close >= open_ else "#ff6b7a" for close, open_ in zip(frame["Close"], frame["Open"])]
    fig.add_trace(
        go.Bar(
            x=frame.index,
            y=frame["Volume"],
            name="Volume",
            marker_color=bar_colors,
            opacity=0.8,
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=frame.index,
            y=frame["RSI_14"],
            name="RSI (14)",
            mode="lines",
            line={"color": "#ffb648", "width": 2},
        ),
        row=3,
        col=1,
    )
    fig.add_hline(y=70, line_dash="dash", line_color="rgba(255, 107, 122, 0.55)", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="rgba(61, 217, 164, 0.55)", row=3, col=1)

    fig.add_trace(
        go.Bar(
            x=frame.index,
            y=frame["MACD_HIST"],
            name="MACD Hist",
            marker_color=["#3dd9a4" if val >= 0 else "#ff6b7a" for val in frame["MACD_HIST"]],
            opacity=0.7,
        ),
        row=4,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=frame.index,
            y=frame["MACD"],
            name="MACD",
            mode="lines",
            line={"color": "#60a5fa", "width": 1.8},
        ),
        row=4,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=frame.index,
            y=frame["MACD_SIGNAL"],
            name="Signal",
            mode="lines",
            line={"color": "#ffb648", "width": 1.6},
        ),
        row=4,
        col=1,
    )

    fig.update_layout(
        height=900,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(11, 19, 36, 0.82)",
        margin={"l": 14, "r": 14, "t": 18, "b": 10},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.01,
            "xanchor": "left",
            "x": 0,
            "font": {"color": "#dbe7fb"},
        },
        font={"color": "#dbe7fb", "family": "Verdana, sans-serif"},
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, zeroline=False, color="#8fa5c5")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(148, 163, 184, 0.12)", zeroline=False, color="#8fa5c5")
    return fig
