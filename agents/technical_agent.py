import math
import pandas as pd
from core.base_agent import BaseAgent


class TechnicalAgent(BaseAgent):
    def __init__(self):
        super().__init__("TechnicalAgent")

    def run(self, ticker: str, **kwargs) -> dict:
        try:
            price_df = kwargs.get("price_df")
            if price_df is None or price_df.empty:
                return self._error(ticker, "No price data provided to TechnicalAgent.")

            close = price_df["Close"].squeeze().dropna()
            if len(close) < 50:
                return self._error(ticker, f"Only {len(close)} price points — need at least 50.")

            price = float(close.iloc[-1])

            # SMA — compute once, reuse
            sma20_series = close.rolling(20).mean()
            sma50_series = close.rolling(50).mean()

            sma20 = float(sma20_series.iloc[-1])
            sma50 = float(sma50_series.iloc[-1])
            sma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None

            # RSI — guard against division by zero
            delta = close.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            last_loss = float(loss.iloc[-1])
            if last_loss == 0:
                rsi = 100.0
            else:
                rsi = float(100 - 100 / (1 + float(gain.iloc[-1]) / last_loss))

            # MACD
            ema12 = close.ewm(span=12).mean()
            ema26 = close.ewm(span=26).mean()
            macd_line = ema12 - ema26
            macd = float(macd_line.iloc[-1])
            signal = float(macd_line.ewm(span=9).mean().iloc[-1])
            hist = round(macd - signal, 4)

            # Bollinger Bands (reuse sma20_series)
            std20 = close.rolling(20).std()
            bb_up = float((sma20_series + 2 * std20).iloc[-1])
            bb_low = float((sma20_series - 2 * std20).iloc[-1])

            # Signal scoring
            score = 0
            notes = []

            if price > sma20:  score += 1; notes.append("Price above SMA20 — short-term bullish")
            else:              score -= 1; notes.append("Price below SMA20 — short-term bearish")

            if price > sma50:  score += 1; notes.append("Price above SMA50 — medium-term bullish")
            else:              score -= 1; notes.append("Price below SMA50 — medium-term bearish")

            if sma200 is not None:
                if price > sma200: score += 1; notes.append("Price above SMA200 — long-term uptrend")
                else:              score -= 1; notes.append("Price below SMA200 — long-term downtrend")

            if rsi < 30:       score += 1; notes.append(f"RSI {rsi:.1f} — oversold, potential bounce")
            elif rsi > 70:     score -= 1; notes.append(f"RSI {rsi:.1f} — overbought, caution")

            if macd > signal:  score += 1; notes.append("MACD above signal — bullish momentum")
            else:              score -= 1; notes.append("MACD below signal — bearish momentum")

            if score >= 3:     trend_signal = "BULLISH"
            elif score <= -3:  trend_signal = "BEARISH"
            else:              trend_signal = "NEUTRAL"

            return self._result(ticker, {
                "signal":        trend_signal,
                "score":         score,
                "current_price": round(price, 2),
                "sma20":         round(sma20, 2),
                "sma50":         round(sma50, 2),
                "sma200":        round(sma200, 2) if sma200 else None,
                "rsi_14":        round(rsi, 2),
                "macd":          round(macd, 4),
                "macd_signal":   round(signal, 4),
                "macd_hist":     hist,
                "bb_upper":      round(bb_up, 2),
                "bb_lower":      round(bb_low, 2),
                "52w_high":      round(float(close.tail(252).max()), 2),
                "52w_low":       round(float(close.tail(252).min()), 2),
                "scoring_notes": notes,
            })

        except Exception as e:
            return self._error(ticker, str(e))
