"""
Data Normalizer — maps raw API responses to canonical internal schema (Point 3).
Not an agent. A lightweight mapping layer.
"""

import pandas as pd


def _safe_float(val):
    if val is None:
        return None
    try:
        f = float(val)
        return f if pd.notna(f) else None
    except (ValueError, TypeError):
        return None


def _derive_ratios(inc, bal, cf):
    """Derive ROE, ROA, D/E, growth from financial statements."""
    net_income = _safe_float(inc.get("net_income"))
    prev_ni = _safe_float(inc.get("net_income_previous"))
    revenue = _safe_float(inc.get("revenue"))
    prev_rev = _safe_float(inc.get("revenue_previous"))
    equity = _safe_float(bal.get("total_stockholders_equity"))
    total_debt = _safe_float(bal.get("total_debt"))
    total_assets = _safe_float(bal.get("total_assets"))

    roe = round(net_income / equity, 4) if net_income and equity and equity > 0 else None
    roa = round(net_income / total_assets, 4) if net_income and total_assets and total_assets > 0 else None
    de = round(total_debt / equity * 100, 2) if total_debt is not None and equity and equity > 0 else None
    rev_growth = round((revenue - prev_rev) / prev_rev, 4) if revenue and prev_rev and prev_rev > 0 else None
    earn_growth = round((net_income - prev_ni) / prev_ni, 4) if net_income and prev_ni and prev_ni > 0 else None
    fcf = _safe_float(cf.get("free_cash_flow"))

    return {"roe": roe, "roa": roa, "de": de, "rev_growth": rev_growth, "earn_growth": earn_growth, "fcf": fcf}


def normalize_financialdatasets(
    ticker: str,
    income: dict | None = None,
    balance: dict | None = None,
    cashflow: dict | None = None,
    snapshot: dict | None = None,
) -> dict:
    """Map financialdatasets.ai API responses to canonical schema."""
    inc = income or {}
    bal = balance or {}
    cf = cashflow or {}
    snap = snapshot or {}

    ratios = _derive_ratios(inc, bal, cf)

    return {
        "source":          "financialdatasets",
        "ticker":          ticker,
        "name":            snap.get("company_name", ticker),
        "sector":          snap.get("sector", "N/A"),
        "industry":        snap.get("industry", "N/A"),
        "market_cap":      _safe_float(snap.get("market_cap")),
        "current_price":   _safe_float(snap.get("price")),
        "52w_high":        _safe_float(snap.get("fifty_two_week_high")),
        "52w_low":         _safe_float(snap.get("fifty_two_week_low")),
        "pe_ratio":        _safe_float(snap.get("pe_ratio")),
        "forward_pe":      _safe_float(snap.get("forward_pe")),
        "pb_ratio":        _safe_float(snap.get("price_to_book")),
        "ev_ebitda":       _safe_float(snap.get("ev_to_ebitda")),
        "roe":             ratios["roe"],
        "roa":             ratios["roa"],
        "debt_to_equity":  ratios["de"],
        "free_cashflow":   ratios["fcf"],
        "revenue_growth":  ratios["rev_growth"],
        "earnings_growth": ratios["earn_growth"],
        "dividend_yield":  _safe_float(snap.get("dividend_yield")),
        "beta":            _safe_float(snap.get("beta")),
        "analyst_target":  _safe_float(snap.get("analyst_target_price")),
        "recommendation":  snap.get("recommendation"),
    }


def compute_data_quality(data: dict) -> dict:
    """Score completeness of normalized data."""
    key_fields = [
        "current_price", "pe_ratio", "roe", "roa", "debt_to_equity",
        "free_cashflow", "revenue_growth", "earnings_growth",
        "market_cap", "beta", "analyst_target",
    ]
    populated = sum(1 for k in key_fields if data.get(k) is not None)
    total = len(key_fields)

    return {
        "fields_populated": populated,
        "fields_total": total,
        "completeness": round(populated / total, 2),
        "missing": [k for k in key_fields if data.get(k) is None],
    }
