import numpy as np
from core.base_agent import BaseAgent
from core.config import MAX_POSITION_SIZE


def _compute_volatility_metrics(returns):
    """Compute vol, VaR, CVaR, max drawdown. Returns dict."""
    vol = float(returns.std() * np.sqrt(252))
    var95 = float(np.percentile(returns, 5))

    var99_cutoff = np.percentile(returns, 1)
    tail = returns[returns <= var99_cutoff]
    cvar99 = float(tail.mean()) if len(tail) > 0 else float(var99_cutoff)

    cumul = (1 + returns).cumprod()
    rm = cumul.cummax()
    max_dd = float(((cumul - rm) / rm).min())

    return {"vol": vol, "var95": var95, "cvar99": cvar99, "max_dd": max_dd}


def _compute_ratios(returns):
    """Compute Sharpe and Sortino ratios."""
    excess = returns - (0.04 / 252)
    ret_std = returns.std()
    sharpe = float(excess.mean() / ret_std * np.sqrt(252)) if ret_std > 0 else 0.0

    downside = returns[returns < 0]
    sortino = 0.0
    if len(downside) > 1:
        down_std = downside.std()
        if down_std > 0:
            sortino = float(excess.mean() / down_std * np.sqrt(252))

    return {"sharpe": sharpe, "sortino": sortino}


def _compute_beta(returns, spy_df):
    """Compute beta vs SPY."""
    if spy_df is None or spy_df.empty:
        return 1.0
    spy_ret = spy_df["Close"].squeeze().pct_change().dropna()
    a, b = returns.align(spy_ret, join="inner")
    if len(a) <= 10:
        return 1.0
    cov = np.cov(a.values, b.values)
    if cov[1][1] == 0:
        return 1.0
    return float(cov[0][1] / cov[1][1])


class RiskAgent(BaseAgent):
    def __init__(self):
        super().__init__("RiskAgent")

    def run(self, ticker: str, **kwargs) -> dict:
        if not ticker or not isinstance(ticker, str):
            return self._error(str(ticker), "Invalid ticker for RiskAgent.")

        try:
            return self._analyze(ticker, kwargs)
        except Exception as e:
            return self._error(ticker, str(e))

    def _analyze(self, ticker: str, kwargs: dict) -> dict:
        price_df = kwargs.get("price_df")
        spy_df = kwargs.get("spy_df")

        if price_df is None or price_df.empty:
            return self._error(ticker, "No price data provided to RiskAgent.")

        closes = price_df["Close"].squeeze().dropna()
        returns = closes.pct_change().dropna()
        if len(returns) < 30:
            return self._error(ticker, "Insufficient data for risk analysis.")

        vm = _compute_volatility_metrics(returns)
        ratios = _compute_ratios(returns)
        beta = _compute_beta(returns, spy_df)
        suggested = min(0.15 / vm["vol"], MAX_POSITION_SIZE) if vm["vol"] > 0 else MAX_POSITION_SIZE

        if vm["vol"] < 0.15:     risk_level = "LOW"
        elif vm["vol"] < 0.25:   risk_level = "MEDIUM"
        elif vm["vol"] < 0.40:   risk_level = "HIGH"
        else:                    risk_level = "VERY HIGH"

        return self._result(ticker, {
            "risk_level":             risk_level,
            "annualized_volatility":  round(vm["vol"], 4),
            "max_drawdown":           round(vm["max_dd"], 4),
            "var_95_daily":           round(vm["var95"], 4),
            "cvar_99_daily":          round(vm["cvar99"], 4),
            "beta_vs_spy":            round(beta, 4),
            "sharpe_ratio":           round(ratios["sharpe"], 4),
            "sortino_ratio":          round(ratios["sortino"], 4),
            "suggested_max_position": round(suggested, 4),
        })
