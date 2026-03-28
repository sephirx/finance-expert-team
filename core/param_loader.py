"""
param_loader — load agent threshold parameters from optimization/agent_params.json.
Falls back to hardcoded defaults if the file is missing or malformed.
"""

import json
import os

_PARAMS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "optimization", "agent_params.json")

_JSON_CACHE: dict = {}
_JSON_MTIME: float = 0.0

_DEFAULTS = {
    "fundamental": {
        "pe_cheap": 15,
        "pe_expensive": 30,
        "roe_strong": 0.15,
        "roe_weak": 0.05,
        "de_high": 200,
        "de_low": 50,
        "rev_growth_good": 0.10,
        "upside_bullish": 10,
        "upside_bearish": -10,
        "buy_threshold": 2,
        "sell_threshold": -2,
    },
    "technical": {
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        "bullish_threshold": 3,
        "bearish_threshold": -3,
    },
    "scorecard": {
        "hit_rate_min": 0.55,
        "sharpe_excellent": 1.0,
        "sharpe_ok": 0.3,
        "calmar_min": 0.3,
        "grade_A": 0.75,
        "grade_Bplus": 0.60,
        "grade_B": 0.45,
        "grade_C": 0.30,
    },
}


def _load_json():
    global _JSON_CACHE, _JSON_MTIME
    try:
        mtime = os.path.getmtime(_PARAMS_PATH)
        if mtime == _JSON_MTIME and _JSON_CACHE:
            return _JSON_CACHE
        with open(_PARAMS_PATH, "r") as f:
            _JSON_CACHE = json.load(f)
        _JSON_MTIME = mtime
        return _JSON_CACHE
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_params(section: str) -> dict:
    """Return parameter dict for a section ('fundamental', 'technical', 'scorecard')."""
    data = _load_json()
    defaults = _DEFAULTS.get(section, {})
    overrides = data.get(section, {})
    merged = dict(defaults)
    merged.update(overrides)
    return merged
