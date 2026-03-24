# Finance Expert Team — Claude Code Guide

## What This Project Does
Multi-agent stock analysis system. Each agent fetches and computes data.
Claude Code reads the output and provides investment analysis.

## How To Run An Analysis
```bash
python main.py --ticker <TICKER> --query "<YOUR QUESTION>"
python main.py --ticker <TICKER> --query "<QUESTION>" --agents fundamental technical
python main.py --ticker <TICKER> --query "<QUESTION>" --format html
python main.py --ticker <TICKER> --query "<QUESTION>" --format both

# Batch analysis (Feature 1)
python main.py --batch watchlist
python main.py --batch "AAPL,NVDA,TSLA" --query "谁的估值最低"
python main.py --batch "AAPL,NVDA,MSFT" --agents fundamental risk --format html

# Research mode (Feature 2)
python main.py --research research.md
python main.py --research research.md --format html
```

## Agent Selection
Claude Code decides which agents to run based on the user's question.
Pass agents explicitly via `--agents`:
- `fundamental` — valuation, P/E, ROE, financials
- `technical` — SMA, RSI, MACD, chart patterns
- `sentiment` — news sentiment, analyst opinions
- `risk` — VaR, beta, volatility (always runs)
- `portfolio` — weighted decision + portfolio context from memory

If `--agents` is omitted, a keyword fallback classifier picks them.

## Portfolio Memory
The system remembers the user's broker, holdings, and preferences.

```bash
python main.py --portfolio show
python main.py --portfolio add AAPL 100 185.50
python main.py --portfolio remove AAPL 50
python main.py --portfolio set-broker IBKR
python main.py --portfolio set-cash 50000
python main.py --portfolio watch NVDA
python main.py --portfolio prefs risk_tolerance=aggressive max_position_pct=15
python main.py --portfolio history
```

Portfolio context flows into PortfolioAgent, which generates suggestions like:
- "Already at 18% — don't add more"
- "Signal is BUY, you could buy up to 30 shares"
- "You're up 25% — consider trimming"

## Output Formats
- `--format text` (default) — Markdown report in terminal
- `--format html` — Interactive Plotly dashboard, auto-opens in browser
- `--format both` — Both outputs

## Data Sources
Primary: financialdatasets.ai (set `FINANCIAL_DATASETS_API_KEY` in `.env`)
Fallback: yfinance (free, no key needed)

## Config
Edit `core/config.py` for signal weights, max position size, API URLs.

## Adding A New Agent
1. Create `agents/your_agent.py` inheriting from `BaseAgent`
2. Implement `run(self, ticker, **kwargs) -> dict`
3. Return `self._result(ticker, data_dict)`
4. Register it in `agents/orchestrator.py`
5. Add it to `core/intent_router.py` AGENT_SCHEMA
