"""
NSE corporate actions stub — Phase 2.

Will fetch bonus, split, and dividend events from NSE to avoid
holding positions through record dates.
"""

from __future__ import annotations

import logging
from datetime import date

logger = logging.getLogger(__name__)


def get_upcoming_events(from_date: date, to_date: date) -> list[dict]:
    """Return upcoming corporate actions in the date range. (Phase 2 stub)"""
    logger.debug("corporate_actions.get_upcoming_events: Phase 2 not yet implemented")
    return []
