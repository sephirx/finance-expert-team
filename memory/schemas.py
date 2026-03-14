"""
Data schemas for the memory system.
Plain dataclasses — no external dependencies.
"""

from dataclasses import dataclass, field, asdict
from datetime import date


@dataclass
class Holding:
    ticker: str
    shares: float
    avg_cost: float
    date_added: str = field(default_factory=lambda: date.today().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Holding":
        return cls(**d)


@dataclass
class UserPreferences:
    risk_tolerance: str = "moderate"       # conservative, moderate, aggressive
    investment_horizon: str = "long_term"  # short_term, medium_term, long_term
    style: str = "value"                   # value, growth, balanced, income
    max_position_pct: float = 20.0         # max % of portfolio in one stock
    sectors_to_avoid: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "UserPreferences":
        return cls(**d)


@dataclass
class PortfolioState:
    broker: str = ""
    currency: str = "USD"
    cash_balance: float = 0.0
    holdings: list[Holding] = field(default_factory=list)
    watchlist: list[str] = field(default_factory=list)
    preferences: UserPreferences = field(default_factory=UserPreferences)

    def to_dict(self) -> dict:
        return {
            "broker": self.broker,
            "currency": self.currency,
            "cash_balance": self.cash_balance,
            "holdings": [h.to_dict() for h in self.holdings],
            "watchlist": self.watchlist,
            "preferences": self.preferences.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PortfolioState":
        holdings = [Holding.from_dict(h) for h in d.get("holdings", [])]
        prefs = UserPreferences.from_dict(d.get("preferences", {}))
        return cls(
            broker=d.get("broker", ""),
            currency=d.get("currency", "USD"),
            cash_balance=d.get("cash_balance", 0.0),
            holdings=holdings,
            watchlist=d.get("watchlist", []),
            preferences=prefs,
        )


@dataclass
class AnalysisRecord:
    ticker: str
    date: str
    team_signal: str
    team_grade: str
    fundamental_signal: str = "N/A"
    technical_signal: str = "N/A"
    sentiment_signal: str = "N/A"
    price_at_analysis: float | None = None
    query: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "AnalysisRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
