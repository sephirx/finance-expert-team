from core.base_agent import BaseAgent


class FundamentalAgent(BaseAgent):
    def __init__(self):
        super().__init__("FundamentalAgent")

    def run(self, ticker: str, **kwargs) -> dict:
        raw = kwargs.get("raw_data", {})
        if not raw:
            return self._error(ticker, "No raw data provided to FundamentalAgent.")

        try:
            pe      = raw.get("pe_ratio")
            fpe     = raw.get("forward_pe")
            pb      = raw.get("pb_ratio")
            ev_eb   = raw.get("ev_ebitda")
            roe     = raw.get("roe")
            roa     = raw.get("roa")
            de      = raw.get("debt_to_equity")
            fcf     = raw.get("free_cashflow")
            rev_g   = raw.get("revenue_growth")
            earn_g  = raw.get("earnings_growth")
            price   = raw.get("current_price")
            target  = raw.get("analyst_target")
            rec     = raw.get("recommendation", "N/A")

            # Upside to analyst target
            upside = None
            if price and target:
                try:
                    upside = round((float(target) - float(price)) / float(price) * 100, 2)
                except Exception:
                    pass

            # Simple scoring: +1 good, -1 bad, 0 neutral
            score = 0
            notes = []

            if pe:
                if float(pe) < 15:
                    score += 1; notes.append("P/E below 15 — cheap")
                elif float(pe) > 30:
                    score -= 1; notes.append("P/E above 30 — expensive")

            if roe:
                if float(roe) > 0.15:
                    score += 1; notes.append("ROE > 15% — strong profitability")
                elif float(roe) < 0.05:
                    score -= 1; notes.append("ROE < 5% — weak profitability")

            if de:
                if float(de) > 200:
                    score -= 1; notes.append("High debt-to-equity — leverage risk")
                elif float(de) < 50:
                    score += 1; notes.append("Low debt — healthy balance sheet")

            if rev_g:
                if float(rev_g) > 0.10:
                    score += 1; notes.append("Revenue growing >10% YoY")
                elif float(rev_g) < 0:
                    score -= 1; notes.append("Revenue declining")

            if upside and upside > 10:
                score += 1; notes.append(f"Analyst target implies {upside}% upside")
            elif upside and upside < -10:
                score -= 1; notes.append(f"Analyst target implies {abs(upside)}% downside")

            if score >= 2:
                rating = "BUY"
            elif score <= -2:
                rating = "SELL"
            else:
                rating = "HOLD"

            return self._result(ticker, {
                "rating":            rating,
                "score":             score,
                "pe_ratio":          pe,
                "forward_pe":        fpe,
                "pb_ratio":          pb,
                "ev_ebitda":         ev_eb,
                "roe":               roe,
                "roa":               roa,
                "debt_to_equity":    de,
                "free_cashflow":     fcf,
                "revenue_growth":    rev_g,
                "earnings_growth":   earn_g,
                "analyst_target":    target,
                "analyst_upside_pct":upside,
                "recommendation":    rec,
                "scoring_notes":     notes,
            })

        except Exception as e:
            return self._error(ticker, str(e))
