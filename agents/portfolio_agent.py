from core.base_agent import BaseAgent
from core.config import SIGNAL_WEIGHTS


class PortfolioAgent(BaseAgent):
    def __init__(self):
        super().__init__("PortfolioAgent")

    # Map text signals to numeric scores
    _FUND_MAP = {"BUY": 1, "HOLD": 0, "SELL": -1}
    _TECH_MAP = {"BULLISH": 1, "NEUTRAL": 0, "BEARISH": -1}
    _SENT_MAP = {"POSITIVE": 1, "NEUTRAL": 0, "NEGATIVE": -1}

    def run(self, ticker: str, **kwargs) -> dict:
        try:
            fund_data = kwargs.get("fundamental", {})
            tech_data = kwargs.get("technical", {})
            sent_data = kwargs.get("sentiment", {})
            risk_data = kwargs.get("risk", {})

            fund_score = self._FUND_MAP.get(fund_data.get("rating", "HOLD"), 0)
            tech_score = self._TECH_MAP.get(tech_data.get("signal", "NEUTRAL"), 0)
            sent_score = self._SENT_MAP.get(sent_data.get("overall_sentiment", "NEUTRAL"), 0)

            weighted = (
                fund_score * SIGNAL_WEIGHTS["fundamental"] +
                tech_score * SIGNAL_WEIGHTS["technical"] +
                sent_score * SIGNAL_WEIGHTS["sentiment"]
            )
            weighted = round(weighted, 4)

            # Final decision
            if weighted >= 0.3:    decision = "BUY"
            elif weighted <= -0.3: decision = "SELL"
            else:                  decision = "HOLD"

            # Conviction based on agreement between signals
            all_scores = [fund_score, tech_score, sent_score]
            agreement  = len(set(all_scores))
            if agreement == 1:     conviction = "HIGH"
            elif agreement == 2:   conviction = "MEDIUM"
            else:                  conviction = "LOW"

            # Position sizing from risk agent
            max_pos = risk_data.get("suggested_max_position", 0.10)
            if decision == "BUY" and conviction == "HIGH":
                position = max_pos
            elif decision == "BUY":
                position = max_pos * 0.5
            else:
                position = 0.0

            price       = tech_data.get("current_price")
            sma200      = tech_data.get("sma200")
            analyst_tgt = fund_data.get("analyst_target")
            var95       = risk_data.get("var_95_daily", -0.02)

            stop_loss = round(price * (1 + var95 * 2), 2) if price else None
            target    = analyst_tgt or (round(price * 1.15, 2) if price else None)

            return self._result(ticker, {
                "decision":           decision,
                "conviction":         conviction,
                "weighted_score":     weighted,
                "fundamental_signal": fund_data.get("rating", "N/A"),
                "technical_signal":   tech_data.get("signal", "N/A"),
                "sentiment_signal":   sent_data.get("overall_sentiment", "N/A"),
                "recommended_position_pct": round(position * 100, 1),
                "entry_price":        price,
                "target_price":       target,
                "stop_loss":          stop_loss,
                "weights_used":       SIGNAL_WEIGHTS,
            })

        except Exception as e:
            return self._error(ticker, str(e))
