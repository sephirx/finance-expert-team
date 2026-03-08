# Changelog

## v1.2 — Performance Testing & Grading Upgrade (2026-03-08)

### What Changed

**5-Phase Performance Test Suite** (`tests/test_team_performance.py`)
- Phase 1: Accuracy test across 10 stocks (AAPL, MSFT, JPM, JNJ, XOM, AMZN, NVDA, KO, TSLA, DIS)
- Phase 2: Consistency test — same stock 3x, verifies identical Grade + Signal
- Phase 3: Speed benchmark — minimal vs full agent pipeline
- Phase 4: Edge cases — delisted tickers, meme stocks, single-letter tickers
- Phase 5: Intent classification validation (7 test cases)

**Results**: 10/10 accuracy, 100% consistency, 1.7s minimal / 2.6s full, 3/3 edge cases, 7/7 intent

### Intent Classification Fixes
- Added "volatile" to risk keywords (was only "volatility" — "How volatile is this stock?" now correctly triggers RiskAgent)
- Added "fundamental" keyword to fundamental intent
- Removed "test" from backtest keywords (too generic, caused false matches)
- Added "sma", "ema", "bollinger" to technical keywords
- Added "catalyst" to sentiment keywords
- Added "danger" to risk keywords
- **Auto-pair**: queries with "buy"/"sell" now trigger both Fundamental + Technical (not just Fundamental alone)

### Proportional Grading System
**Problem**: Old grading used fixed point thresholds (5+ = A, 4 = B+, etc.) — stocks that only ran 2-3 agents were penalized because they couldn't earn enough points.

**Fix**: Switched to proportional scoring (`score / max_possible_score`):
- Only criteria that are applicable are counted in the denominator
- Lowered thresholds: Sharpe 0.3 (was 0.5), Hit Rate 55% (was 60%)
- MODERATE agreement now counts as positive (was only STRONG)
- Added alpha vs SPY as a new grade factor
- Grade bands: A (75%+), B+ (60%+), B (45%+), C (30%+), D (<30%)

**Before → After**:
| Stock | Old Grade | New Grade |
|---|---|---|
| AAPL | B+ | A |
| KO | B | B |
| MSFT | D | C |

---

## v1.1 — Scorecard + Bug Fixes (2026-03-06)

### Tier 1 Performance Scorecard
- New `ScorecardAgent` with industry-standard metrics
- Hit Rate (30d/60d/90d forward return simulation)
- Calmar Ratio (annualized return / max drawdown)
- CVaR 99% (Expected Shortfall)
- Information Ratio (alpha / tracking error)
- Tracking Error vs SPY
- Signal Agreement (STRONG/MODERATE/WEAK)
- Team Grade (A through D)
- Professional ASCII scorecard box in reports

### Bug Fixes
- Fixed backtest NaN propagation (`.fillna(0)` on strategy returns before cumprod)
- Fixed RSI division by zero when loss=0 (returns RSI=100)
- Fixed duplicate yfinance downloads (centralized in DataAgent, 5 API calls → 2)
- Fixed rate limiter file I/O contention (switched to in-memory state)
- Added CVaR 99% to RiskAgent
- Removed dead code (`message_bus.py`, report file saving)

### Infrastructure
- 4-source data fallback chain (yfinance → Alpha Vantage → FMP → Stooq)
- Rate limiter with 5-minute circuit breaker
- 6-hour source-quality-aware cache
- Timing on all phases and agents
- RiskAgent always runs (scorecard depends on it)

---

## v1.0 — Initial Release (2026-03-06)

- 8 specialized agents + orchestrator
- Smart intent routing (keyword-based)
- Parallel agent execution (ThreadPoolExecutor)
- Free data sources only (yfinance, Alpha Vantage, FMP, Stooq)
- Zero LLM API cost — pure Python data processors
- Claude Code integration
