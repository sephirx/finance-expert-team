"""
Backtest engine for strategy parameter auto-tuning (Feature 3).
All functions ≤60 lines (R4). No recursion (R1).
"""

import numpy as np
import pandas as pd

_RISK_FREE_ANNUAL = 0.04


def generate_technical_signals(close: pd.Series) -> pd.Series:
    """Vectorized rolling SMA/RSI/MACD/Bollinger. Returns int score series [-5,+5]."""
    score = pd.Series(0, index=close.index, dtype=float)

    # SMA 20/50/200
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    score += np.where(close > sma20, 1, -1)
    score += np.where(close > sma50, 1, -1)
    # SMA200 only where enough data exists
    has_sma200 = sma200.notna()
    score += np.where(has_sma200, np.where(close > sma200, 1, -1), 0)

    # RSI-14
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    score += np.where(rsi < 30, 1, np.where(rsi > 70, -1, 0))

    # MACD 12/26/9
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    score += np.where(macd_line > signal_line, 1, -1)

    return score.fillna(0).astype(int)


def signals_to_position(tech_scores: pd.Series, fund_const: float,
                        sent_const: float, weights: dict,
                        threshold: float = 0.3) -> pd.Series:
    """Convert signals to long-only positions (1=LONG, 0=FLAT)."""
    tech_norm = tech_scores / 5.0
    w_f = weights["fundamental"]
    w_t = weights["technical"]
    w_s = weights["sentiment"]
    weighted = fund_const * w_f + tech_norm * w_t + sent_const * w_s
    position = (weighted >= threshold).astype(int)
    return position


def compute_strategy_returns(price_df: pd.DataFrame, position: pd.Series) -> pd.Series:
    """Next-day open-to-open returns with position shifted by 1 to avoid look-ahead."""
    # Shift position by 1: signal today → position tomorrow
    pos_shifted = position.shift(1).fillna(0)

    if "Open" in price_df.columns:
        opens = price_df["Open"].squeeze()
        fwd_returns = opens.pct_change().shift(-1)  # open[t+1]/open[t] - 1
        strat_returns = pos_shifted * fwd_returns
    else:
        close = price_df["Close"].squeeze()
        fwd_returns = close.pct_change()
        strat_returns = pos_shifted * fwd_returns

    return strat_returns.dropna()


def compute_sharpe(returns: pd.Series, risk_free_annual: float = _RISK_FREE_ANNUAL) -> float:
    """Annualized Sharpe ratio. Returns -999.0 for degenerate cases."""
    if len(returns) < 30:
        return -999.0
    std = returns.std()
    if std == 0 or np.isnan(std):
        return -999.0
    daily_rf = risk_free_annual / 252
    excess = returns - daily_rf
    return float(excess.mean() / std * np.sqrt(252))


def backtest(price_df: pd.DataFrame, weights: dict,
             fund_rating: str = "HOLD", threshold: float = 0.3) -> float:
    """Run full backtest and return Sharpe ratio."""
    _FUND_MAP = {"BUY": 1.0, "HOLD": 0.0, "SELL": -1.0}
    fund_const = _FUND_MAP.get(fund_rating, 0.0)
    sent_const = 0.0  # sentiment cannot be backtested

    close = price_df["Close"].squeeze().dropna()
    if len(close) < 50:
        return -999.0

    tech_scores = generate_technical_signals(close)
    position = signals_to_position(tech_scores, fund_const, sent_const, weights, threshold)
    strat_returns = compute_strategy_returns(price_df, position)
    return compute_sharpe(strat_returns)
