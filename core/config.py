import os
from datetime import date
from dotenv import load_dotenv

load_dotenv()

# Optional API keys for fallback data sources
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")
FMP_API_KEY       = os.getenv("FMP_API_KEY", "")
FRED_API_KEY      = os.getenv("FRED_API_KEY", "")
NEWS_API_KEY      = os.getenv("NEWS_API_KEY", "")

# Cache
CACHE_DIR          = os.path.join(os.path.dirname(__file__), "..", "data", "cache")
CACHE_EXPIRY_HOURS = 6

# Agent weights for portfolio scoring
SIGNAL_WEIGHTS = {
    "fundamental": 0.40,
    "technical":   0.35,
    "sentiment":   0.25,
}

# Risk limits
MAX_POSITION_SIZE = 0.20   # max 20% of portfolio in one stock

# Backtesting
BACKTEST_START   = "2020-01-01"
BACKTEST_END     = date.today().isoformat()
INITIAL_CAPITAL  = 100_000
TRANSACTION_COST = 0.001   # 0.1% per trade
