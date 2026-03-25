<div align="center">

# Finance Expert Team

**Multi-agent AI stock analysis — zero LLM API cost.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Version](https://img.shields.io/badge/Version-v1.4-F59E0B?style=flat-square)](CHANGELOG.md)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)](LICENSE)

*Built by [@sephirx_li](https://x.com/sephirx_li)*

</div>

---

You ask a question. The system picks the right agents, pulls free market data, runs analysis in parallel, and returns a structured investment report — no OpenAI key, no Anthropic key.

## Quickstart

```bash
git clone https://github.com/sephirx-li/finance-expert-team.git
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
```

**Agents:** `fundamental` `technical` `sentiment` `risk` `portfolio` — selected automatically or via `--agents`.
**Output:** `--format text` (default) · `--format html` (interactive Plotly dashboard) · `--format both`

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

- **v1.4** — Batch analysis (`--batch`), research.md system (`--research`), criteria evaluation
- **v1.3** — HTML dashboard, data normalizer, portfolio CLI
- **v1.2** — Performance test suite, proportional grading
- **v1.1** — ScorecardAgent, centralized data fetching
- **v1.0** — Initial release

---

<div align="center">

*Not financial advice. For educational and research purposes only.*

</div>
