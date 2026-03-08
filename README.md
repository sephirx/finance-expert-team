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
    ├── Phase 3 (sequential):RiskAgent        → VaR, CVaR, beta, max drawdown, position sizing
    │                        PortfolioAgent   → weighted signal aggregation
    │
    ├── Phase 4 (optional):  BacktestAgent    → SMA crossover strategy backtest
    │
    ├── Phase 5 (always):    ScorecardAgent   → Hit Rate, Calmar, Info Ratio, Team Grade
    │
    └── Phase 6 (always):    ReportAgent      → structured investment memo + scorecard
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
========================================================
  PERFORMANCE SCORECARD — AAPL       Grade: A
========================================================

  Team Signal: BUY         Agreement: MODERATE
    Fundamental: BUY          Technical: BEARISH
    Sentiment:   N/A

  Signal Quality
    Hit Rate (30d):  66.3%   (60d):  62.7%   (90d):  59.1%
    Information Coefficient: 0.48

  Risk-Adjusted Returns
    Sharpe:     1.02   Sortino:    1.45
    Calmar:     0.93   Info Ratio:  0.48
    Alpha vs SPY: 3.72%

  Risk Profile
    VaR (95%): -1.92%   CVaR (99%): -3.41%
    Beta:    1.19   Volatility: 25.08%
    Max Drawdown: -26.44%   Risk Level: MEDIUM
    Tracking Error: 7.69%

========================================================
```

Each report includes the full scorecard above, followed by detailed agent breakdowns (Fundamental, Technical, Risk, etc.).

---

## Project Structure

```
finance-expert-team/
├── main.py                   ← entry point
├── agents/
│   ├── orchestrator.py       ← routes queries to agents (6-phase pipeline)
│   ├── data_agent.py         ← data fetching + 4-source fallback chain
│   ├── fundamental_agent.py  ← valuation analysis
│   ├── technical_agent.py    ← chart indicators
│   ├── sentiment_agent.py    ← news sentiment
│   ├── risk_agent.py         ← VaR, CVaR, beta, Sharpe, Sortino
│   ├── portfolio_agent.py    ← portfolio decision
│   ├── backtest_agent.py     ← strategy backtesting
│   ├── scorecard_agent.py    ← Hit Rate, Calmar, Info Ratio, Team Grade
│   └── report_agent.py       ← report + scorecard rendering
├── core/
│   ├── base_agent.py         ← base class (no LLM dependency)
│   ├── config.py             ← settings
│   └── rate_limiter.py       ← API rate limiting with circuit breaker
├── tests/
│   └── test_team_performance.py  ← 5-phase performance test suite
└── data/cache/               ← auto-cached responses (6h expiry)
```

---

## License

MIT — free to use, not free to modify and redistribute as your own.

---

## Author

Built by [@sephirx](https://github.com/sephirx) — CFA Level 1 candidate, quant enthusiast.

*Follow on X for updates, trade ideas, and project progress.*
