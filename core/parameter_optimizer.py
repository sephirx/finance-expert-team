"""
Parameter optimizer — auto-tunes SIGNAL_WEIGHTS via backtesting (Feature 3).
All functions ≤60 lines (R4). No recursion (R1).
"""

import json
import os
import random
from datetime import datetime, timezone

from core.config import OPTIMAL_WEIGHTS_PATH, WEIGHTS_STALENESS_DAYS, OPTIMIZER_PARAMS
from strategies.backtest_engine import backtest

_OW_CACHE: dict = {"weights": None, "mtime": 0.0}


def _generate_grid(fixed_sentiment: float, step: float) -> list:
    """All valid (fund, tech, sent) combos where fund+tech = 1-fixed_sentiment."""
    budget = round(1.0 - fixed_sentiment, 10)
    combos = []
    f = 0.0
    while round(f, 10) <= round(budget, 10):
        t = round(budget - f, 10)
        if t >= 0:
            combos.append({
                "fundamental": round(f, 10),
                "technical":   round(t, 10),
                "sentiment":   fixed_sentiment,
            })
        f = round(f + step, 10)
    return combos


def _random_search(fixed_sentiment: float, n: int, rng_seed: int = 42) -> list:
    """Uniform random samples over weight simplex (fund+tech = 1-fixed_sentiment)."""
    rng = random.Random(rng_seed)
    budget = round(1.0 - fixed_sentiment, 10)
    combos = []
    for _ in range(n):
        f = round(rng.uniform(0.0, budget), 4)
        t = round(budget - f, 4)
        combos.append({"fundamental": f, "technical": t, "sentiment": fixed_sentiment})
    return combos


def _fine_grid_around(top_weights: list, fixed_sentiment: float,
                      radius: float, step: float) -> list:
    """Fine grid ±radius around each top weight combo."""
    seen = set()
    combos = []
    budget = round(1.0 - fixed_sentiment, 10)
    for w in top_weights:
        f_center = w["fundamental"]
        f_lo = max(0.0, round(f_center - radius, 10))
        f_hi = min(budget, round(f_center + radius, 10))
        f = f_lo
        while round(f, 10) <= round(f_hi, 10):
            t = round(budget - f, 10)
            if t >= 0:
                key = (round(f, 4), round(t, 4))
                if key not in seen:
                    seen.add(key)
                    combos.append({"fundamental": round(f, 4),
                                   "technical":   round(t, 4),
                                   "sentiment":   fixed_sentiment})
            f = round(f + step, 10)
    return combos


def _eval_combo(combo: dict, price_dfs: dict, fund_ratings: dict, threshold: float) -> float:
    """Average Sharpe across all tickers for one weight combo."""
    sharpes = []
    for ticker, price_df in price_dfs.items():
        rating = fund_ratings.get(ticker, "HOLD")
        s = backtest(price_df, combo, fund_rating=rating, threshold=threshold)
        if s > -999.0:
            sharpes.append(s)
    if not sharpes:
        return -999.0
    return sum(sharpes) / len(sharpes)


def optimize_weights(tickers: list, price_dfs: dict, fund_ratings: dict,
                     iterations: int = 0) -> tuple:
    """
    Phase A: coarse grid. Phase B: fine grid around top_k.
    If iterations > 0, use random search instead.
    Returns (best_weights, best_sharpe).
    """
    p = OPTIMIZER_PARAMS
    fixed_s = p["fixed_sentiment_weight"]
    threshold = p["threshold"]

    if iterations > 0:
        combos = _random_search(fixed_s, iterations)
        label = f"Random search ({iterations} iterations)"
    else:
        combos = _generate_grid(fixed_s, p["coarse_step"])
        label = f"Coarse grid (step={p['coarse_step']})"

    print(f"\n[Optimizer] {label} — {len(combos)} combos, {len(tickers)} ticker(s)")
    print(f"  {'fund':>6} {'tech':>6} {'sent':>6} {'sharpe':>8}")
    print(f"  {'-'*32}")

    results = []
    for combo in combos:
        sharpe = _eval_combo(combo, price_dfs, fund_ratings, threshold)
        results.append((sharpe, combo))
        print(f"  {combo['fundamental']:>6.2f} {combo['technical']:>6.2f} "
              f"{combo['sentiment']:>6.2f} {sharpe:>8.4f}")

    results.sort(key=lambda x: x[0], reverse=True)

    if iterations > 0:
        best_sharpe, best_weights = results[0]
        return best_weights, best_sharpe

    # Phase B: fine grid around top_k
    top_k = p["fine_top_k"]
    top_combos = [c for _, c in results[:top_k]]
    fine_combos = _fine_grid_around(top_combos, fixed_s, p["fine_radius"], p["fine_step"])

    print(f"\n[Optimizer] Fine grid (step={p['fine_step']}) — {len(fine_combos)} combos")
    print(f"  {'fund':>6} {'tech':>6} {'sent':>6} {'sharpe':>8}")
    print(f"  {'-'*32}")

    for combo in fine_combos:
        sharpe = _eval_combo(combo, price_dfs, fund_ratings, threshold)
        results.append((sharpe, combo))
        print(f"  {combo['fundamental']:>6.2f} {combo['technical']:>6.2f} "
              f"{combo['sentiment']:>6.2f} {sharpe:>8.4f}")

    results.sort(key=lambda x: x[0], reverse=True)
    best_sharpe, best_weights = results[0]
    print(f"\n[Optimizer] Best: fund={best_weights['fundamental']:.2f} "
          f"tech={best_weights['technical']:.2f} "
          f"sent={best_weights['sentiment']:.2f} "
          f"sharpe={best_sharpe:.4f}")
    return best_weights, best_sharpe


def save_optimal_weights(weights: dict, sharpe: float, tickers: list,
                         path: str = OPTIMAL_WEIGHTS_PATH) -> None:
    """Save optimal weights to JSON."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "weights":      weights,
        "sharpe":       sharpe,
        "tickers":      tickers,
        "optimized_at": datetime.now(timezone.utc).isoformat(),
        "version":      1,
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    _OW_CACHE["weights"] = None  # invalidate cache
    print(f"[Optimizer] Saved to {path}")


def load_optimal_weights(path: str = OPTIMAL_WEIGHTS_PATH,
                         max_age_days: int = WEIGHTS_STALENESS_DAYS) -> dict | None:
    """Load saved weights. Returns None if missing, stale, corrupt, or invalid."""
    global _OW_CACHE
    if not os.path.exists(path):
        return None
    try:
        mtime = os.path.getmtime(path)
        if _OW_CACHE["weights"] is not None and mtime == _OW_CACHE["mtime"]:
            return _OW_CACHE["weights"]
        with open(path) as f:
            data = json.load(f)
        weights = data.get("weights", {})
        if not weights or abs(sum(weights.values()) - 1.0) > 0.01:
            return None
        optimized_at = datetime.fromisoformat(data["optimized_at"])
        if (datetime.now(timezone.utc) - optimized_at).days > max_age_days:
            return None
        _OW_CACHE.update({"weights": weights, "mtime": mtime})
        return weights
    except Exception:
        return None
