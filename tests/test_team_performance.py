#!/usr/bin/env python3
"""
Finance Expert Team — 5-Phase General Performance Test
======================================================
Phase 1: Accuracy (10 stocks across sectors)
Phase 2: Consistency (same stock 3x)
Phase 3: Speed Benchmark
Phase 4: Edge Cases
Phase 5: Signal Agreement Analysis
"""
import sys
import os
import time
import json
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import Orchestrator, classify_intent

# ─────────────────────── Helpers ───────────────────────

def run_analysis(ticker, query, label=""):
    """Run a single analysis and return (result_dict, elapsed_seconds, error)."""
    orch = Orchestrator()
    start = time.time()
    try:
        report = orch.analyze(query=query, ticker=ticker)
        elapsed = time.time() - start
        return {"report": report, "ticker": ticker, "query": query}, elapsed, None
    except Exception as e:
        elapsed = time.time() - start
        return None, elapsed, str(e)


def extract_scorecard(report_text):
    """Pull key metrics from the report text."""
    metrics = {}
    for line in report_text.split("\n"):
        line = line.strip()
        if "Team Signal:" in line:
            metrics["team_signal"] = line.split("Team Signal:")[1].split()[0].strip()
        if "Grade:" in line and "SCORECARD" in line:
            metrics["grade"] = line.split("Grade:")[1].strip()
        if "Agreement:" in line:
            metrics["agreement"] = line.split("Agreement:")[1].strip()
        if "Sharpe:" in line:
            try:
                metrics["sharpe"] = line.split("Sharpe:")[1].split()[0].strip()
            except:
                pass
        if "Max Drawdown:" in line:
            try:
                metrics["max_drawdown"] = line.split("Max Drawdown:")[1].split()[0].strip()
            except:
                pass
        if "Risk Level:" in line:
            try:
                metrics["risk_level"] = line.split("Risk Level:")[1].strip()
            except:
                pass
    return metrics


# ─────────────────────── Phase 1: Accuracy ───────────────────────

PHASE1_STOCKS = [
    ("AAPL",  "Is AAPL a good buy right now?"),           # Mega-cap tech
    ("MSFT",  "What is the valuation and technical outlook?"),  # Mega-cap tech
    ("JPM",   "Analyze risk and fundamentals"),           # Financials
    ("JNJ",   "Is this stock undervalued? Check sentiment"),  # Healthcare
    ("XOM",   "Technical and risk analysis"),              # Energy
    ("AMZN",  "Full portfolio analysis"),                  # Consumer/Tech
    ("NVDA",  "Buy or sell? Check all signals"),           # Semiconductor
    ("KO",    "Is KO a safe dividend stock?"),             # Consumer staples
    ("TSLA",  "Backtest and technical analysis"),          # EV/Growth
    ("DIS",   "Fundamental and sentiment analysis"),       # Entertainment
]


def phase1_accuracy():
    print("\n" + "="*70)
    print("  PHASE 1: ACCURACY TEST — 10 Stocks Across Sectors")
    print("="*70)

    results = []
    for i, (ticker, query) in enumerate(PHASE1_STOCKS):
        print(f"\n--- [{i+1}/10] {ticker} ---")
        res, elapsed, err = run_analysis(ticker, query, f"Phase1-{ticker}")
        if err:
            print(f"  FAILED: {err}")
            results.append({"ticker": ticker, "status": "FAIL", "error": err, "time": elapsed})
        else:
            metrics = extract_scorecard(res["report"])
            print(f"  Grade={metrics.get('grade','?')} Signal={metrics.get('team_signal','?')} "
                  f"Agreement={metrics.get('agreement','?')} Time={elapsed:.1f}s")
            results.append({
                "ticker": ticker, "status": "OK", "time": elapsed,
                "grade": metrics.get("grade"),
                "signal": metrics.get("team_signal"),
                "agreement": metrics.get("agreement"),
                "risk_level": metrics.get("risk_level"),
                "sharpe": metrics.get("sharpe"),
                "max_drawdown": metrics.get("max_drawdown"),
            })

    # Summary
    ok = [r for r in results if r["status"] == "OK"]
    fail = [r for r in results if r["status"] == "FAIL"]
    avg_time = sum(r["time"] for r in ok) / len(ok) if ok else 0

    print(f"\n{'─'*50}")
    print(f"Phase 1 Summary: {len(ok)}/10 passed, {len(fail)} failed")
    print(f"Average time: {avg_time:.1f}s")
    if ok:
        grades = [r["grade"] for r in ok if r.get("grade")]
        signals = [r["signal"] for r in ok if r.get("signal")]
        print(f"Grades: {grades}")
        print(f"Signals: {signals}")
    if fail:
        print(f"Failed: {[r['ticker'] for r in fail]}")
    return results


# ─────────────────────── Phase 2: Consistency ───────────────────────

def phase2_consistency():
    print("\n" + "="*70)
    print("  PHASE 2: CONSISTENCY TEST — Same Stock 3x")
    print("="*70)

    ticker = "AAPL"
    query = "Is AAPL a good buy right now?"
    runs = []

    for i in range(3):
        print(f"\n--- Run {i+1}/3 ---")
        res, elapsed, err = run_analysis(ticker, query)
        if err:
            print(f"  FAILED: {err}")
            runs.append({"status": "FAIL", "error": err})
        else:
            metrics = extract_scorecard(res["report"])
            runs.append({"status": "OK", "metrics": metrics, "time": elapsed})
            print(f"  Grade={metrics.get('grade','?')} Signal={metrics.get('team_signal','?')} Time={elapsed:.1f}s")

    ok_runs = [r for r in runs if r["status"] == "OK"]
    if len(ok_runs) >= 2:
        signals = [r["metrics"].get("team_signal") for r in ok_runs]
        grades = [r["metrics"].get("grade") for r in ok_runs]
        consistent_signal = len(set(signals)) == 1
        consistent_grade = len(set(grades)) == 1
        print(f"\n{'─'*50}")
        print(f"Signal consistent: {'YES' if consistent_signal else 'NO'} ({signals})")
        print(f"Grade consistent:  {'YES' if consistent_grade else 'NO'} ({grades})")
    return runs


# ─────────────────────── Phase 3: Speed Benchmark ───────────────────────

def phase3_speed():
    print("\n" + "="*70)
    print("  PHASE 3: SPEED BENCHMARK")
    print("="*70)

    tests = [
        ("AAPL", "Is it a buy?", "Minimal (fund+tech)"),
        ("AAPL", "Full portfolio analysis with sentiment and risk and backtest", "Full (all agents)"),
    ]

    for ticker, query, label in tests:
        intents = classify_intent(query)
        print(f"\n--- {label} | Intents={intents} ---")
        _, elapsed, err = run_analysis(ticker, query)
        if err:
            print(f"  FAILED: {err}")
        else:
            print(f"  Time: {elapsed:.1f}s")
    return True


# ─────────────────────── Phase 4: Edge Cases ───────────────────────

def phase4_edge_cases():
    print("\n" + "="*70)
    print("  PHASE 4: EDGE CASES")
    print("="*70)

    cases = [
        ("BRK", "Analyze BRK", "Non-standard ticker (no suffix)"),
        ("GME",  "Is GME a buy?", "Meme stock (high volatility)"),
        ("T",    "Risk analysis", "Single-letter ticker"),
    ]

    results = []
    for ticker, query, label in cases:
        print(f"\n--- {label}: {ticker} ---")
        res, elapsed, err = run_analysis(ticker, query)
        if err:
            print(f"  FAILED: {err}")
            results.append({"ticker": ticker, "status": "FAIL", "label": label, "error": err})
        else:
            metrics = extract_scorecard(res["report"])
            print(f"  OK — Grade={metrics.get('grade','?')} Time={elapsed:.1f}s")
            results.append({"ticker": ticker, "status": "OK", "label": label, "time": elapsed})
    return results


# ─────────────────────── Phase 5: Intent Classification ───────────────────────

def phase5_intent():
    print("\n" + "="*70)
    print("  PHASE 5: INTENT CLASSIFICATION & SIGNAL AGREEMENT")
    print("="*70)

    tests = [
        ("Is AAPL a good buy?",                       {"fundamental", "technical"}),
        ("What is the RSI and MACD?",                  {"technical"}),
        ("Backtest a moving average strategy",         {"backtest"}),
        ("Full portfolio with sentiment and risk",     {"portfolio", "sentiment", "risk"}),
        ("News and analyst opinions",                  {"sentiment"}),
        ("How volatile is this stock?",                {"risk"}),
        ("Random unrelated query",                     {"fundamental", "technical"}),  # default
    ]

    passed = 0
    for query, expected in tests:
        result = classify_intent(query)
        match = result == expected
        status = "PASS" if match else "FAIL"
        if match:
            passed += 1
        print(f"  [{status}] '{query}' → {result} (expected {expected})")

    print(f"\nIntent classification: {passed}/{len(tests)} passed")
    return passed, len(tests)


# ─────────────────────── Main ───────────────────────

if __name__ == "__main__":
    total_start = time.time()

    print("\n" + "#"*70)
    print("#  FINANCE EXPERT TEAM — GENERAL PERFORMANCE TEST")
    print("#"*70)

    # Phase 5 first (no API calls, instant)
    p5_passed, p5_total = phase5_intent()

    # Phase 1: Accuracy
    p1_results = phase1_accuracy()

    # Phase 2: Consistency
    p2_results = phase2_consistency()

    # Phase 3: Speed
    phase3_speed()

    # Phase 4: Edge Cases
    p4_results = phase4_edge_cases()

    # ─────────── Final Report ───────────
    total_time = time.time() - total_start

    print("\n" + "="*70)
    print("  FINAL TEST REPORT")
    print("="*70)

    p1_ok = sum(1 for r in p1_results if r["status"] == "OK")
    p4_ok = sum(1 for r in p4_results if r["status"] == "OK")

    print(f"  Phase 1 (Accuracy):      {p1_ok}/10 stocks analyzed successfully")
    print(f"  Phase 2 (Consistency):    3 runs completed")
    print(f"  Phase 3 (Speed):          Benchmark complete")
    print(f"  Phase 4 (Edge Cases):     {p4_ok}/{len(p4_results)} passed")
    print(f"  Phase 5 (Intent):         {p5_passed}/{p5_total} passed")
    print(f"\n  Total test time: {total_time:.0f}s ({total_time/60:.1f} min)")
    print("="*70)
