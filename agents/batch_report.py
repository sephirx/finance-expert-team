"""
Batch Report — comparison table for multi-ticker analysis (Watchlist Batch).
All functions ≤60 lines (R4). No recursion (R1).
"""

import os
import tempfile
import webbrowser
from datetime import date

GRADE_ORDER = {"A": 0, "A-": 1, "B+": 2, "B": 3, "B-": 4, "C": 5, "D": 6, "?": 7}


def build_batch_report(results: list[dict], output_format: str) -> str:
    """Entry point. Returns text report string; html/both also opens browser."""
    success = [r for r in results if not r.get("error")]
    failed = [r for r in results if r.get("error")]

    if not success and failed:
        lines = ["[Batch] All tickers failed:"]
        for r in failed:
            lines.append(f"  {r['ticker']}: {r['error']}")
        return "\n".join(lines)

    text = build_batch_text_report(results)

    if output_format in ("html", "both"):
        html = build_batch_html_report(results)
        path = open_batch_in_browser(results, html)
        text += f"\n\nBatch HTML report: {path}"

    return text


def build_batch_text_report(results: list[dict]) -> str:
    """Generate aligned comparison table + Top Pick line."""
    today = date.today().isoformat()
    success = [r for r in results if not r.get("error")]
    failed = [r for r in results if r.get("error")]
    tickers_str = str(len(results))

    header = (
        f"╔{'═'*62}╗\n"
        f"║  WATCHLIST BATCH ANALYSIS — {today:<32}║\n"
        f"╚{'═'*62}╝\n"
        f"Tickers: {tickers_str}"
    )

    if not success:
        lines = [header, "\nAll tickers failed:"]
        for r in failed:
            lines.append(f"  {r['ticker']}: {r['error']}")
        return "\n".join(lines)

    col_w = {"ticker": 6, "signal": 6, "grade": 5, "fund": 12,
             "tech": 10, "sent": 10, "beta": 6, "var": 8}

    def _row(t, sig, gr, fund, tech, sent, beta, var95):
        def _c(v, w): return str(v or "N/A")[:w].center(w)
        beta_s = f"{beta:.2f}" if isinstance(beta, (int, float)) else "N/A"
        var_s = f"{var95:.1%}" if isinstance(var95, (int, float)) else "N/A"
        return (f"│ {_c(t,6)} │ {_c(sig,6)} │ {_c(gr,5)} │ {_c(fund,12)} │"
                f" {_c(tech,8)} │ {_c(sent,8)} │ {_c(beta_s,6)} │ {_c(var_s,8)} │")

    sep = ("├────────┼────────┼───────┼──────────────┼──────────┼──────────┼────────┼──────────┤")
    top_border = "┌────────┬────────┬───────┬──────────────┬──────────┬──────────┬────────┬──────────┐"
    bot_border = "└────────┴────────┴───────┴──────────────┴──────────┴──────────┴────────┴──────────┘"
    col_header = _row("Ticker", "Signal", "Grade", "Fundamental", "Technical",
                      "Sentiment", "Beta", "VaR(95%)")

    rows = [top_border, col_header, sep]
    for r in results:
        if r.get("error"):
            rows.append(_row(r["ticker"], "ERROR", "—", r["error"][:12], "—", "—", None, None))
        else:
            rows.append(_row(
                r["ticker"], r.get("team_signal", "?"), r.get("team_grade", "?"),
                r.get("fundamental_signal", "N/A"), r.get("technical_signal", "N/A"),
                r.get("sentiment_signal", "N/A"), r.get("beta"), r.get("var_95"),
            ))
    rows.append(bot_border)

    top = _pick_top(success)
    top_line = ""
    if top:
        var_s = f"{top['var_95']:.1%}" if isinstance(top.get("var_95"), (int, float)) else "N/A"
        top_line = (f"\nTop Pick: {top['ticker']} — Grade {top.get('team_grade','?')}, "
                    f"{top.get('team_signal','?')} signal, VaR {var_s}")

    failed_lines = ""
    if failed:
        failed_lines = "\nFailed: " + ", ".join(f"{r['ticker']} ({r['error'][:40]})" for r in failed)

    return "\n".join([header, ""] + rows + [top_line, failed_lines]).rstrip()


def _pick_top(results: list[dict]) -> dict | None:
    """From BUY-signal tickers, pick best by grade then lowest VaR magnitude."""
    buy = [r for r in results if (r.get("team_signal") or "").upper() == "BUY"]
    if not buy:
        buy = results  # fall back to all if none are BUY
    if not buy:
        return None

    def _sort_key(r):
        grade = GRADE_ORDER.get(r.get("team_grade", "?"), 7)
        var = r.get("var_95")
        var_key = abs(var) if isinstance(var, (int, float)) else 1.0
        return (grade, var_key)

    return sorted(buy, key=_sort_key)[0]


def build_batch_html_report(results: list[dict]) -> str:
    """Generate HTML comparison summary page using warm theme."""
    today = date.today().isoformat()
    rows_html = ""
    for r in results:
        if r.get("error"):
            rows_html += (f"<tr><td>{r['ticker']}</td><td colspan='7' style='color:#EB4C4C'>"
                          f"ERROR: {r['error'][:80]}</td></tr>\n")
            continue
        signal = r.get("team_signal", "?")
        sig_color = "#2E8B57" if signal == "BUY" else ("#EB4C4C" if signal == "SELL" else "#888")
        beta = r.get("beta")
        var95 = r.get("var_95")
        beta_s = f"{beta:.2f}" if isinstance(beta, (int, float)) else "N/A"
        var_s = f"{var95:.1%}" if isinstance(var95, (int, float)) else "N/A"
        html_link = ""
        if r.get("html_path") and os.path.exists(r["html_path"]):
            html_link = f' <a href="{r["html_path"]}">↗</a>'
        rows_html += (
            f"<tr>"
            f"<td><b>{r['ticker']}</b>{html_link}</td>"
            f"<td style='color:{sig_color}'><b>{signal}</b></td>"
            f"<td>{r.get('team_grade','?')}</td>"
            f"<td>{r.get('fundamental_signal','N/A')}</td>"
            f"<td>{r.get('technical_signal','N/A')}</td>"
            f"<td>{r.get('sentiment_signal','N/A')}</td>"
            f"<td>{beta_s}</td>"
            f"<td>{var_s}</td>"
            f"</tr>\n"
        )

    top = _pick_top([r for r in results if not r.get("error")])
    top_html = ""
    if top:
        var_s = f"{top['var_95']:.1%}" if isinstance(top.get("var_95"), (int, float)) else "N/A"
        top_html = (f"<p style='margin-top:16px;font-size:1.1em'>"
                    f"<b>Top Pick:</b> {top['ticker']} — Grade {top.get('team_grade','?')}, "
                    f"{top.get('team_signal','?')} signal, VaR {var_s}</p>")

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Batch Analysis — {today}</title>
<style>
  body {{ background:#FFEDC7; color:#3D2020; font-family:Inter,system-ui,sans-serif;
         margin:40px auto; max-width:900px; }}
  h1 {{ font-size:1.4em; }}
  table {{ border-collapse:collapse; width:100%; margin-top:16px; }}
  th,td {{ border:1px solid #FFA6A6; padding:8px 12px; text-align:center; }}
  th {{ background:#fff; font-weight:600; }}
  tr:nth-child(even) {{ background:#fff8ee; }}
</style>
</head>
<body>
<h1>Watchlist Batch Analysis — {today}</h1>
<p>Tickers: {len(results)}</p>
<table>
<thead><tr>
  <th>Ticker</th><th>Signal</th><th>Grade</th>
  <th>Fundamental</th><th>Technical</th><th>Sentiment</th>
  <th>Beta</th><th>VaR(95%)</th>
</tr></thead>
<tbody>
{rows_html}
</tbody>
</table>
{top_html}
</body>
</html>"""


def open_batch_in_browser(results: list[dict], html: str) -> str:
    """Write batch HTML to temp file and open in browser. Returns path."""
    today = date.today().isoformat().replace("-", "")
    tickers_part = "_".join(r["ticker"] for r in results[:4])
    fname = f"batch_{tickers_part}_{today}.html"
    path = os.path.join(tempfile.gettempdir(), fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open(f"file://{path}")
    return path
