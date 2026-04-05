#!/usr/bin/env python3
"""
Backfill daily candles from NSE bhav copy archives.

Downloads bhav copy for each trading day in the date range and
upserts into the daily_candles table.  Skips weekends automatically.
Failed dates are logged and skipped (not fatal).

Usage:
    python scripts/backfill_bhav.py 2025-01-01 2025-12-31
    python scripts/backfill_bhav.py 2026-01-01 2026-04-05 --workers 3
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import logging
import time
from datetime import date, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s — %(message)s")
logger = logging.getLogger("backfill_bhav")


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def backfill(start_date: date, end_date: date, delay: float = 2.0) -> None:
    from atos.core.database import get_db
    from atos.core.exceptions import BhavCopyError
    from atos.data.nse.bhav_copy import download_and_ingest_bhav

    failed = []
    total_rows = 0

    for d in daterange(start_date, end_date):
        # Skip weekends
        if d.weekday() >= 5:
            continue

        logger.info("Processing %s...", d.isoformat())
        try:
            with get_db() as db:
                rows = download_and_ingest_bhav(d, db)
            total_rows += rows
            logger.info("  ✓ %d rows", rows)
        except BhavCopyError as exc:
            logger.warning("  ✗ Skipped %s: %s", d.isoformat(), exc)
            failed.append(d)
        except Exception as exc:
            logger.error("  ✗ Failed %s: %s", d.isoformat(), exc)
            failed.append(d)

        # Polite delay to avoid NSE rate-limiting
        time.sleep(delay)

    logger.info("Backfill complete: %d rows across %d successful dates", total_rows, total_rows)
    if failed:
        logger.warning("Failed dates (%d): %s", len(failed), [d.isoformat() for d in failed])


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill NSE bhav copy data")
    parser.add_argument("start_date", help="Start date YYYY-MM-DD")
    parser.add_argument("end_date", help="End date YYYY-MM-DD")
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Seconds to wait between requests (default: 2.0)",
    )
    args = parser.parse_args()

    start = date.fromisoformat(args.start_date)
    end = date.fromisoformat(args.end_date)

    if start > end:
        logger.error("start_date must be before end_date")
        sys.exit(1)

    logger.info("Backfilling %s to %s...", start.isoformat(), end.isoformat())
    backfill(start, end, delay=args.delay)


if __name__ == "__main__":
    main()
