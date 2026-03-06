# Finance Expert Team

**An open-source multi-agent AI system for US stock analysis — built to run inside Claude Code, zero API cost.**

> Fundamental analysis · Technical analysis · Sentiment · Risk management · Backtesting · Portfolio decision

---

## What It Does

You ask a question. The system figures out which agents to run, fetches real market data, computes indicators, and returns a structured investment research report — all for free.

```
$ python main.py --ticker AAPL --query "Is AAPL a good buy right now?"

[Orchestrator] Intents detected: fundamental, technical
[Phase 1] Fetching data...        ← yfinance (free)
[Phase 2] FundamentalAgent...     ← valuation, ratios, DCF
[Phase 2] TechnicalAgent...       ← RSI, MACD, SMA, signals
[Phase 3] RiskAgent...            ← VaR, beta, position sizing
[Phase 3] PortfolioAgent...       ← weighted final decision
[Phase 5] Report ready.
```

---

## Agent Architecture

```
User Query
    │
    ▼
[Orchestrator] — classifies intent, decides which agents to run
    │
    ├── Phase 1 (always):    DataAgent        → fetches price, financials, ratios
    │
    ├── Phase 2 (parallel):  FundamentalAgent → P/E, ROE, DCF, analyst targets
    │                        TechnicalAgent   → SMA, RSI, MACD, Bollinger Bands
    │                        SentimentAgent   → news sentiment, catalysts
    │
    ├── Phase 3 (sequential):RiskAgent        → VaR, beta, max drawdown, position sizing
    │                        PortfolioAgent   → weighted signal aggregation
    │
    ├── Phase 4 (optional):  BacktestAgent    → SMA crossover strategy backtest
    │
    └── Phase 5 (always):    ReportAgent      → structured investment memo
```

**Smart routing** — only relevant agents are triggered based on your question:

| Query | Agents triggered |
|---|---|
| "Is AAPL undervalued?" | Data → Fundamental → Report |
| "TSLA technical outlook" | Data → Technical → Report |
| "Build me a portfolio" | All agents |
| "Backtest moving average" | Data → Backtest → Report |

---

## Data Sources (All Free)

| Source | Data | API Key |
|---|---|---|
| Yahoo Finance (`yfinance`) | Price, volume, financials, ratios | Not required |
| Alpha Vantage | News sentiment | Free at alphavantage.co |
| Financial Modeling Prep | Company profiles | Free tier |
| Stooq | Price fallback | Not required |

**Automatic fallback chain:** yfinance → Alpha Vantage → FMP → Stooq

**Rate limiter built-in** — automatically waits when free tier limits are hit, then retries.

**6-hour cache** — same ticker won't burn your API quota twice.

---

## Quickstart

```bash
# 1. Clone
git clone https://github.com/sephirx/finance-expert-team.git
cd finance-expert-team

# 2. Install dependencies
pip install yfinance pandas numpy requests python-dotenv ta pandas-datareader matplotlib plotly

# 3. (Optional) Add API keys for news sentiment
cp .env.example .env
# Edit .env with your keys

# 4. Run
python main.py --ticker AAPL --query "Is AAPL a good buy right now?"
python main.py --ticker NVDA --query "What is the technical and sentiment outlook?"
python main.py --ticker TSLA --query "Backtest a moving average strategy on TSLA"
```

---

## Run Inside Claude Code

This project is designed to work **natively inside Claude Code** — no Anthropic API key needed, no extra cost.

```bash
# Open the project in Claude Code
cd finance-expert-team

# Ask Claude Code to analyze a stock
# "Run NVDA analysis and tell me if it's a good buy"
# "Backtest a strategy on MSFT and explain the results"
# "Compare AAPL and GOOGL fundamentals"
```

Claude Code reads the structured output from all agents and provides full investment analysis.

See [CLAUDE.md](CLAUDE.md) for Claude Code usage guide.

---

## Example Output

```
# AAPL — Finance Expert Team Report

## FundamentalAgent
- rating: BUY (score: +2)
- P/E: 32.9 — expensive but growing
- ROE: 152% — exceptional profitability
- Revenue growth: +15.7% YoY
- Analyst target: $293 → 12.7% upside

## TechnicalAgent
- Signal: BULLISH (score: +3)
- Price above SMA20, SMA50, SMA200
- RSI 58 — neutral, room to run
- MACD above signal — bullish momentum

## RiskAgent
- Risk level: MEDIUM
- Annualized volatility: 28%
- Beta vs SPY: 1.12
- Suggested max position: 10%

## PortfolioAgent
- Decision: BUY
- Conviction: HIGH
- Recommended position: 10%
- Entry: $260 | Target: $293 | Stop: $240
```

---

## Project Structure

```
finance-expert-team/
├── main.py                   ← entry point
├── agents/
│   ├── orchestrator.py       ← routes queries to agents
│   ├── data_agent.py         ← data fetching + fallback chain
│   ├── fundamental_agent.py  ← valuation analysis
│   ├── technical_agent.py    ← chart indicators
│   ├── sentiment_agent.py    ← news sentiment
│   ├── risk_agent.py         ← risk metrics
│   ├── portfolio_agent.py    ← portfolio decision
│   ├── backtest_agent.py     ← strategy backtesting
│   └── report_agent.py       ← report generation
├── core/
│   ├── base_agent.py         ← base class
│   ├── config.py             ← settings
│   ├── message_bus.py        ← inter-agent communication
│   └── rate_limiter.py       ← API rate limiting
└── data/cache/               ← auto-cached responses
```

---

## License

MIT — free to use, not free to modify and redistribute as your own.

---

## Author

Built by [@sephirx](https://github.com/sephirx) — CFA Level 1 candidate, quant enthusiast.

*Follow on X for updates, trade ideas, and project progress.*
