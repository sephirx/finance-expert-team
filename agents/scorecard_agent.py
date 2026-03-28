"""
ScorecardAgent — performance metrics and grading.
All functions ≤60 lines (R4). No recursion (R1).
"""

import numpy as np
import pandas as pd
from core.base_agent import BaseAgent
from core.param_loader import get_params


def compute_hit_rate(closes: pd.Series, signal: str) -> dict:
    """Check if signal would have been correct over 30/60/90d windows."""
    results = {}
    for days, label in [(30, "30d"), (60, "60d"), (90, "90d")]:
        if len(closes) < days + 252:
            results[label] = None
            continue
        wins = 0
        total = 0
        lookback = min(252, len(closes) - days)
        for i in range(lookback):  # R2: bounded by lookback
            idx = -(lookback - i) - days
            if abs(idx) >= len(closes):
                continue
            fwd_return = (float(closes.iloc[idx + days]) - float(closes.iloc[idx])) / float(closes.iloc[idx])
            if signal == "BUY" and fwd_return > 0:       wins += 1
            elif signal == "SELL" and fwd_return < 0:     wins += 1
            elif signal == "HOLD" and abs(fwd_return) < 0.05: wins += 1
            total += 1
        results[label] = round(wins / total, 4) if total > 0 else None
    return results


def compute_tracking_metrics(returns, spy_df):
    """Compute tracking error, info ratio, alpha vs SPY."""
    if spy_df is None or spy_df.empty:
        return {"tracking_error": 0.0, "info_ratio": 0.0, "alpha": 0.0}
    spy_ret = spy_df["Close"].squeeze().pct_change().dropna()
    a_r, a_b = returns.align(spy_ret, join="inner")
    if len(a_r) <= 10:
        return {"tracking_error": 0.0, "info_ratio": 0.0, "alpha": 0.0}
    diff = a_r - a_b
    te = round(float(diff.std() * np.sqrt(252)), 4)
    alpha = round(float((a_r.mean() - a_b.mean()) * 252), 4)
    ir = round(alpha / te, 4) if te != 0 else 0.0
    return {"tracking_error": te, "info_ratio": ir, "alpha": alpha}


def determine_team_signal(fund_data, tech_data, portfolio_data):
    """Majority vote across agent signals."""
    signals = []
    if fund_data.get("rating"):
        signals.append(fund_data["rating"])
    if tech_data.get("signal"):
        tech_map = {"BULLISH": "BUY", "NEUTRAL": "HOLD", "BEARISH": "SELL"}
        signals.append(tech_map.get(tech_data["signal"], "HOLD"))
    if portfolio_data.get("decision"):
        signals.append(portfolio_data["decision"])
    if not signals:
        return "HOLD"
    buy_count = sum(1 for s in signals if s == "BUY")
    sell_count = sum(1 for s in signals if s == "SELL")
    if buy_count > sell_count:   return "BUY"
    elif sell_count > buy_count: return "SELL"
    return "HOLD"


def compute_agreement(fund_data, tech_data, sent_data):
    """Compute signal agreement level."""
    agent_signals = {
        "fundamental": fund_data.get("rating", "N/A"),
        "technical":   tech_data.get("signal", "N/A"),
        "sentiment":   sent_data.get("overall_sentiment", "N/A"),
    }
    active = [v for v in agent_signals.values() if v != "N/A"]
    if not active:
        return "N/A", agent_signals
    normalized = [s.replace("BULLISH", "BUY").replace("BEARISH", "SELL")
                   .replace("POSITIVE", "BUY").replace("NEGATIVE", "SELL") for s in active]
    unique = len(set(normalized))
    if unique == 1:   agreement = "STRONG"
    elif unique == 2: agreement = "MODERATE"
    else:             agreement = "WEAK"
    return agreement, agent_signals


def compute_grade(hit_rates, sharpe, calmar, agreement, alpha):
    """Compute team grade from metrics."""
    p = get_params("scorecard")
    grade_score = 0
    max_score = 0

    if hit_rates.get("30d") is not None:
        max_score += 1
        if hit_rates["30d"] > p["hit_rate_min"]: grade_score += 1
    if hit_rates.get("90d") is not None:
        max_score += 1
        if hit_rates["90d"] > p["hit_rate_min"]: grade_score += 1

    max_score += 2
    if sharpe > p["sharpe_excellent"]:   grade_score += 2
    elif sharpe > p["sharpe_ok"]:        grade_score += 1

    max_score += 1
    if calmar > p["calmar_min"]: grade_score += 1

    if agreement != "N/A":
        max_score += 1
        if agreement in ("STRONG", "MODERATE"): grade_score += 1

    max_score += 1
    if alpha > 0: grade_score += 1

    ratio = grade_score / max_score if max_score > 0 else 0
    if ratio >= p["grade_A"]:     return "A"
    elif ratio >= p["grade_Bplus"]: return "B+"
    elif ratio >= p["grade_B"]:   return "B"
    elif ratio >= p["grade_C"]:   return "C"
    return "D"


class ScorecardAgent(BaseAgent):
    def __init__(self):
        super().__init__("ScorecardAgent")

    def run(self, ticker: str, **kwargs) -> dict:
        if not ticker or not isinstance(ticker, str):
            return self._error(str(ticker), "Invalid ticker for ScorecardAgent.")
        try:
            return self._analyze(ticker, kwargs)
        except Exception as e:
            return self._error(ticker, str(e))

    def _analyze(self, ticker: str, kwargs: dict) -> dict:
        price_df = kwargs.get("price_df")
        spy_df = kwargs.get("spy_df")
        fund_data = kwargs.get("fundamental", {})
        tech_data = kwargs.get("technical", {})
        sent_data = kwargs.get("sentiment", {})
        risk_data = kwargs.get("risk", {})
        portfolio_data = kwargs.get("portfolio", {})

        if price_df is None or price_df.empty:
            return self._error(ticker, "No price data for scorecard.")

        closes = price_df["Close"].squeeze().dropna()
        returns = closes.pct_change().dropna()

        team_signal = determine_team_signal(fund_data, tech_data, portfolio_data)
        hit_rates = compute_hit_rate(closes, team_signal)
        cvar_99 = self._compute_cvar(returns)
        tracking = compute_tracking_metrics(returns, spy_df)
        agreement, agent_signals = compute_agreement(fund_data, tech_data, sent_data)

        max_dd = risk_data.get("max_drawdown", 0)
        ann_return_val = self._estimate_annual_return(closes)
        calmar = round(ann_return_val / abs(max_dd), 4) if max_dd != 0 else 0.0

        sharpe = risk_data.get("sharpe_ratio", 0)
        grade = compute_grade(hit_rates, sharpe, calmar, agreement, tracking["alpha"])

        return self._result(ticker, {
            "team_grade": grade, "team_signal": team_signal,
            "signal_agreement": agreement, "agent_signals": agent_signals,
            "hit_rate_30d": hit_rates.get("30d"), "hit_rate_60d": hit_rates.get("60d"),
            "hit_rate_90d": hit_rates.get("90d"), "cvar_99_daily": cvar_99,
            "calmar_ratio": calmar, "tracking_error": tracking["tracking_error"],
            "information_ratio": tracking["info_ratio"], "annualized_alpha": tracking["alpha"],
        })

    def _compute_cvar(self, returns, confidence=0.99):
        cutoff = np.percentile(returns, (1 - confidence) * 100)
        tail = returns[returns <= cutoff]
        return round(float(tail.mean()), 6) if len(tail) > 0 else float(cutoff)

    def _estimate_annual_return(self, closes):
        two_yr = closes.tail(504)
        if len(two_yr) <= 252:
            return 0
        total = float(two_yr.iloc[-1] / two_yr.iloc[0] - 1)
        n = len(two_yr) / 252
        return float((1 + total) ** (1 / n) - 1)
