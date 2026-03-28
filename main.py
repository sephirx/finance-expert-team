#!/usr/bin/env python3
"""
Finance Expert Team — AI stock analysis.
All functions ≤60 lines (R4). No recursion (R1).
"""

import argparse
import os
from agents.orchestrator import Orchestrator, _run_single_ticker
from core.intent_router import ALL_AGENTS
from memory.portfolio_store import PortfolioStore


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


def _collect_criteria_results(plan):
    """Re-run (cached) single ticker analyses and evaluate criteria. Returns dict."""
    from core.research_parser import evaluate_criteria
    store = PortfolioStore()
    ticker_results = {}
    for ticker in plan.tickers:
        r = _run_single_ticker(ticker, plan.raw_query, plan.agents, store, silent=True)
        if r.get("error"):
            ticker_results[ticker] = []
        else:
            ticker_results[ticker] = evaluate_criteria(
                plan.criteria, r["fund"], r["risk_data"]
            )
    return ticker_results


def run_research_analysis(args):
    """Run batch analysis driven by a research.md file."""
    from core.research_parser import load_research_plan, format_criteria_report
    plan = load_research_plan(args.research)

    print(f"\n{'='*60}")
    print(f"  Finance Expert Team — Research Mode")
    print(f"  Target  : {plan.target}")
    print(f"  Tickers : {', '.join(plan.tickers)}")
    if plan.agents:
        print(f"  Agents  : {', '.join(plan.agents)}")
    if plan.time_range:
        print(f"  Period  : {plan.time_range}")
    print(f"  Criteria: {len(plan.criteria)} rule(s)")
    print(f"{'='*60}")

    report = Orchestrator().analyze_batch(
        tickers=plan.tickers, query=plan.raw_query,
        agents=plan.agents, output_format=args.format,
    )
    print(f"\n{report}")

    if plan.criteria:
        print("\n[Research] Evaluating criteria against agent output...")
        ticker_results = _collect_criteria_results(plan)
        print(format_criteria_report(ticker_results))


def run_optimization(args):
    """Run strategy parameter optimization to find best SIGNAL_WEIGHTS."""
    from memory.portfolio_store import PortfolioStore
    from agents.data_agent import DataAgent
    from agents.fundamental_agent import FundamentalAgent
    from core.parameter_optimizer import optimize_weights, save_optimal_weights

    store = PortfolioStore()
    opt_arg = args.optimize.strip()

    if opt_arg.lower() == "watchlist":
        tickers = list(store.state.watchlist)
        if not tickers:
            print("Watchlist is empty. Add tickers with: python main.py --portfolio watch TICKER")
            return
    else:
        tickers = [t.strip().upper() for t in opt_arg.split(",") if t.strip()]

    if not tickers:
        print("No tickers to optimize.")
        return

    iterations = args.iterations if hasattr(args, "iterations") and args.iterations else 0

    print(f"\n{'='*60}")
    print(f"  Finance Expert Team — Strategy Optimizer")
    print(f"  Tickers    : {', '.join(tickers)}")
    print(f"  Search     : {'Random (' + str(iterations) + ' iters)' if iterations else 'Grid'}")
    print(f"{'='*60}")

    price_dfs = {}
    fund_ratings = {}
    for ticker in tickers:
        print(f"[Optimizer] Fetching data for {ticker}...")
        data_result = DataAgent().run(ticker)
        if data_result.get("error"):
            print(f"  WARNING: Could not fetch data for {ticker} — skipping")
            continue
        raw_data = data_result.get("data", {})
        price_df = raw_data.get("price_df")
        if price_df is None or price_df.empty:
            print(f"  WARNING: No price data for {ticker} — skipping")
            continue
        price_dfs[ticker] = price_df

        fund_result = FundamentalAgent().run(ticker, raw_data=raw_data)
        fund_ratings[ticker] = fund_result.get("data", {}).get("rating", "HOLD")

    if not price_dfs:
        print("No valid price data available for optimization.")
        return

    best_weights, best_sharpe = optimize_weights(
        list(price_dfs.keys()), price_dfs, fund_ratings, iterations=iterations
    )
    save_optimal_weights(best_weights, best_sharpe, list(price_dfs.keys()))

    print(f"\n[Optimizer] Done. Next analysis run will use optimal weights automatically.")


def run_meta_optimization(args):
    """Run autonomous agent-params optimization via Claude API."""
    from agents.meta_optimizer import run_optimization_loop
    show_log = getattr(args, "show_log", False)
    iterations = getattr(args, "iterations", 1) or 1
    run_optimization_loop(iterations=iterations, show_log=show_log)


def run_batch_analysis(args):
    """Run batch analysis on a list of tickers or the watchlist."""
    from memory.portfolio_store import PortfolioStore
    store = PortfolioStore()
    batch_arg = args.batch.strip()

    if batch_arg.lower() == "watchlist":
        tickers = list(store.state.watchlist)
        if not tickers:
            print("Watchlist is empty. Add tickers with: python main.py --portfolio watch TICKER")
            return
    else:
        tickers = [t.strip().upper() for t in batch_arg.split(",") if t.strip()]

    if not tickers:
        print("No tickers to analyze.")
        return

    query = (args.query or "综合分析").strip()

    print(f"\n{'='*60}")
    print(f"  Finance Expert Team — Batch Analysis")
    print(f"  Tickers : {', '.join(tickers)}")
    print(f"  Query   : {query}")
    if args.agents:
        print(f"  Agents  : {', '.join(args.agents)}")
    print(f"  Format  : {args.format}")
    print(f"{'='*60}")

    report = Orchestrator().analyze_batch(
        tickers=tickers, query=query,
        agents=args.agents, output_format=args.format,
    )
    print(f"\n{report}")


def main():
    parser = argparse.ArgumentParser(description="Finance Expert Team")
    parser.add_argument("--ticker", help="Stock ticker (e.g. AAPL)")
    parser.add_argument("--query", help="Your question")
    parser.add_argument("--agents", nargs="*", choices=ALL_AGENTS)
    parser.add_argument("--format", choices=["text", "html", "both"], default="text")
    parser.add_argument("--regulate", action="store_true")
    parser.add_argument("--portfolio", nargs="*")
    parser.add_argument("--batch", help='"watchlist" or "AAPL,NVDA,TSLA"')
    parser.add_argument("--research", help="Path to research.md file")
    parser.add_argument("--optimize", help='Ticker(s) or "watchlist" — tune SIGNAL_WEIGHTS')
    parser.add_argument("--iterations", type=int, default=0,
                        help="0=grid search (default), N>0=random search with N samples")
    parser.add_argument("--meta-optimize", action="store_true",
                        help="Run autonomous agent-params optimization (uses Claude API)")
    parser.add_argument("--show-log", action="store_true",
                        help="Show experiment log (use with --meta-optimize)")
    args = parser.parse_args()

    if args.regulate:
        run_regulation_check()
    elif args.portfolio is not None:
        run_portfolio_command(args.portfolio)
    elif args.research:
        run_research_analysis(args)
    elif getattr(args, "meta_optimize", False):
        run_meta_optimization(args)
    elif args.optimize:
        run_optimization(args)
    elif args.batch:
        run_batch_analysis(args)
    elif args.ticker and args.query:
        run_analysis(args)
    else:
        parser.error("--ticker and --query required (or use --regulate / --portfolio / --batch / --optimize / --meta-optimize)")


if __name__ == "__main__":
    main()
