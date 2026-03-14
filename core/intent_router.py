"""
Intent Router — Claude-powered agent selection (Point 1).

When running inside Claude Code, Claude decides which agents to run.
This module provides:
  1. A schema describing each agent (for Claude to read)
  2. A fallback keyword classifier (if running standalone without Claude)
"""

AGENT_SCHEMA = {
    "fundamental": {
        "description": "Valuation analysis — P/E, ROE, DCF, analyst targets, revenue growth. "
                       "Use when the question is about whether a stock is worth buying, "
                       "company quality, financials, or fair value.",
        "examples": ["Is AAPL undervalued?", "Should I buy MSFT?", "What are NVDA's fundamentals?"],
    },
    "technical": {
        "description": "Chart/indicator analysis — SMA, RSI, MACD, Bollinger Bands. "
                       "Use when the question is about price trends, entry/exit timing, "
                       "momentum, or chart patterns.",
        "examples": ["What's the technical outlook for TSLA?", "Is AAPL overbought?", "Good entry point for GOOGL?"],
    },
    "sentiment": {
        "description": "News and market sentiment analysis — headline sentiment, analyst upgrades/downgrades. "
                       "Use when the question is about market mood, news, catalysts, or analyst opinions.",
        "examples": ["What's the sentiment on NVDA?", "Any bad news about META?", "Are analysts bullish on AAPL?"],
    },
    "risk": {
        "description": "Risk metrics — VaR, CVaR, beta, max drawdown, volatility, position sizing. "
                       "Use when the question is about safety, risk exposure, or how much to invest.",
        "examples": ["How risky is TSLA?", "What's a safe position size for NVDA?", "Is AAPL volatile?"],
    },
    "portfolio": {
        "description": "Portfolio-level decision making — weighted signal aggregation, position sizing, "
                       "entry/target/stop prices, portfolio rebalancing based on user holdings. "
                       "Use when combining multiple signals into an actionable recommendation, "
                       "or when the user asks about their portfolio.",
        "examples": ["Build me a portfolio", "How should I allocate?", "What do you suggest I do with my holdings?"],
    },
}

ALL_AGENTS = list(AGENT_SCHEMA.keys())

# Default agent sets for common query types
DEFAULTS = {
    "full_analysis": ["fundamental", "technical", "risk", "portfolio"],
    "quick_look":    ["fundamental", "technical"],
}


def classify_intent_fallback(query: str) -> list[str]:
    """
    Keyword-based fallback — only used when running standalone (not via Claude Code).
    Claude Code should pass agents explicitly via --agents flag.
    """
    INTENT_MAP = {
        "fundamental": ["valuation", "value", "worth", "dcf", "pe", "price target",
                        "overvalued", "undervalued", "buy", "sell", "fundamental"],
        "technical":   ["chart", "technical", "trend", "signal", "entry", "exit",
                        "rsi", "macd", "moving average", "timing", "sma", "ema", "bollinger"],
        "sentiment":   ["sentiment", "news", "feeling", "opinion", "analyst",
                        "upgrade", "downgrade", "insider", "catalyst"],
        "risk":        ["risk", "volatility", "volatile", "drawdown", "var",
                        "safe", "hedge", "exposure", "position", "danger"],
        "portfolio":   ["portfolio", "allocate", "diversify", "build", "rebalance",
                        "weights", "invest", "holdings"],
    }

    q = query.lower()
    matched = [intent for intent, keywords in INTENT_MAP.items()
               if any(k in q for k in keywords)]

    # Auto-pair: buy/sell triggers both fundamental + technical
    if matched == ["fundamental"] and any(k in q for k in ["buy", "sell"]):
        matched.append("technical")

    return matched or DEFAULTS["quick_look"]
