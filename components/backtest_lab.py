"""Strategy Lab / Backtest Lab UI."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from config.backtest_config import BACKTEST_COPY, DEFAULT_BACKTESTS, STRATEGY_TEMPLATES
from services.backtesting import BacktestConfig, BacktestResult, run_backtest
from services.market_data import SearchMatch, search_tickers
from utils.formatters import format_currency, format_currency_full, format_percent


def render_backtest_lab() -> None:
    """Render the Strategy Lab tab."""
    st.markdown(
        """
        <div class="detail-card" style="margin-bottom:1rem;">
            <div class="section-title">Strategy Lab</div>
            <div class="section-subtitle">
                Test how Trend Lens setups and a few simple technical templates behaved historically.
                Use this as research context, not as a prediction engine.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    config = render_backtest_controls()
    if st.button("Run Strategy Lab", use_container_width=True, key="run_strategy_lab"):
        st.session_state["strategy_lab_result"] = run_backtest(config)
        st.session_state["strategy_lab_config"] = config

    result = st.session_state.get("strategy_lab_result")
    if result is None:
        st.info("Choose a strategy, date range, and position assumptions, then run the Strategy Lab.")
        return

    render_backtest_results(result)


def render_backtest_controls() -> BacktestConfig:
    """Render Strategy Lab input controls and return the selected config."""
    today = date.today()
    default_start = today - timedelta(days=365 * DEFAULT_BACKTESTS["years"])
    st.markdown('<div class="input-shell">', unsafe_allow_html=True)
    left, right = st.columns([1.2, 1], gap="large")

    with left:
        query = st.text_input(
            "Test ticker or company",
            value=st.session_state.get("strategy_lab_query", "MSFT"),
            max_chars=40,
            help="Use a ticker like MSFT or a company name like Microsoft.",
            key="strategy_lab_query_input",
        ).strip()
        st.session_state["strategy_lab_query"] = query
        matches = search_tickers(query)
        if matches:
            ticker = _render_match_selector(matches)
        else:
            ticker = query.upper()
            if query:
                st.caption("No search matches found. Trend Lens will try your input as the ticker symbol directly.")

        strategy = st.selectbox(
            "Strategy template",
            options=[template.label for template in STRATEGY_TEMPLATES],
            index=0,
            help="These templates are simple rule sets based on the same setup framework used in the main dashboard.",
        )
        active_template = next(template for template in STRATEGY_TEMPLATES if template.label == strategy)
        st.caption(active_template.description)

        col_a, col_b = st.columns(2, gap="medium")
        with col_a:
            start_date = st.date_input("Test from", value=default_start, max_value=today, key="bt_start")
        with col_b:
            end_date = st.date_input("Test to", value=today, max_value=today, key="bt_end")

    with right:
        col_a, col_b = st.columns(2, gap="medium")
        with col_a:
            holding_period_days = st.number_input(
                "Max holding time (days)",
                min_value=1,
                max_value=252,
                value=DEFAULT_BACKTESTS["holding_period_days"],
                step=1,
                help="A simple time exit in trading days if stop loss or take profit does not trigger first.",
            )
        with col_b:
            slippage_pct = st.number_input(
                "Slippage assumption (%)",
                min_value=0.0,
                max_value=5.0,
                value=float(DEFAULT_BACKTESTS["slippage_pct"]),
                step=0.05,
                help="A small execution penalty applied to entries and exits to keep the simulation less optimistic.",
            )

        col_c, col_d = st.columns(2, gap="medium")
        with col_c:
            initial_capital = st.number_input(
                "Starting capital ($)",
                min_value=1000.0,
                value=float(DEFAULT_BACKTESTS["initial_capital"]),
                step=1000.0,
                help="The simulated account size at the start of the test.",
            )
        with col_d:
            trade_size_pct = st.number_input(
                "Capital used per trade (%)",
                min_value=1.0,
                max_value=100.0,
                value=float(DEFAULT_BACKTESTS["trade_size_pct"]),
                step=5.0,
                help="How much of the simulated account each trade uses.",
            )

        col_e, col_f = st.columns(2, gap="medium")
        with col_e:
            use_stop = st.toggle("Use stop loss", value=False, help="Exit early if the trade falls a set amount from entry.")
            stop_loss_pct = (
                st.number_input("Stop loss level (%)", min_value=0.5, max_value=50.0, value=8.0, step=0.5, key="bt_stop")
                if use_stop
                else None
            )
        with col_f:
            use_take = st.toggle("Use take profit", value=False, help="Exit early if the trade reaches a chosen gain target.")
            take_profit_pct = (
                st.number_input("Take profit level (%)", min_value=0.5, max_value=100.0, value=15.0, step=0.5, key="bt_take")
                if use_take
                else None
            )

    with st.expander("How to read this lab", expanded=False):
        st.write(BACKTEST_COPY["assumptions"])
        for warning in BACKTEST_COPY["warnings"]:
            st.write(f"- {warning}")

    st.markdown("</div>", unsafe_allow_html=True)

    return BacktestConfig(
        ticker=ticker,
        strategy_name=strategy,
        start_date=start_date,
        end_date=end_date,
        holding_period_days=int(holding_period_days),
        initial_capital=float(initial_capital),
        trade_size_pct=float(trade_size_pct),
        stop_loss_pct=float(stop_loss_pct) if stop_loss_pct is not None else None,
        take_profit_pct=float(take_profit_pct) if take_profit_pct is not None else None,
        slippage_pct=float(slippage_pct),
    )


def render_backtest_results(result: BacktestResult) -> None:
    """Render Strategy Lab results and charts."""
    if result.error:
        st.error(result.error)
        return

    explanation = (
        f"This test found {len(result.trades)} historical trades with a {result.win_rate:.0%} win rate "
        f"and an average trade return of {result.average_return:.1%}. Use it as historical evidence, not as a prediction."
    )
    interpretation = build_result_interpretation(result)
    st.markdown(
        (
            '<div class="detail-card" style="margin-bottom:1rem;">'
            '<div class="section-title">Historical Read</div>'
            f'<div class="section-subtitle">{explanation}</div>'
            f'<div class="metric-caption" style="margin-top:0.55rem;">{interpretation}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        (
            '<div style="display:flex; flex-wrap:wrap; gap:0.75rem; margin-bottom:1rem;">'
            f'{_mini_card("Trades", str(len(result.trades)))}'
            f'{_mini_card("Win Rate", format_percent(result.win_rate), "Share of trades that finished positive.")}'
            f'{_mini_card("Average Trade", format_percent(result.average_return), "Average gain or loss per trade.")}'
            f'{_mini_card("Median Trade", format_percent(result.median_return), "Middle trade outcome, less skewed by outliers.")}'
            f'{_mini_card("Best Trade", format_percent(result.best_trade), "Largest single-trade gain.")}'
            f'{_mini_card("Worst Trade", format_percent(result.worst_trade), "Largest single-trade loss.")}'
            f'{_mini_card("Avg Hold", f"{result.average_holding_days:.1f}d", "Average number of trading days per position.")}'
            f'{_mini_card("Max Drawdown", format_percent(result.max_drawdown), "Worst peak-to-trough equity decline during the test.")}'
            f'{_mini_card("Final Equity", format_currency_full(result.final_equity), "Ending account value after all simulated trades.")}'
            f'{_mini_card("Benchmark", format_percent(result.benchmark_return) if result.benchmark_return is not None else "N/A", "Buy-and-hold return over the same date range.")}'
            f'{_mini_card("Profit Factor", f"{result.profit_factor:.2f}" if result.profit_factor is not None else "N/A", "Gross gains divided by gross losses.")}'
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.4, 1], gap="large")
    with left:
        st.markdown('<div class="detail-card chart-shell">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Equity Curve</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-subtitle" style="margin-bottom:0.8rem;">This shows how the simulated account would have changed over time if you followed the selected rules.</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(build_equity_curve(result), use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown('<div class="detail-card chart-shell">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Trade Return Distribution</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-subtitle" style="margin-bottom:0.8rem;">A quick look at whether results clustered tightly or swung around from trade to trade.</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(build_return_distribution(result), use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="detail-card chart-shell" style="margin-top:1rem;">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Signal Map</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle" style="margin-bottom:0.9rem;">Entries and exits overlaid on price so you can see where the strategy actually acted.</div>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(build_signal_chart(result), use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Trade Log", expanded=False):
        if result.trades:
            st.caption("Each row shows one completed historical trade, including the entry, exit, result, and why the trade closed.")
            st.dataframe(trades_to_frame(result.trades), use_container_width=True, hide_index=True)
        else:
            st.caption("No historical trades matched the selected strategy and date range.")


def build_equity_curve(result: BacktestResult) -> go.Figure:
    """Build the Strategy Lab equity curve chart."""
    frame = result.equity_curve
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=frame["Date"],
            y=frame["Equity"],
            mode="lines",
            name="Equity",
            line={"color": "#60a5fa", "width": 2.4},
        )
    )
    fig.update_layout(
        height=360,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(11, 19, 36, 0.82)",
        margin={"l": 12, "r": 12, "t": 10, "b": 8},
        font={"color": "#dbe7fb", "family": "Verdana, sans-serif"},
    )
    fig.update_xaxes(showgrid=False, color="#8fa5c5")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(148, 163, 184, 0.12)", color="#8fa5c5")
    return fig


def build_return_distribution(result: BacktestResult) -> go.Figure:
    """Build a simple trade return histogram."""
    returns = [trade.return_pct * 100 for trade in result.trades]
    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=returns,
            nbinsx=16,
            marker_color="#3dd9a4",
            opacity=0.82,
            name="Trade Returns",
        )
    )
    fig.update_layout(
        height=360,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(11, 19, 36, 0.82)",
        margin={"l": 12, "r": 12, "t": 10, "b": 8},
        font={"color": "#dbe7fb", "family": "Verdana, sans-serif"},
        bargap=0.08,
    )
    fig.update_xaxes(title="Return %", showgrid=False, color="#8fa5c5")
    fig.update_yaxes(title="Trades", showgrid=True, gridcolor="rgba(148, 163, 184, 0.12)", color="#8fa5c5")
    return fig


def build_signal_chart(result: BacktestResult) -> go.Figure:
    """Build a price chart with entry and exit markers."""
    frame = result.signal_frame
    fig = make_subplots(rows=1, cols=1)
    fig.add_trace(go.Scatter(x=frame.index, y=frame["Close"], mode="lines", name="Price", line={"color": "#e6eefc", "width": 2.2}))
    fig.add_trace(go.Scatter(x=frame.index, y=frame["SMA_50"], mode="lines", name="50DMA", line={"color": "#60a5fa", "width": 1.5}))
    fig.add_trace(go.Scatter(x=frame.index, y=frame["SMA_200"], mode="lines", name="200DMA", line={"color": "#3dd9a4", "width": 1.5}))
    entry_frame = frame.dropna(subset=["Entry"])
    exit_frame = frame.dropna(subset=["Exit"])
    fig.add_trace(
        go.Scatter(
            x=entry_frame.index,
            y=entry_frame["Entry"],
            mode="markers",
            name="Entries",
            marker={"symbol": "triangle-up", "size": 10, "color": "#3dd9a4"},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=exit_frame.index,
            y=exit_frame["Exit"],
            mode="markers",
            name="Exits",
            marker={"symbol": "triangle-down", "size": 10, "color": "#ff6b7a"},
        )
    )
    fig.update_layout(
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(11, 19, 36, 0.82)",
        margin={"l": 12, "r": 12, "t": 10, "b": 8},
        font={"color": "#dbe7fb", "family": "Verdana, sans-serif"},
        legend={"orientation": "h", "y": 1.02, "x": 0},
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, color="#8fa5c5")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(148, 163, 184, 0.12)", color="#8fa5c5")
    return fig


def trades_to_frame(trades: list) -> pd.DataFrame:
    """Convert trade results into a Streamlit-friendly table."""
    return pd.DataFrame(
        [
            {
                "Entered": trade.entry_date.date().isoformat(),
                "Exited": trade.exit_date.date().isoformat(),
                "Entry": format_currency_full(trade.entry_price),
                "Exit": format_currency_full(trade.exit_price),
                "Trade Return": format_percent(trade.return_pct),
                "Profit / Loss": format_currency_full(trade.pnl),
                "Days Held": trade.holding_days,
                "Exit Type": trade.exit_reason,
                "Setup": trade.setup_label,
            }
            for trade in trades
        ]
    )


def _render_match_selector(matches: list[SearchMatch]) -> str:
    best = matches[0]
    st.markdown(
        (
            '<div class="section-subtitle" style="margin: 0.35rem 0 0.65rem 0;">'
            f'Best match: <strong style="color:#e6eefc;">{best.symbol}</strong> — {best.name}'
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    if len(matches) == 1:
        return best.symbol
    selected_label = st.selectbox(
        "Choose match",
        options=[match.label for match in matches],
        index=0,
        key="strategy_lab_match",
    )
    return next(match for match in matches if match.label == selected_label).symbol


def build_result_interpretation(result: BacktestResult) -> str:
    """Create a plain-English summary of the backtest result."""
    if not result.trades:
        return "No trades were triggered in the selected period, so this setup may have been rare or inactive for this name."

    if result.win_rate >= 0.55 and result.average_return > 0 and result.max_drawdown > -0.2:
        return "Historically, this setup showed a reasonably constructive edge here, though the path still included normal drawdowns."
    if result.average_return > 0 and result.max_drawdown <= -0.2:
        return "Returns were positive on average, but the ride was rough enough that position sizing and patience would have mattered."
    if result.average_return <= 0 and result.win_rate < 0.5:
        return "Historically, this rule set did not show a strong edge on this name over the chosen window."
    return "Historically, the outcome was mixed enough that this setup looks more situational than consistently reliable."


def _mini_card(label: str, value: str, help_text: str | None = None) -> str:
    caption = f'<div class="metric-caption" style="margin-top:0.4rem; line-height:1.45;">{help_text}</div>' if help_text else ""
    return f'<div class="mini-stat"><span>{label}</span><strong>{value}</strong>{caption}</div>'
