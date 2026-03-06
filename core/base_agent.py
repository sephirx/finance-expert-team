from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """
    Base class for all agents.
    Agents are pure data processors — no LLM calls.
    They fetch, compute, and return structured data.
    Claude Code reads the output and does the analysis.
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def run(self, ticker: str, **kwargs) -> dict[str, Any]:
        """
        Each agent implements this.
        Returns a dict with:
          - agent: str
          - ticker: str
          - data: dict  (structured numbers and facts)
          - error: str | None
        """
        pass

    def _result(self, ticker: str, data: dict, error: str = None) -> dict:
        return {
            "agent": self.name,
            "ticker": ticker,
            "data": data,
            "error": error,
        }

    def _error(self, ticker: str, message: str) -> dict:
        return self._result(ticker=ticker, data={}, error=message)
