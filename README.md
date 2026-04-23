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
* ✅ Position Advisor Score (out of 20)
* 🎯 **Total Score (out of 100)**
* 🧭 **Setup Classification**
* 📌 **Actionable Recommendation**
* 👀 **Watchlist ranking dashboard**
* 📰 **Catalyst Layer**

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
| **Trim**            | Oversized or weakening          |
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

* 📊 Historical score tracking
* 📈 Relative strength vs index
* ⚡ Performance optimization

---

## ⚠️ Not Financial Advice

Trend Lens is for personal research and decision support only.
It is not financial advice and not a recommendation to buy or sell any security.
