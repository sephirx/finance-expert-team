from core.base_agent import BaseAgent
from core.param_loader import get_params


def _sf(val):
    """Safe float conversion."""
    if val is None:
        return None
    try:
        f = float(val)
        return f if f == f else None
    except (ValueError, TypeError):
        return None


def _score_fundamentals(pe, roe, de, rev_g, upside):
    """Score fundamental metrics. Returns (score, notes)."""
    p = get_params("fundamental")
    score = 0
    notes = []

    if pe is not None:
        if pe < p["pe_cheap"]:       score += 1; notes.append(f"P/E below {p['pe_cheap']} — cheap")
        elif pe > p["pe_expensive"]: score -= 1; notes.append(f"P/E above {p['pe_expensive']} — expensive")

    if roe is not None:
        if roe > p["roe_strong"]:   score += 1; notes.append(f"ROE > {p['roe_strong']*100:.0f}% — strong profitability")
        elif roe < p["roe_weak"]:   score -= 1; notes.append(f"ROE < {p['roe_weak']*100:.0f}% — weak profitability")

    if de is not None:
        if de > p["de_high"]:   score -= 1; notes.append("High debt-to-equity — leverage risk")
        elif de < p["de_low"]:  score += 1; notes.append("Low debt — healthy balance sheet")

    if rev_g is not None:
        if rev_g > p["rev_growth_good"]:  score += 1; notes.append(f"Revenue growing >{p['rev_growth_good']*100:.0f}% YoY")
        elif rev_g < 0:                   score -= 1; notes.append("Revenue declining")

    if upside is not None:
        if upside > p["upside_bullish"]:    score += 1; notes.append(f"Analyst target implies {upside}% upside")
        elif upside < p["upside_bearish"]:  score -= 1; notes.append(f"Analyst target implies {abs(upside)}% downside")

    return score, notes


class FundamentalAgent(BaseAgent):
    def __init__(self):
        super().__init__("FundamentalAgent")

    def run(self, ticker: str, **kwargs) -> dict:
        if not ticker or not isinstance(ticker, str):
            return self._error(str(ticker), "Invalid ticker for FundamentalAgent.")

        raw = kwargs.get("raw_data", {})
        if not raw:
            return self._error(ticker, "No raw data provided to FundamentalAgent.")

        try:
            return self._analyze(ticker, raw)
        except Exception as e:
            return self._error(ticker, str(e))

    def _analyze(self, ticker: str, raw: dict) -> dict:
        pe     = _sf(raw.get("pe_ratio"))
        fpe    = _sf(raw.get("forward_pe"))
        pb     = _sf(raw.get("pb_ratio"))
        ev_eb  = _sf(raw.get("ev_ebitda"))
        roe    = _sf(raw.get("roe"))
        roa    = _sf(raw.get("roa"))
        de     = _sf(raw.get("debt_to_equity"))
        fcf    = raw.get("free_cashflow")
        rev_g  = _sf(raw.get("revenue_growth"))
        earn_g = _sf(raw.get("earnings_growth"))
        price  = _sf(raw.get("current_price"))
        target = _sf(raw.get("analyst_target"))
        rec    = raw.get("recommendation", "N/A")

        upside = None
        if price and target and price > 0:
            upside = round((target - price) / price * 100, 2)

        score, notes = _score_fundamentals(pe, roe, de, rev_g, upside)

        p = get_params("fundamental")
        if score >= p["buy_threshold"]:      rating = "BUY"
        elif score <= p["sell_threshold"]:   rating = "SELL"
        else:                                rating = "HOLD"

        return self._result(ticker, {
            "rating": rating, "score": score,
            "pe_ratio": pe, "forward_pe": fpe, "pb_ratio": pb, "ev_ebitda": ev_eb,
            "roe": roe, "roa": roa, "debt_to_equity": de, "free_cashflow": fcf,
            "revenue_growth": rev_g, "earnings_growth": earn_g,
            "analyst_target": target, "analyst_upside_pct": upside,
            "recommendation": rec, "scoring_notes": notes,
        })
