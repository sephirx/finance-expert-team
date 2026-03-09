#!/usr/bin/env python3
"""
Finance Expert Team
-------------------
Usage:
    python main.py --ticker AAPL --query "Is AAPL a good buy right now?"
    python main.py --ticker TSLA --query "Backtest a moving average strategy"
    python main.py --ticker NVDA --query "What is the risk and technical outlook?"
    python main.py --regulate                 # Run Tier 1 static compliance check
"""

import argparse
import os
from agents.orchestrator import Orchestrator


def run_regulation_check():
    """Run Tier 1 Power of Ten static analysis on the codebase."""
    from regulation.power_of_ten import PowerOfTenChecker
    from regulation.compliance_report import ComplianceReporter

    project_root = os.path.dirname(os.path.abspath(__file__))
    checker = PowerOfTenChecker(project_root)
    checker.run_all()

    reporter = ComplianceReporter(checker)
    grade = reporter.get_compliance_grade()

    print(f"\n{'='*60}")
    print(f"  Tier 1 Regulation — Power of Ten Static Analysis")
    print(f"  Compliance Grade: {grade}")
    print(f"{'='*60}")
    print(reporter.generate_text_report())

    summary = checker.summary()
    if summary["failed"] > 0:
        print("Action items:")
        for result in checker.results:
            if not result.passed:
                for v in result.violations:
                    print(f"  [{v.rule_id}] {v.file_path}:{v.line_number} — {v.message}")
        print()

    return summary["compliance_rate"]


def main():
    parser = argparse.ArgumentParser(description="Finance Expert Team — AI stock analysis")
    parser.add_argument("--ticker", required=False, help="Stock ticker (e.g. AAPL)")
    parser.add_argument("--query",  required=False, help="Your question about the stock")
    parser.add_argument("--regulate", action="store_true",
                        help="Run Tier 1 Power of Ten static compliance check")
    args = parser.parse_args()

    if args.regulate:
        run_regulation_check()
        return

    if not args.ticker or not args.query:
        parser.error("--ticker and --query are required (or use --regulate)")

    ticker = args.ticker.upper().strip()
    query  = args.query.strip()

    print(f"\n{'='*60}")
    print(f"  Finance Expert Team")
    print(f"  Ticker : {ticker}")
    print(f"  Query  : {query}")
    print(f"{'='*60}")

    report = Orchestrator().analyze(query=query, ticker=ticker)
    print(f"\n{report}")


if __name__ == "__main__":
    main()
