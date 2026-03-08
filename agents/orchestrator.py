import time
import concurrent.futures
from agents.data_agent import DataAgent
from agents.fundamental_agent import FundamentalAgent
from agents.technical_agent import TechnicalAgent
from agents.sentiment_agent import SentimentAgent
from agents.risk_agent import RiskAgent
from agents.portfolio_agent import PortfolioAgent
from agents.backtest_agent import BacktestAgent
from agents.report_agent import ReportAgent

INTENT_MAP = {
    "fundamental": ["valuation", "value", "worth", "dcf", "pe", "price target", "overvalued", "undervalued", "buy", "sell"],
    "technical":   ["chart", "technical", "trend", "signal", "entry", "exit", "rsi", "macd", "moving average", "timing"],
    "sentiment":   ["sentiment", "news", "feeling", "opinion", "analyst", "upgrade", "downgrade", "insider"],
    "risk":        ["risk", "volatility", "drawdown", "var", "safe", "hedge", "exposure", "position"],
    "backtest":    ["backtest", "historical", "strategy", "simulate", "test", "past performance"],
    "portfolio":   ["portfolio", "allocate", "diversify", "build", "rebalance", "weights", "invest"],
}


def classify_intent(query: str) -> set[str]:
    q = query.lower()
    matched = {intent for intent, keywords in INTENT_MAP.items() if any(k in q for k in keywords)}
    return matched or {"fundamental", "technical"}


def _fmt(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    return f"{seconds:.1f}s"


class Orchestrator:
    def analyze(self, query: str, ticker: str) -> str:
        total_start = time.time()
        intents = classify_intent(query)

        # Count expected agents
        agent_count = 1  # DataAgent always
        if "fundamental" in intents: agent_count += 1
        if "technical" in intents:   agent_count += 1
        if "sentiment" in intents:   agent_count += 1
        if "risk" in intents or "portfolio" in intents: agent_count += 1
        if "portfolio" in intents or ({"fundamental", "technical"} <= intents): agent_count += 1
        if "backtest" in intents:    agent_count += 1
        agent_count += 1  # ReportAgent always

        print(f"\n[Orchestrator] Ticker={ticker} | Intents={intents}")
        print(f"[Orchestrator] Will run {agent_count} agents\n")

        # Phase 1: Data
        t = time.time()
        print("[Phase 1/5] Fetching market data...")
        data_result = DataAgent().run(ticker)
        phase1_time = time.time() - t

        if data_result.get("error"):
            print(f"[Phase 1/5] FAILED ({_fmt(phase1_time)})")
            return f"ERROR: {data_result['error']}"

        raw_data = data_result.get("data", {})
        price_df = raw_data.get("price_df")
        spy_df   = raw_data.get("spy_df")
        all_results = {"DataAgent": data_result}
        print(f"[Phase 1/5] Done ({_fmt(phase1_time)})")

        # Phase 2: Analysis agents in parallel
        phase2 = {}
        if "fundamental" in intents:
            phase2["FundamentalAgent"] = (FundamentalAgent(), {"raw_data": raw_data})
        if "technical" in intents:
            phase2["TechnicalAgent"] = (TechnicalAgent(), {"price_df": price_df})
        if "sentiment" in intents:
            phase2["SentimentAgent"] = (SentimentAgent(), {})

        if phase2:
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
                        all_results[name] = f.result()
                    except Exception as e:
                        all_results[name] = {"agent": name, "ticker": ticker, "data": {}, "error": str(e)}
                        print(f"  {name}: FAILED ({_fmt(elapsed)})")
                    else:
                        print(f"  {name}: done ({_fmt(elapsed)})")
            print(f"[Phase 2/5] All done ({_fmt(time.time() - t)})")
        else:
            print("[Phase 2/5] Skipped — no analysis agents needed")

        # Phase 3: Risk + Portfolio
        fund_data = all_results.get("FundamentalAgent", {}).get("data", {})
        tech_data = all_results.get("TechnicalAgent",   {}).get("data", {})
        sent_data = all_results.get("SentimentAgent",   {}).get("data", {})

        risk_data = {}
        ran_phase3 = False
        t = time.time()

        if "risk" in intents or "portfolio" in intents:
            ran_phase3 = True
            t2 = time.time()
            print("[Phase 3/5] Running RiskAgent...")
            risk_result = RiskAgent().run(ticker, price_df=price_df, spy_df=spy_df)
            all_results["RiskAgent"] = risk_result
            risk_data = risk_result.get("data", {})
            print(f"  RiskAgent: done ({_fmt(time.time() - t2)})")

        if "portfolio" in intents or ({"fundamental", "technical"} <= intents):
            ran_phase3 = True
            t2 = time.time()
            print("[Phase 3/5] Running PortfolioAgent...")
            port_result = PortfolioAgent().run(
                ticker,
                fundamental=fund_data,
                technical=tech_data,
                sentiment=sent_data,
                risk=risk_data,
            )
            all_results["PortfolioAgent"] = port_result
            print(f"  PortfolioAgent: done ({_fmt(time.time() - t2)})")

        if ran_phase3:
            print(f"[Phase 3/5] All done ({_fmt(time.time() - t)})")
        else:
            print("[Phase 3/5] Skipped")

        # Phase 4: Backtest
        if "backtest" in intents:
            t = time.time()
            print("[Phase 4/5] Running BacktestAgent...")
            all_results["BacktestAgent"] = BacktestAgent().run(ticker, price_df=price_df)
            print(f"[Phase 4/5] Done ({_fmt(time.time() - t)})")
        else:
            print("[Phase 4/5] Skipped — no backtest requested")

        # Phase 5: Report
        t = time.time()
        print("[Phase 5/5] Generating report...")
        report_result = ReportAgent().run(ticker, all_results=all_results)
        print(f"[Phase 5/5] Done ({_fmt(time.time() - t)})")

        total = time.time() - total_start
        print(f"\n[Orchestrator] Total time: {_fmt(total)}")

        return report_result["data"]["report_text"]
