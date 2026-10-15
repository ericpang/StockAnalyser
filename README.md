# ⚡ Stock Analytics

> An AI-powered quantitative stock intelligence platform combining the **stock-analysis** skill engine, real-time SEC/Yahoo Finance metrics, Google News sentiment, and Google Gemini AI investment synthesis.

---

## 🚀 Key Features

### 🛡️ Institutional 6-Point Quality Screen
Automated quantitative sanity check evaluating financial strength and capital efficiency:
1. **PEG Ratio < 2.0** — Price/Earnings-to-Growth multiple validation.
2. **5-Year Positive EPS Growth** — Multi-year earnings expansion trajectory (CAGR).
3. **Return on Equity (ROE) > 12%** — Capital compounding efficiency.
4. **Current Ratio > 1.0** — Short-term working capital solvency.
5. **Return on Invested Capital (ROIC) > 12%** — NOPAT relative to invested capital confirming a durable economic moat.
6. **Debt to EBITDA < 2.0x** — Conservative leverage and obligation coverage.

### 📊 8-Dimension Quantitative Matrix
* **Fundamentals & Quality**: Trailing P/E, PEG, Operating Margin, Revenue Growth YoY, Debt-to-Equity.
* **Analyst Consensus**: Consensus Rating, Mean Price Target, Upside Potential %, Analyst Coverage Pool.
* **Earnings Surprise**: Actual vs. Expected EPS, Surprise %, Historical 4Q Beat Streak.
* **Technical Momentum**: 14-Day RSI, Overbought/Oversold regime, 52-Week High proximity, Relative Volume.
* **Sector Dynamics**: Stock vs. Sector 1-Month performance, Relative Sector Strength multiple.
* **Macro & Market Context**: VIX index level, Market Regime, SPY 10-Day Trend, Safe-Haven Risk-Off detection.
* **News & Sentiment Feed**: Real-time RSS sentiment extraction with polarity tagging.

### 🤖 Google Gemini AI Copilot & Investment Memo
* **Executive Investment Thesis**: Automated synthesis of quantitative scores into an institutional memo.
* **Bull vs. Bear Debate Grid**: Key upside drivers weighed against critical downside failure points.
* **Interactive Stock Copilot**: Real-time conversational AI context-aware of the current ticker, balance sheet, and live news.

### 📈 Interactive Price & Volume Studio
* Native SVG Candlestick & Area Line visualization (zero external chart libraries).
* 20-Day Simple Moving Average (SMA) overlay.
* Volume histogram and interactive crosshair hover card with Date, OHLC, and Volume.

---

## 🛠️ Tech Stack & Architecture

* **Frontend**: Vanilla HTML5, CSS3 (Futuristic Dark-Synthwave theme), and JavaScript.
* **Backend**: Python 3 standard library (`http.server`, `urllib.request`, `json`, `socketserver`).
* **Data Sources**: Yahoo Finance (`yfinance`), Google News RSS, and Google Gemini API (`gemini-2.5-flash`).
* **Skills**: Installed via Agent Skill framework (`stock-analysis`).

---

## ⚡ Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/ericpang/StockAnalyser.git
cd StockAnalyser
```

### 2. Start the Analytics Server
```bash
python server.py
```
The server will start listening at **`http://localhost:3000/`**.

### 3. Open in Browser
Visit **`http://localhost:3000/`**, enter any stock ticker (e.g. `NVDA`, `AAPL`, `TSLA`, `MSFT`), and click **Analyze Stock**.

*(Optional)* Click **Setup Gemini AI ⚡** in the top navigation bar to connect your Google Gemini API key for qualitative memos and live Copilot chat.

---

## 📄 License
Educational and informational use only. Not financial advice.
