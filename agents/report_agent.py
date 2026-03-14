"""
ReportAgent — generates analysis reports.
Supports text (Markdown) and html (Plotly) output.
All functions ≤60 lines (R4). No recursion (R1).
"""

import json
from datetime import datetime
from core.base_agent import BaseAgent
from regulation.runtime_guards import RegulationContext

_SKIP_FIELDS = {"price_history_csv", "price_df", "spy_df", "source",
                "grade_breakdown", "series", "data_quality", "portfolio_context"}


def _pct(v):
    return f"{v:.1%}" if v is not None else "N/A"


def _flt(v, d=2):
    return f"{v:.{d}f}" if v is not None else "N/A"


def _build_scorecard_text(sc, risk, ticker):
    """Build the ASCII scorecard block."""
    if not sc:
        return ""
    grade = sc.get("team_grade", "?")
    signal = sc.get("team_signal", "?")
    agree = sc.get("signal_agreement", "?")
    sigs = sc.get("agent_signals", {})

    lines = ["", "```", f"{'='*56}",
             f"  PERFORMANCE SCORECARD — {ticker}       Grade: {grade}",
             f"{'='*56}", "",
             f"  Team Signal: {signal:<10}  Agreement: {agree}",
             f"    Fundamental: {sigs.get('fundamental', 'N/A'):<12} Technical: {sigs.get('technical', 'N/A')}",
             f"    Sentiment:   {sigs.get('sentiment', 'N/A')}", "",
             f"  Signal Quality",
             f"    Hit Rate (30d): {_pct(sc.get('hit_rate_30d')):>7}   "
             f"(60d): {_pct(sc.get('hit_rate_60d')):>7}   (90d): {_pct(sc.get('hit_rate_90d')):>7}",
             f"    Information Coefficient: {_flt(sc.get('information_ratio'))}", "",
             f"  Risk-Adjusted Returns",
             f"    Sharpe:  {_flt(risk.get('sharpe_ratio')):>7}   Sortino: {_flt(risk.get('sortino_ratio')):>7}",
             f"    Calmar:  {_flt(sc.get('calmar_ratio')):>7}   Info Ratio: {_flt(sc.get('information_ratio')):>7}",
             f"    Alpha vs SPY: {_pct(sc.get('annualized_alpha'))}", "",
             f"  Risk Profile",
             f"    VaR (95%): {_pct(risk.get('var_95_daily')):>7}   CVaR (99%): {_pct(risk.get('cvar_99_daily')):>7}",
             f"    Beta: {_flt(risk.get('beta_vs_spy')):>7}   Volatility: {_pct(risk.get('annualized_volatility')):>7}",
             f"    Max Drawdown: {_pct(risk.get('max_drawdown')):>7}   Risk Level: {risk.get('risk_level')}",
             f"    Tracking Error: {_pct(sc.get('tracking_error'))}", "",
             f"{'='*56}", "```", ""]
    return "\n".join(lines)


def _build_portfolio_text(all_results):
    """Build portfolio context section."""
    ctx = all_results.get("PortfolioAgent", {}).get("data", {}).get("portfolio_context", {})
    if not ctx or not ctx.get("has_portfolio"):
        return ""
    lines = ["## Portfolio Context"]
    if ctx.get("currently_held"):
        lines.append(f"- **Currently held**: {ctx.get('holding_shares', 0)} shares "
                     f"@ ${ctx.get('avg_cost', 0):.2f}")
        lines.append(f"- **Unrealized P&L**: {ctx.get('unrealized_pnl_pct', 0):+.1f}%")
        lines.append(f"- **Position size**: {ctx.get('current_position_pct', 0):.1f}% of portfolio")
    for s in ctx.get("suggestions", []):
        lines.append(f"- {s}")
    for w in ctx.get("warnings", []):
        lines.append(f"- **WARNING**: {w}")
    lines.append("")
    return "\n".join(lines)


def _build_regulation_text(reg_ctx):
    """Build regulation compliance section."""
    if reg_ctx is None:
        return ""
    s = reg_ctx.summary()
    status = "COMPLIANT" if reg_ctx.is_compliant() else "NON-COMPLIANT"
    lines = ["", "```", f"{'='*56}", "  TIER 1 REGULATION — Runtime Compliance",
             f"{'='*56}", "", f"  Status:     {status}",
             f"  Agents:     {s['agents_passed']}/{s['agents_checked']} passed",
             f"  Violations: {s['runtime_violations']}", f"  Warnings:   {s['runtime_warnings']}", ""]
    if s["violations"]:
        lines.append("  Issues:")
        for v in s["violations"]:
            lines.append(f"    - {v}")
        lines.append("")
    lines.extend(["  Rules: R1 R2 R3 R5 R7 R9 (Power of Ten — Holzmann)",
                  f"{'='*56}", "```", ""])
    return "\n".join(lines)


def _format_agent_data(data):
    """Format agent data dict into Markdown lines."""
    lines = []
    for key, val in data.items():
        if key in _SKIP_FIELDS or val is None or hasattr(val, "iloc"):
            continue
        if isinstance(val, float):
            is_pct = any(k in key for k in ["return", "drawdown", "volatility",
                                             "growth", "yield", "rate", "var_", "cvar"])
            lines.append(f"- **{key}**: {val:.2%}" if is_pct else f"- **{key}**: {val:.4f}")
        elif isinstance(val, list):
            lines.append(f"- **{key}**:")
            for item in val[:20]:  # R3: bounded
                lines.append(f"  - {item}")
        elif isinstance(val, dict):
            lines.append(f"- **{key}**: {json.dumps(val)}")
        else:
            lines.append(f"- **{key}**: {val}")
    return lines


class ReportAgent(BaseAgent):
    def __init__(self):
        super().__init__("ReportAgent")

    def run(self, ticker: str, **kwargs) -> dict:
        if not ticker or not isinstance(ticker, str):
            return self._error(str(ticker), "Invalid ticker for ReportAgent.")
        all_results = kwargs.get("all_results", {})
        if not all_results:
            return self._error(ticker, "No agent results provided to ReportAgent.")

        reg_ctx = kwargs.get("regulation_ctx")
        fmt = kwargs.get("output_format", "text")
        store = kwargs.get("portfolio_store")

        text = self._build_text(ticker, all_results, reg_ctx)
        result = {"report_text": text}

        if fmt in ("html", "both"):
            try:
                result["html_report_path"] = self._build_html(ticker, all_results, store)
            except Exception as e:
                print(f"  HTML report failed: {e}")

        return self._result(ticker, result)

    def _build_text(self, ticker, all_results, reg_ctx):
        """Build full Markdown text report."""
        lines = [f"# {ticker} — Finance Expert Team Report",
                 f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
        sc = all_results.get("ScorecardAgent", {}).get("data", {})
        risk = all_results.get("RiskAgent", {}).get("data", {})
        lines.append(_build_scorecard_text(sc, risk, ticker))
        lines.append(_build_portfolio_text(all_results))

        for name, result in all_results.items():
            if name == "ScorecardAgent" or not isinstance(result, dict):
                continue
            lines.append(f"## {name}")
            if result.get("error"):
                lines.append(f"ERROR: {result['error']}\n")
                continue
            lines.extend(_format_agent_data(result.get("data", {})))
            lines.append("")

        lines.append(_build_regulation_text(reg_ctx))
        lines.append("---")
        lines.append("*Educational purposes only. Not financial advice.*")
        return "\n".join(lines)

    def _build_html(self, ticker, all_results, store):
        from agents.visual_report import build_html_report, open_in_browser
        html = build_html_report(ticker, all_results, store)
        path = open_in_browser(ticker, html)
        print(f"  HTML report opened in browser: {path}")
        return path
