import numpy as np
import yfinance as yf
from core.base_agent import BaseAgent
from core.config import BACKTEST_START, BACKTEST_END, INITIAL_CAPITAL, TRANSACTION_COST
from core.rate_limiter import wait_if_needed


class BacktestAgent(BaseAgent):
    def __init__(self):
        super().__init__("BacktestAgent")

    def run(self, ticker: str, **kwargs) -> dict:
        try:
            wait_if_needed("yfinance")
            df     = yf.download(ticker, start=BACKTEST_START, end=BACKTEST_END, progress=False)
            closes = df["Close"].squeeze()

            sma50  = closes.rolling(50).mean()
            sma200 = closes.rolling(200).mean()

            # Signal: 1 = long, 0 = cash. Shift 1 to avoid look-ahead bias.
            signal  = (sma50 > sma200).astype(int).shift(1)
            returns = closes.pct_change()

            strat_ret = signal * returns - TRANSACTION_COST * signal.diff().abs()
            equity    = (1 + strat_ret).cumprod() * INITIAL_CAPITAL
            bh_equity = (1 + returns).cumprod() * INITIAL_CAPITAL

            total_ret  = float(equity.iloc[-1] / INITIAL_CAPITAL - 1)
            bh_ret     = float(bh_equity.iloc[-1] / INITIAL_CAPITAL - 1)
            n_years    = len(closes) / 252
            ann_ret    = float((1 + total_ret) ** (1 / n_years) - 1)

            dr         = strat_ret.dropna()
            sharpe     = float(dr.mean() / dr.std() * np.sqrt(252))
            down       = dr[dr < 0].std()
            sortino    = float(dr.mean() / down * np.sqrt(252)) if down > 0 else 0

            roll_max   = equity.cummax()
            max_dd     = float(((equity - roll_max) / roll_max).min())

            trades     = int(signal.diff().abs().sum())
            win_trades = (strat_ret[signal.diff() != 0] > 0).sum()
            win_rate   = float(win_trades / trades) if trades > 0 else 0

            alpha      = round(total_ret - bh_ret, 4)

            return self._result(ticker, {
                "strategy":             "SMA 50/200 Golden Cross",
                "period":               f"{BACKTEST_START} to {BACKTEST_END}",
                "initial_capital":      INITIAL_CAPITAL,
                "final_value":          round(float(equity.iloc[-1]), 2),
                "total_return":         round(total_ret, 4),
                "annualized_return":    round(ann_ret, 4),
                "buy_and_hold_return":  round(bh_ret, 4),
                "alpha_vs_bh":          alpha,
                "sharpe_ratio":         round(sharpe, 4),
                "sortino_ratio":        round(sortino, 4),
                "max_drawdown":         round(max_dd, 4),
                "number_of_trades":     trades,
                "win_rate":             round(win_rate, 4),
                "verdict":              "PROMISING" if sharpe > 1 and alpha > 0 else
                                        "MARGINAL"  if sharpe > 0.5 else "POOR",
            })

        except Exception as e:
            return self._error(ticker, str(e))
