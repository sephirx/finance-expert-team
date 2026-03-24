"""
Research Parser — parse research.md files and evaluate criteria.
All functions ≤60 lines (R4). No recursion (R1).
"""

import re
from dataclasses import dataclass, field
from core.intent_router import ALL_AGENTS


@dataclass
class ResearchPlan:
    target:     str
    tickers:    list
    agents:     object          # list[str] | None
    time_range: str
    criteria:   list
    raw_query:  str


# Maps normalized metric names to (source, key_or_lambda)
METRIC_KEY_MAP = {
    "peg ratio": ("peg",    None),          # computed: pe_ratio / (earnings_growth * 100)
    "roe":       ("fund",   "roe"),
    "pe ratio":  ("fund",   "pe_ratio"),
    "pe":        ("fund",   "pe_ratio"),
    "forward pe":("fund",   "forward_pe"),
    "pb ratio":  ("fund",   "pb_ratio"),
    "pb":        ("fund",   "pb_ratio"),
    "roa":       ("fund",   "roa"),
    "revenue growth": ("fund", "revenue_growth"),
    "beta":      ("risk",   "beta_vs_spy"),
}

_OPS = {
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
    "<":  lambda a, b: a < b,
    ">":  lambda a, b: a > b,
    "==": lambda a, b: a == b,
    "=":  lambda a, b: a == b,
}


def _parse_sections(text: str) -> dict:
    """Split markdown on '## ' headings, return dict of section_name → content."""
    sections = {}
    current = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip().lower()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def _parse_tickers(raw: str) -> list:
    """Comma-split, uppercase, filter valid ticker patterns."""
    parts = re.split(r"[,\s]+", raw.strip())
    return [p.upper() for p in parts if re.fullmatch(r"[A-Z]{1,5}", p.upper())]


def _parse_agents(raw: str) -> object:
    """Comma-split, intersect with ALL_AGENTS. None if empty."""
    parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
    valid = [p for p in parts if p in ALL_AGENTS]
    return valid if valid else None


_CONNECTORS = re.compile(r"(且|and|or|或|,|;|\s)+", re.IGNORECASE)


def _parse_criteria(raw: str) -> list:
    """Extract numeric rules from criteria text."""
    # Only match ASCII word chars + spaces/slash for metric names (excludes CJK connectors)
    pattern = r"([A-Za-z][A-Za-z0-9\s/]*?)\s*(<=?|>=?|==?)\s*([\d.]+)(%?)"
    results = []
    for m in re.finditer(pattern, raw):
        metric = m.group(1).strip().lower()
        # Strip any trailing connector words
        metric = _CONNECTORS.sub(" ", metric).strip()
        op     = m.group(2)
        value  = float(m.group(3))
        is_pct = bool(m.group(4))
        threshold = value / 100.0 if is_pct else value
        results.append({"metric": metric, "op": op, "threshold": threshold, "is_pct": is_pct})
    return results


def _get_metric_value(metric: str, fund: dict, risk_data: dict) -> object:
    """Look up metric value from fund/risk data. Returns float or None."""
    entry = METRIC_KEY_MAP.get(metric)
    if entry is None:
        return None
    source, key = entry
    if source == "peg":
        pe = fund.get("pe_ratio")
        eg = fund.get("earnings_growth")
        if pe is None or eg is None or eg == 0:
            return None
        return pe / (eg * 100)
    if source == "fund":
        return fund.get(key)
    if source == "risk":
        return risk_data.get(key)
    return None


def evaluate_criteria(criteria: list, fund: dict, risk_data: dict) -> list:
    """Evaluate each criterion against actual data. Returns list of result dicts."""
    results = []
    for rule in criteria:
        actual = _get_metric_value(rule["metric"], fund, risk_data)
        if actual is None:
            results.append({**rule, "actual": "N/A", "passed": None})
            continue
        op_fn = _OPS.get(rule["op"])
        passed = op_fn(actual, rule["threshold"]) if op_fn else None
        results.append({**rule, "actual": actual, "passed": passed})
    return results


def format_criteria_report(ticker_results: dict) -> str:
    """Format PASS/FAIL evaluation table as string."""
    lines = [
        "\n╔══════════════════════════════════════╗",
        "║  RESEARCH CRITERIA EVALUATION        ║",
        "╚══════════════════════════════════════╝",
    ]
    for ticker, evals in ticker_results.items():
        lines.append(f"\n{ticker}:")
        passed_count = 0
        total = len(evals)
        for e in evals:
            metric_disp = e["metric"].upper()
            op          = e["op"]
            threshold   = e["threshold"]
            is_pct      = e["is_pct"]
            actual      = e["actual"]
            passed      = e["passed"]

            t_str = f"{threshold*100:.2f}%" if is_pct else f"{threshold:.2f}"
            if actual == "N/A":
                a_str  = "N/A"
                status = "[N/A]"
            else:
                a_str  = f"{actual*100:.2f}%" if is_pct else f"{actual:.2f}"
                status = "[PASS ✓]" if passed else "[FAIL ✗]"
                if passed:
                    passed_count += 1

            lines.append(f"  {metric_disp} {op} {t_str:<8}  →  actual: {a_str:<10} {status}")

        lines.append(f"\nVerdict: {ticker} passes {passed_count}/{total}.")
    return "\n".join(lines)


def load_research_plan(path: str) -> ResearchPlan:
    """Parse a research.md file and return a ResearchPlan. Raises ValueError on bad input."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    secs = _parse_sections(text)

    target     = secs.get("研究目标", secs.get("target", "")).strip()
    tickers    = _parse_tickers(secs.get("股票列表", secs.get("tickers", secs.get("ticker list", ""))))
    agents_raw = secs.get("使用 agents", secs.get("agents", secs.get("use agents", "")))
    agents     = _parse_agents(agents_raw) if agents_raw else None
    time_range = secs.get("时间范围", secs.get("time range", "")).strip()
    crit_raw   = secs.get("评判标准", secs.get("criteria", "")).strip()
    criteria   = _parse_criteria(crit_raw) if crit_raw else []

    if not tickers:
        raise ValueError(f"No valid tickers found in research plan: {path}")

    raw_query = target
    if crit_raw:
        raw_query += f"\n评判标准：{crit_raw}"

    return ResearchPlan(
        target=target, tickers=tickers, agents=agents,
        time_range=time_range, criteria=criteria, raw_query=raw_query,
    )
