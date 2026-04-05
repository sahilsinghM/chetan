"""
NSE event calendar stub — Phase 3.

Will provide earnings dates, F&O expiry dates, RBI policy announcements, etc.
to allow the position manager to reduce/exit positions ahead of high-risk events.
"""

from __future__ import annotations

import logging
from datetime import date

logger = logging.getLogger(__name__)


def is_high_risk_tomorrow(symbol: str, today: date) -> bool:
    """Return True if there is a high-risk event tomorrow for `symbol`. (Phase 3 stub)"""
    logger.debug("event_calendar.is_high_risk_tomorrow: Phase 3 not yet implemented")
    return False


def get_fno_expiry_dates(year: int, month: int) -> list[date]:
    """Return F&O expiry dates for the given month. (Phase 3 stub)"""
    return []
