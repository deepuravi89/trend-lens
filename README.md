# Trend Lens

Trend Lens is a local-first Streamlit dashboard for personal stock analysis. It combines technical signals, fundamental quality checks, and portfolio-aware position sizing into one premium research cockpit.

## What The App Does

- Looks up a ticker or company name with `yfinance`
- Scores the technical setup out of 40
- Scores the fundamental picture out of 40
- Scores your position context out of 20
- Produces a total score out of 100 with a verdict and confidence label
- Shows factor-by-factor point contributions so the score is inspectable
- Calculates practical position math using your actual portfolio value and max allocation rules
- Plots price, moving averages, volume, RSI, and MACD with Plotly

## Project Structure

```text
trend-lens/
├── app.py
├── components/
├── config/
├── services/
├── tests/
├── utils/
└── requirements.txt
```

## Setup

Create and activate a virtual environment, then install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Run

```bash
python3 -m streamlit run app.py
```

## Run Tests

```bash
python3 -m pytest
```

## What The Scores Mean

- `Technical score (40)`:
  Looks at price vs 50DMA and 200DMA, 50DMA vs 200DMA, RSI, MACD, volume, and distance from key moving averages.
- `Fundamental score (40)`:
  Looks at valuation, growth, returns on capital, leverage, cash flow, margins, and data completeness.
- `Position score (20)`:
  Looks at your current allocation, remaining room under your max cap, available cash, unrealized gain/loss, and whether the stock looks extended.
- `Total score (100)`:
  Combines all three sections into a single readout.

## Confidence Labels

- `High`:
  Data coverage is strong and the signals line up cleanly.
- `Medium`:
  The setup is usable, but either the signals are mixed or some data is missing.
- `Low`:
  Sparse fundamentals or weak alignment reduce trust in the conclusion.

## Metric Glossary System

Trend Lens now includes a centralized metric knowledge layer so users can learn key indicators on demand without cluttering the dashboard.

- Metric definitions live in `config/metric_definitions.py`
- Tooltip and glossary helpers live in `utils/metric_help.py`
- UI components read from that central registry instead of hardcoding explanations inline

If you add a new metric in the future:

1. Add a canonical key and definition in `config/metric_definitions.py`
2. Reuse that same key in scoring or UI components
3. Keep interpretation ranges aligned with the thresholds in `config/scoring_config.py`
4. Prefer short, practical definitions over long academic explanations

## How To Use The Position Advisor Inputs

- `Total portfolio value`:
  Your full portfolio size. This is used to calculate current allocation and max allowable size.
- `Shares owned`:
  How many shares of this stock you currently own.
- `Average cost basis`:
  Used to estimate unrealized gain/loss.
- `Max portfolio allocation (%)`:
  Your hard ceiling for this position.
- `Target position size (%)`:
  Optional softer target below the hard cap.
- `Cash available to deploy`:
  Capital you are actually willing to put to work now.

The app uses these fields to estimate:
- Current position value
- Current allocation %
- Unrealized gain/loss
- Room left before your max allocation
- Shares you can add with cash
- Shares you can add before reaching your allocation cap
- Suggested shares to add now when the recommendation supports adding

## How Allocation Is Calculated

Trend Lens uses true portfolio-based sizing math for the Position Advisor:

- `Current position value = shares owned × current price`
- `Current allocation % = current position value / total portfolio value`
- `Max allowed position value = total portfolio value × max portfolio allocation %`
- `Remaining room to add = max allowed position value - current position value`
- `Cash-limited add amount = min(cash available to deploy, remaining room to add)`
- `Estimated shares can add now = floor(cash-limited add amount / current price)`

If you provide a target position size:

- `Target position value = total portfolio value × target position size %`
- `Gap to target = target position value - current position value`

## Position Advisor Labels

- `Add`:
  Strong overall setup, supportive technicals, and real room under your cap.
- `Add Small`:
  Decent setup, but either remaining room, score quality, or conviction is more limited.
- `Add on Pullback`:
  Strong stock overall, but technically extended enough that waiting may improve entry quality.
- `Hold`:
  Reasonable setup with no urgent action, or a position already near target size.
- `Trim`:
  Position is oversized, technically stretched, or weaker than its current weight justifies.
- `Avoid New Buy`:
  Setup lacks enough technical or fundamental support for fresh capital.

## Known Limitations

- The app relies on Yahoo Finance field coverage through `yfinance`, which can be incomplete or noisy.
- Some companies and ETFs have sparse or inconsistent fundamental fields.
- The scoring model is transparent and intentionally simple; it is a decision-support framework, not a predictive model.
- Suggested add sizes are practical heuristics, not optimization outputs.
- If total portfolio value is missing or zero, allocation-aware advice is intentionally reduced.
- If average cost basis is missing while shares are held, unrealized gain/loss math cannot be computed accurately.

## Not Financial Advice

Trend Lens is a personal research and decision-support tool. It is not a trading bot, not investment advice, and not a recommendation to buy or sell any security.
