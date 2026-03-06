import numpy as np
from core.base_agent import BaseAgent
from core.config import BACKTEST_START, BACKTEST_END, INITIAL_CAPITAL, TRANSACTION_COST


class BacktestAgent(BaseAgent):
    def __init__(self):
        super().__init__("BacktestAgent")

    def run(self, ticker: str, **kwargs) -> dict:
        try:
            price_df = kwargs.get("price_df")
            if price_df is None or price_df.empty:
                return self._error(ticker, "No price data provided to BacktestAgent.")

            closes = price_df["Close"].squeeze().dropna()
            # Filter to backtest window
            closes = closes.loc[BACKTEST_START:BACKTEST_END]
            if len(closes) < 201:
                return self._error(ticker, f"Only {len(closes)} data points in backtest window — need 201+.")

            sma50 = closes.rolling(50).mean()
            sma200 = closes.rolling(200).mean()

            # Signal: 1 = long, 0 = cash. Shift to avoid look-ahead bias.
            signal = (sma50 > sma200).astype(int).shift(1)
            returns = closes.pct_change()

            # Calculate strategy returns — fillna(0) to prevent NaN cumprod
            trade_cost = TRANSACTION_COST * signal.diff().abs()
            strat_ret = (signal * returns - trade_cost).fillna(0)
            bh_ret = returns.fillna(0)

            equity = (1 + strat_ret).cumprod() * INITIAL_CAPITAL
            bh_equity = (1 + bh_ret).cumprod() * INITIAL_CAPITAL

            total_ret = float(equity.iloc[-1] / INITIAL_CAPITAL - 1)
            bh_return = float(bh_equity.iloc[-1] / INITIAL_CAPITAL - 1)
            n_years = len(closes) / 252
            ann_ret = float((1 + total_ret) ** (1 / n_years) - 1) if n_years > 0 else 0

            dr = strat_ret[strat_ret != 0]
            std = dr.std()
            sharpe = float(dr.mean() / std * np.sqrt(252)) if std > 0 else 0
            down = dr[dr < 0]
            down_std = down.std() if len(down) > 1 else 0
            sortino = float(dr.mean() / down_std * np.sqrt(252)) if down_std > 0 else 0

            roll_max = equity.cummax()
            max_dd = float(((equity - roll_max) / roll_max).min())

            trades = int(signal.diff().abs().sum())
            win_trades = int((strat_ret[signal.diff().abs() == 1] > 0).sum())
            win_rate = round(win_trades / trades, 4) if trades > 0 else 0

            alpha = round(total_ret - bh_return, 4)

            if sharpe > 1 and alpha > 0:   verdict = "PROMISING"
            elif sharpe > 0.5:             verdict = "MARGINAL"
            else:                          verdict = "POOR"

            return self._result(ticker, {
                "strategy":            "SMA 50/200 Golden Cross",
                "period":              f"{BACKTEST_START} to {BACKTEST_END}",
                "initial_capital":     INITIAL_CAPITAL,
                "final_value":         round(float(equity.iloc[-1]), 2),
                "total_return":        round(total_ret, 4),
                "annualized_return":   round(ann_ret, 4),
                "buy_and_hold_return": round(bh_return, 4),
                "alpha_vs_bh":         alpha,
                "sharpe_ratio":        round(sharpe, 4),
                "sortino_ratio":       round(sortino, 4),
                "max_drawdown":        round(max_dd, 4),
                "number_of_trades":    trades,
                "win_rate":            round(win_rate, 4),
                "verdict":             verdict,
            })

        except Exception as e:
            return self._error(ticker, str(e))
