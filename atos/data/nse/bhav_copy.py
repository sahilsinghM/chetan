"""
NSE Bhav Copy ingestion.

Downloads the daily OHLCV file from NSE archives, parses it, and upserts
into the daily_candles table.  Also upserts new symbols into instruments.

NSE URL pattern (new format):
    https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{DDMMYYYY}_F_0000.csv.zip

Old format (fallback):
    https://www1.nseindia.com/content/historical/EQUITIES/{YYYY}/{MON}/cm{DD}{MON}{YYYY}bhav.csv.zip

Usage:
    from atos.data.nse.bhav_copy import download_and_ingest_bhav
    rows = download_and_ingest_bhav(date(2025, 1, 15))
"""

from __future__ import annotations

import io
import logging
import zipfile
from datetime import date

import pandas as pd
import requests
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from atos.core.exceptions import BhavCopyError
from atos.core.models.candle import DailyCandle
from atos.core.models.instrument import Instrument

logger = logging.getLogger(__name__)

# NSE blocks default Python user agents — spoof a browser
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

_TIMEOUT = 30  # seconds


def _build_url(trade_date: date) -> str:
    """Return the NSE bhav copy download URL for the given date."""
    dd = trade_date.strftime("%d")
    mm = trade_date.strftime("%m")
    yyyy = trade_date.strftime("%Y")
    ddmmyyyy = f"{dd}{mm}{yyyy}"
    return (
        f"https://nsearchives.nseindia.com/content/cm/"
        f"BhavCopy_NSE_CM_0_0_0_{ddmmyyyy}_F_0000.csv.zip"
    )


def download_bhav_csv(trade_date: date) -> pd.DataFrame:
    """
    Download and parse the NSE bhav copy for `trade_date`.

    Returns a DataFrame with columns:
        symbol, open, high, low, close, volume, delivery_pct, series
    """
    url = _build_url(trade_date)
    logger.info("Downloading bhav copy from %s", url)

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
    except requests.HTTPError as exc:
        raise BhavCopyError(
            f"HTTP {exc.response.status_code} fetching bhav copy for {trade_date}: {url}"
        ) from exc
    except requests.RequestException as exc:
        raise BhavCopyError(f"Network error fetching bhav copy: {exc}") from exc

    # Unzip in-memory
    try:
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            csv_name = next(n for n in zf.namelist() if n.endswith(".csv"))
            with zf.open(csv_name) as csv_file:
                df = pd.read_csv(csv_file)
    except (zipfile.BadZipFile, StopIteration) as exc:
        raise BhavCopyError(f"Could not unzip bhav copy for {trade_date}") from exc

    return _normalise(df, trade_date)


def _normalise(df: pd.DataFrame, trade_date: date) -> pd.DataFrame:
    """Normalise raw bhav CSV to a standard schema."""
    # Column names vary across NSE formats — handle both old and new
    df.columns = [c.strip().upper() for c in df.columns]

    # New format columns: TckrSymb, SctySrs, OpnPric, HghPric, LwPric, ClsPric, TtlTradgVol
    # Old format columns: SYMBOL, SERIES, OPEN, HIGH, LOW, CLOSE, TOTTRDQTY, DELIVQTY
    col_map_new = {
        "TCKRSYMB": "symbol",
        "SCTYSRS": "series",
        "OPNPRIC": "open",
        "HGHPRIC": "high",
        "LWPRIC": "low",
        "CLSPRIC": "close",
        "TTLTRADGVOL": "volume",
    }
    col_map_old = {
        "SYMBOL": "symbol",
        "SERIES": "series",
        "OPEN": "open",
        "HIGH": "high",
        "LOW": "low",
        "CLOSE": "close",
        "TOTTRDQTY": "volume",
        "DELIVQTY": "delivery_qty",
        "TRADEDQTY": "volume",
    }

    if "TCKRSYMB" in df.columns:
        df = df.rename(columns=col_map_new)
    else:
        df = df.rename(columns=col_map_old)

    # Keep only equity series (EQ, BE, SM, BZ, etc.)
    if "series" in df.columns:
        df = df[df["series"].isin(["EQ", "BE", "SM", "BZ", "N"])].copy()

    # Calculate delivery percentage if possible
    if "delivery_qty" in df.columns and "volume" in df.columns:
        df["delivery_pct"] = (
            pd.to_numeric(df["delivery_qty"], errors="coerce")
            / pd.to_numeric(df["volume"], errors="coerce")
            * 100
        ).round(2)
    else:
        df["delivery_pct"] = None

    df["date"] = trade_date
    df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce").fillna(0).astype(int)

    for col in ("open", "high", "low", "close"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    keep = ["symbol", "series", "date", "open", "high", "low", "close", "volume", "delivery_pct"]
    keep = [c for c in keep if c in df.columns]
    df = df[keep].dropna(subset=["symbol", "close"])
    df["symbol"] = df["symbol"].str.strip().str.upper()

    return df.reset_index(drop=True)


def upsert_bhav(df: pd.DataFrame, db: Session) -> int:
    """
    Bulk-upsert bhav copy data into instruments + daily_candles tables.
    Returns the number of candle rows upserted.
    """
    if df.empty:
        return 0

    # 1. Upsert instruments (add new symbols we haven't seen before)
    symbols = df["symbol"].unique().tolist()
    for symbol in symbols:
        stmt = pg_insert(Instrument).values(symbol=symbol).on_conflict_do_nothing(
            index_elements=["symbol"]
        )
        db.execute(stmt)

    # 2. Upsert daily candles
    records = df[
        ["symbol", "date", "open", "high", "low", "close", "volume", "delivery_pct"]
    ].to_dict(orient="records")

    stmt = pg_insert(DailyCandle).values(records)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_daily_candle",
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "volume": stmt.excluded.volume,
            "delivery_pct": stmt.excluded.delivery_pct,
        },
    )
    db.execute(stmt)

    logger.info("Upserted %d bhav rows for %s", len(records), df["date"].iloc[0])
    return len(records)


def download_and_ingest_bhav(trade_date: date, db: Session) -> int:
    """
    Download bhav copy for `trade_date` and upsert into DB.
    Returns number of rows upserted.
    """
    df = download_bhav_csv(trade_date)
    return upsert_bhav(df, db)
