import os
from dotenv import load_dotenv

load_dotenv()

# API keys
FINANCIAL_DATASETS_API_KEY = os.getenv("FINANCIAL_DATASETS_API_KEY", "")
ALPHA_VANTAGE_KEY          = os.getenv("ALPHA_VANTAGE_KEY", "")
NEWS_API_KEY               = os.getenv("NEWS_API_KEY", "")

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

# Data paths
DATA_DIR           = os.path.join(os.path.dirname(__file__), "..", "data")
PORTFOLIO_STATE_PATH   = os.path.join(DATA_DIR, "portfolio_state.json")
ANALYSIS_HISTORY_PATH  = os.path.join(DATA_DIR, "analysis_history.json")

# Reports
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")

# financialdatasets.ai
FDS_BASE_URL = "https://api.financialdatasets.ai"
