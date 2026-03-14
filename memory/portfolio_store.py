"""
Portfolio Store — persistent portfolio state (Point 5).

Stores broker info, holdings, cash, watchlist, and user preferences.
Reads/writes to data/portfolio_state.json.
"""

import json
import os
from datetime import date

from core.config import PORTFOLIO_STATE_PATH, DATA_DIR
from memory.schemas import PortfolioState, Holding, UserPreferences


class PortfolioStore:
    def __init__(self, path: str = PORTFOLIO_STATE_PATH):
        self._path = path
        self._state = self._load()

    def _load(self) -> PortfolioState:
        if os.path.exists(self._path):
            with open(self._path) as f:
                return PortfolioState.from_dict(json.load(f))
        return PortfolioState()

    def save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(self._state.to_dict(), f, indent=2)

    @property
    def state(self) -> PortfolioState:
        return self._state

    # ---- Holdings ----

    def add_holding(self, ticker: str, shares: float, avg_cost: float):
        ticker = ticker.upper().strip()
        # If already held, average in
        for h in self._state.holdings:
            if h.ticker == ticker:
                total_shares = h.shares + shares
                h.avg_cost = round(
                    (h.avg_cost * h.shares + avg_cost * shares) / total_shares, 4
                )
                h.shares = total_shares
                self.save()
                return
        self._state.holdings.append(
            Holding(ticker=ticker, shares=shares, avg_cost=avg_cost,
                    date_added=date.today().isoformat())
        )
        self.save()

    def remove_holding(self, ticker: str, shares: float | None = None):
        ticker = ticker.upper().strip()
        for i, h in enumerate(self._state.holdings):
            if h.ticker == ticker:
                if shares is None or shares >= h.shares:
                    self._state.holdings.pop(i)
                else:
                    h.shares -= shares
                self.save()
                return True
        return False

    def get_holding(self, ticker: str) -> Holding | None:
        ticker = ticker.upper().strip()
        for h in self._state.holdings:
            if h.ticker == ticker:
                return h
        return None

    def get_all_holdings(self) -> list[Holding]:
        return self._state.holdings

    # ---- Broker / Preferences ----

    def set_broker(self, broker: str):
        self._state.broker = broker
        self.save()

    def set_cash(self, amount: float):
        self._state.cash_balance = amount
        self.save()

    def set_preferences(self, **kwargs):
        prefs = self._state.preferences
        for k, v in kwargs.items():
            if hasattr(prefs, k):
                setattr(prefs, k, v)
        self.save()

    # ---- Watchlist ----

    def add_to_watchlist(self, ticker: str):
        ticker = ticker.upper().strip()
        if ticker not in self._state.watchlist:
            self._state.watchlist.append(ticker)
            self.save()

    def remove_from_watchlist(self, ticker: str):
        ticker = ticker.upper().strip()
        if ticker in self._state.watchlist:
            self._state.watchlist.remove(ticker)
            self.save()

    # ---- Portfolio metrics ----

    def total_invested(self) -> float:
        return sum(h.shares * h.avg_cost for h in self._state.holdings)

    def portfolio_value(self, current_prices: dict[str, float]) -> float:
        value = self._state.cash_balance
        for h in self._state.holdings:
            price = current_prices.get(h.ticker, h.avg_cost)
            value += h.shares * price
        return round(value, 2)

    def sector_exposure(self, sector_map: dict[str, str], current_prices: dict[str, float]) -> dict[str, float]:
        """Returns {sector: pct_of_portfolio}."""
        total = self.portfolio_value(current_prices)
        if total <= 0:
            return {}
        exposure: dict[str, float] = {}
        for h in self._state.holdings:
            sector = sector_map.get(h.ticker, "Unknown")
            price = current_prices.get(h.ticker, h.avg_cost)
            value = h.shares * price
            exposure[sector] = exposure.get(sector, 0) + value
        return {s: round(v / total * 100, 1) for s, v in exposure.items()}

    def position_pct(self, ticker: str, current_prices: dict[str, float]) -> float:
        """What % of portfolio does this ticker represent?"""
        total = self.portfolio_value(current_prices)
        if total <= 0:
            return 0.0
        h = self.get_holding(ticker)
        if not h:
            return 0.0
        price = current_prices.get(ticker, h.avg_cost)
        return round(h.shares * price / total * 100, 1)

    def summary(self) -> dict:
        return {
            "broker": self._state.broker,
            "currency": self._state.currency,
            "cash_balance": self._state.cash_balance,
            "num_holdings": len(self._state.holdings),
            "total_invested": round(self.total_invested(), 2),
            "watchlist": self._state.watchlist,
            "preferences": self._state.preferences.to_dict(),
            "holdings": [
                {"ticker": h.ticker, "shares": h.shares, "avg_cost": h.avg_cost}
                for h in self._state.holdings
            ],
        }
