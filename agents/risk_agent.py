import numpy as np
from core.base_agent import BaseAgent
from core.config import MAX_POSITION_SIZE


class RiskAgent(BaseAgent):
    def __init__(self):
        super().__init__("RiskAgent")

    def run(self, ticker: str, **kwargs) -> dict:
        try:
            price_df = kwargs.get("price_df")
            spy_df = kwargs.get("spy_df")

            if price_df is None or price_df.empty:
                return self._error(ticker, "No price data provided to RiskAgent.")

            closes = price_df["Close"].squeeze().dropna()
            returns = closes.pct_change().dropna()

            if len(returns) < 30:
                return self._error(ticker, "Insufficient data for risk analysis.")

            vol = float(returns.std() * np.sqrt(252))
            var95 = float(np.percentile(returns, 5))

            cumul = (1 + returns).cumprod()
            rm = cumul.cummax()
            max_dd = float(((cumul - rm) / rm).min())

            # Sharpe (4% risk-free)
            excess = returns - (0.04 / 252)
            ret_std = returns.std()
            sharpe = float(excess.mean() / ret_std * np.sqrt(252)) if ret_std > 0 else 0.0

            # Sortino
            downside = returns[returns < 0]
            if len(downside) > 1:
                down_std = downside.std()
                sortino = float(excess.mean() / down_std * np.sqrt(252)) if down_std > 0 else 0.0
            else:
                sortino = 0.0

            # Beta vs SPY
            beta = 1.0
            if spy_df is not None and not spy_df.empty:
                spy_ret = spy_df["Close"].squeeze().pct_change().dropna()
                a, b = returns.align(spy_ret, join="inner")
                if len(a) > 10:
                    cov = np.cov(a.values, b.values)
                    if cov[1][1] != 0:
                        beta = float(cov[0][1] / cov[1][1])

            # Position sizing
            suggested = min(0.15 / vol, MAX_POSITION_SIZE) if vol > 0 else MAX_POSITION_SIZE

            # Risk level
            if vol < 0.15:     risk_level = "LOW"
            elif vol < 0.25:   risk_level = "MEDIUM"
            elif vol < 0.40:   risk_level = "HIGH"
            else:              risk_level = "VERY HIGH"

            return self._result(ticker, {
                "risk_level":             risk_level,
                "annualized_volatility":  round(vol, 4),
                "max_drawdown":           round(max_dd, 4),
                "var_95_daily":           round(var95, 4),
                "beta_vs_spy":            round(beta, 4),
                "sharpe_ratio":           round(sharpe, 4),
                "sortino_ratio":          round(sortino, 4),
                "suggested_max_position": round(suggested, 4),
            })

        except Exception as e:
            return self._error(ticker, str(e))
