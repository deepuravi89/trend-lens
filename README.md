# 📊 Trend Lens

**Trend Lens** is a local-first Streamlit app for personal stock analysis.

It combines **technical signals, fundamental quality checks, and portfolio-aware position sizing** into a single dashboard so you can decide whether a stock is worth **adding, holding, trimming, or avoiding**.

> 🧠 A decision-support tool — not a trading bot and not financial advice.

---

## 🚀 Why Trend Lens

Most tools show you **data**.
Trend Lens helps you answer:

> **“What should I do with this stock right now?”**

It brings together:

* Signal interpretation (technical + fundamental)
* Portfolio context (position sizing)
* Clear action bias (Add / Hold / Trim)
* Ranked watchlist review
* Recent catalyst context

---

## 🧠 What It Analyzes

Trend Lens evaluates a stock from three perspectives:

### 📈 Technical Analysis

* Trend (50DMA, 200DMA)
* Momentum (RSI, MACD)
* Volume confirmation
* Price extension

### 📊 Fundamental Analysis

* Valuation (P/E, PEG)
* Growth (revenue, earnings)
* Profitability (ROE, margins)
* Balance sheet (debt)
* Cash flow quality

### 🎯 Position Analysis

* Your current holdings
* Portfolio size
* Target sizing rules
* Available capital

---

## ⚡ What You Get

* ✅ Technical Score (out of 40)
* ✅ Fundamental Score (out of 40)
* ✅ Position Advisor Score (out of 20) — entry timing, sizing room, and reward vs. risk only
* 🎯 **Total Score (out of 100)**
* 🧭 **Setup Classification**
* 📌 **Actionable Recommendation**
* 👀 **Watchlist ranking dashboard**
* 📰 **Catalyst Layer**
* 🧪 **Strategy Lab / Backtest Lab**

---

## 🆕 What's New in v6

* **Headline matches the advisor.** The top of the page now shows the Position Advisor's call (Add / Hold / Trim / …), so it can no longer say "Strong Buy Zone" next to a Hold.
* **Earnings warning.** Shows the next earnings date, with a red flag when it is 7 days away or less. Also shown in the watchlist.
* **Relative strength vs the S&P 500.** 3- and 6-month return compared with SPY, shown next to the score (not part of it).
* **Score History tab.** Every stock you open is logged once a day with a neutral "new buyer" call (fixed $100k portfolio, no shares owned). After 1, 3 and 6 months the tab shows whether Add calls and high scores actually beat the S&P 500.

To log a list of tickers daily without opening the app:

```bash
python3 scripts/log_scores.py AAPL MSFT KO
```

For example, with cron at 5pm on weekdays:

```bash
0 17 * * 1-5 cd /path/to/trend-lens && .venv/bin/python scripts/log_scores.py --file tickers.txt
```

History is saved locally in `data/score_history.csv` (not committed to git).

---

## 🆕 What's New in v5

Version 5 fixes scoring bugs that made the app recommend **Hold** for almost everything:

* **Add is reachable again.** The advisor decides before its own 20 points are added, so its thresholds (72 / 82 / 58 / 45) are now read as a percent of the 80-point technical + fundamental score instead of a 100-point total.
* **No double counting.** The Position Advisor Score no longer re-rewards the stock's technical/fundamental score. It is now entry timing (0–8) + sizing room (0–8) + reward vs. risk (0–4).
* **Debt-to-equity units.** Yahoo reports this as a percent (150 = 1.5x). It is now converted to a ratio, so healthy balance sheets are no longer all marked "Heavy".
* **Negative ratios.** A negative P/E or PEG (losses) no longer scores as "Attractive", and negative shareholder equity is flagged.
* **Trim works for holders.** Trim now fires when a position is over your cap (unless it is a Strong Uptrend), when a large gain (20%+) in a full-size position is also extended, or when both trend and fundamentals are weak.
* **Cleaner catalyst keywords.** Headline keywords match whole words, so "win" no longer matches "window".

---

## 🧭 Setup Classification

Trend Lens simplifies charts into intuitive setup types:

| Setup                         | Meaning                              |
| ----------------------------- | ------------------------------------ |
| **Strong Uptrend**            | Trend and momentum aligned           |
| **Constructive but Extended** | Strong, but stretched                |
| **Recovery Setup**            | Improving short-term, weak long-term |
| **Mixed Setup**               | No clear edge                        |
| **Weak Downtrend**            | Trend and momentum weak              |

> These are rule-based interpretations, not predictions.

---

## 🎯 Recommendation System

| Recommendation      | Meaning                         |
| ------------------- | ------------------------------- |
| **Add**             | Strong setup + room to build    |
| **Add Small**       | Decent setup, measured approach |
| **Add on Pullback** | Strong but extended             |
| **Hold**            | No strong action needed         |
| **Trim**            | Oversized, a large extended gain at full size, or weak trend + weak fundamentals |
| **Avoid New Buy**   | Weak setup                      |

---

## 👀 Watchlist

Trend Lens now includes a watchlist that acts like a ranked action dashboard, not just a saved ticker list.

For each name, the watchlist shows:

* Ticker
* Company
* Total score
* Technical score
* Fundamental score
* Setup
* Recommendation
* Confidence
* Catalyst bias
* Optional note / thesis

If you add ownership context, it can also show:

* Current allocation
* Room to add

By default, the watchlist ranks names by:

1. Total score
2. Recommendation priority
3. Confidence
4. Catalyst bias

This helps surface which stock deserves attention first.

---

## 📰 Catalyst Layer

The Catalyst Layer adds lightweight recent context for each stock.

It does **not** replace the core score.
It supports the main analysis with a simple read on recent developments.

For individual stocks, the Catalyst Layer leans more on company-specific events.
For ETFs, it leans more on index, sector, and market context so broad funds do not look artificially empty when company-style news is sparse.

For each stock, Trend Lens shows:

* `Catalyst bias`: **Positive / Neutral / Caution**
* `Freshness`: **Fresh / Recent / Stale**
* Supportive catalyst bullets
* Risk bullets
* Optional recent-item expander

### Catalyst Bias Meaning

| Bias         | Meaning |
| ------------ | ------- |
| **Positive** | Recent news looks broadly supportive |
| **Neutral**  | News is mixed, sparse, or not strong enough to lean either way |
| **Caution**  | Recent developments lean negative or raise near-term risk |

### Freshness Windows

| Label      | Meaning |
| ---------- | ------- |
| **Fresh**  | 0–3 days old |
| **Recent** | 4–10 days old |
| **Stale**  | 11–21 days old or sparse |

---

## 🧪 Strategy Lab / Backtest Lab

Trend Lens now includes a simple Strategy Lab so you can test how a setup or rule set behaved historically.

You can run daily-bar backtests for:

* **Strong Uptrend**
* **Recovery Setup**
* **Pullback in Uptrend**
* **Momentum Confirmation**
* **Avoid Weakness baseline**

For each test, Trend Lens shows:

* Number of trades
* Win rate
* Average and median return
* Best and worst trade
* Average holding days
* Max drawdown
* Final simulated equity
* Same-period benchmark return
* Equity curve and trade log

### How To Interpret It

The Strategy Lab is for **research and education only**.

It helps answer:

> “If this setup happened historically, what usually happened next?”

It does **not** tell you what will happen next time.

### Important Limitations

* Uses **daily data only**
* Assumes **next-day entry after a signal**
* Long-only in v1
* Uses simplified slippage and exit handling
* Ignores taxes and real-world execution constraints

Treat it as historical context, not as a trading system.

---

## 🧮 Position Math (Your Edge)

Trend Lens stands out by incorporating **portfolio-aware decisions**:

* Current allocation %
* Remaining room before cap
* Unrealized gain/loss
* Estimated shares you can add now

👉 This is what turns analysis into **actionable decisions**

---

## 📚 Built-in Learning Layer

* ℹ️ Tooltips for every metric
* Clear interpretation ranges
* Beginner-friendly explanations
* Bottom-page metric glossary

---

## 🛠 How To Use

### 1. Enter a Stock

Search by ticker or company name.

### 2. Read the Summary

* Price
* Score
* Verdict
* Confidence
* Quick setup / recommendation context

### 3. Check Technical Setup

* Setup classification
* Factor breakdown

### 4. Review Fundamentals

* Business quality
* Valuation context

### 5. Add Your Position

Enter:

* Shares owned
* Cost basis
* Portfolio value
* Max position size
* Target position size (optional)
* Cash available

### 6. Decide

Use:

* Recommendation
* Position Math panel
* Catalyst Layer

### 7. Review the Watchlist

Use the Watchlist tab to compare multiple names, rank them by opportunity, and decide which stock deserves a deeper look first.

---

## 🔄 Example Workflow

1. Enter a ticker
2. Check score + setup
3. Validate fundamentals
4. Enter position inputs
5. Use recommendation + math panel
6. Decide: add, wait, hold, or trim

---

## ⚠️ Limitations

* Rule-based model (not predictive)
* Depends on Yahoo Finance (`yfinance`)
* Some data may be incomplete
* Catalyst coverage can be sparse or noisy depending on the ticker and recent news flow
* Catalyst bias is a context layer, not a sentiment engine or prediction model
* Not personalized financial advice

---

## ⚙️ Setup Instructions

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

---

## 🛣 Roadmap

Planned improvements:

* 🧾 Thesis notes and sell rules per holding
* 🏷 Sector-relative valuation
* ⚡ Performance optimization

---

## ⚠️ Not Financial Advice

Trend Lens is for personal research and decision support only.
It is not financial advice and not a recommendation to buy or sell any security.
