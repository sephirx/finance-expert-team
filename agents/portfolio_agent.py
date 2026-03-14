"""
PortfolioAgent — memory-aware portfolio advisor (Point 5).
All functions ≤60 lines (R4). No recursion (R1).
"""

from core.base_agent import BaseAgent
from core.config import SIGNAL_WEIGHTS
from memory.portfolio_store import PortfolioStore

_FUND_MAP = {"BUY": 1, "HOLD": 0, "SELL": -1}
_TECH_MAP = {"BULLISH": 1, "NEUTRAL": 0, "BEARISH": -1}
_SENT_MAP = {"POSITIVE": 1, "NEUTRAL": 0, "NEGATIVE": -1}


def _compute_weighted_decision(fund_data, tech_data, sent_data):
    """Compute weighted score and decision."""
    fs = _FUND_MAP.get(fund_data.get("rating", "HOLD"), 0)
    ts = _TECH_MAP.get(tech_data.get("signal", "NEUTRAL"), 0)
    ss = _SENT_MAP.get(sent_data.get("overall_sentiment", "NEUTRAL"), 0)

    weighted = round(fs * SIGNAL_WEIGHTS["fundamental"] +
                     ts * SIGNAL_WEIGHTS["technical"] +
                     ss * SIGNAL_WEIGHTS["sentiment"], 4)

    if weighted >= 0.3:    decision = "BUY"
    elif weighted <= -0.3: decision = "SELL"
    else:                  decision = "HOLD"

    scores = [fs, ts, ss]
    unique = len(set(scores))
    conviction = "HIGH" if unique == 1 else "MEDIUM" if unique == 2 else "LOW"

    return decision, conviction, weighted


def _assess_existing_holding(holding, price, decision, prefs, store):
    """Generate suggestions for a ticker already held."""
    suggestions = []
    warnings = []
    prices = {holding.ticker: price} if price else {}
    pos_pct = store.position_pct(holding.ticker, prices)
    pnl = round((price - holding.avg_cost) / holding.avg_cost * 100, 1) if price else 0
    max_pct = prefs.max_position_pct

    if decision == "BUY":
        if pos_pct >= max_pct:
            warnings.append(f"Already at {pos_pct}% of portfolio (max {max_pct}%). Do not add more.")
        elif pos_pct >= max_pct * 0.7:
            suggestions.append(f"Can add up to {round(max_pct - pos_pct, 1)}% more before hitting limit.")
        else:
            suggestions.append(f"Signal is BUY. Current position {pos_pct}% — room to add.")
    elif decision == "SELL":
        word = "taking profit" if pnl > 0 else "cutting losses"
        suggestions.append(f"Signal is SELL. You're {'up' if pnl > 0 else 'down'} {pnl}% — consider {word}.")
    elif decision == "HOLD":
        if pnl > 20:
            suggestions.append(f"Up {pnl}% — consider trimming to lock in gains.")
        elif pnl < -15:
            suggestions.append(f"Down {pnl}% — reassess thesis or set a stop loss.")

    return {
        "currently_held": True, "current_position_pct": pos_pct,
        "unrealized_pnl_pct": pnl, "holding_shares": holding.shares,
        "avg_cost": holding.avg_cost, "suggestions": suggestions, "warnings": warnings,
    }


def _assess_new_position(decision, price, store, prefs):
    """Generate suggestions for a ticker not yet held."""
    suggestions = []
    warnings = []

    if decision == "BUY" and store.state.cash_balance > 0 and price:
        max_invest = store.state.cash_balance * (prefs.max_position_pct / 100)
        max_shares = int(max_invest / price)
        if max_shares > 0:
            suggestions.append(f"Signal is BUY. You could buy up to {max_shares} shares "
                               f"(${max_invest:,.0f} = {prefs.max_position_pct}% of portfolio).")
        else:
            warnings.append("Insufficient cash for this position.")
    elif decision == "BUY":
        suggestions.append("Signal is BUY. Not currently held — consider opening a position.")

    return {"currently_held": False, "current_position_pct": 0.0,
            "suggestions": suggestions, "warnings": warnings}


class PortfolioAgent(BaseAgent):
    def __init__(self):
        super().__init__("PortfolioAgent")

    def run(self, ticker: str, **kwargs) -> dict:
        if not ticker or not isinstance(ticker, str):
            return self._error(str(ticker), "Invalid ticker for PortfolioAgent.")
        fund_data = kwargs.get("fundamental", {})
        tech_data = kwargs.get("technical", {})
        if not fund_data and not tech_data:
            return self._error(ticker, "No fundamental or technical data for PortfolioAgent.")
        try:
            return self._analyze(ticker, kwargs)
        except Exception as e:
            return self._error(ticker, str(e))

    def _analyze(self, ticker: str, kwargs: dict) -> dict:
        fund_data = kwargs.get("fundamental", {})
        tech_data = kwargs.get("technical", {})
        sent_data = kwargs.get("sentiment", {})
        risk_data = kwargs.get("risk", {})
        store = kwargs.get("portfolio_store")

        decision, conviction, weighted = _compute_weighted_decision(fund_data, tech_data, sent_data)

        max_pos = risk_data.get("suggested_max_position", 0.10)
        if decision == "BUY" and conviction == "HIGH":   position = max_pos
        elif decision == "BUY":                          position = max_pos * 0.5
        else:                                            position = 0.0

        price = tech_data.get("current_price")
        var95 = risk_data.get("var_95_daily", -0.02)
        stop_loss = round(price * (1 + var95 * 2), 2) if price else None
        target = fund_data.get("analyst_target") or (round(price * 1.15, 2) if price else None)

        result = {
            "decision": decision, "conviction": conviction, "weighted_score": weighted,
            "fundamental_signal": fund_data.get("rating", "N/A"),
            "technical_signal": tech_data.get("signal", "N/A"),
            "sentiment_signal": sent_data.get("overall_sentiment", "N/A"),
            "recommended_position_pct": round(position * 100, 1),
            "entry_price": price, "target_price": target, "stop_loss": stop_loss,
        }

        if store:
            result["portfolio_context"] = self._get_context(ticker, decision, price, store)

        return self._result(ticker, result)

    def _get_context(self, ticker, decision, price, store):
        """Build portfolio context from memory stack."""
        holdings = store.get_all_holdings()
        if not holdings and store.state.cash_balance <= 0:
            return {"has_portfolio": False}

        ctx = {"has_portfolio": True, "total_holdings": len(holdings),
               "portfolio_summary": {"broker": store.state.broker or "Not set",
                                     "cash": store.state.cash_balance,
                                     "num_positions": len(holdings)}}
        holding = store.get_holding(ticker)
        if holding and price:
            ctx.update(_assess_existing_holding(holding, price, decision, store.state.preferences, store))
        else:
            ctx.update(_assess_new_position(decision, price, store, store.state.preferences))
        return ctx
