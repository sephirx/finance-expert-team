"""
Orchestrator — manages the multi-agent analysis pipeline.
All functions ≤60 lines (R4). No recursion (R1).
"""

import time
import concurrent.futures
from agents.data_agent import DataAgent
from agents.fundamental_agent import FundamentalAgent
from agents.technical_agent import TechnicalAgent
from agents.sentiment_agent import SentimentAgent
from agents.risk_agent import RiskAgent
from agents.portfolio_agent import PortfolioAgent
from agents.report_agent import ReportAgent
from agents.scorecard_agent import ScorecardAgent
from regulation.runtime_guards import RegulationContext
from core.intent_router import classify_intent_fallback, ALL_AGENTS
from memory.portfolio_store import PortfolioStore
from memory.memory_manager import MemoryManager

MAX_BATCH_TICKERS = 20


def _fmt(seconds: float) -> str:
    return f"{seconds*1000:.0f}ms" if seconds < 1 else f"{seconds:.1f}s"


def _resolve_intents(query: str, agents: list[str] | None) -> set[str]:
    """Determine which agents to run."""
    if agents:
        intents = set(a for a in agents if a in ALL_AGENTS)
    else:
        intents = set(classify_intent_fallback(query))
    intents.add("risk")  # always needed for scorecard
    return intents


def _run_phase2(intents, ticker, raw_data, price_df, reg_ctx):
    """Phase 2: run analysis agents in parallel. Returns all_results dict."""
    phase2 = {}
    if "fundamental" in intents:
        phase2["FundamentalAgent"] = (FundamentalAgent(), {"raw_data": raw_data})
    if "technical" in intents:
        phase2["TechnicalAgent"] = (TechnicalAgent(), {"price_df": price_df})
    if "sentiment" in intents:
        phase2["SentimentAgent"] = (SentimentAgent(), {})

    results = {}
    if not phase2:
        print("[Phase 2/5] Skipped — no analysis agents needed")
        return results

    t = time.time()
    names = list(phase2.keys())
    print(f"[Phase 2/5] Running {len(names)} agents in parallel: {', '.join(names)}...")
    with concurrent.futures.ThreadPoolExecutor() as ex:
        agent_times = {}
        futures = {}
        for name, (agent, kw) in phase2.items():
            agent_times[name] = time.time()
            futures[ex.submit(agent.run, ticker, **kw)] = name

        for f in concurrent.futures.as_completed(futures):
            name = futures[f]
            elapsed = time.time() - agent_times[name]
            try:
                results[name] = f.result()
            except Exception as e:
                results[name] = {"agent": name, "ticker": ticker, "data": {}, "error": str(e)}
                print(f"  {name}: FAILED ({_fmt(elapsed)})")
            else:
                print(f"  {name}: done ({_fmt(elapsed)})")
            reg_ctx.check_agent(results[name], name)
    print(f"[Phase 2/5] All done ({_fmt(time.time() - t)})")
    return results


def _run_phase3(intents, ticker, fund, tech, sent, risk_data, price_df, spy_df, store, reg_ctx):
    """Phase 3: risk + portfolio. Returns (risk_result, port_result|None)."""
    results = {}
    t = time.time()
    print("[Phase 3/5] Running RiskAgent...")
    risk_result = RiskAgent().run(ticker, price_df=price_df, spy_df=spy_df)
    results["RiskAgent"] = risk_result
    r_data = risk_result.get("data", {})
    reg_ctx.check_agent(risk_result, "RiskAgent")
    print(f"  RiskAgent: done ({_fmt(time.time() - t)})")

    if "portfolio" in intents or ({"fundamental", "technical"} <= intents):
        t2 = time.time()
        print("[Phase 3/5] Running PortfolioAgent...")
        port_result = PortfolioAgent().run(
            ticker, fundamental=fund, technical=tech,
            sentiment=sent, risk=r_data, portfolio_store=store,
        )
        results["PortfolioAgent"] = port_result
        reg_ctx.check_agent(port_result, "PortfolioAgent")
        print(f"  PortfolioAgent: done ({_fmt(time.time() - t2)})")

    print(f"[Phase 3/5] All done ({_fmt(time.time() - t)})")
    return results, r_data


def _save_to_memory(mm, ticker, query, sc_data, fund, tech, sent, raw_data):
    """Save analysis results to memory."""
    price = raw_data.get("current_price") or tech.get("current_price")
    mm.record_analysis(
        ticker=ticker, team_signal=sc_data.get("team_signal", "HOLD"),
        team_grade=sc_data.get("team_grade", "?"),
        fundamental_signal=fund.get("rating", "N/A"),
        technical_signal=tech.get("signal", "N/A"),
        sentiment_signal=sent.get("overall_sentiment", "N/A"),
        price_at_analysis=price, query=query,
    )


def _run_single_ticker(ticker: str, query: str, agents, store, silent: bool = False) -> dict:
    """Run Phase 1-4 for one ticker. Returns structured result dict."""
    def _p(*a, **kw):
        if not silent:
            print(*a, **kw)

    intents = _resolve_intents(query, agents)
    reg_ctx = RegulationContext()
    _p(f"\n[Orchestrator] Ticker={ticker} | Agents={intents}")

    t = time.time()
    _p("[Phase 1/5] Fetching market data...")
    data_result = DataAgent().run(ticker)
    if data_result.get("error"):
        _p(f"[Phase 1/5] FAILED ({_fmt(time.time() - t)})")
        return {"ticker": ticker, "error": data_result["error"],
                "all_results": {}, "fund": {}, "tech": {}, "sent": {},
                "risk_data": {}, "sc_data": {}, "raw_data": {}, "reg_ctx": reg_ctx}
    raw_data = data_result.get("data", {})
    price_df = raw_data.get("price_df")
    spy_df = raw_data.get("spy_df")
    all_results = {"DataAgent": data_result}
    reg_ctx.check_agent(data_result, "DataAgent")
    _p(f"[Phase 1/5] Done ({_fmt(time.time() - t)})")

    p2 = _run_phase2(intents, ticker, raw_data, price_df, reg_ctx) if not silent else \
        _run_phase2_silent(intents, ticker, raw_data, price_df, reg_ctx)
    all_results.update(p2)
    fund = p2.get("FundamentalAgent", {}).get("data", {})
    tech = p2.get("TechnicalAgent", {}).get("data", {})
    sent = p2.get("SentimentAgent", {}).get("data", {})

    p3, risk_data = _run_phase3(intents, ticker, fund, tech, sent,
                                 {}, price_df, spy_df, store, reg_ctx) if not silent else \
        _run_phase3_silent(intents, ticker, fund, tech, sent,
                           {}, price_df, spy_df, store, reg_ctx)
    all_results.update(p3)

    sc_result = ScorecardAgent().run(
        ticker, price_df=price_df, spy_df=spy_df,
        fundamental=fund, technical=tech, sentiment=sent,
        risk=risk_data, portfolio=all_results.get("PortfolioAgent", {}).get("data", {}),
    )
    all_results["ScorecardAgent"] = sc_result
    reg_ctx.check_agent(sc_result, "ScorecardAgent")
    sc_data = sc_result.get("data", {})

    return {
        "ticker": ticker, "error": None,
        "all_results": all_results, "fund": fund, "tech": tech, "sent": sent,
        "risk_data": risk_data, "sc_data": sc_data, "raw_data": raw_data,
        "reg_ctx": reg_ctx,
    }


def _run_phase2_silent(intents, ticker, raw_data, price_df, reg_ctx):
    """Phase 2 without print output (for batch parallel runs)."""
    phase2 = {}
    if "fundamental" in intents:
        phase2["FundamentalAgent"] = (FundamentalAgent(), {"raw_data": raw_data})
    if "technical" in intents:
        phase2["TechnicalAgent"] = (TechnicalAgent(), {"price_df": price_df})
    if "sentiment" in intents:
        phase2["SentimentAgent"] = (SentimentAgent(), {})

    results = {}
    if not phase2:
        return results

    with concurrent.futures.ThreadPoolExecutor() as ex:
        futures = {ex.submit(agent.run, ticker, **kw): name
                   for name, (agent, kw) in phase2.items()}
        for f in concurrent.futures.as_completed(futures):
            name = futures[f]
            try:
                results[name] = f.result()
            except Exception as e:
                results[name] = {"agent": name, "ticker": ticker, "data": {}, "error": str(e)}
            reg_ctx.check_agent(results[name], name)
    return results


def _run_phase3_silent(intents, ticker, fund, tech, sent, risk_data, price_df, spy_df, store, reg_ctx):
    """Phase 3 without print output (for batch parallel runs)."""
    results = {}
    risk_result = RiskAgent().run(ticker, price_df=price_df, spy_df=spy_df)
    results["RiskAgent"] = risk_result
    r_data = risk_result.get("data", {})
    reg_ctx.check_agent(risk_result, "RiskAgent")

    if "portfolio" in intents or ({"fundamental", "technical"} <= intents):
        port_result = PortfolioAgent().run(
            ticker, fundamental=fund, technical=tech,
            sentiment=sent, risk=r_data, portfolio_store=store,
        )
        results["PortfolioAgent"] = port_result
        reg_ctx.check_agent(port_result, "PortfolioAgent")

    return results, r_data


class Orchestrator:
    def analyze(self, query: str, ticker: str,
                agents: list[str] | None = None, output_format: str = "text") -> str:
        total_start = time.time()
        store = PortfolioStore()
        mm = MemoryManager()

        last = mm.get_last_analysis(ticker)
        if last:
            print(f"[Memory] Last analysis of {ticker}: {last.date} — "
                  f"Signal={last.team_signal}, Grade={last.team_grade}")

        r = _run_single_ticker(ticker, query, agents, store, silent=False)
        if r["error"]:
            return f"ERROR: {r['error']}"

        all_results = r["all_results"]
        fund, tech, sent = r["fund"], r["tech"], r["sent"]
        raw_data, sc_data, reg_ctx = r["raw_data"], r["sc_data"], r["reg_ctx"]

        # Phase 5: Report
        t = time.time()
        print("[Phase 5/5] Generating report...")
        rpt = ReportAgent().run(ticker, all_results=all_results,
                                regulation_ctx=reg_ctx, output_format=output_format,
                                portfolio_store=store)
        reg_ctx.check_agent(rpt, "ReportAgent")
        print(f"[Phase 5/5] Done ({_fmt(time.time() - t)})")

        _save_to_memory(mm, ticker, query, sc_data, fund, tech, sent, raw_data)
        self._print_regulation(reg_ctx)
        print(f"\n[Orchestrator] Total time: {_fmt(time.time() - total_start)}")
        return rpt["data"]["report_text"]

    def analyze_batch(self, tickers: list[str], query: str = "综合分析",
                      agents: list[str] | None = None, output_format: str = "text") -> str:
        from agents.batch_report import build_batch_report
        if not tickers:
            return "ERROR: No tickers provided."
        tickers = tickers[:MAX_BATCH_TICKERS]
        store = PortfolioStore()
        mm = MemoryManager()

        print(f"\n[Batch] Analyzing {len(tickers)} tickers: {', '.join(tickers)}")
        print(f"[Batch] Query: {query}")

        def _run(ticker):
            return _run_single_ticker(ticker, query, agents, store, silent=True)

        workers = min(len(tickers), 5)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_run, t): t for t in tickers}
            raw_results = {}
            for f in concurrent.futures.as_completed(futures):
                ticker = futures[f]
                try:
                    raw_results[ticker] = f.result()
                except Exception as e:
                    raw_results[ticker] = {"ticker": ticker, "error": str(e),
                                           "all_results": {}, "fund": {}, "tech": {},
                                           "sent": {}, "risk_data": {}, "sc_data": {},
                                           "raw_data": {}, "reg_ctx": None}
                status = "DONE" if not raw_results[ticker]["error"] else "FAILED"
                print(f"  [{status}] {ticker}")

        batch_results = []
        for ticker in tickers:
            r = raw_results[ticker]
            if r["error"]:
                batch_results.append({"ticker": ticker, "error": r["error"]})
                continue

            sc_data = r["sc_data"]
            fund, tech, sent, risk_data = r["fund"], r["tech"], r["sent"], r["risk_data"]
            raw_data, all_results, reg_ctx = r["raw_data"], r["all_results"], r["reg_ctx"]

            _save_to_memory(mm, ticker, query, sc_data, fund, tech, sent, raw_data)

            html_path = None
            if output_format in ("html", "both"):
                rpt = ReportAgent().run(ticker, all_results=all_results,
                                        regulation_ctx=reg_ctx, output_format="html",
                                        portfolio_store=store)
                html_path = rpt.get("data", {}).get("html_path")

            batch_results.append({
                "ticker": ticker, "error": None,
                "all_results": all_results,
                "team_signal": sc_data.get("team_signal", "?"),
                "team_grade": sc_data.get("team_grade", "?"),
                "fundamental_signal": fund.get("rating", "N/A"),
                "technical_signal": tech.get("signal", "N/A"),
                "sentiment_signal": sent.get("overall_sentiment", "N/A"),
                "beta": risk_data.get("beta_vs_spy"),
                "var_95": risk_data.get("var_95_daily"),
                "html_path": html_path,
            })

        return build_batch_report(batch_results, output_format)

    def _print_regulation(self, reg_ctx):
        s = reg_ctx.summary()
        status = "COMPLIANT" if reg_ctx.is_compliant() else "NON-COMPLIANT"
        print(f"\n[Regulation] Tier 1 Status: {status}")
        print(f"[Regulation] Agents: {s['agents_passed']}/{s['agents_checked']} passed")
        if s["runtime_violations"] > 0:
            print(f"[Regulation] Violations: {s['runtime_violations']}")
            for v in s["violations"][:5]:
                print(f"  - {v}")
