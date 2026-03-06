# Finance Expert Team — Claude Code Guide

## What This Project Does
Multi-agent stock analysis system. Each agent fetches and computes data.
Claude Code reads the output and provides investment analysis.

## How To Run An Analysis
```bash
python main.py --ticker <TICKER> --query "<YOUR QUESTION>"
```

## Example Queries
```bash
python main.py --ticker AAPL --query "Is AAPL a good buy right now?"
python main.py --ticker NVDA --query "What is the technical and risk outlook?"
python main.py --ticker TSLA --query "Backtest a moving average strategy"
python main.py --ticker MSFT --query "Full portfolio analysis with sentiment"
```

## Intent Keywords (What Triggers Which Agents)
- **fundamental**: valuation, value, pe, buy, sell, undervalued, overvalued, dcf
- **technical**: chart, trend, rsi, macd, moving average, signal, entry, exit
- **sentiment**: news, sentiment, analyst, upgrade, downgrade, catalyst
- **risk**: risk, volatility, drawdown, var, position, safe
- **backtest**: backtest, strategy, historical, simulate, past performance
- **portfolio**: portfolio, allocate, diversify, build, invest

## Agent Overview
| Agent | Does |
|---|---|
| DataAgent | Fetches price, ratios, financials from yfinance (fallback: AV → FMP → Stooq) |
| FundamentalAgent | Scores P/E, ROE, growth, analyst targets → BUY/HOLD/SELL |
| TechnicalAgent | Computes SMA, RSI, MACD, Bollinger Bands → BULLISH/NEUTRAL/BEARISH |
| SentimentAgent | Fetches news headlines → POSITIVE/NEUTRAL/NEGATIVE |
| RiskAgent | Computes VaR, beta, max drawdown, suggested position size |
| PortfolioAgent | Weights all signals → final BUY/HOLD/SELL with entry/target/stop |
| BacktestAgent | Runs SMA 50/200 crossover backtest → Sharpe, drawdown, alpha vs buy-and-hold |
| ReportAgent | Assembles all outputs into structured report |

## Config File
Edit `core/config.py` to change:
- Signal weights (fundamental/technical/sentiment)
- Max position size
- Backtest period and initial capital
- Cache expiry

## Data Cache
Results cached for 6 hours in `data/cache/`.
To force fresh data: delete the cache file for that ticker.

## Rate Limits (Free Tier)
Handled automatically. If a source hits its limit, the system waits and retries.
- yfinance: 2000 calls/hour
- Alpha Vantage: 5 calls/minute
- FMP: 10 calls/minute

## Adding A New Agent
1. Create `agents/your_agent.py` inheriting from `BaseAgent`
2. Implement `run(self, ticker, **kwargs) -> dict`
3. Return `self._result(ticker, data_dict)`
4. Register it in `agents/orchestrator.py`
