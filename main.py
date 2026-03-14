#!/usr/bin/env python3
"""
Finance Expert Team — AI stock analysis.
All functions ≤60 lines (R4). No recursion (R1).
"""

import argparse
import os
from agents.orchestrator import Orchestrator
from core.intent_router import ALL_AGENTS


def run_regulation_check():
    """Run Tier 1 Power of Ten static compliance check."""
    from regulation.power_of_ten import PowerOfTenChecker
    from regulation.compliance_report import ComplianceReporter

    project_root = os.path.dirname(os.path.abspath(__file__))
    checker = PowerOfTenChecker(project_root)
    checker.run_all()
    reporter = ComplianceReporter(checker)
    grade = reporter.get_compliance_grade()

    print(f"\n{'='*60}")
    print(f"  Tier 1 Regulation — Compliance Grade: {grade}")
    print(f"{'='*60}")
    print(reporter.generate_text_report())

    for result in checker.results:
        if not result.passed:
            for v in result.violations[:10]:  # R3: bounded
                print(f"  [{v.rule_id}] {v.file_path}:{v.line_number} — {v.message}")
    return checker.summary()["compliance_rate"]


def _portfolio_show(store):
    """Display portfolio overview."""
    s = store.summary()
    print(f"\n{'='*50}")
    print(f"  Portfolio Overview")
    print(f"{'='*50}")
    print(f"  Broker:    {s['broker'] or 'Not set'}")
    print(f"  Cash:      ${s['cash_balance']:,.2f}")
    print(f"  Positions: {s['num_holdings']}")
    print(f"  Invested:  ${s['total_invested']:,.2f}")
    if s["holdings"]:
        print(f"\n  {'Ticker':<8} {'Shares':>8} {'Avg Cost':>10}")
        print(f"  {'-'*28}")
        for h in s["holdings"]:
            print(f"  {h['ticker']:<8} {h['shares']:>8.1f} ${h['avg_cost']:>9.2f}")
    if s["watchlist"]:
        print(f"\n  Watchlist: {', '.join(s['watchlist'])}")
    p = s["preferences"]
    print(f"\n  Risk: {p['risk_tolerance']} | Horizon: {p['investment_horizon']} | "
          f"Style: {p['style']} | Max Pos: {p['max_position_pct']}%")
    print(f"{'='*50}\n")


def _portfolio_mutate(args, store):
    """Handle add/remove/set portfolio commands."""
    cmd = args[0].lower()
    if cmd == "add" and len(args) >= 4:
        store.add_holding(args[1].upper(), float(args[2]), float(args[3]))
        print(f"Added {args[2]} shares of {args[1].upper()} @ ${float(args[3]):.2f}")
    elif cmd == "remove" and len(args) >= 2:
        shares = float(args[2]) if len(args) > 2 else None
        store.remove_holding(args[1].upper(), shares)
        print(f"Removed {'all' if shares is None else shares} {args[1].upper()}")
    elif cmd == "set-broker" and len(args) >= 2:
        store.set_broker(args[1])
        print(f"Broker set to: {args[1]}")
    elif cmd == "set-cash" and len(args) >= 2:
        store.set_cash(float(args[1]))
        print(f"Cash: ${float(args[1]):,.2f}")
    elif cmd == "watch" and len(args) >= 2:
        store.add_to_watchlist(args[1])
        print(f"Added {args[1].upper()} to watchlist")
    elif cmd == "unwatch" and len(args) >= 2:
        store.remove_from_watchlist(args[1])
        print(f"Removed {args[1].upper()} from watchlist")
    elif cmd == "prefs" and len(args) >= 2:
        kw = {}
        for pair in args[1:]:
            if "=" in pair:
                k, v = pair.split("=", 1)
                kw[k] = float(v) if k == "max_position_pct" else v
        store.set_preferences(**kw)
        print(f"Preferences updated: {kw}")
    else:
        print(f"Unknown or incomplete command: {' '.join(args)}")


def _portfolio_history():
    """Display analysis history."""
    from memory.memory_manager import MemoryManager
    mm = MemoryManager()
    s = mm.summary()
    print(f"\nAnalyses: {s['total_analyses']} total, {s['unique_tickers']} tickers")
    for r in s["recent"]:
        print(f"  {r['date']} {r['ticker']:<6} Signal={r['team_signal']:<5} Grade={r['team_grade']}")
    print()


def run_portfolio_command(args):
    """Route portfolio subcommands."""
    from memory.portfolio_store import PortfolioStore
    if not args:
        print("Commands: show, add, remove, set-broker, set-cash, watch, unwatch, prefs, history")
        return
    store = PortfolioStore()
    cmd = args[0].lower()
    if cmd == "show":
        _portfolio_show(store)
    elif cmd == "history":
        _portfolio_history()
    else:
        _portfolio_mutate(args, store)


def run_analysis(args):
    """Run the main analysis pipeline."""
    ticker = args.ticker.upper().strip()
    query = args.query.strip()

    print(f"\n{'='*60}")
    print(f"  Finance Expert Team")
    print(f"  Ticker : {ticker}")
    print(f"  Query  : {query}")
    if args.agents:
        print(f"  Agents : {', '.join(args.agents)}")
    print(f"  Format : {args.format}")
    print(f"{'='*60}")

    report = Orchestrator().analyze(
        query=query, ticker=ticker,
        agents=args.agents, output_format=args.format,
    )
    print(f"\n{report}")

    # HTML report is opened in browser automatically by ReportAgent


def main():
    parser = argparse.ArgumentParser(description="Finance Expert Team")
    parser.add_argument("--ticker", help="Stock ticker (e.g. AAPL)")
    parser.add_argument("--query", help="Your question")
    parser.add_argument("--agents", nargs="*", choices=ALL_AGENTS)
    parser.add_argument("--format", choices=["text", "html", "both"], default="text")
    parser.add_argument("--regulate", action="store_true")
    parser.add_argument("--portfolio", nargs="*")
    args = parser.parse_args()

    if args.regulate:
        run_regulation_check()
    elif args.portfolio is not None:
        run_portfolio_command(args.portfolio)
    elif args.ticker and args.query:
        run_analysis(args)
    else:
        parser.error("--ticker and --query required (or use --regulate / --portfolio)")


if __name__ == "__main__":
    main()
