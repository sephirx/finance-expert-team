"""
Memory Manager — persistent analysis history (Point 5).

Stores past analysis results so the system can reference prior signals,
track recommendation accuracy, and provide historical context.
Capped at 200 records to keep things bounded.
"""

import json
import os
from datetime import date

from core.config import ANALYSIS_HISTORY_PATH, DATA_DIR
from memory.schemas import AnalysisRecord

MAX_RECORDS = 200


class MemoryManager:
    def __init__(self, path: str = ANALYSIS_HISTORY_PATH):
        self._path = path
        self._records = self._load()

    def _load(self) -> list[AnalysisRecord]:
        if os.path.exists(self._path):
            with open(self._path) as f:
                data = json.load(f)
                return [AnalysisRecord.from_dict(r) for r in data]
        return []

    def _save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            json.dump([r.to_dict() for r in self._records], f, indent=2)

    def record_analysis(
        self,
        ticker: str,
        team_signal: str,
        team_grade: str,
        fundamental_signal: str = "N/A",
        technical_signal: str = "N/A",
        sentiment_signal: str = "N/A",
        price_at_analysis: float | None = None,
        query: str = "",
    ):
        record = AnalysisRecord(
            ticker=ticker.upper().strip(),
            date=date.today().isoformat(),
            team_signal=team_signal,
            team_grade=team_grade,
            fundamental_signal=fundamental_signal,
            technical_signal=technical_signal,
            sentiment_signal=sentiment_signal,
            price_at_analysis=price_at_analysis,
            query=query,
        )
        self._records.append(record)
        # Cap at MAX_RECORDS — remove oldest
        if len(self._records) > MAX_RECORDS:
            self._records = self._records[-MAX_RECORDS:]
        self._save()

    def get_history(self, ticker: str) -> list[AnalysisRecord]:
        ticker = ticker.upper().strip()
        return [r for r in self._records if r.ticker == ticker]

    def get_recent(self, n: int = 10) -> list[AnalysisRecord]:
        return self._records[-n:]

    def get_last_analysis(self, ticker: str) -> AnalysisRecord | None:
        history = self.get_history(ticker)
        return history[-1] if history else None

    def summary(self) -> dict:
        tickers = set(r.ticker for r in self._records)
        return {
            "total_analyses": len(self._records),
            "unique_tickers": len(tickers),
            "tickers_analyzed": sorted(tickers),
            "recent": [r.to_dict() for r in self._records[-5:]],
        }
