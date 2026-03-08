import json
import os
import hashlib
import time
import requests
import yfinance as yf
import pandas as pd
from core.base_agent import BaseAgent
from core.config import CACHE_DIR, CACHE_EXPIRY_HOURS, ALPHA_VANTAGE_KEY, FMP_API_KEY
from core.rate_limiter import wait_if_needed

FMP_BASE = "https://financialmodelingprep.com/api/v3"
AV_BASE  = "https://www.alphavantage.co/query"

# Fields that go into cache (no large DataFrames)
_CACHE_EXCLUDE = {"price_df", "spy_df"}


def _safe_float(val):
    if val is None:
        return None
    try:
        f = float(val)
        return f if pd.notna(f) else None
    except (ValueError, TypeError):
        return None


class DataAgent(BaseAgent):
    def __init__(self):
        super().__init__("DataAgent")

    # ------------------------------------------------------------------ cache

    def _cache_path(self, ticker: str, source: str = "") -> str:
        key = hashlib.md5(f"{ticker}_{source}".encode()).hexdigest()
        return os.path.join(CACHE_DIR, f"{key}.json")

    def _load_cache(self, ticker: str) -> dict | None:
        # Try full-quality sources first
        for source in ["yfinance", "alpha_vantage", "financial_modeling_prep", "stooq", ""]:
            path = self._cache_path(ticker, source)
            if not os.path.exists(path):
                continue
            age_hours = (time.time() - os.path.getmtime(path)) / 3600
            if age_hours > CACHE_EXPIRY_HOURS:
                os.remove(path)
                continue
            with open(path) as f:
                return json.load(f)
        return None

    def _save_cache(self, ticker: str, data: dict):
        os.makedirs(CACHE_DIR, exist_ok=True)
        source = data.get("source", "")
        cacheable = {k: v for k, v in data.items() if k not in _CACHE_EXCLUDE}
        with open(self._cache_path(ticker, source), "w") as f:
            json.dump(cacheable, f)

    # ------------------------------------------------ price data (shared)

    def _download_prices(self, ticker: str) -> pd.DataFrame:
        """Download max available price data once. All agents use this."""
        wait_if_needed("yfinance")
        df = yf.download(ticker, period="5y", progress=False)
        if df.empty:
            return df
        # Flatten MultiIndex columns if needed
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df

    def _download_spy(self) -> pd.DataFrame:
        """Download SPY benchmark data. Used by RiskAgent."""
        wait_if_needed("yfinance")
        df = yf.download("SPY", period="5y", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df

    # --------------------------------------------------------- data sources

    def _from_yfinance(self, ticker: str, price_df: pd.DataFrame) -> dict | None:
        try:
            wait_if_needed("yfinance")
            stock = yf.Ticker(ticker)
            info = stock.info or {}
            if not info.get("regularMarketPrice") and not info.get("currentPrice"):
                return None

            return {
                "source":          "yfinance",
                "ticker":          ticker,
                "name":            info.get("longName", ticker),
                "sector":          info.get("sector", "N/A"),
                "industry":        info.get("industry", "N/A"),
                "market_cap":      info.get("marketCap"),
                "current_price":   _safe_float(info.get("currentPrice") or info.get("regularMarketPrice")),
                "52w_high":        _safe_float(info.get("fiftyTwoWeekHigh")),
                "52w_low":         _safe_float(info.get("fiftyTwoWeekLow")),
                "pe_ratio":        _safe_float(info.get("trailingPE")),
                "forward_pe":      _safe_float(info.get("forwardPE")),
                "pb_ratio":        _safe_float(info.get("priceToBook")),
                "ev_ebitda":       _safe_float(info.get("enterpriseToEbitda")),
                "roe":             _safe_float(info.get("returnOnEquity")),
                "roa":             _safe_float(info.get("returnOnAssets")),
                "debt_to_equity":  _safe_float(info.get("debtToEquity")),
                "free_cashflow":   info.get("freeCashflow"),
                "revenue_growth":  _safe_float(info.get("revenueGrowth")),
                "earnings_growth": _safe_float(info.get("earningsGrowth")),
                "dividend_yield":  _safe_float(info.get("dividendYield")),
                "beta":            _safe_float(info.get("beta")),
                "analyst_target":  _safe_float(info.get("targetMeanPrice")),
                "recommendation":  info.get("recommendationKey"),
            }
        except Exception as e:
            print(f"[DataAgent] yfinance failed for {ticker}: {e}")
            return None

    def _from_alpha_vantage(self, ticker: str) -> dict | None:
        if not ALPHA_VANTAGE_KEY:
            return None
        try:
            wait_if_needed("alpha_vantage")
            r = requests.get(f"{AV_BASE}?function=OVERVIEW&symbol={ticker}&apikey={ALPHA_VANTAGE_KEY}", timeout=10)
            data = r.json()
            if not data.get("Symbol"):
                return None

            wait_if_needed("alpha_vantage")
            price_data = requests.get(f"{AV_BASE}?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHA_VANTAGE_KEY}", timeout=10).json()
            quote = price_data.get("Global Quote", {})

            return {
                "source":          "alpha_vantage",
                "ticker":          ticker,
                "name":            data.get("Name", ticker),
                "sector":          data.get("Sector", "N/A"),
                "industry":        data.get("Industry", "N/A"),
                "market_cap":      _safe_float(data.get("MarketCapitalization")),
                "current_price":   _safe_float(quote.get("05. price")),
                "52w_high":        _safe_float(data.get("52WeekHigh")),
                "52w_low":         _safe_float(data.get("52WeekLow")),
                "pe_ratio":        _safe_float(data.get("PERatio")),
                "forward_pe":      _safe_float(data.get("ForwardPE")),
                "pb_ratio":        _safe_float(data.get("PriceToBookRatio")),
                "ev_ebitda":       _safe_float(data.get("EVToEBITDA")),
                "roe":             _safe_float(data.get("ReturnOnEquityTTM")),
                "roa":             _safe_float(data.get("ReturnOnAssetsTTM")),
                "debt_to_equity":  _safe_float(data.get("DebtToEquityRatio")),
                "free_cashflow":   _safe_float(data.get("FreeCashflow")),
                "revenue_growth":  _safe_float(data.get("QuarterlyRevenueGrowthYOY")),
                "earnings_growth": _safe_float(data.get("QuarterlyEarningsGrowthYOY")),
                "dividend_yield":  _safe_float(data.get("DividendYield")),
                "beta":            _safe_float(data.get("Beta")),
                "analyst_target":  _safe_float(data.get("AnalystTargetPrice")),
                "recommendation":  None,
            }
        except Exception as e:
            print(f"[DataAgent] Alpha Vantage failed for {ticker}: {e}")
            return None

    def _from_fmp(self, ticker: str) -> dict | None:
        api_key = FMP_API_KEY or "demo"
        if api_key == "demo":
            return None  # demo key only works for AAPL, skip
        try:
            wait_if_needed("financial_modeling_prep")
            r = requests.get(f"{FMP_BASE}/profile/{ticker}?apikey={api_key}", timeout=10)
            data = r.json()
            if not data or not isinstance(data, list):
                return None
            d = data[0]
            rng = d.get("range", "")
            return {
                "source":          "financial_modeling_prep",
                "ticker":          ticker,
                "name":            d.get("companyName", ticker),
                "sector":          d.get("sector", "N/A"),
                "industry":        d.get("industry", "N/A"),
                "market_cap":      _safe_float(d.get("mktCap")),
                "current_price":   _safe_float(d.get("price")),
                "52w_high":        _safe_float(rng.split("-")[-1].strip()) if rng else None,
                "52w_low":         _safe_float(rng.split("-")[0].strip()) if rng else None,
                "pe_ratio":        None,
                "forward_pe":      None,
                "pb_ratio":        None,
                "ev_ebitda":       None,
                "roe":             _safe_float(d.get("roe")),
                "roa":             None,
                "debt_to_equity":  None,
                "free_cashflow":   None,
                "revenue_growth":  None,
                "earnings_growth": None,
                "dividend_yield":  None,
                "beta":            _safe_float(d.get("beta")),
                "analyst_target":  None,
                "recommendation":  None,
            }
        except Exception as e:
            print(f"[DataAgent] FMP failed for {ticker}: {e}")
            return None

    def _from_stooq(self, ticker: str) -> dict | None:
        try:
            import pandas_datareader.data as web
            wait_if_needed("stooq")
            df = web.DataReader(ticker, "stooq")
            if df.empty:
                return None
            return {
                "source":          "stooq",
                "ticker":          ticker,
                "name":            ticker,
                "sector":          "N/A",
                "industry":        "N/A",
                "market_cap":      None,
                "current_price":   float(df["Close"].iloc[0]),
                "52w_high":        float(df["High"].max()),
                "52w_low":         float(df["Low"].min()),
                "pe_ratio":        None,
                "forward_pe":      None,
                "pb_ratio":        None,
                "ev_ebitda":       None,
                "roe":             None,
                "roa":             None,
                "debt_to_equity":  None,
                "free_cashflow":   None,
                "revenue_growth":  None,
                "earnings_growth": None,
                "dividend_yield":  None,
                "beta":            None,
                "analyst_target":  None,
                "recommendation":  None,
            }
        except Exception as e:
            print(f"[DataAgent] Stooq failed for {ticker}: {e}")
            return None

    # ------------------------------------------------- fallback orchestration

    _SOURCES = ["_from_yfinance", "_from_alpha_vantage", "_from_fmp", "_from_stooq"]

    def _fetch_fundamentals(self, ticker: str, price_df: pd.DataFrame) -> dict:
        cached = self._load_cache(ticker)
        if cached:
            print(f"[DataAgent] Loaded {ticker} from cache (source: {cached.get('source')}).")
            return cached

        for method_name in self._SOURCES:
            source = method_name.replace("_from_", "")
            print(f"[DataAgent] Trying {source} for {ticker}...")
            if method_name == "_from_yfinance":
                result = self._from_yfinance(ticker, price_df)
            else:
                result = getattr(self, method_name)(ticker)
            if result:
                print(f"[DataAgent] Got data from {source}.")
                self._save_cache(ticker, result)
                return result

        raise RuntimeError(
            f"All data sources failed for {ticker}. "
            "Check your API keys in .env or try again later."
        )

    # --------------------------------------------------------------- run

    def run(self, ticker: str, **kwargs) -> dict:
        try:
            # Validate ticker
            ticker = ticker.upper().strip()
            if not ticker.isalpha() or len(ticker) > 5:
                return self._error(ticker, f"Invalid ticker format: '{ticker}'")

            # Download price data ONCE — shared with all agents
            t = time.time()
            print(f"  Downloading {ticker} price data (5yr)...")
            price_df = self._download_prices(ticker)
            if price_df.empty:
                return self._error(ticker, f"No price data found for {ticker}")
            print(f"  {ticker} prices: {len(price_df)} rows ({time.time()-t:.1f}s)")

            t = time.time()
            print(f"  Downloading SPY benchmark...")
            spy_df = self._download_spy()
            print(f"  SPY prices: {len(spy_df)} rows ({time.time()-t:.1f}s)")

            # Fetch fundamental data
            t = time.time()
            fundamentals = self._fetch_fundamentals(ticker, price_df)
            print(f"  Fundamentals: done ({time.time()-t:.1f}s)")

            # Attach DataFrames (not cached, but passed to other agents)
            fundamentals["price_df"] = price_df
            fundamentals["spy_df"] = spy_df

            return self._result(ticker=ticker, data=fundamentals)

        except Exception as e:
            return self._error(ticker, str(e))
