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

* 📌 Watchlist & multi-stock comparison
* 📊 Historical score tracking
* 📈 Relative strength vs index
* ⚡ Performance optimization

---

## ⚠️ Not Financial Advice

Trend Lens is for personal research and decision support only.
It is not financial advice and not a recommendation to buy or sell any security.
