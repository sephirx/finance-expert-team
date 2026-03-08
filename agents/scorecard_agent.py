import numpy as np
import pandas as pd
from core.base_agent import BaseAgent


class ScorecardAgent(BaseAgent):
    """
    Computes industry-standard performance metrics.
    Tier 1: Hit Rate, Calmar, CVaR, Information Ratio, Tracking Error.
    Aggregates all agent signals into a unified performance scorecard.
    """

    def __init__(self):
        super().__init__("ScorecardAgent")

    def _compute_hit_rate(self, closes: pd.Series, signal: str) -> dict:
        """
        Check if the signal (BUY/HOLD/SELL) would have been correct
        over 30, 60, 90 day forward returns.
        Uses historical data: looks at past signals vs actual outcomes.
        """
        results = {}
        current_price = float(closes.iloc[-1])

        for days, label in [(30, "30d"), (60, "60d"), (90, "90d")]:
            if len(closes) < days + 252:
                results[label] = None
                continue

            # Simulate: at each point in the last year, what would this signal have returned?
            wins = 0
            total = 0
            lookback = min(252, len(closes) - days)

            for i in range(lookback):
                idx = -(lookback - i) - days
                if abs(idx) >= len(closes):
                    continue
                entry = float(closes.iloc[idx])
                exit_price = float(closes.iloc[idx + days])
                fwd_return = (exit_price - entry) / entry

                if signal == "BUY" and fwd_return > 0:
                    wins += 1
                elif signal == "SELL" and fwd_return < 0:
                    wins += 1
                elif signal == "HOLD" and abs(fwd_return) < 0.05:
                    wins += 1
                total += 1

            results[label] = round(wins / total, 4) if total > 0 else None

        return results

    def _compute_calmar(self, ann_return: float, max_dd: float) -> float:
        """Calmar Ratio = Annualized Return / |Max Drawdown|"""
        if max_dd == 0:
            return 0.0
        return round(ann_return / abs(max_dd), 4)

    def _compute_cvar(self, returns: pd.Series, confidence: float = 0.99) -> float:
        """CVaR / Expected Shortfall at given confidence level."""
        cutoff = np.percentile(returns, (1 - confidence) * 100)
        tail = returns[returns <= cutoff]
        if len(tail) == 0:
            return float(cutoff)
        return round(float(tail.mean()), 6)

    def _compute_tracking_error(self, returns: pd.Series, benchmark_returns: pd.Series) -> float:
        """Annualized tracking error vs benchmark."""
        aligned_r, aligned_b = returns.align(benchmark_returns, join="inner")
        if len(aligned_r) < 10:
            return 0.0
        diff = aligned_r - aligned_b
        return round(float(diff.std() * np.sqrt(252)), 4)

    def _compute_information_ratio(self, alpha: float, tracking_error: float) -> float:
        """Information Ratio = Alpha / Tracking Error."""
        if tracking_error == 0:
            return 0.0
        return round(alpha / tracking_error, 4)

    def run(self, ticker: str, **kwargs) -> dict:
        try:
            price_df     = kwargs.get("price_df")
            spy_df       = kwargs.get("spy_df")
            fund_data    = kwargs.get("fundamental", {})
            tech_data    = kwargs.get("technical", {})
            sent_data    = kwargs.get("sentiment", {})
            risk_data    = kwargs.get("risk", {})
            backtest_data = kwargs.get("backtest", {})
            portfolio_data = kwargs.get("portfolio", {})

            if price_df is None or price_df.empty:
                return self._error(ticker, "No price data for scorecard.")

            closes = price_df["Close"].squeeze().dropna()
            returns = closes.pct_change().dropna()

            # Determine the team's overall signal
            signals = []
            if fund_data.get("rating"):
                signals.append(fund_data["rating"])
            if tech_data.get("signal"):
                tech_map = {"BULLISH": "BUY", "NEUTRAL": "HOLD", "BEARISH": "SELL"}
                signals.append(tech_map.get(tech_data["signal"], "HOLD"))
            if portfolio_data.get("decision"):
                signals.append(portfolio_data["decision"])

            # Majority vote
            if signals:
                buy_count  = sum(1 for s in signals if s == "BUY")
                sell_count = sum(1 for s in signals if s == "SELL")
                if buy_count > sell_count:
                    team_signal = "BUY"
                elif sell_count > buy_count:
                    team_signal = "SELL"
                else:
                    team_signal = "HOLD"
            else:
                team_signal = "HOLD"

            # --- Hit Rate ---
            hit_rates = self._compute_hit_rate(closes, team_signal)

            # --- CVaR (99%) ---
            cvar_99 = self._compute_cvar(returns, 0.99)

            # --- Tracking Error & Information Ratio ---
            tracking_error = 0.0
            info_ratio = 0.0
            ann_alpha = 0.0

            if spy_df is not None and not spy_df.empty:
                spy_ret = spy_df["Close"].squeeze().pct_change().dropna()
                tracking_error = self._compute_tracking_error(returns, spy_ret)

                # Annualized alpha vs SPY
                aligned_r, aligned_b = returns.align(spy_ret, join="inner")
                if len(aligned_r) > 10:
                    ann_alpha = round(float((aligned_r.mean() - aligned_b.mean()) * 252), 4)
                    info_ratio = self._compute_information_ratio(ann_alpha, tracking_error)

            # --- Calmar Ratio ---
            max_dd = risk_data.get("max_drawdown", 0)
            ann_return_val = backtest_data.get("annualized_return")
            if ann_return_val is None:
                # Estimate from price data (2yr)
                two_yr = closes.tail(504)
                if len(two_yr) > 252:
                    total = float(two_yr.iloc[-1] / two_yr.iloc[0] - 1)
                    n = len(two_yr) / 252
                    ann_return_val = float((1 + total) ** (1 / n) - 1)
                else:
                    ann_return_val = 0
            calmar = self._compute_calmar(ann_return_val, max_dd)

            # --- Signal Agreement ---
            agent_signals = {
                "fundamental": fund_data.get("rating", "N/A"),
                "technical":   tech_data.get("signal", "N/A"),
                "sentiment":   sent_data.get("overall_sentiment", "N/A"),
            }
            active_signals = [v for v in agent_signals.values() if v != "N/A"]
            if active_signals:
                unique = len(set(s.replace("BULLISH", "BUY").replace("BEARISH", "SELL").replace("POSITIVE", "BUY").replace("NEGATIVE", "SELL") for s in active_signals))
                if unique == 1:   agreement = "STRONG"
                elif unique == 2: agreement = "MODERATE"
                else:             agreement = "WEAK"
            else:
                agreement = "N/A"

            # --- Team Grade ---
            grade_score = 0
            if hit_rates.get("30d") and hit_rates["30d"] > 0.6: grade_score += 1
            if hit_rates.get("90d") and hit_rates["90d"] > 0.6: grade_score += 1
            sharpe = risk_data.get("sharpe_ratio", 0)
            if sharpe > 1:    grade_score += 2
            elif sharpe > 0.5: grade_score += 1
            if calmar > 0.5:  grade_score += 1
            if agreement == "STRONG": grade_score += 1

            if grade_score >= 5:   team_grade = "A"
            elif grade_score >= 4: team_grade = "B+"
            elif grade_score >= 3: team_grade = "B"
            elif grade_score >= 2: team_grade = "C"
            else:                  team_grade = "D"

            return self._result(ticker, {
                "team_grade":           team_grade,
                "team_signal":          team_signal,
                "signal_agreement":     agreement,
                "agent_signals":        agent_signals,
                "hit_rate_30d":         hit_rates.get("30d"),
                "hit_rate_60d":         hit_rates.get("60d"),
                "hit_rate_90d":         hit_rates.get("90d"),
                "cvar_99_daily":        cvar_99,
                "calmar_ratio":         calmar,
                "tracking_error":       tracking_error,
                "information_ratio":    info_ratio,
                "annualized_alpha":     ann_alpha,
                "grade_breakdown": {
                    "hit_rate_points":    1 if (hit_rates.get("30d") or 0) > 0.6 else 0,
                    "sharpe_points":      2 if sharpe > 1 else (1 if sharpe > 0.5 else 0),
                    "calmar_points":      1 if calmar > 0.5 else 0,
                    "agreement_points":   1 if agreement == "STRONG" else 0,
                    "total":              grade_score,
                },
            })

        except Exception as e:
            return self._error(ticker, str(e))
