"""
MetaOptimizer — autonomous agent-params optimization loop.
Uses Claude API to suggest threshold mutations, evaluates via ScorecardAgent hit_rates.
All functions ≤60 lines (R4). No recursion (R1).
"""

import json
import os
import copy
import time
from datetime import datetime

import anthropic

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PARAMS_PATH = os.path.join(_BASE, "optimization", "agent_params.json")
_TEST_SET_PATH = os.path.join(_BASE, "optimization", "test_set.json")
_LOG_PATH = os.path.join(_BASE, "optimization", "experiment_log.tsv")

_CLIENT = None


def _client():
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = anthropic.Anthropic()
    return _CLIENT


def _load_params():
    with open(_PARAMS_PATH, "r") as f:
        return json.load(f)


def _save_params(params: dict):
    with open(_PARAMS_PATH, "w") as f:
        json.dump(params, f, indent=2)


def _load_test_set():
    with open(_TEST_SET_PATH, "r") as f:
        return json.load(f)


def _load_log_tail(n=10) -> str:
    """Return last n lines of experiment_log.tsv as string."""
    try:
        with open(_LOG_PATH, "r") as f:
            lines = f.readlines()
        return "".join(lines[-n:]) if lines else ""
    except FileNotFoundError:
        return ""


def _append_log(iteration, composite, param_changed, old_val, new_val, status, description):
    with open(_LOG_PATH, "a") as f:
        f.write(f"{iteration}\t{composite:.4f}\t{param_changed}\t"
                f"{old_val}\t{new_val}\t{status}\t{description}\n")


def _run_ticker_silent(ticker: str, agents: list) -> tuple[dict, dict]:
    """Run analysis for one ticker silently. Returns (sc_data, risk_data)."""
    from agents.orchestrator import _run_single_ticker
    from memory.portfolio_store import PortfolioStore
    store = PortfolioStore()
    r = _run_single_ticker(ticker, "综合分析", agents, store, silent=True)
    return r.get("sc_data", {}), r.get("risk_data", {})


def _compute_composite(sc_data: dict, risk_data: dict, weights: dict) -> float:
    """Compute composite score from scorecard + risk data using test_set weights."""
    h30 = sc_data.get("hit_rate_30d") or 0.0
    h90 = sc_data.get("hit_rate_90d") or 0.0
    sharpe = risk_data.get("sharpe_ratio", 0.0)
    grade = sc_data.get("team_grade", "D")

    sharpe_score = 1.0 if sharpe > 1.0 else (0.5 if sharpe > 0.3 else 0.0)
    grade_map = {"A": 1.0, "B+": 0.8, "B": 0.6, "C": 0.4, "D": 0.0}
    grade_score = grade_map.get(grade, 0.0)

    return (weights["hit_rate_30d"] * h30
            + weights["hit_rate_90d"] * h90
            + weights["sharpe_score"] * sharpe_score
            + weights["grade_score"] * grade_score)


def _evaluate_params(tickers: list, agents: list, weights: dict) -> float:
    """Run all test tickers and return mean composite_score."""
    scores = []
    for ticker in tickers:
        sc, risk = _run_ticker_silent(ticker, agents)
        if sc:
            scores.append(_compute_composite(sc, risk, weights))
    return sum(scores) / len(scores) if scores else 0.0


def _ask_claude(params: dict, log_tail: str, current_score: float) -> dict:
    """Ask Claude to suggest one parameter mutation. Returns mutation dict."""
    prompt = f"""You are optimizing agent threshold parameters for a stock analysis system.
Current parameters:
{json.dumps(params, indent=2)}

Recent experiment history (TSV: iteration, composite_score, param_changed, old_val, new_val, status):
{log_tail if log_tail else "(no history yet)"}

Current composite_score: {current_score:.4f}

The composite_score ranges 0-1. Higher is better.
It is computed as: 0.40*hit_rate_30d + 0.30*hit_rate_90d + 0.20*sharpe_score + 0.10*grade_score

Suggest ONE parameter change that may improve the composite_score.
Consider: what signals are currently too sensitive or not sensitive enough?
Do NOT repeat a change that was recently discarded.

Respond ONLY with valid JSON in this exact format:
{{
  "section": "fundamental" | "technical" | "scorecard",
  "param": "<param_name>",
  "new_value": <number>,
  "rationale": "<one sentence>"
}}"""

    msg = _client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    # strip markdown fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)


def _apply_mutation(params: dict, mutation: dict) -> dict:
    """Return a new params dict with the mutation applied."""
    new_params = copy.deepcopy(params)
    section = mutation["section"]
    param = mutation["param"]
    if section in new_params and param in new_params[section]:
        new_params[section][param] = mutation["new_value"]
    return new_params


def run_optimization_loop(iterations: int = 50, show_log: bool = False):
    """Main optimization loop. Runs for `iterations` rounds."""
    if show_log:
        print(_load_log_tail(n=50))
        return

    test_set = _load_test_set()
    tickers = test_set["tickers"]
    agents = test_set["agents"]
    weights = test_set["composite_weights"]

    print(f"\n{'='*60}")
    print(f"  Meta-Optimizer  |  iterations={iterations}")
    print(f"  Test tickers: {', '.join(tickers)}")
    print(f"{'='*60}\n")

    # baseline score with current params
    print("[Iter 0] Evaluating baseline...")
    baseline = _evaluate_params(tickers, agents, weights)
    print(f"[Iter 0] Baseline composite_score = {baseline:.4f}")

    best_score = baseline
    for i in range(1, iterations + 1):
        print(f"\n[Iter {i}/{iterations}] Asking Claude for suggestion...")
        params = _load_params()
        log_tail = _load_log_tail()

        try:
            mutation = _ask_claude(params, log_tail, best_score)
        except Exception as e:
            print(f"  Claude API error: {e} — skipping")
            continue

        section = mutation.get("section", "?")
        param = mutation.get("param", "?")
        new_val = mutation.get("new_value")
        rationale = mutation.get("rationale", "")
        old_val = params.get(section, {}).get(param, "?")

        print(f"  Suggestion: [{section}] {param}: {old_val} → {new_val}")
        print(f"  Rationale: {rationale}")

        new_params = _apply_mutation(params, mutation)
        _save_params(new_params)

        print(f"  Evaluating new params on {len(tickers)} tickers...")
        new_score = _evaluate_params(tickers, agents, weights)
        print(f"  composite_score: {best_score:.4f} → {new_score:.4f}", end="  ")

        if new_score >= best_score:
            best_score = new_score
            status = "keep"
            print("KEEP ✓")
        else:
            _save_params(params)  # revert
            status = "discard"
            print("DISCARD ✗")

        _append_log(i, new_score, f"{section}.{param}", old_val, new_val, status, rationale)
        time.sleep(1)  # rate limit buffer

    print(f"\n{'='*60}")
    print(f"  Optimization complete. Best score: {best_score:.4f}")
    print(f"  Log: {_LOG_PATH}")
    print(f"{'='*60}\n")
