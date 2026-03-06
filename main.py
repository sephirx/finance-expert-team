#!/usr/bin/env python3
"""
Finance Expert Team
-------------------
Usage:
    python main.py --ticker AAPL --query "Is AAPL a good buy right now?"
    python main.py --ticker TSLA --query "Backtest a moving average strategy"
    python main.py --ticker NVDA --query "What is the risk and technical outlook?"
"""

import argparse
from agents.orchestrator import Orchestrator


def main():
    parser = argparse.ArgumentParser(description="Finance Expert Team — AI stock analysis")
    parser.add_argument("--ticker", required=True, help="Stock ticker (e.g. AAPL)")
    parser.add_argument("--query",  required=True, help="Your question about the stock")
    args = parser.parse_args()

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
