"""
TechnicalAgent — chart indicators + time series for visualization.
All functions ≤60 lines (R4). No recursion (R1).
"""

import pandas as pd
from core.base_agent import BaseAgent
from core.param_loader import get_params

SERIES_LENGTH = 252


def _compute_sma(close, periods):
    """Compute SMA series for given periods. Returns dict of series."""
    result = {}
    for p in periods:
        if len(close) >= p:
            result[f"sma{p}"] = close.rolling(p).mean()
    return result


def _compute_rsi(close):
    """Compute RSI-14 current value and series."""
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, float("nan"))
    rsi_series = 100 - 100 / (1 + rs)
    last_loss = float(loss.iloc[-1])
    rsi = 100.0 if last_loss == 0 else float(100 - 100 / (1 + float(gain.iloc[-1]) / last_loss))
    return rsi, rsi_series


def _compute_macd(close):
    """Compute MACD line, signal, and histogram."""
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def _compute_bollinger(close, sma20_series):
    """Compute Bollinger Bands."""
    std20 = close.rolling(20).std()
    bb_up = sma20_series + 2 * std20
    bb_low = sma20_series - 2 * std20
    return bb_up, bb_low


def _score_signals(price, sma20, sma50, sma200, rsi, macd, signal):
    """Score technical signals. Returns (score, notes)."""
    p = get_params("technical")
    score = 0
    notes = []

    if price > sma20:  score += 1; notes.append("Price above SMA20 — short-term bullish")
    else:              score -= 1; notes.append("Price below SMA20 — short-term bearish")

    if price > sma50:  score += 1; notes.append("Price above SMA50 — medium-term bullish")
    else:              score -= 1; notes.append("Price below SMA50 — medium-term bearish")

    if sma200 is not None:
        if price > sma200: score += 1; notes.append("Price above SMA200 — long-term uptrend")
        else:              score -= 1; notes.append("Price below SMA200 — long-term downtrend")

    if rsi < p["rsi_oversold"]:    score += 1; notes.append(f"RSI {rsi:.1f} — oversold, potential bounce")
    elif rsi > p["rsi_overbought"]: score -= 1; notes.append(f"RSI {rsi:.1f} — overbought, caution")

    if macd > signal:  score += 1; notes.append("MACD above signal — bullish momentum")
    else:              score -= 1; notes.append("MACD below signal — bearish momentum")

    return score, notes


def _build_series(close, price_df, smas, rsi_s, macd_l, macd_sig, macd_h, bb_up, bb_low):
    """Build series data for visualization. Returns dict."""
    tail = slice(-SERIES_LENGTH, None)
    dates = [d.isoformat() if hasattr(d, "isoformat") else str(d) for d in close.index[tail]]

    ohlc = {}
    for col in ["Open", "High", "Low", "Close"]:
        if col in price_df.columns:
            s = price_df[col].squeeze().dropna()
            ohlc[col.lower()] = [round(float(v), 2) for v in s.iloc[tail]]
    if "Volume" in price_df.columns:
        ohlc["volume"] = [int(v) for v in price_df["Volume"].squeeze().dropna().iloc[tail]]

    def _to_list(s):
        return [round(float(v), 2) if pd.notna(v) else None for v in s.iloc[tail]]

    series = {"dates": dates, "ohlc": ohlc, "rsi": _to_list(rsi_s)}
    series["macd"] = [round(float(v), 4) if pd.notna(v) else None for v in macd_l.iloc[tail]]
    series["macd_signal"] = [round(float(v), 4) if pd.notna(v) else None for v in macd_sig.iloc[tail]]
    series["macd_hist"] = [round(float(v), 4) if pd.notna(v) else None for v in macd_h.iloc[tail]]
    series["bb_upper"] = _to_list(bb_up)
    series["bb_lower"] = _to_list(bb_low)

    for name, s in smas.items():
        series[name] = _to_list(s)

    return series


class TechnicalAgent(BaseAgent):
    def __init__(self):
        super().__init__("TechnicalAgent")

    def run(self, ticker: str, **kwargs) -> dict:
        if not ticker or not isinstance(ticker, str):
            return self._error(str(ticker), "Invalid ticker for TechnicalAgent.")
        try:
            return self._analyze(ticker, kwargs)
        except Exception as e:
            return self._error(ticker, str(e))

    def _analyze(self, ticker: str, kwargs: dict) -> dict:
        price_df = kwargs.get("price_df")
        if price_df is None or price_df.empty:
            return self._error(ticker, "No price data provided to TechnicalAgent.")

        close = price_df["Close"].squeeze().dropna()
        if len(close) < 50:
            return self._error(ticker, f"Only {len(close)} price points — need at least 50.")

        price = float(close.iloc[-1])
        smas = _compute_sma(close, [20, 50, 200])
        rsi, rsi_series = _compute_rsi(close)
        macd_line, signal_line, hist_series = _compute_macd(close)
        bb_up, bb_low = _compute_bollinger(close, smas.get("sma20", close.rolling(20).mean()))

        sma20 = float(smas["sma20"].iloc[-1])
        sma50 = float(smas["sma50"].iloc[-1])
        sma200 = float(smas["sma200"].iloc[-1]) if "sma200" in smas else None
        macd_val = float(macd_line.iloc[-1])
        sig_val = float(signal_line.iloc[-1])

        score, notes = _score_signals(price, sma20, sma50, sma200, rsi, macd_val, sig_val)

        tp = get_params("technical")
        if score >= tp["bullish_threshold"]:     trend_signal = "BULLISH"
        elif score <= tp["bearish_threshold"]:   trend_signal = "BEARISH"
        else:                                    trend_signal = "NEUTRAL"

        series = _build_series(close, price_df, smas, rsi_series,
                               macd_line, signal_line, hist_series, bb_up, bb_low)

        return self._result(ticker, {
            "signal": trend_signal, "score": score,
            "current_price": round(price, 2),
            "sma20": round(sma20, 2), "sma50": round(sma50, 2),
            "sma200": round(sma200, 2) if sma200 else None,
            "rsi_14": round(rsi, 2),
            "macd": round(macd_val, 4), "macd_signal": round(sig_val, 4),
            "macd_hist": round(macd_val - sig_val, 4),
            "bb_upper": round(float(bb_up.iloc[-1]), 2),
            "bb_lower": round(float(bb_low.iloc[-1]), 2),
            "52w_high": round(float(close.tail(252).max()), 2),
            "52w_low": round(float(close.tail(252).min()), 2),
            "scoring_notes": notes,
            "series": series,
        })
