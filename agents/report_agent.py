import json
from datetime import datetime
from core.base_agent import BaseAgent
from regulation.runtime_guards import RegulationContext

_SKIP_FIELDS = {"price_history_csv", "price_df", "spy_df", "source", "grade_breakdown"}


class ReportAgent(BaseAgent):
    def __init__(self):
        super().__init__("ReportAgent")

    def _build_scorecard(self, all_results: dict, ticker: str) -> str:
        sc = all_results.get("ScorecardAgent", {}).get("data", {})
        risk = all_results.get("RiskAgent", {}).get("data", {})
        bt = all_results.get("BacktestAgent", {}).get("data", {})

        if not sc:
            return ""

        def pct(v):
            return f"{v:.1%}" if v is not None else "N/A"

        def flt(v, d=2):
            return f"{v:.{d}f}" if v is not None else "N/A"

        grade    = sc.get("team_grade", "?")
        signal   = sc.get("team_signal", "?")
        agree    = sc.get("signal_agreement", "?")
        hr30     = sc.get("hit_rate_30d")
        hr60     = sc.get("hit_rate_60d")
        hr90     = sc.get("hit_rate_90d")
        calmar   = sc.get("calmar_ratio")
        cvar     = sc.get("cvar_99_daily")
        te       = sc.get("tracking_error")
        ir       = sc.get("information_ratio")
        alpha    = sc.get("annualized_alpha")
        sharpe   = risk.get("sharpe_ratio")
        sortino  = risk.get("sortino_ratio")
        var95    = risk.get("var_95_daily")
        cvar99   = risk.get("cvar_99_daily")
        maxdd    = risk.get("max_drawdown")
        beta     = risk.get("beta_vs_spy")
        vol      = risk.get("annualized_volatility")
        rlevel   = risk.get("risk_level")
        bt_ret   = bt.get("total_return")
        bh_ret   = bt.get("buy_and_hold_return")
        bt_verd  = bt.get("verdict")

        signals  = sc.get("agent_signals", {})
        fund_sig = signals.get("fundamental", "N/A")
        tech_sig = signals.get("technical", "N/A")
        sent_sig = signals.get("sentiment", "N/A")

        lines = []
        lines.append("")
        lines.append("```")
        lines.append(f"{'='*56}")
        lines.append(f"  PERFORMANCE SCORECARD — {ticker}       Grade: {grade}")
        lines.append(f"{'='*56}")
        lines.append(f"")
        lines.append(f"  Team Signal: {signal:<10}  Agreement: {agree}")
        lines.append(f"    Fundamental: {fund_sig:<12} Technical: {tech_sig}")
        lines.append(f"    Sentiment:   {sent_sig}")
        lines.append(f"")
        lines.append(f"  Signal Quality")
        lines.append(f"    Hit Rate (30d): {pct(hr30):>7}   (60d): {pct(hr60):>7}   (90d): {pct(hr90):>7}")
        lines.append(f"    Information Coefficient: {flt(ir)}")
        lines.append(f"")
        lines.append(f"  Risk-Adjusted Returns")
        lines.append(f"    Sharpe:  {flt(sharpe):>7}   Sortino: {flt(sortino):>7}")
        lines.append(f"    Calmar:  {flt(calmar):>7}   Info Ratio: {flt(ir):>7}")
        lines.append(f"    Alpha vs SPY: {pct(alpha)}")
        lines.append(f"")
        lines.append(f"  Risk Profile")
        lines.append(f"    VaR (95%): {pct(var95):>7}   CVaR (99%): {pct(cvar99):>7}")
        lines.append(f"    Beta: {flt(beta):>7}   Volatility: {pct(vol):>7}")
        lines.append(f"    Max Drawdown: {pct(maxdd):>7}   Risk Level: {rlevel}")
        lines.append(f"    Tracking Error: {pct(te)}")
        lines.append(f"")

        if bt_ret is not None:
            lines.append(f"  Backtest (SMA 50/200)")
            lines.append(f"    Strategy: {pct(bt_ret):>7}   Buy&Hold: {pct(bh_ret):>7}")
            lines.append(f"    Verdict: {bt_verd}")
            lines.append(f"")

        lines.append(f"{'='*56}")
        lines.append("```")
        lines.append("")

        return "\n".join(lines)

    def _build_regulation_section(self, reg_ctx: RegulationContext | None) -> str:
        """Build Tier 1 Regulation compliance section for the report."""
        if reg_ctx is None:
            return ""

        summary = reg_ctx.summary()
        status = "COMPLIANT" if reg_ctx.is_compliant() else "NON-COMPLIANT"

        lines = []
        lines.append("")
        lines.append("```")
        lines.append(f"{'='*56}")
        lines.append(f"  TIER 1 REGULATION — Runtime Compliance")
        lines.append(f"{'='*56}")
        lines.append(f"")
        lines.append(f"  Status:     {status}")
        lines.append(f"  Agents:     {summary['agents_passed']}/{summary['agents_checked']} passed")
        lines.append(f"  Violations: {summary['runtime_violations']}")
        lines.append(f"  Warnings:   {summary['runtime_warnings']}")
        lines.append(f"")

        if summary["violations"]:
            lines.append(f"  Issues:")
            for v in summary["violations"]:
                lines.append(f"    - {v}")
            lines.append(f"")

        lines.append(f"  Rules Enforced:")
        lines.append(f"    R1: No Recursion          R2: Bounded Loops")
        lines.append(f"    R3: Memory Bounds          R5: I/O Validation")
        lines.append(f"    R7: Error Propagation      R9: Nesting Depth")
        lines.append(f"")
        lines.append(f"  Source: Power of Ten (NASA/JPL) — G. Holzmann")
        lines.append(f"{'='*56}")
        lines.append("```")
        lines.append("")

        return "\n".join(lines)

    def run(self, ticker: str, **kwargs) -> dict:
        if not ticker or not isinstance(ticker, str):
            return self._error(str(ticker), "Invalid ticker for ReportAgent.")

        all_results = kwargs.get("all_results", {})
        if not all_results:
            return self._error(ticker, "No agent results provided to ReportAgent.")

        reg_ctx = kwargs.get("regulation_ctx")

        lines = []
        lines.append(f"# {ticker} — Finance Expert Team Report")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

        # Scorecard first if available
        scorecard = self._build_scorecard(all_results, ticker)
        if scorecard:
            lines.append(scorecard)

        # Agent details
        for agent_name, result in all_results.items():
            if agent_name == "ScorecardAgent":
                continue  # already rendered as scorecard
            if not isinstance(result, dict):
                continue
            lines.append(f"## {agent_name}")
            if result.get("error"):
                lines.append(f"ERROR: {result['error']}\n")
                continue
            data = result.get("data", {})
            for key, val in data.items():
                if key in _SKIP_FIELDS or val is None:
                    continue
                if hasattr(val, "iloc"):
                    continue
                if isinstance(val, float):
                    if any(k in key for k in ["return", "drawdown", "volatility", "growth", "yield", "rate", "var_", "cvar"]):
                        lines.append(f"- **{key}**: {val:.2%}")
                    else:
                        lines.append(f"- **{key}**: {val:.4f}")
                elif isinstance(val, list):
                    lines.append(f"- **{key}**:")
                    for item in val:
                        lines.append(f"  - {item}")
                elif isinstance(val, dict):
                    lines.append(f"- **{key}**: {json.dumps(val)}")
                else:
                    lines.append(f"- **{key}**: {val}")
            lines.append("")

        # Tier 1 Regulation section
        reg_section = self._build_regulation_section(reg_ctx)
        if reg_section:
            lines.append(reg_section)

        lines.append("---")
        lines.append("*This report is generated by Finance Expert Team for educational purposes only.*")
        lines.append("*It does not constitute financial advice. Always do your own research.*")

        report = "\n".join(lines)
        return self._result(ticker, {"report_text": report})
