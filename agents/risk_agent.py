import numpy as np
import yfinance as yf
from core.base_agent import BaseAgent
from core.config import MAX_POSITION_SIZE
from core.rate_limiter import wait_if_needed


class RiskAgent(BaseAgent):
    def __init__(self):
        super().__init__("RiskAgent")

    def run(self, ticker: str, **kwargs) -> dict:
        try:
            wait_if_needed("yfinance")
            df      = yf.download(ticker, period="2y", progress=False)
            closes  = df["Close"].squeeze()
            returns = closes.pct_change().dropna()

            vol    = float(returns.std() * np.sqrt(252))
            var95  = float(np.percentile(returns, 5))
            cumul  = (1 + returns).cumprod()
            rm     = cumul.cummax()
            max_dd = float(((cumul - rm) / rm).min())

            # Sharpe (4% risk-free)
            excess = returns - (0.04 / 252)
            sharpe = float(excess.mean() / returns.std() * np.sqrt(252))

            # Sortino
            down   = returns[returns < 0].std()
            sortino = float(excess.mean() / down * np.sqrt(252)) if down > 0 else 0

            # Beta vs SPY
            wait_if_needed("yfinance")
            spy        = yf.download("SPY", period="2y", progress=False)
            spy_ret    = spy["Close"].squeeze().pct_change().dropna()
            a, b       = returns.align(spy_ret, join="inner")
            cov        = np.cov(a, b)
            beta       = float(cov[0][1] / cov[1][1]) if cov[1][1] != 0 else 1.0

            # Suggested position size (vol scaling)
            suggested = min(0.15 / vol, MAX_POSITION_SIZE)

            # Risk level
            if vol < 0.15:                  risk_level = "LOW"
            elif vol < 0.25:                risk_level = "MEDIUM"
            elif vol < 0.40:                risk_level = "HIGH"
            else:                           risk_level = "VERY HIGH"

            return self._result(ticker, {
                "risk_level":              risk_level,
                "annualized_volatility":   round(vol, 4),
                "max_drawdown":            round(max_dd, 4),
                "var_95_daily":            round(var95, 4),
                "beta_vs_spy":             round(beta, 4),
                "sharpe_ratio":            round(sharpe, 4),
                "sortino_ratio":           round(sortino, 4),
                "suggested_max_position":  round(suggested, 4),
            })

        except Exception as e:
            return self._error(ticker, str(e))
