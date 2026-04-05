"""Telegram /status command handler."""

from __future__ import annotations

import logging

from atos.core.cache import cache
from atos.core.database import check_connection

logger = logging.getLogger(__name__)


async def status_handler(update, context) -> None:
    """/status — Report system health."""
    db_ok = check_connection()
    redis_ok = cache.ping()
    killswitch = cache.is_killswitch_active()

    db_icon = "🟢" if db_ok else "🔴"
    redis_icon = "🟢" if redis_ok else "🔴"
    ks_icon = "🔴 ACTIVE" if killswitch else "🟢 off"

    from config.settings import settings

    cfg = settings()
    dhan_configured = bool(cfg.dhan_client_id and cfg.dhan_access_token)
    dhan_icon = "🟢" if dhan_configured else "🟡 not configured"

    text = (
        "<b>ATOS System Status</b>\n\n"
        f"Database:    {db_icon}\n"
        f"Redis:       {redis_icon}\n"
        f"Dhan API:    {dhan_icon}\n"
        f"Killswitch:  {ks_icon}\n"
        f"Mode:        {'📄 PAPER' if cfg.paper_trade_mode else '💰 LIVE'}"
    )
    await update.message.reply_text(text, parse_mode="HTML")
