"""
Visual Report — Plotly HTML dashboard builder (Point 6).
All functions ≤60 lines (R4). No recursion (R1).
"""

import os
import tempfile
import webbrowser
from datetime import datetime

import plotly.graph_objects as go
from plotly.subplots import make_subplots

C_BG = "#FFEDC7"
C_CARD = "#FFFFFF"
C_TEXT = "#3D2020"
C_GREEN = "#2E8B57"
C_RED = "#EB4C4C"
C_BLUE = "#FF7070"
C_YELLOW = "#FFA6A6"
C_PURPLE = "#EB4C4C"
C_ORANGE = "#FF7070"
C_GRID = "#FFA6A6"


def _pct(v):
    return f"{v:.1%}" if v is not None else "N/A"


def _flt(v, d=2):
    return f"{v:.{d}f}" if v is not None else "N/A"


def _dark_layout(fig, height=400, title=""):
    """Apply warm theme to a figure."""
    fig.update_layout(
        template="plotly_white", paper_bgcolor=C_BG, plot_bgcolor=C_CARD,
        font=dict(color=C_TEXT, family="Inter, system-ui, sans-serif"),
        height=height, showlegend=True, margin=dict(l=60, r=30, t=60, b=30),
        title=dict(text=title, font=dict(size=16)) if title else {},
    )
    fig.update_xaxes(gridcolor=C_GRID, showgrid=True)
    fig.update_yaxes(gridcolor=C_GRID, showgrid=True)


def _add_candlestick(fig, dates, ohlc):
    """Add candlestick or line trace to price chart."""
    if all(k in ohlc for k in ("open", "high", "low", "close")):
        fig.add_trace(go.Candlestick(
            x=dates, open=ohlc["open"], high=ohlc["high"],
            low=ohlc["low"], close=ohlc["close"], name="Price",
            increasing_line_color=C_GREEN, decreasing_line_color=C_RED,
        ), row=1, col=1)
    elif "close" in ohlc:
        fig.add_trace(go.Scatter(
            x=dates, y=ohlc["close"], name="Close",
            line=dict(color=C_TEXT, width=1),
        ), row=1, col=1)


def _add_sma_overlays(fig, dates, series):
    """Add SMA lines to price chart."""
    sma_config = [("sma20", C_BLUE, "SMA 20"), ("sma50", C_ORANGE, "SMA 50"),
                  ("sma200", C_PURPLE, "SMA 200")]
    for key, color, name in sma_config:
        if key in series:
            fig.add_trace(go.Scatter(
                x=dates, y=series[key], name=name,
                line=dict(color=color, width=1, dash="dot"), opacity=0.8,
            ), row=1, col=1)


def _add_bollinger(fig, dates, series):
    """Add Bollinger Bands to price chart."""
    if "bb_upper" not in series or "bb_lower" not in series:
        return
    fig.add_trace(go.Scatter(
        x=dates, y=series["bb_upper"], name="BB Upper",
        line=dict(color=C_YELLOW, width=0.5, dash="dash"), opacity=0.4,
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=dates, y=series["bb_lower"], name="BB Lower",
        line=dict(color=C_YELLOW, width=0.5, dash="dash"),
        fill="tonexty", fillcolor="rgba(255,166,166,0.1)", opacity=0.4,
    ), row=1, col=1)


def _add_rsi(fig, dates, series):
    """Add RSI subplot."""
    if "rsi" not in series:
        return
    fig.add_trace(go.Scatter(x=dates, y=series["rsi"], name="RSI",
                             line=dict(color=C_BLUE, width=1.5)), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color=C_RED, opacity=0.5, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color=C_GREEN, opacity=0.5, row=2, col=1)


def _add_macd(fig, dates, series):
    """Add MACD subplot."""
    if "macd" in series and "macd_signal" in series:
        fig.add_trace(go.Scatter(x=dates, y=series["macd"], name="MACD",
                                 line=dict(color=C_BLUE, width=1.5)), row=3, col=1)
        fig.add_trace(go.Scatter(x=dates, y=series["macd_signal"], name="Signal",
                                 line=dict(color=C_ORANGE, width=1.5)), row=3, col=1)
    if "macd_hist" in series:
        colors = [C_GREEN if (v or 0) >= 0 else C_RED for v in series["macd_hist"]]
        fig.add_trace(go.Bar(x=dates, y=series["macd_hist"], name="Histogram",
                             marker_color=colors, opacity=0.6), row=3, col=1)


def build_price_chart(series, ticker):
    """Build price chart with RSI and MACD subplots."""
    dates = series.get("dates", [])
    ohlc = series.get("ohlc", {})
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                        row_heights=[0.6, 0.2, 0.2],
                        subplot_titles=(f"{ticker} Price", "RSI (14)", "MACD"))
    _add_candlestick(fig, dates, ohlc)
    _add_sma_overlays(fig, dates, series)
    _add_bollinger(fig, dates, series)
    _add_rsi(fig, dates, series)
    _add_macd(fig, dates, series)
    _dark_layout(fig, height=800)
    fig.update_layout(xaxis_rangeslider_visible=False,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig


def build_radar_chart(fund_data):
    """Build fundamental radar chart."""
    mappings = [
        ("P/E", "pe_ratio", lambda v: max(0, 10 - v / 5) if v else 5),
        ("ROE", "roe", lambda v: min(10, v * 40) if v else 5),
        ("Rev Growth", "revenue_growth", lambda v: min(10, max(0, v * 50 + 5)) if v else 5),
        ("Debt Health", "debt_to_equity", lambda v: max(0, 10 - v / 30) if v else 5),
        ("Upside", "analyst_upside_pct", lambda v: min(10, max(0, v / 3 + 5)) if v else 5),
        ("Earn Growth", "earnings_growth", lambda v: min(10, max(0, v * 30 + 5)) if v else 5),
    ]
    cats = [m[0] for m in mappings] + [mappings[0][0]]
    vals = [round(m[2](fund_data.get(m[1])), 1) for m in mappings]
    vals.append(vals[0])

    fig = go.Figure(go.Scatterpolar(r=vals, theta=cats, fill="toself",
                                     fillcolor="rgba(235,76,76,0.15)",
                                     line=dict(color=C_RED, width=2)))
    fig.update_layout(
        polar=dict(bgcolor=C_CARD,
                   radialaxis=dict(visible=True, range=[0, 10], gridcolor=C_GRID, color=C_TEXT),
                   angularaxis=dict(gridcolor=C_GRID, color=C_TEXT)),
        template="plotly_white", paper_bgcolor=C_BG,
        font=dict(color=C_TEXT, family="Inter, system-ui, sans-serif"),
        height=400, showlegend=False, margin=dict(l=60, r=60, t=60, b=40),
        title=dict(text="Fundamental Radar", font=dict(size=16)),
    )
    return fig


def build_signal_bar(scorecard):
    """Build signal agreement horizontal bar."""
    signals = scorecard.get("agent_signals", {})
    signal_map = {"BUY": 1, "BULLISH": 1, "POSITIVE": 1,
                  "HOLD": 0, "NEUTRAL": 0,
                  "SELL": -1, "BEARISH": -1, "NEGATIVE": -1}
    agents = [a.title() for a in signals]
    values = [signal_map.get(s, 0) for s in signals.values()]
    colors = [C_GREEN if v > 0 else C_RED if v < 0 else C_YELLOW for v in values]

    fig = go.Figure(go.Bar(x=values, y=agents, orientation="h", marker_color=colors,
                           text=list(signals.values()), textposition="outside",
                           textfont=dict(color=C_TEXT)))
    _dark_layout(fig, height=200, title="Signal Agreement")
    fig.update_layout(xaxis=dict(range=[-1.5, 1.5], dtick=1, gridcolor=C_GRID,
                                 ticktext=["SELL", "HOLD", "BUY"], tickvals=[-1, 0, 1]),
                      showlegend=False, margin=dict(l=100, r=60, t=50, b=30))
    return fig


def build_risk_gauges(risk_data):
    """Build risk gauge indicators."""
    metrics = [
        ("VaR (95%)", risk_data.get("var_95_daily"), -0.05, 0, True),
        ("Beta", risk_data.get("beta_vs_spy"), 0, 2.5, False),
        ("Max DD", risk_data.get("max_drawdown"), -0.5, 0, True),
        ("Volatility", risk_data.get("annualized_volatility"), 0, 0.6, False),
    ]
    fig = make_subplots(rows=1, cols=4, specs=[[{"type": "indicator"}] * 4],
                        horizontal_spacing=0.05)
    for i, (name, val, mn, mx, is_pct) in enumerate(metrics, 1):
        fig.add_trace(go.Indicator(
            mode="gauge+number", value=val if val is not None else 0,
            title=dict(text=name, font=dict(size=13, color=C_TEXT)),
            number=dict(font=dict(size=18, color=C_TEXT),
                        valueformat=".1%" if is_pct else ".2f"),
            gauge=dict(axis=dict(range=[mn, mx], tickcolor=C_TEXT),
                       bar=dict(color=C_BLUE), bgcolor=C_CARD, bordercolor=C_GRID,
                       steps=[{"range": [mn, mn + (mx - mn) * 0.33],
                               "color": C_RED if is_pct else C_GREEN},
                              {"range": [mn + (mx - mn) * 0.33, mn + (mx - mn) * 0.66],
                               "color": C_YELLOW},
                              {"range": [mn + (mx - mn) * 0.66, mx],
                               "color": C_GREEN if is_pct else C_RED}]),
        ), row=1, col=i)
    _dark_layout(fig, height=250)
    fig.update_layout(margin=dict(l=30, r=30, t=50, b=20))
    return fig


def _build_charts_html(all_results):
    """Build all chart HTML fragments. Returns combined string."""
    tech = all_results.get("TechnicalAgent", {}).get("data", {})
    fund = all_results.get("FundamentalAgent", {}).get("data", {})
    risk = all_results.get("RiskAgent", {}).get("data", {})
    sc = all_results.get("ScorecardAgent", {}).get("data", {})
    series = tech.get("series", {})

    parts = []
    if series and series.get("dates"):
        parts.append(build_price_chart(series, tech.get("ticker", "")).to_html(
            full_html=False, include_plotlyjs=False))
    if fund:
        parts.append(build_radar_chart(fund).to_html(full_html=False, include_plotlyjs=False))
    if sc.get("agent_signals"):
        parts.append(build_signal_bar(sc).to_html(full_html=False, include_plotlyjs=False))
    if risk:
        parts.append(build_risk_gauges(risk).to_html(full_html=False, include_plotlyjs=False))
    return "\n".join(parts)


def _build_scorecard_table(scorecard, risk_data):
    """Build HTML table rows for scorecard metrics."""
    pairs = [
        ("Hit Rate (30d)", _pct(scorecard.get("hit_rate_30d"))),
        ("Hit Rate (60d)", _pct(scorecard.get("hit_rate_60d"))),
        ("Hit Rate (90d)", _pct(scorecard.get("hit_rate_90d"))),
        ("Sharpe", _flt(risk_data.get("sharpe_ratio"))),
        ("Sortino", _flt(risk_data.get("sortino_ratio"))),
        ("Calmar", _flt(scorecard.get("calmar_ratio"))),
        ("Info Ratio", _flt(scorecard.get("information_ratio"))),
        ("Alpha vs SPY", _pct(scorecard.get("annualized_alpha"))),
        ("Risk Level", risk_data.get("risk_level", "N/A")),
    ]
    return "".join(f"<tr><td>{n}</td><td>{v}</td></tr>" for n, v in pairs)


def _build_portfolio_html(portfolio):
    """Build portfolio context HTML section."""
    ctx = portfolio.get("portfolio_context", {})
    if not ctx or not ctx.get("has_portfolio"):
        return ""
    sugg = "".join(f'<li style="color:{C_GREEN}">{s}</li>' for s in ctx.get("suggestions", []))
    warn = "".join(f'<li style="color:{C_RED}">{w}</li>' for w in ctx.get("warnings", []))
    held = ""
    if ctx.get("currently_held"):
        pnl = ctx.get("unrealized_pnl_pct", 0)
        pc = C_GREEN if pnl >= 0 else C_RED
        held = (f'<div style="margin-bottom:12px"><span>{ctx.get("holding_shares", 0)} shares '
                f'@ ${ctx.get("avg_cost", 0):.2f}</span>'
                f'<span style="color:{pc};margin-left:16px">P&L: {pnl:+.1f}%</span></div>')
    return (f'<div class="card"><h2>Portfolio Context</h2>{held}'
            f'{"<ul>" + sugg + "</ul>" if sugg else ""}'
            f'{"<ul>" + warn + "</ul>" if warn else ""}</div>')


def _build_decision_html(portfolio):
    """Build recommendation section HTML."""
    if not portfolio:
        return ""
    dec = portfolio.get("decision", "N/A")
    dc = {"BUY": C_GREEN, "SELL": C_RED, "HOLD": C_YELLOW}.get(dec, C_TEXT)
    return (f'<div class="card"><h2>Recommendation</h2>'
            f'<div style="display:flex;gap:32px;align-items:center;flex-wrap:wrap">'
            f'<div><div style="font-size:36px;font-weight:700;color:{dc}">{dec}</div>'
            f'<div style="opacity:0.6">Conviction: {portfolio.get("conviction", "N/A")}</div></div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px">'
            f'<div><div style="opacity:0.6">Entry</div>${portfolio.get("entry_price", "N/A")}</div>'
            f'<div><div style="opacity:0.6">Target</div>${portfolio.get("target_price", "N/A")}</div>'
            f'<div><div style="opacity:0.6">Stop</div>${portfolio.get("stop_loss", "N/A")}</div>'
            f'</div></div></div>')


def _notes_html(label, notes):
    """Build a notes card."""
    if not notes:
        return ""
    items = "".join(f'<li style="padding:4px 0;font-size:13px">{n}</li>' for n in notes)
    return f'<div class="card"><h2>{label}</h2><ul>{items}</ul></div>'


def build_html_report(ticker, all_results, portfolio_store=None):
    """Assemble full HTML dashboard from chart fragments."""
    sc = all_results.get("ScorecardAgent", {}).get("data", {})
    portfolio = all_results.get("PortfolioAgent", {}).get("data", {})
    fund = all_results.get("FundamentalAgent", {}).get("data", {})
    tech = all_results.get("TechnicalAgent", {}).get("data", {})
    risk = all_results.get("RiskAgent", {}).get("data", {})

    grade = sc.get("team_grade", "?")
    signal = sc.get("team_signal", "?")
    gc = {"A": C_GREEN, "B+": C_GREEN, "B": C_BLUE, "C": C_YELLOW, "D": C_RED}.get(grade, C_TEXT)
    sigc = {"BUY": C_GREEN, "SELL": C_RED, "HOLD": C_YELLOW}.get(signal, C_TEXT)

    charts = _build_charts_html(all_results)
    sc_table = _build_scorecard_table(sc, risk)
    port_html = _build_portfolio_html(portfolio)
    dec_html = _build_decision_html(portfolio)
    fund_notes = _notes_html("Fundamental Notes", fund.get("scoring_notes", []))
    tech_notes = _notes_html("Technical Notes", tech.get("scoring_notes", []))
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    return _html_template(ticker, now, grade, gc, signal, sigc,
                          sc.get("signal_agreement", "?"),
                          dec_html, charts, sc_table, port_html, fund_notes, tech_notes)


def _html_template(ticker, now, grade, gc, signal, sigc, agreement,
                   dec_html, charts, sc_table, port_html, fund_notes, tech_notes):
    """Return the full HTML string."""
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{ticker} — Finance Expert Team</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:{C_BG};color:{C_TEXT};font-family:Inter,-apple-system,system-ui,sans-serif;
padding:24px;max-width:1200px;margin:0 auto}}
.header{{display:flex;justify-content:space-between;align-items:center;padding:24px 0;
border-bottom:1px solid {C_GRID};margin-bottom:24px;flex-wrap:wrap;gap:16px}}
.header h1{{font-size:28px;font-weight:700}}
.grade-badge{{display:inline-flex;align-items:center;gap:12px;padding:12px 24px;
background:{C_CARD};border-radius:12px;border:1px solid {C_GRID}}}
.grade{{font-size:42px;font-weight:800;color:{gc}}}
.signal{{font-size:20px;font-weight:600;color:{sigc}}}
.card{{background:{C_CARD};border:1px solid {C_GRID};border-radius:12px;padding:20px;margin-bottom:20px}}
.card h2{{font-size:16px;font-weight:600;margin-bottom:16px;opacity:0.8}}
.card ul{{list-style:none;padding:0}}
.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
@media(max-width:768px){{.grid-2{{grid-template-columns:1fr}}}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:10px 16px;text-align:left;border-bottom:1px solid {C_GRID};font-size:14px}}
th{{opacity:0.6;font-weight:500}}
.footer{{text-align:center;padding:24px 0;opacity:0.4;font-size:12px;
border-top:1px solid {C_GRID};margin-top:24px}}
</style></head><body>
<div class="header"><div><h1>{ticker}</h1>
<div style="opacity:0.5;font-size:14px">{now} · Finance Expert Team</div></div>
<div class="grade-badge"><div class="grade">{grade}</div>
<div><div class="signal">{signal}</div>
<div style="font-size:12px;opacity:0.5">Agreement: {agreement}</div></div></div></div>
{dec_html}
<div class="card">{charts}</div>
<div class="grid-2"><div class="card"><h2>Scorecard</h2>
<table><thead><tr><th>Metric</th><th>Value</th></tr></thead>
<tbody>{sc_table}</tbody></table></div>
<div>{port_html}{fund_notes}{tech_notes}</div></div>
<div class="footer">Educational purposes only. Not financial advice.</div>
</body></html>"""


def open_in_browser(ticker, html):
    """Write HTML to a temp file and open it in the default browser."""
    filename = f"{ticker}_{datetime.now().strftime('%Y-%m-%d')}.html"
    path = os.path.join(tempfile.gettempdir(), filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open(f"file://{path}")
    return path
