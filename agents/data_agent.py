import json
import os
import hashlib
import time
import requests
import yfinance as yf
from core.base_agent import BaseAgent
from core.config import CACHE_DIR, CACHE_EXPIRY_HOURS, ALPHA_VANTAGE_KEY, FRED_API_KEY
from core.rate_limiter import wait_if_needed

FMP_BASE = "https://financialmodelingprep.com/api/v3"
AV_BASE  = "https://www.alphavantage.co/query"


class DataAgent(BaseAgent):
    def __init__(self):
        super().__init__("DataAgent")

    # ------------------------------------------------------------------ cache

    def _cache_path(self, ticker: str) -> str:
        key = hashlib.md5(ticker.encode()).hexdigest()
        return os.path.join(CACHE_DIR, f"{key}.json")

    def _load_cache(self, ticker: str) -> dict | None:
        path = self._cache_path(ticker)
        if not os.path.exists(path):
            return None
        age_hours = (time.time() - os.path.getmtime(path)) / 3600
        if age_hours > CACHE_EXPIRY_HOURS:
            return None
        with open(path) as f:
            return json.load(f)

    def _save_cache(self, ticker: str, data: dict):
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(self._cache_path(ticker), "w") as f:
            json.dump(data, f)

    # --------------------------------------------------------- data sources

    def _from_yfinance(self, ticker: str) -> dict | None:
        """Primary source. Free, no key needed."""
        try:
            wait_if_needed("yfinance")
            stock = yf.Ticker(ticker)
            info = stock.info or {}
            if not info.get("regularMarketPrice") and not info.get("currentPrice"):
                return None  # invalid ticker or no data
            hist = stock.history(period="1y")
            return {
                "source": "yfinance",
                "ticker": ticker,
                "name": info.get("longName", ticker),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "market_cap": info.get("marketCap"),
                "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "pb_ratio": info.get("priceToBook"),
                "ev_ebitda": info.get("enterpriseToEbitda"),
                "roe": info.get("returnOnEquity"),
                "roa": info.get("returnOnAssets"),
                "debt_to_equity": info.get("debtToEquity"),
                "free_cashflow": info.get("freeCashflow"),
                "revenue_growth": info.get("revenueGrowth"),
                "earnings_growth": info.get("earningsGrowth"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
                "analyst_target": info.get("targetMeanPrice"),
                "recommendation": info.get("recommendationKey"),
                "price_history_csv": hist["Close"].tail(252).to_csv() if not hist.empty else "",
            }
        except Exception as e:
            print(f"[DataAgent] yfinance failed for {ticker}: {e}")
            return None

    def _from_alpha_vantage(self, ticker: str) -> dict | None:
        """Fallback 1. Requires ALPHA_VANTAGE_KEY."""
        if not ALPHA_VANTAGE_KEY:
            return None
        try:
            wait_if_needed("alpha_vantage")
            overview_url = (
                f"{AV_BASE}?function=OVERVIEW&symbol={ticker}&apikey={ALPHA_VANTAGE_KEY}"
            )
            r = requests.get(overview_url, timeout=10)
            data = r.json()
            if not data.get("Symbol"):
                return None

            wait_if_needed("alpha_vantage")
            price_url = (
                f"{AV_BASE}?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHA_VANTAGE_KEY}"
            )
            price_data = requests.get(price_url, timeout=10).json()
            quote = price_data.get("Global Quote", {})

            return {
                "source": "alpha_vantage",
                "ticker": ticker,
                "name": data.get("Name", ticker),
                "sector": data.get("Sector", "N/A"),
                "industry": data.get("Industry", "N/A"),
                "market_cap": data.get("MarketCapitalization"),
                "current_price": quote.get("05. price"),
                "52w_high": data.get("52WeekHigh"),
                "52w_low": data.get("52WeekLow"),
                "pe_ratio": data.get("PERatio"),
                "forward_pe": data.get("ForwardPE"),
                "pb_ratio": data.get("PriceToBookRatio"),
                "ev_ebitda": data.get("EVToEBITDA"),
                "roe": data.get("ReturnOnEquityTTM"),
                "roa": data.get("ReturnOnAssetsTTM"),
                "debt_to_equity": data.get("DebtToEquityRatio"),
                "free_cashflow": data.get("FreeCashflow"),
                "revenue_growth": data.get("QuarterlyRevenueGrowthYOY"),
                "earnings_growth": data.get("QuarterlyEarningsGrowthYOY"),
                "dividend_yield": data.get("DividendYield"),
                "beta": data.get("Beta"),
                "analyst_target": data.get("AnalystTargetPrice"),
                "recommendation": None,
                "price_history_csv": "",
            }
        except Exception as e:
            print(f"[DataAgent] Alpha Vantage failed for {ticker}: {e}")
            return None

    def _from_fmp(self, ticker: str) -> dict | None:
        """Fallback 2. Free tier: 250 calls/day."""
        try:
            wait_if_needed("financial_modeling_prep")
            url = f"{FMP_BASE}/profile/{ticker}?apikey=demo"
            r = requests.get(url, timeout=10)
            data = r.json()
            if not data or not isinstance(data, list):
                return None
            d = data[0]

            return {
                "source": "financial_modeling_prep",
                "ticker": ticker,
                "name": d.get("companyName", ticker),
                "sector": d.get("sector", "N/A"),
                "industry": d.get("industry", "N/A"),
                "market_cap": d.get("mktCap"),
                "current_price": d.get("price"),
                "52w_high": d.get("range", "").split("-")[-1].strip() if d.get("range") else None,
                "52w_low": d.get("range", "").split("-")[0].strip() if d.get("range") else None,
                "pe_ratio": None,
                "forward_pe": None,
                "pb_ratio": None,
                "ev_ebitda": None,
                "roe": d.get("roe"),
                "roa": None,
                "debt_to_equity": None,
                "free_cashflow": None,
                "revenue_growth": None,
                "earnings_growth": None,
                "dividend_yield": None,
                "beta": d.get("beta"),
                "analyst_target": None,
                "recommendation": None,
                "price_history_csv": "",
            }
        except Exception as e:
            print(f"[DataAgent] FMP failed for {ticker}: {e}")
            return None

    def _from_stooq(self, ticker: str) -> dict | None:
        """Fallback 3. No API key needed. Price data only."""
        try:
            import pandas_datareader.data as web
            wait_if_needed("stooq")
            df = web.DataReader(ticker, "stooq")
            if df.empty:
                return None
            current_price = float(df["Close"].iloc[0])
            return {
                "source": "stooq",
                "ticker": ticker,
                "name": ticker,
                "sector": "N/A",
                "industry": "N/A",
                "market_cap": None,
                "current_price": current_price,
                "52w_high": float(df["High"].max()),
                "52w_low": float(df["Low"].min()),
                "pe_ratio": None,
                "forward_pe": None,
                "pb_ratio": None,
                "ev_ebitda": None,
                "roe": None,
                "roa": None,
                "debt_to_equity": None,
                "free_cashflow": None,
                "revenue_growth": None,
                "earnings_growth": None,
                "dividend_yield": None,
                "beta": None,
                "analyst_target": None,
                "recommendation": None,
                "price_history_csv": df["Close"].tail(252).to_csv(),
            }
        except Exception as e:
            print(f"[DataAgent] Stooq failed for {ticker}: {e}")
            return None

    # ------------------------------------------------- fallback orchestration

    SOURCES = [
        ("yfinance",               "_from_yfinance"),
        ("alpha_vantage",          "_from_alpha_vantage"),
        ("financial_modeling_prep","_from_fmp"),
        ("stooq",                  "_from_stooq"),
    ]

    def _fetch(self, ticker: str) -> dict:
        cached = self._load_cache(ticker)
        if cached:
            print(f"[DataAgent] Loaded {ticker} from cache (source: {cached.get('source')}).")
            return cached

        for source_name, method_name in self.SOURCES:
            print(f"[DataAgent] Trying {source_name} for {ticker}...")
            result = getattr(self, method_name)(ticker)
            if result:
                print(f"[DataAgent] Got data from {source_name}.")
                self._save_cache(ticker, result)
                return result

        raise RuntimeError(
            f"All data sources failed for {ticker}. "
            "Check your API keys in .env or try again later."
        )

    # --------------------------------------------------------------- run

    def run(self, ticker: str, **kwargs) -> dict:
        try:
            raw = self._fetch(ticker)
            return self._result(ticker=ticker, data=raw)
        except Exception as e:
            return self._error(ticker, str(e))
