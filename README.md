# Trend Lens

Trend Lens is a local-first Streamlit dashboard for personal stock analysis. It blends technical signals, fundamentals, and your own position sizing inputs into a simple buy/hold/trim style readout.

## Features

- Live ticker lookup with `yfinance`
- Technical score out of 40
- Fundamental score out of 40
- Position advisor score out of 20
- Total score out of 100 with plain-English verdicts
- Interactive Plotly chart suite with price, moving averages, volume, RSI, and MACD
- Defensive handling for sparse or missing fundamental fields

## Project Structure

```text
trend-lens/
├── app.py
├── components/
│   ├── charts.py
│   ├── inputs.py
│   └── score_cards.py
├── config/
│   └── scoring_config.py
├── services/
│   ├── advisor.py
│   ├── market_data.py
│   └── scoring.py
├── utils/
│   ├── calculations.py
│   └── formatters.py
└── requirements.txt
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Then open the local URL shown in the terminal, usually `http://localhost:8501`.

## Notes

- This app is designed as a personal decision-support tool, not financial advice.
- `yfinance` field coverage varies by stock, so some fundamental sections may show reduced confidence instead of crashing.
- The scoring logic is centralized in `config/scoring_config.py` for easier tuning later.
