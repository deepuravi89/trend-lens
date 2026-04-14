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

## Known Limitations

- The app relies on Yahoo Finance field coverage through `yfinance`, which can be incomplete or noisy.
- Some companies and ETFs have sparse or inconsistent fundamental fields.
- The scoring model is transparent and intentionally simple; it is a decision-support framework, not a predictive model.
- Suggested add sizes are practical heuristics, not optimization outputs.

## Not Financial Advice

Trend Lens is a personal research and decision-support tool. It is not a trading bot, not investment advice, and not a recommendation to buy or sell any security.
