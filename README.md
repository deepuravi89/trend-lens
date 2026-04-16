# Trend Lens

Trend Lens is a local-first Streamlit app for personal stock analysis. It combines technical signals, fundamental quality checks, and portfolio-aware position sizing into one dashboard so you can judge whether a stock looks attractive to add, hold, trim, or avoid.

It is a decision-support tool, not a trading bot, and not financial advice.

## Overview

Trend Lens helps you evaluate a stock from three angles:

- `Technical analysis`: trend, momentum, volume, and extension
- `Fundamental analysis`: valuation, growth, profitability, leverage, and cash flow
- `Position analysis`: your current holdings, sizing rules, and room to add

The app turns those inputs into:

- a technical score
- a fundamental score
- a position advisor score
- a total score out of 100
- a setup classification
- a practical recommendation

## Key Features

- `Technical Score`
  Factor-by-factor breakdown of price vs moving averages, RSI, MACD, volume, and distance from trend.
- `Fundamental Score`
  Factor-by-factor breakdown of valuation, growth, returns, leverage, margins, cash flow, and data completeness.
- `Position Advisor`
  Portfolio-aware recommendation based on your current position, portfolio size, target sizing, and available cash.
- `Position Math`
  Clear sizing panel showing allocation, room left, unrealized gain/loss, and estimated shares you can add now.
- `Setup Classification`
  Rule-based chart read such as `Strong Uptrend`, `Recovery Setup`, or `Weak Downtrend`.
- `Recommendation System`
  Action labels including `Add`, `Add Small`, `Add on Pullback`, `Hold`, `Trim`, and `Avoid New Buy`.
- `Metric Glossary`
  Inline help, tooltips, and a bottom-page metric guide for beginner-friendly definitions.

## Setup Classification

Trend Lens adds a simple rule-based setup label on top of the raw technical score to make the chart easier to interpret.

- `Strong Uptrend`
  Price is above key moving averages and momentum is supportive. This is usually the healthiest type of setup.
- `Constructive but Extended`
  The stock still looks strong, but it may be stretched enough that a fresh entry is less attractive right now.
- `Recovery Setup`
  Near-term action is improving, but the longer-term trend is not fully repaired yet.
- `Mixed Setup`
  Some signals look constructive, but the chart does not have a clean edge.
- `Weak Downtrend`
  Trend and momentum both look weak, so timing risk is higher.

These setup labels are rule-based interpretations, not predictions.

## Recommendation Logic

Trend Lens uses the setup label, total score, and your position context to produce a practical action bias.

- `Add`
  The stock looks strong and you still have meaningful room to build the position.
- `Add Small`
  The setup is workable, but conviction, timing, or remaining room argues for a measured add.
- `Add on Pullback`
  The stock looks strong overall, but it is extended enough that patience may improve entry quality.
- `Hold`
  The stock is reasonable to keep, but there is no strong case to press harder right now.
- `Trim`
  The position is oversized, stretched, or weaker than its size currently justifies.
- `Avoid New Buy`
  The setup does not offer enough support for fresh capital right now.

## How To Use The App

### Inputs

- `Shares owned`
  How many shares you currently hold.
- `Average cost basis`
  Your average purchase price per share.
- `Portfolio value used for sizing`
  The portfolio value Trend Lens should use when calculating allocation.
- `Max position size`
  Your hard cap for the position as a percentage of the portfolio.
- `Target position size`
  Optional softer target below the hard cap.
- `Cash available`
  Capital you are willing to deploy now.

### How To Read The Outputs

- `Score`
  The total score combines technical, fundamental, and position-aware analysis into one number out of 100.
- `Setup type`
  A plain-English read of the current chart structure.
- `Recommendation`
  The practical action bias based on score, setup, and your sizing inputs.
- `Position math`
  The sizing panel shows current allocation, room before your cap, unrealized gain/loss, and how much you could add now.

## Example Workflow

1. Enter a ticker or company name.
2. Review the top summary: current price, total score, verdict, confidence, and quick summary.
3. Check the `Technical Score` card to see the setup label and factor breakdown.
4. Review the `Fundamental Score` card to see whether the business quality and valuation support the chart.
5. Enter your position inputs in the `Position Advisor` section.
6. Use the recommendation and `Position Math` panel to judge whether to add, wait, hold, or trim.

## Limitations

- Trend Lens is a rule-based model, not a predictive system.
- It depends on Yahoo Finance data through `yfinance`, which can be incomplete or noisy.
- Some stocks and ETFs have sparse or inconsistent fundamental coverage.
- Recommendations are decision-support heuristics, not personalized investment advice.

## Setup Instructions

Create and activate a virtual environment, then install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Run the app:

```bash
python3 -m streamlit run app.py
```

Run tests:

```bash
python3 -m pytest
```

## Not Financial Advice

Trend Lens is for personal research and decision support only. It is not financial advice and not a recommendation to buy or sell any security.
