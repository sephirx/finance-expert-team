<div align="center">

# Finance Expert Team

**Multi-agent AI stock analysis — zero LLM API cost, runs entirely in Python.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)](LICENSE)
[![Version](https://img.shields.io/badge/Version-v1.3-F59E0B?style=flat-square)](CHANGELOG.md)
[![Data](https://img.shields.io/badge/Data-Free_Sources_Only-8B5CF6?style=flat-square)](https://finance.yahoo.com)
[![Agents](https://img.shields.io/badge/Agents-8_Specialized-EF4444?style=flat-square)](#agent-architecture)

*Built by [@sephirx_li](https://x.com/sephirx_li)*

</div>

---

You ask a question about a stock. The system figures out which agents to run, pulls real market data for free, runs analysis in parallel, and produces a structured investment research report with an interactive HTML dashboard.

```
$ python main.py --ticker NVDA --query "Is NVDA a good buy right now?" --format html

[Orchestrator] Ticker=NVDA | Agents={'fundamental', 'technical', 'risk'}
[Phase 1/5] Fetching market data...                        <- yfinance (free)
[Phase 2/5] Running 2 agents in parallel: Fundamental, Technical...
  FundamentalAgent: done (820ms)
  TechnicalAgent:   done (340ms)
[Phase 3/5] Running RiskAgent...
[Phase 4/5] Computing performance scorecard...
[Phase 5/5] Generating report...                          <- opens HTML in browser

[Orchestrator] Total time: 2.4s
```

---

## What's New in v1.3

> [!IMPORTANT]
> This release adds an interactive HTML dashboard, data normalization layer, and a cleaner pipeline. The backtesting agent has been removed in favor of a more reliable core pipeline.

| Feature | Previous | Current |
|---|---|---|
| Output format | ASCII terminal only | Terminal + interactive HTML dashboard |
| Charts | None | Candlestick, RSI, MACD, Bollinger, Radar, Signal bar, Risk gauges |
| Data pipeline | Raw yfinance dicts | Normalized canonical schema with quality scoring |
| Agent routing | Fixed keyword matching | Structured schema readable by Claude Code |
| Portfolio CLI | Not available | Full portfolio management (`show`, `add`, `watch`, `prefs`) |
| Data quality | Silent degraded fallbacks | Quality-aware caching with completeness scoring |

```diff
- Output: walls of text, no visualization
+ Output: interactive Plotly HTML dashboard that opens in your browser automatically

- Data: 4 agents downloading the same ticker independently (4x API calls)
+ Data: centralized DataAgent, price DataFrame passed to all agents (1x API call)

- Cache: degraded fallback data stored for 6h, no way to know quality
+ Cache: source-quality-aware, completeness score attached to every cached result
```

---

## Agent Architecture

```
User Query
    |
    v
[Orchestrator] -- classifies intent, routes to relevant agents only
    |
    +-- Phase 1 (always):     DataAgent         -> price, financials, ratios (4-source fallback)
    |                                              price DataFrame passed to all downstream agents
    |
    +-- Phase 2 (parallel):   FundamentalAgent  -> P/E, ROE, DCF, analyst targets, revenue growth
    |                         TechnicalAgent    -> SMA 20/50/200, RSI, MACD, Bollinger Bands
    |                         SentimentAgent    -> news sentiment, analyst upgrades/downgrades
    |
    +-- Phase 3 (sequential): RiskAgent         -> VaR 95%, CVaR 99%, beta, Sharpe, Sortino, max DD
    |                         PortfolioAgent    -> weighted signal aggregation, entry/target/stop
    |
    +-- Phase 4 (always):     ScorecardAgent    -> Hit Rate, Calmar, Info Ratio, Team Grade A-D
    |
    +-- Phase 5 (always):     ReportAgent       -> text memo + HTML dashboard (auto-opens browser)
```

**Smart routing** — only relevant agents activate based on what you ask:

| Query | Agents triggered |
|---|---|
| "Is AAPL undervalued?" | Fundamental, Risk, Scorecard, Report |
| "TSLA technical outlook" | Technical, Risk, Scorecard, Report |
| "How risky is NVDA?" | Risk, Scorecard, Report |
| "Is MSFT a good buy?" | Fundamental + Technical (auto-paired on buy/sell), Risk, Scorecard, Report |
| "Build me a portfolio" | All agents |

---

## Data Sources

All free. No credit card required.

| Source | Data | API Key |
|---|---|---|
| Yahoo Finance (`yfinance`) | Price, OHLCV, financials, ratios | Not required |
| Alpha Vantage | News sentiment | Free at alphavantage.co |
| Financial Modeling Prep | Company profiles | Free tier |
| Stooq | Price fallback | Not required |

**Automatic fallback chain:** yfinance -> Alpha Vantage -> FMP -> Stooq

**Rate limiter with circuit breaker** — waits and retries when free tier limits are hit. A 5-minute circuit breaker prevents hammering a dead source.

**6-hour quality-aware cache** — results are cached with a data completeness score. Degraded fallback data does not displace a good prior cache entry.

> [!NOTE]
> Our core advantage over alternatives like TradingAgents (30K+ stars): **zero LLM API cost**. No OpenAI key, no Anthropic key. Pure Python data processors.

---

## Quickstart

```bash
# 1. Clone
git clone https://github.com/sephirx-li/finance-expert-team.git
cd finance-expert-team

# 2. Install
pip install -e .

# 3. (Optional) add API keys for news sentiment
cp .env.example .env  # then fill in ALPHA_VANTAGE_KEY

# 4. Run
python main.py --ticker AAPL --query "Is AAPL a good buy right now?"
python main.py --ticker NVDA --query "Technical and sentiment outlook?" --format html
python main.py --ticker TSLA --query "How risky is TSLA?" --agents risk
```

---

## HTML Dashboard

Pass `--format html` or `--format both` to get an interactive Plotly dashboard that opens automatically in your browser.

The dashboard includes:

- **Candlestick chart** with SMA 20/50/200 overlays and Bollinger Bands
- **RSI and MACD** subplots with overbought/oversold reference lines
- **Fundamental radar chart** — P/E, ROE, Revenue Growth, Debt, Analyst Upside, Earnings Growth
- **Signal agreement bar** — visual BUY/HOLD/SELL breakdown across all agents
- **Risk gauges** — VaR 95%, Beta, Max Drawdown, Volatility
- **Scorecard table** — Hit Rate, Sharpe, Sortino, Calmar, Info Ratio, Alpha vs SPY
- **Recommendation panel** — entry price, target, stop loss, conviction level
- **Portfolio context** — P&L on current holdings, position warnings

---

## Portfolio Management

Track your holdings and get personalized analysis context.

```bash
# Show portfolio overview
python main.py --portfolio show

# Add a position: add <TICKER> <SHARES> <AVG_COST>
python main.py --portfolio add AAPL 50 182.50

# Set cash balance and broker
python main.py --portfolio set-cash 25000
python main.py --portfolio set-broker IBKR

# Watchlist
python main.py --portfolio watch NVDA
python main.py --portfolio watch MSFT

# Set preferences
python main.py --portfolio prefs risk_tolerance=moderate investment_horizon=long style=value

# View analysis history
python main.py --portfolio history
```

When you run an analysis with a portfolio configured, the PortfolioAgent incorporates your existing holdings, cash balance, and preferences into the recommendation — e.g. "Already at 18% allocation, do not add more" or "Signal is BUY, you could buy up to 30 shares within your limits."

---

## Example Output

```
========================================================
  PERFORMANCE SCORECARD -- AAPL       Grade: A
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
    Alpha vs SPY: +3.72%

  Risk Profile
    VaR (95%): -1.92%   CVaR (99%): -3.41%
    Beta:    1.19   Volatility: 25.08%
    Max Drawdown: -26.44%   Risk Level: MEDIUM
    Tracking Error: 7.69%

========================================================
```

---

## Performance Benchmarks

From `tests/test_team_performance.py`, run across 10 stocks (AAPL, MSFT, JPM, JNJ, XOM, AMZN, NVDA, KO, TSLA, DIS):

| Test | Result |
|---|---|
| Accuracy (10 stocks, all complete) | 10/10 |
| Consistency (same stock, 3 runs) | 100% identical Grade + Signal |
| Minimal pipeline speed | ~1.7s |
| Full pipeline speed | ~2.6s |
| Edge cases (delisted, meme stocks, 1-letter tickers) | 3/3 handled |
| Intent classification (7 test cases) | 7/7 correct |

---

## Grading System

Grades are computed proportionally — only applicable criteria count in the denominator, so a stock analyzed with fewer agents is not penalized.

| Grade | Threshold | Meaning |
|---|---|---|
| A | 75%+ | Strong across all applicable metrics |
| B+ | 60%+ | Good overall |
| B | 45%+ | Decent, some weaknesses |
| C | 30%+ | Mixed signals |
| D | <30% | Weak or insufficient data |

Metrics contributing to the grade: Sharpe (threshold: 0.3), Hit Rate (threshold: 55%), signal agreement (MODERATE or better counts), alpha vs SPY, and agent signal quality.

---

## Regulation Layer

The project ships with a Tier 1 compliance checker based on NASA/JPL's Power of Ten safety-critical coding rules.

```bash
python main.py --regulate
```

Runs a static analysis pass over all source files and outputs a compliance grade. All functions are 60 lines or under (Rule 4). No recursion (Rule 1).

---

## Project Structure

```
finance-expert-team/
+-- main.py                        entry point: CLI arg parsing and routing
+-- agents/
|   +-- orchestrator.py            6-phase pipeline, intent routing, memory
|   +-- data_agent.py              data fetching, 4-source fallback, 6h cache
|   +-- fundamental_agent.py       P/E, ROE, DCF, analyst targets
|   +-- technical_agent.py         SMA, RSI, MACD, Bollinger Bands
|   +-- sentiment_agent.py         news sentiment via Alpha Vantage
|   +-- risk_agent.py              VaR, CVaR, beta, Sharpe, Sortino, max drawdown
|   +-- portfolio_agent.py         weighted signal aggregation, position sizing
|   +-- scorecard_agent.py         Hit Rate, Calmar, Info Ratio, Team Grade
|   +-- report_agent.py            text report + HTML dashboard assembly
|   +-- visual_report.py           Plotly charts (candlestick, radar, gauges)
+-- core/
|   +-- base_agent.py              base class, no LLM dependency
|   +-- config.py                  settings, API keys, cache TTL
|   +-- rate_limiter.py            in-memory rate limiting, circuit breaker
|   +-- data_normalizer.py         canonical schema mapping + quality scoring
|   +-- intent_router.py           agent schema + keyword fallback classifier
+-- memory/
|   +-- memory_manager.py          analysis history (SQLite)
|   +-- portfolio_store.py         portfolio holdings, watchlist, preferences
+-- regulation/
|   +-- power_of_ten.py            static compliance checker
|   +-- compliance_report.py       compliance grade reporter
|   +-- runtime_guards.py          runtime agent output validation
+-- tests/
    +-- test_team_performance.py   5-phase performance test suite
```

---

## Running Inside Claude Code

This project is designed to work natively inside Claude Code — Claude reads the structured output from all agents and provides full investment analysis directly.

See [CLAUDE.md](CLAUDE.md) for the Claude Code usage guide and agent schema documentation.

```bash
# Inside Claude Code, just ask:
# "Run NVDA full analysis and tell me if it's a good buy"
# "Compare AAPL and GOOGL fundamentals"
# "Show my portfolio and suggest rebalancing"
```

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

- **v1.3** — HTML dashboard, data normalizer, visual report agent, portfolio CLI
- **v1.2** — Performance test suite, proportional grading, intent classification fixes
- **v1.1** — ScorecardAgent, centralized data fetching, critical bug fixes
- **v1.0** — Initial release, 8 agents, parallel execution, free data sources

---

## License

MIT — free to use for personal and commercial projects.

---

<div align="center">

Built by [@sephirx_li](https://x.com/sephirx_li) — CFA Level 1 candidate, quant enthusiast.

*Not financial advice. For educational and research purposes only.*

</div>
