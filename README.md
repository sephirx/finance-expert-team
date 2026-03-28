<div align="center">

# Finance Expert Team

**Multi-agent AI stock analysis — zero LLM API cost.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Version](https://img.shields.io/badge/Version-v1.6-F59E0B?style=flat-square)](CHANGELOG.md)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)](LICENSE)

*Built by [@sephirx_li](https://x.com/sephirx_li)*

</div>

---

You ask a question. The system picks the right agents, pulls free market data, runs analysis in parallel, and returns a structured investment report — no OpenAI key, no Anthropic key.

## Quickstart

```bash
git clone https://github.com/sephirx/finance-expert-team.git
cd finance-expert-team
pip install -e .
python main.py --ticker AAPL --query "Is AAPL a good buy right now?"
```

## Usage

```bash
# Single ticker
python main.py --ticker NVDA --query "Technical and fundamental outlook" --format html

# Batch analysis
python main.py --batch "AAPL,NVDA,MSFT" --query "谁的估值最低"
python main.py --batch watchlist --agents fundamental risk

# Research mode (structured config file)
python main.py --research research.md

# Portfolio
python main.py --portfolio show
python main.py --portfolio add AAPL 50 182.50
python main.py --portfolio watch NVDA

# Optimization — run before sleep
python main.py --optimize watchlist              # grid search signal weights
python main.py --meta-optimize                   # tune agent thresholds via Claude loop (20 iters)
python main.py --overnight watchlist             # weight + meta-param optimization in one command
python main.py --overnight "AAPL,NVDA" --iterations 50
```

**Agents:** `fundamental` `technical` `sentiment` `risk` `portfolio` — selected automatically or via `--agents`.
**Output:** `--format text` (default) · `--format html` (interactive Plotly dashboard) · `--format both`

## Overnight Pipeline

`--overnight` chains `parameter_optimizer` and `meta_optimizer` in a single command, designed to run unattended while you sleep.

```
--overnight <tickers>
  1. parameter_optimizer  — grid/random search over signal weights (backtesting)
  2. meta_optimizer       — Claude loop tunes agent decision thresholds (20 iters default)
  3. Saves best config to core/config.py automatically
```

## Research Mode

Write a `research.md` to define a structured multi-stock research task:

```markdown
## 研究目标
对比 NVDA vs AMD 的估值洼地

## 股票列表
NVDA, AMD

## 使用 Agents
fundamental, risk

## 评判标准
PEG ratio < 1 且 ROE > 20%
```

The system evaluates each ticker against your criteria and outputs PASS/FAIL verdicts.

## Architecture

```
User Query → Orchestrator → DataAgent (free sources, 6h cache)
                          → FundamentalAgent  (parallel)
                          → TechnicalAgent    (parallel)
                          → SentimentAgent    (parallel)
                          → RiskAgent
                          → PortfolioAgent
                          → ScorecardAgent → ReportAgent
```

Data sources: yfinance → Alpha Vantage → FMP → Stooq (automatic fallback chain).

## Changelog

- **v1.6** — `--overnight` pipeline: weight optimizer + meta-optimizer in one command; `update_test_set()` syncs test tickers with watchlist; fix `--meta-optimize` default iterations (1→20)
- **v1.5** — Batch analysis, research.md system, parameter optimizer, MetaOptimizer agent
- **v1.3** — HTML dashboard, data normalizer, portfolio CLI
- **v1.2** — Performance test suite, proportional grading
- **v1.1** — ScorecardAgent, centralized data fetching
- **v1.0** — Initial release

---

<div align="center">

*Not financial advice. For educational and research purposes only.*

</div>
