"""
TradingView chart screenshot capture.

Navigates to a symbol's chart, waits for it to fully render
(including indicators), and returns PNG bytes.

Chart snapshots are saved locally to data/charts/{symbol}/{date}_{tf}.png.

Usage:
    import asyncio
    from atos.data.tradingview.chart_capture import capture_chart

    png_bytes = asyncio.run(capture_chart("RELIANCE", "1D"))
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from pathlib import Path

from atos.data.tradingview.playwright_session import TV_BASE_URL, TVSession

logger = logging.getLogger(__name__)

CHART_DIR = Path("data/charts")

# Timeframe string to TradingView URL parameter mapping
_TF_MAP = {
    "1D": "D",
    "1W": "W",
    "1M": "M",
    "1H": "60",
    "15m": "15",
    "5m": "5",
}


def _snapshot_path(symbol: str, timeframe: str, trade_date: date | None = None) -> Path:
    """Return local path for saving a chart snapshot."""
    d = trade_date or date.today()
    target_dir = CHART_DIR / symbol
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"{d.isoformat()}_{timeframe}.png"


async def capture_chart(
    symbol: str,
    timeframe: str = "1D",
    exchange: str = "NSE",
    save: bool = True,
) -> bytes:
    """
    Navigate to TradingView chart for `symbol` and return PNG screenshot bytes.

    :param symbol: NSE ticker symbol (e.g. "RELIANCE")
    :param timeframe: Chart timeframe key from _TF_MAP (e.g. "1D", "1H", "5m")
    :param exchange: Exchange prefix for TradingView (default "NSE")
    :param save: If True, also save the PNG to data/charts/{symbol}/
    :returns: PNG image bytes
    """
    tv_tf = _TF_MAP.get(timeframe, timeframe)
    url = f"{TV_BASE_URL}/chart/?symbol={exchange}:{symbol}&interval={tv_tf}"

    logger.info("Capturing chart: %s %s → %s", symbol, timeframe, url)

    async with TVSession() as tv:
        page = await tv.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # Wait for the main chart container to appear
            await page.wait_for_selector(".chart-container", timeout=20000)
            # Additional wait for candles + indicators to render
            await asyncio.sleep(4)
            # Dismiss any cookie / subscription popups if present
            for selector in [
                '[data-name="accept-all-cookies"]',
                ".tv-dialog__close",
                '[aria-label="Close"]',
            ]:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=1000):
                        await btn.click()
                except Exception:
                    pass

            png_bytes = await page.screenshot(full_page=False)
        finally:
            await page.close()

    if save:
        path = _snapshot_path(symbol, timeframe)
        path.write_bytes(png_bytes)
        logger.info("Saved chart snapshot to %s (%d bytes)", path, len(png_bytes))

    return png_bytes


def capture_chart_sync(
    symbol: str,
    timeframe: str = "1D",
    exchange: str = "NSE",
    save: bool = True,
) -> bytes:
    """Synchronous wrapper for capture_chart (for use outside async contexts)."""
    return asyncio.run(capture_chart(symbol, timeframe, exchange, save))
