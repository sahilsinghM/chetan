"""Telegram /kill and /resume command handlers."""

from __future__ import annotations

import logging

from atos.core.cache import cache
from atos.core.constants import EventType
from atos.core.database import get_db
from atos.core.models.event_log import EventLog

logger = logging.getLogger(__name__)


async def kill_handler(update, context) -> None:
    """
    /kill — Activate the killswitch.

    Sets Redis key atos:killswitch = "1".
    Every scheduler job and order call checks this before acting.
    """
    cache.set_killswitch()

    with get_db() as db:
        db.add(
            EventLog(
                event_type=EventType.KILLSWITCH_ACTIVATED,
                source="TELEGRAM",
                note=f"Activated by Telegram user {update.effective_user.id}",
            )
        )

    logger.warning("KILLSWITCH ACTIVATED via Telegram by user %s", update.effective_user.id)
    await update.message.reply_text(
        "🔴 <b>KILLSWITCH ACTIVATED</b>\n\n"
        "All automation halted. No new trades or orders will be placed.\n"
        "Use /resume to re-enable.",
        parse_mode="HTML",
    )


async def resume_handler(update, context) -> None:
    """/resume — Deactivate the killswitch."""
    cache.clear_killswitch()

    with get_db() as db:
        db.add(
            EventLog(
                event_type=EventType.KILLSWITCH_CLEARED,
                source="TELEGRAM",
                note=f"Cleared by Telegram user {update.effective_user.id}",
            )
        )

    logger.info("Killswitch cleared by Telegram user %s", update.effective_user.id)
    await update.message.reply_text(
        "🟢 <b>Killswitch cleared</b> — automation resumed.",
        parse_mode="HTML",
    )
