#!/usr/bin/env python3
"""
Seed the instruments (universe) table from the NSE equity master list.

Downloads the NSE equity master CSV (free, no auth required) and loads
all EQ series instruments into the instruments table.

Usage:
    python scripts/seed_universe.py
    python scripts/seed_universe.py --nse500  # mark NSE 500 stocks
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import io
import logging

import pandas as pd
import requests
from sqlalchemy.dialects.postgresql import insert as pg_insert

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s — %(message)s")
logger = logging.getLogger("seed_universe")

NSE_EQUITY_MASTER_URL = "https://www.nseindia.com/api/equity-master"
NSE_SYMBOLS_CSV_URL = (
    "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.nseindia.com/",
}


def download_equity_list() -> pd.DataFrame:
    logger.info("Downloading NSE equity list from %s", NSE_SYMBOLS_CSV_URL)
    resp = requests.get(NSE_SYMBOLS_CSV_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    df.columns = [c.strip().upper() for c in df.columns]
    logger.info("Downloaded %d symbols", len(df))
    return df


def load_universe(df: pd.DataFrame) -> int:
    from atos.core.database import get_db
    from atos.core.models.instrument import Instrument

    col_map = {
        "SYMBOL": "symbol",
        "NAME OF COMPANY": "company_name",
        "SERIES": "series",
        "ISIN NUMBER": "isin",
    }
    df = df.rename(columns=col_map)
    df["symbol"] = df["symbol"].str.strip().str.upper()

    # Keep EQ series only
    if "series" in df.columns:
        df = df[df["series"].str.strip() == "EQ"]

    records = []
    for _, row in df.iterrows():
        records.append(
            {
                "symbol": row.get("symbol", ""),
                "company_name": row.get("company_name"),
                "isin": row.get("isin"),
                "series": "EQ",
                "exchange": "NSE",
                "is_active": True,
            }
        )

    if not records:
        logger.warning("No EQ series instruments found")
        return 0

    with get_db() as db:
        for i in range(0, len(records), 500):
            batch = records[i : i + 500]
            stmt = pg_insert(Instrument).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["symbol"],
                set_={
                    "company_name": stmt.excluded.company_name,
                    "isin": stmt.excluded.isin,
                    "is_active": True,
                },
            )
            db.execute(stmt)

    logger.info("Upserted %d instruments", len(records))
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed NSE instrument universe")
    parser.add_argument("--nse500", action="store_true", help="Also mark NSE 500 stocks")
    args = parser.parse_args()

    df = download_equity_list()
    n = load_universe(df)
    logger.info("Seed complete: %d instruments loaded", n)


if __name__ == "__main__":
    main()
