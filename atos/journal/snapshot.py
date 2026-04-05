"""
Chart snapshot store.

Phase 1: Save/load PNG files on local disk under data/charts/.
Phase 3: Will add S3 upload behind the same interface.

Usage:
    from atos.journal.snapshot import save_snapshot, load_snapshot

    path = save_snapshot(symbol="RELIANCE", timeframe="1D", png_bytes=bytes_)
    # path = "data/charts/RELIANCE/2026-04-05_1D.png"
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

CHART_DIR = Path("data/charts")


def save_snapshot(
    symbol: str,
    timeframe: str,
    png_bytes: bytes,
    trade_date: date | None = None,
) -> str:
    """
    Save PNG bytes to disk and return the relative path string.
    Creates the directory if needed.
    """
    d = trade_date or date.today()
    target_dir = CHART_DIR / symbol
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{d.isoformat()}_{timeframe}.png"
    path.write_bytes(png_bytes)
    logger.debug("Saved chart snapshot: %s (%d bytes)", path, len(png_bytes))
    return str(path)


def load_snapshot(path: str) -> bytes | None:
    """Load PNG bytes from a saved snapshot path. Returns None if not found."""
    p = Path(path)
    if not p.exists():
        logger.warning("Chart snapshot not found: %s", path)
        return None
    return p.read_bytes()
