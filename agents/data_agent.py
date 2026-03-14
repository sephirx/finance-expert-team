"""
DataAgent — fetches market data from financialdatasets.ai (Point 2).

Primary: financialdatasets.ai REST API (fundamentals + price history)
Fallback: yfinance (price data only, if API key missing)
"""

import json
import os
import hashlib
import time
import requests
import pandas as pd
from core.base_agent import BaseAgent
from core.config import (
    CACHE_DIR, CACHE_EXPIRY_HOURS,
    FINANCIAL_DATASETS_API_KEY, FDS_BASE_URL,
)
from core.rate_limiter import wait_if_needed
from core.data_normalizer import normalize_financialdatasets, compute_data_quality

_CACHE_EXCLUDE = {"price_df", "spy_df", "data_quality"}


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

    def _cache_path(self, ticker: str) -> str:
        key = hashlib.md5(f"{ticker}_fds".encode()).hexdigest()
        return os.path.join(CACHE_DIR, f"{key}.json")

    def _load_cache(self, ticker: str) -> dict | None:
        path = self._cache_path(ticker)
        if not os.path.exists(path):
            return None
        age_hours = (time.time() - os.path.getmtime(path)) / 3600
        if age_hours > CACHE_EXPIRY_HOURS:
            os.remove(path)
            return None
        with open(path) as f:
            return json.load(f)

    def _save_cache(self, ticker: str, data: dict):
        os.makedirs(CACHE_DIR, exist_ok=True)
        cacheable = {k: v for k, v in data.items() if k not in _CACHE_EXCLUDE}
        with open(self._cache_path(ticker), "w") as f:
            json.dump(cacheable, f)

    # ------------------------------------------------ API helpers

    def _fds_headers(self) -> dict:
        return {"X-API-KEY": FINANCIAL_DATASETS_API_KEY}

    def _fds_get(self, endpoint: str, params: dict) -> dict | None:
        """Make a GET request to financialdatasets.ai."""
        wait_if_needed("financialdatasets")
        url = f"{FDS_BASE_URL}{endpoint}"
        try:
            r = requests.get(url, params=params, headers=self._fds_headers(), timeout=15)
            if r.status_code == 200:
                return r.json()
            print(f"[DataAgent] FDS {endpoint} returned {r.status_code}")
            return None
        except Exception as e:
            print(f"[DataAgent] FDS {endpoint} error: {e}")
            return None

    # ------------------------------------------------ price data

    def _download_prices_fds(self, ticker: str) -> pd.DataFrame:
        """Download price history from financialdatasets.ai."""
        data = self._fds_get("/prices/historical", {
            "ticker": ticker,
            "interval": "day",
            "interval_multiplier": 1,
            "start_date": "2020-01-01",
        })
        if not data or "prices" not in data:
            return pd.DataFrame()

        prices = data["prices"]
        if not prices:
            return pd.DataFrame()

        df = pd.DataFrame(prices)
        # Map columns to standard OHLCV format
        col_map = {}
        for col in df.columns:
            cl = col.lower()
            if "open" in cl: col_map[col] = "Open"
            elif "high" in cl: col_map[col] = "High"
            elif "low" in cl: col_map[col] = "Low"
            elif "close" in cl and "adj" not in cl: col_map[col] = "Close"
            elif "volume" in cl: col_map[col] = "Volume"
            elif "date" in cl or "time" in cl: col_map[col] = "Date"
        df = df.rename(columns=col_map)

        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date").sort_index()

        return df

    def _download_prices_yfinance(self, ticker: str) -> pd.DataFrame:
        """Fallback: download prices from yfinance."""
        try:
            import yfinance as yf
            df = yf.download(ticker, period="5y", progress=False)
            if df.empty:
                return df
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except Exception as e:
            print(f"[DataAgent] yfinance fallback failed: {e}")
            return pd.DataFrame()

    def _download_prices(self, ticker: str) -> pd.DataFrame:
        """Download prices — try financialdatasets.ai first, fallback to yfinance."""
        if FINANCIAL_DATASETS_API_KEY:
            df = self._download_prices_fds(ticker)
            if not df.empty:
                return df
            print("[DataAgent] FDS prices empty, falling back to yfinance...")

        return self._download_prices_yfinance(ticker)

    def _download_spy(self) -> pd.DataFrame:
        """Download SPY benchmark data."""
        if FINANCIAL_DATASETS_API_KEY:
            df = self._download_prices_fds("SPY")
            if not df.empty:
                return df

        return self._download_prices_yfinance("SPY")

    # ------------------------------------------------ fundamental data

    def _fetch_fds_fundamentals(self, ticker: str) -> dict | None:
        """Fetch fundamentals from financialdatasets.ai endpoints."""
        if not FINANCIAL_DATASETS_API_KEY:
            return None

        print(f"[DataAgent] Fetching fundamentals from financialdatasets.ai...")

        income = self._fds_get("/financial-statements/income-statements", {
            "ticker": ticker, "period": "ttm", "limit": 1,
        })
        balance = self._fds_get("/financial-statements/balance-sheets", {
            "ticker": ticker, "period": "quarterly", "limit": 1,
        })
        cashflow = self._fds_get("/financial-statements/cash-flow-statements", {
            "ticker": ticker, "period": "ttm", "limit": 1,
        })
        snapshot = self._fds_get("/financial-metrics/snapshot", {
            "ticker": ticker,
        })

        # Extract first record from each list response
        inc_data = None
        if income and "income_statements" in income:
            stmts = income["income_statements"]
            inc_data = stmts[0] if stmts else None

        bal_data = None
        if balance and "balance_sheets" in balance:
            sheets = balance["balance_sheets"]
            bal_data = sheets[0] if sheets else None

        cf_data = None
        if cashflow and "cash_flow_statements" in cashflow:
            stmts = cashflow["cash_flow_statements"]
            cf_data = stmts[0] if stmts else None

        snap_data = None
        if snapshot and "snapshot" in snapshot:
            snap_data = snapshot["snapshot"]
        elif snapshot:
            snap_data = snapshot

        if not inc_data and not snap_data:
            return None

        normalized = normalize_financialdatasets(
            ticker=ticker,
            income=inc_data,
            balance=bal_data,
            cashflow=cf_data,
            snapshot=snap_data,
        )
        return normalized

    def _fetch_yfinance_fundamentals(self, ticker: str) -> dict | None:
        """Fallback: fetch fundamentals from yfinance."""
        try:
            import yfinance as yf
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
            print(f"[DataAgent] yfinance fundamentals failed: {e}")
            return None

    def _fetch_fundamentals(self, ticker: str) -> dict:
        """Fetch fundamentals — financialdatasets.ai first, yfinance fallback."""
        cached = self._load_cache(ticker)
        if cached:
            print(f"[DataAgent] Loaded {ticker} from cache (source: {cached.get('source')}).")
            return cached

        # Try financialdatasets.ai first
        result = self._fetch_fds_fundamentals(ticker)
        if result:
            quality = compute_data_quality(result)
            result["data_quality"] = quality
            print(f"[DataAgent] Got data from financialdatasets.ai "
                  f"({quality['fields_populated']}/{quality['fields_total']} fields).")
            self._save_cache(ticker, result)
            return result

        # Fallback to yfinance
        print("[DataAgent] FDS unavailable, falling back to yfinance...")
        result = self._fetch_yfinance_fundamentals(ticker)
        if result:
            quality = compute_data_quality(result)
            result["data_quality"] = quality
            print(f"[DataAgent] Got data from yfinance "
                  f"({quality['fields_populated']}/{quality['fields_total']} fields).")
            self._save_cache(ticker, result)
            return result

        raise RuntimeError(
            f"All data sources failed for {ticker}. "
            "Set FINANCIAL_DATASETS_API_KEY in .env or try again later."
        )

    # --------------------------------------------------------------- run

    def run(self, ticker: str, **kwargs) -> dict:
        try:
            if not ticker or not isinstance(ticker, str):
                return self._error(str(ticker), "Ticker must be a non-empty string.")

            ticker = ticker.upper().strip()
            if not ticker.isalpha() or len(ticker) > 5:
                return self._error(ticker, f"Invalid ticker format: '{ticker}'")

            # Download price data
            t = time.time()
            print(f"  Downloading {ticker} price data...")
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
            fundamentals = self._fetch_fundamentals(ticker)
            print(f"  Fundamentals: done ({time.time()-t:.1f}s)")

            # Attach DataFrames (not cached, but passed to other agents)
            fundamentals["price_df"] = price_df
            fundamentals["spy_df"] = spy_df

            return self._result(ticker=ticker, data=fundamentals)

        except Exception as e:
            return self._error(ticker, str(e))
