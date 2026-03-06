import time
import json
import os
from threading import Lock

RATE_STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "cache", "rate_state.json")

# Rate limit config per source (calls allowed per window_seconds)
RATE_LIMITS = {
    "yfinance":              {"calls": 2000, "window_seconds": 3600},  # generous, unofficial
    "alpha_vantage":         {"calls": 5,    "window_seconds": 60},    # free: 5/min, 500/day
    "financial_modeling_prep": {"calls": 10, "window_seconds": 60},   # free: 10/min, 250/day
    "stooq":                 {"calls": 100,  "window_seconds": 60},    # unofficial, conservative
}

_lock = Lock()


def _load_state() -> dict:
    if os.path.exists(RATE_STATE_FILE):
        try:
            with open(RATE_STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_state(state: dict):
    os.makedirs(os.path.dirname(RATE_STATE_FILE), exist_ok=True)
    with open(RATE_STATE_FILE, "w") as f:
        json.dump(state, f)


def check_and_consume(source: str) -> tuple[bool, float]:
    """
    Returns (allowed: bool, wait_seconds: float).
    If allowed=False, wait_seconds tells you how long until the window resets.
    Automatically consumes one call if allowed.
    """
    with _lock:
        config = RATE_LIMITS.get(source, {"calls": 60, "window_seconds": 60})
        state = _load_state()
        now = time.time()

        entry = state.get(source, {"count": 0, "window_start": now})

        # Reset window if expired
        if now - entry["window_start"] >= config["window_seconds"]:
            entry = {"count": 0, "window_start": now}

        if entry["count"] >= config["calls"]:
            wait = config["window_seconds"] - (now - entry["window_start"])
            return False, max(wait, 0)

        entry["count"] += 1
        state[source] = entry
        _save_state(state)
        return True, 0


def wait_if_needed(source: str, verbose: bool = True):
    """
    Blocks until a call slot is available, then consumes it.
    Automatically retries after the rate limit window resets.
    """
    while True:
        allowed, wait_seconds = check_and_consume(source)
        if allowed:
            return
        if verbose:
            mins = int(wait_seconds // 60)
            secs = int(wait_seconds % 60)
            print(f"[RateLimiter] {source} limit reached. "
                  f"Waiting {mins}m {secs}s for window to reset...")
        time.sleep(wait_seconds + 1)  # +1s buffer
