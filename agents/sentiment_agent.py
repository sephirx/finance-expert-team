import requests
from core.base_agent import BaseAgent
from core.config import ALPHA_VANTAGE_KEY, NEWS_API_KEY
from core.rate_limiter import wait_if_needed

AV_BASE   = "https://www.alphavantage.co/query"
NEWS_BASE = "https://newsapi.org/v2/everything"


class SentimentAgent(BaseAgent):
    def __init__(self):
        super().__init__("SentimentAgent")

    def _fetch_av_news(self, ticker: str) -> list[dict]:
        if not ALPHA_VANTAGE_KEY:
            return []
        try:
            wait_if_needed("alpha_vantage")
            url  = f"{AV_BASE}?function=NEWS_SENTIMENT&tickers={ticker}&limit=10&apikey={ALPHA_VANTAGE_KEY}"
            data = requests.get(url, timeout=10).json()
            return [
                {
                    "title":     item.get("title"),
                    "source":    item.get("source"),
                    "sentiment": item.get("overall_sentiment_label", "unknown"),
                    "score":     item.get("overall_sentiment_score", 0),
                }
                for item in data.get("feed", [])[:10]
            ]
        except Exception:
            return []

    def _fetch_newsapi(self, ticker: str) -> list[dict]:
        if not NEWS_API_KEY:
            return []
        try:
            url  = f"{NEWS_BASE}?q={ticker}&pageSize=10&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
            data = requests.get(url, timeout=10).json()
            return [
                {
                    "title":     a.get("title"),
                    "source":    a.get("source", {}).get("name"),
                    "sentiment": "unknown",
                    "score":     0,
                }
                for a in data.get("articles", [])[:10]
            ]
        except Exception:
            return []

    def run(self, ticker: str, **kwargs) -> dict:
        if not ticker or not isinstance(ticker, str):
            return self._error(str(ticker), "Invalid ticker for SentimentAgent.")
        if not isinstance(ticker, str) or len(ticker) > 10:
            return self._error(ticker, "Ticker format invalid for SentimentAgent.")

        try:
            news = self._fetch_av_news(ticker) or self._fetch_newsapi(ticker)

            # Aggregate sentiment score
            scored = [n for n in news if n.get("score") != 0]
            avg_score = round(sum(n["score"] for n in scored) / len(scored), 4) if scored else None

            positive = sum(1 for n in news if "Positive" in str(n.get("sentiment", "")))
            negative = sum(1 for n in news if "Negative" in str(n.get("sentiment", "")))
            neutral  = len(news) - positive - negative

            if avg_score is not None:
                if avg_score > 0.15:   overall = "POSITIVE"
                elif avg_score < -0.15: overall = "NEGATIVE"
                else:                   overall = "NEUTRAL"
            elif positive > negative:   overall = "POSITIVE"
            elif negative > positive:   overall = "NEGATIVE"
            else:                       overall = "NEUTRAL"

            return self._result(ticker, {
                "overall_sentiment":  overall,
                "avg_sentiment_score": avg_score,
                "positive_count":     positive,
                "negative_count":     negative,
                "neutral_count":      neutral,
                "total_articles":     len(news),
                "headlines":          [n["title"] for n in news[:5] if n.get("title")],
                "data_source":        "alpha_vantage" if ALPHA_VANTAGE_KEY else ("newsapi" if NEWS_API_KEY else "none"),
                "note":               "No news API key configured." if not news else None,
            })

        except Exception as e:
            return self._error(ticker, str(e))
