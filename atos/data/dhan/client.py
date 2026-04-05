"""
Dhan API client — wraps the dhanhq SDK with retry logic and a paper-trade gate.

All order-placement methods check paper_trade_mode and return a fake order ID
when True — no real orders are placed until the flag is explicitly disabled.

Usage:
    from atos.data.dhan.client import dhan_client
    quote = dhan_client.get_ltp("RELIANCE", "NSE_EQ")
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from atos.core.exceptions import BrokerError
from config.settings import settings

logger = logging.getLogger(__name__)

# Attempt to import dhanhq; gracefully degrade if not installed
try:
    from dhanhq import dhanhq  # type: ignore[import]

    _DHAN_AVAILABLE = True
except ImportError:
    _DHAN_AVAILABLE = False
    logger.warning("dhanhq package not installed — Dhan API calls will be mocked")


_RETRY_KWARGS: dict[str, Any] = {
    "stop": stop_after_attempt(3),
    "wait": wait_exponential(multiplier=1, min=2, max=30),
    "retry": retry_if_exception_type(Exception),
    "reraise": True,
}


class DhanClient:
    """Thin wrapper around the dhanhq SDK."""

    def __init__(self) -> None:
        cfg = settings()
        self._paper = cfg.paper_trade_mode
        if _DHAN_AVAILABLE and cfg.dhan_client_id and cfg.dhan_access_token:
            self._client = dhanhq(cfg.dhan_client_id, cfg.dhan_access_token)
        else:
            self._client = None
            logger.warning(
                "DhanClient running in stub mode — no real API calls will be made"
            )

    # ── Market data ───────────────────────────────────────────

    @retry(**_RETRY_KWARGS)
    def get_ltp(self, security_id: str, exchange_segment: str = "NSE_EQ") -> float:
        """Return the last traded price for a security."""
        if self._client is None:
            raise BrokerError("Dhan client not initialised — check credentials")
        try:
            resp = self._client.get_ltp_data(
                security_id=security_id,
                exchange_segment=exchange_segment,
            )
            return float(resp["data"]["last_price"])
        except Exception as exc:
            raise BrokerError(f"get_ltp failed for {security_id}: {exc}") from exc

    @retry(**_RETRY_KWARGS)
    def get_historical_candles(
        self,
        security_id: str,
        exchange_segment: str,
        instrument_type: str,
        from_date: str,
        to_date: str,
        interval: str = "D",
    ) -> list[dict]:
        """
        Fetch OHLCV candles from Dhan historical API.

        :param interval: '1', '5', '15', '25', '60' (minutes) or 'D' (daily)
        :returns: list of candle dicts with keys open/high/low/close/volume/start_time
        """
        if self._client is None:
            raise BrokerError("Dhan client not initialised — check credentials")
        try:
            resp = self._client.historical_minute_charts(
                symbol=security_id,
                exchange_segment=exchange_segment,
                instrument_type=instrument_type,
                expiry_code=0,
                from_date=from_date,
                to_date=to_date,
            )
            return resp.get("data", [])
        except Exception as exc:
            raise BrokerError(
                f"get_historical_candles failed for {security_id}: {exc}"
            ) from exc

    # ── Order placement (paper-gated) ────────────────────────

    def place_market_order(
        self,
        security_id: str,
        exchange_segment: str,
        transaction_type: str,
        quantity: int,
        product_type: str = "CNC",
    ) -> dict:
        """
        Place a market order. Returns a fake result if paper_trade_mode=True.
        transaction_type: 'BUY' or 'SELL'
        """
        if self._paper:
            fake_id = f"PAPER_{security_id}_{transaction_type}"
            logger.info(
                "PAPER ORDER: %s %s x%d (market)",
                transaction_type,
                security_id,
                quantity,
            )
            return {"order_id": fake_id, "status": "PAPER", "paper": True}

        if self._client is None:
            raise BrokerError("Dhan client not initialised — check credentials")

        try:
            resp = self._client.place_order(
                security_id=security_id,
                exchange_segment=exchange_segment,
                transaction_type=transaction_type,
                quantity=quantity,
                order_type="MARKET",
                product_type=product_type,
                price=0,
            )
            return resp
        except Exception as exc:
            raise BrokerError(f"place_market_order failed: {exc}") from exc

    def place_limit_order(
        self,
        security_id: str,
        exchange_segment: str,
        transaction_type: str,
        quantity: int,
        price: float,
        product_type: str = "CNC",
    ) -> dict:
        """Place a limit order. Paper-gated."""
        if self._paper:
            fake_id = f"PAPER_{security_id}_{transaction_type}_LIMIT"
            logger.info(
                "PAPER LIMIT ORDER: %s %s x%d @ %.2f",
                transaction_type,
                security_id,
                quantity,
                price,
            )
            return {"order_id": fake_id, "status": "PAPER", "paper": True}

        if self._client is None:
            raise BrokerError("Dhan client not initialised — check credentials")

        try:
            resp = self._client.place_order(
                security_id=security_id,
                exchange_segment=exchange_segment,
                transaction_type=transaction_type,
                quantity=quantity,
                order_type="LIMIT",
                product_type=product_type,
                price=price,
            )
            return resp
        except Exception as exc:
            raise BrokerError(f"place_limit_order failed: {exc}") from exc

    # ── Positions ─────────────────────────────────────────────

    @retry(**_RETRY_KWARGS)
    def get_positions(self) -> list[dict]:
        """Return all open positions from Dhan."""
        if self._client is None:
            return []
        try:
            resp = self._client.get_positions()
            return resp.get("data", [])
        except Exception as exc:
            raise BrokerError(f"get_positions failed: {exc}") from exc

    def is_available(self) -> bool:
        """Return True if the Dhan client is properly initialised."""
        return self._client is not None


@lru_cache(maxsize=1)
def get_dhan_client() -> DhanClient:
    """Return a cached DhanClient singleton."""
    return DhanClient()
