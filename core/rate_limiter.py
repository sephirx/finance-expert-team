import time
from threading import Lock

# Rate limit config per source (calls allowed per window_seconds)
RATE_LIMITS = {
    "yfinance":               {"calls": 2000, "window_seconds": 3600},
    "alpha_vantage":          {"calls": 5,    "window_seconds": 60},
    "financial_modeling_prep": {"calls": 10,  "window_seconds": 60},
    "stooq":                  {"calls": 100,  "window_seconds": 60},
}

_lock = Lock()
_state: dict[str, dict] = {}


def check_and_consume(source: str) -> tuple[bool, float]:
    with _lock:
        config = RATE_LIMITS.get(source, {"calls": 60, "window_seconds": 60})
        now = time.time()

        entry = _state.get(source, {"count": 0, "window_start": now})

        if now - entry["window_start"] >= config["window_seconds"]:
            entry = {"count": 0, "window_start": now}

        if entry["count"] >= config["calls"]:
            wait = config["window_seconds"] - (now - entry["window_start"])
            return False, max(wait, 0)

        entry["count"] += 1
        _state[source] = entry
        return True, 0


def wait_if_needed(source: str, verbose: bool = True):
    max_wait = 300  # 5 min circuit breaker
    waited = 0
    while True:
        allowed, wait_seconds = check_and_consume(source)
        if allowed:
            return
        if waited >= max_wait:
            raise RuntimeError(f"Rate limiter timeout: {source} blocked for >{max_wait}s")
        if verbose:
            mins = int(wait_seconds // 60)
            secs = int(wait_seconds % 60)
            print(f"[RateLimiter] {source} limit reached. "
                  f"Waiting {mins}m {secs}s for window to reset...")
        time.sleep(wait_seconds + 1)
        waited += wait_seconds + 1
