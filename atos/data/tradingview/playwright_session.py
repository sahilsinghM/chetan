"""
TradingView browser session management via Playwright.

Maintains a persistent browser context on disk so login is done once
and reused across all chart capture calls.

Usage:
    from atos.data.tradingview.playwright_session import TVSession

    async with TVSession() as tv:
        page = await tv.new_page()
        ...
"""

from __future__ import annotations

import logging
from pathlib import Path

from config.settings import settings

logger = logging.getLogger(__name__)

TV_SESSION_DIR = Path.home() / ".atos" / "tv_session"
TV_BASE_URL = "https://www.tradingview.com"
TV_LOGIN_URL = f"{TV_BASE_URL}/accounts/signin/"

# Attempt to import playwright; gracefully degrade if not installed
try:
    from playwright.async_api import (
        Browser,
        BrowserContext,
        Playwright,
        async_playwright,
    )

    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False
    logger.warning("playwright not installed — chart capture will not work")


class TVSession:
    """
    Async context manager providing a Playwright browser context
    with TradingView session cookies persisted to disk.
    """

    def __init__(self) -> None:
        self._playwright: "Playwright | None" = None
        self._browser: "Browser | None" = None
        self._context: "BrowserContext | None" = None

    async def __aenter__(self) -> "TVSession":
        if not _PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "playwright is not installed. Run: pip install playwright && playwright install chromium"
            )
        TV_SESSION_DIR.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        # Load persistent session storage if available
        storage_state = TV_SESSION_DIR / "state.json"
        self._context = await self._browser.new_context(
            viewport={"width": 1600, "height": 900},
            storage_state=str(storage_state) if storage_state.exists() else None,
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        if not storage_state.exists():
            await self._login()
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._context:
            # Persist cookies / localStorage for next run
            await self._context.storage_state(path=str(TV_SESSION_DIR / "state.json"))
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def new_page(self) -> "playwright.async_api.Page":  # type: ignore[name-defined]
        if self._context is None:
            raise RuntimeError("TVSession not entered — use `async with TVSession()`")
        return await self._context.new_page()

    async def _login(self) -> None:
        """Log in to TradingView using credentials from settings."""
        cfg = settings()
        if not cfg.tradingview_username or not cfg.tradingview_password:
            logger.warning(
                "TradingView credentials not set — chart capture may have limited indicators"
            )
            return

        logger.info("Logging in to TradingView as %s", cfg.tradingview_username)
        page = await self._context.new_page()
        try:
            await page.goto(TV_LOGIN_URL, wait_until="networkidle")
            # Click 'Email' sign-in option
            await page.click('[data-overflow-tooltip-text="Email"]', timeout=5000)
            await page.fill('input[name="username"]', cfg.tradingview_username)
            await page.fill('input[name="password"]', cfg.tradingview_password)
            await page.click('button[type="submit"]')
            # Wait for redirect back to homepage
            await page.wait_for_url(f"{TV_BASE_URL}/**", timeout=15000)
            logger.info("TradingView login successful")
        except Exception as exc:
            logger.warning("TradingView login failed: %s — continuing without login", exc)
        finally:
            await page.close()
