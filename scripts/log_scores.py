"""Log today's Trend Lens call for a list of tickers.

Run it once a day (by hand or with cron) so the Score History tab has data:

    python3 scripts/log_scores.py AAPL MSFT KO
    python3 scripts/log_scores.py --file my_tickers.txt   # one ticker per line
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.getLogger("streamlit").setLevel(logging.ERROR)

from services.market_data import get_stock_snapshot  # noqa: E402
from services.score_history import HISTORY_PATH, record_score  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tickers", nargs="*")
    parser.add_argument("--file", type=Path, help="text file with one ticker per line")
    args = parser.parse_args()

    tickers = [t.strip().upper() for t in args.tickers]
    if args.file:
        tickers += [line.strip().upper() for line in args.file.read_text().splitlines() if line.strip() and not line.startswith("#")]
    if not tickers:
        parser.error("give at least one ticker")

    failures = 0
    for ticker in dict.fromkeys(tickers):
        snapshot = get_stock_snapshot(ticker)
        if snapshot.error:
            print(f"{ticker}: skipped ({snapshot.error})")
            failures += 1
            continue
        record = record_score(snapshot)
        print(f"{ticker}: {record['call']} · score {record['total']:.0f} · {record['setup']}")
    print(f"Saved to {HISTORY_PATH}")
    return 1 if failures == len(tickers) else 0


if __name__ == "__main__":
    raise SystemExit(main())
