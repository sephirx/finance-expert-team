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


class Orchestrator:
    def analyze(self, query: str, ticker: str) -> str:
        intents = classify_intent(query)
        print(f"\n[Orchestrator] Ticker={ticker} | Intents={intents}")

        # Phase 1: Data — downloads ALL price data once, shared with all agents
        print("[Phase 1] Fetching data...")
        data_result = DataAgent().run(ticker)
        if data_result.get("error"):
            return f"ERROR: {data_result['error']}"

        raw_data = data_result.get("data", {})
        price_df = raw_data.get("price_df")
        spy_df   = raw_data.get("spy_df")
        all_results = {"DataAgent": data_result}

        # Phase 2: Analysis agents in parallel — using shared price data
        phase2 = {}
        if "fundamental" in intents:
            phase2["FundamentalAgent"] = (FundamentalAgent(), {"raw_data": raw_data})
        if "technical" in intents:
            phase2["TechnicalAgent"] = (TechnicalAgent(), {"price_df": price_df})
        if "sentiment" in intents:
            phase2["SentimentAgent"] = (SentimentAgent(), {})

        if phase2:
            print(f"[Phase 2] Running in parallel: {list(phase2.keys())}")
            with concurrent.futures.ThreadPoolExecutor() as ex:
                futures = {
                    ex.submit(agent.run, ticker, **kw): name
                    for name, (agent, kw) in phase2.items()
                }
                for f in concurrent.futures.as_completed(futures):
                    name = futures[f]
                    try:
                        all_results[name] = f.result()
                    except Exception as e:
                        all_results[name] = {"agent": name, "ticker": ticker, "data": {}, "error": str(e)}
                        print(f"[Phase 2] {name} FAILED: {e}")
                    else:
                        print(f"[Phase 2] {name} done.")

        # Phase 3: Risk + Portfolio (need phase 2 results)
        fund_data = all_results.get("FundamentalAgent", {}).get("data", {})
        tech_data = all_results.get("TechnicalAgent",   {}).get("data", {})
        sent_data = all_results.get("SentimentAgent",   {}).get("data", {})

        risk_data = {}
        if "risk" in intents or "portfolio" in intents:
            print("[Phase 3] Running RiskAgent...")
            risk_result = RiskAgent().run(ticker, price_df=price_df, spy_df=spy_df)
            all_results["RiskAgent"] = risk_result
            risk_data = risk_result.get("data", {})

        if "portfolio" in intents or ({"fundamental", "technical"} <= intents):
            print("[Phase 3] Running PortfolioAgent...")
            port_result = PortfolioAgent().run(
                ticker,
                fundamental=fund_data,
                technical=tech_data,
                sentiment=sent_data,
                risk=risk_data,
            )
            all_results["PortfolioAgent"] = port_result

        # Phase 4: Backtest (uses shared price data)
        if "backtest" in intents:
            print("[Phase 4] Running BacktestAgent...")
            all_results["BacktestAgent"] = BacktestAgent().run(ticker, price_df=price_df)

        # Phase 5: Report (always last)
        print("[Phase 5] Generating report...")
        report_result = ReportAgent().run(ticker, all_results=all_results)
        return report_result["data"]["report_text"]
