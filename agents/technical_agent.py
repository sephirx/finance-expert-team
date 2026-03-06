import numpy as np
import yfinance as yf
from core.base_agent import BaseAgent
from core.rate_limiter import wait_if_needed


class TechnicalAgent(BaseAgent):
    def __init__(self):
        super().__init__("TechnicalAgent")

    def run(self, ticker: str, **kwargs) -> dict:
        try:
            wait_if_needed("yfinance")
            df    = yf.download(ticker, period="1y", progress=False)
            close = df["Close"].squeeze()

            sma20  = float(close.rolling(20).mean().iloc[-1])
            sma50  = float(close.rolling(50).mean().iloc[-1])
            sma200 = float(close.rolling(200).mean().iloc[-1])

            # RSI
            delta = close.diff()
            gain  = delta.clip(lower=0).rolling(14).mean()
            loss  = (-delta.clip(upper=0)).rolling(14).mean()
            rsi   = float((100 - 100 / (1 + gain / loss)).iloc[-1])

            # MACD
            ema12  = close.ewm(span=12).mean()
            ema26  = close.ewm(span=26).mean()
            macd   = float((ema12 - ema26).iloc[-1])
            signal = float((ema12 - ema26).ewm(span=9).mean().iloc[-1])
            hist   = round(macd - signal, 4)

            # Bollinger Bands
            sma20s  = close.rolling(20).mean()
            std20   = close.rolling(20).std()
            bb_up   = float((sma20s + 2 * std20).iloc[-1])
            bb_low  = float((sma20s - 2 * std20).iloc[-1])

            price = float(close.iloc[-1])

            # Simple signal scoring
            score = 0
            notes = []

            if price > sma20:  score += 1; notes.append("Price above SMA20 — short-term bullish")
            else:              score -= 1; notes.append("Price below SMA20 — short-term bearish")

            if price > sma50:  score += 1; notes.append("Price above SMA50 — medium-term bullish")
            else:              score -= 1; notes.append("Price below SMA50 — medium-term bearish")

            if price > sma200: score += 1; notes.append("Price above SMA200 — long-term uptrend")
            else:              score -= 1; notes.append("Price below SMA200 — long-term downtrend")

            if rsi < 30:       score += 1; notes.append(f"RSI {rsi:.1f} — oversold, potential bounce")
            elif rsi > 70:     score -= 1; notes.append(f"RSI {rsi:.1f} — overbought, caution")

            if macd > signal:  score += 1; notes.append("MACD above signal — bullish momentum")
            else:              score -= 1; notes.append("MACD below signal — bearish momentum")

            if score >= 3:     trend = "BULLISH"
            elif score <= -3:  trend = "BEARISH"
            else:              trend = "NEUTRAL"

            return self._result(ticker, {
                "signal":        trend,
                "score":         score,
                "current_price": round(price, 2),
                "sma20":         round(sma20, 2),
                "sma50":         round(sma50, 2),
                "sma200":        round(sma200, 2),
                "rsi_14":        round(rsi, 2),
                "macd":          round(macd, 4),
                "macd_signal":   round(signal, 4),
                "macd_hist":     hist,
                "bb_upper":      round(bb_up, 2),
                "bb_lower":      round(bb_low, 2),
                "52w_high":      round(float(close.max()), 2),
                "52w_low":       round(float(close.min()), 2),
                "scoring_notes": notes,
            })

        except Exception as e:
            return self._error(ticker, str(e))
