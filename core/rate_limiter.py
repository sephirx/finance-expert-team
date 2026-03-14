import time
from threading import Lock

RATE_LIMITS = {
    "financialdatasets":      {"calls": 60,   "window_seconds": 60},
    "alpha_vantage":          {"calls": 5,    "window_seconds": 60},
}

MAX_WAIT_SECONDS = 300
MAX_RETRIES = 30  # R2: bounded

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
    waited = 0.0
    for _ in range(MAX_RETRIES):  # R2: bounded loop
        allowed, wait_seconds = check_and_consume(source)
        if allowed:
            return
        if waited >= MAX_WAIT_SECONDS:
            raise RuntimeError(f"Rate limiter timeout: {source} blocked for >{MAX_WAIT_SECONDS}s")
        if verbose:
            mins = int(wait_seconds // 60)
            secs = int(wait_seconds % 60)
            print(f"[RateLimiter] {source} limit reached. Waiting {mins}m {secs}s...")
        time.sleep(wait_seconds + 1)
        waited += wait_seconds + 1
    raise RuntimeError(f"Rate limiter: {source} exceeded {MAX_RETRIES} retries")
