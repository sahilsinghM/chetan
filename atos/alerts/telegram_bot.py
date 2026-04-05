"""
ATOS Telegram Bot.

Provides:
  - Outbound alerts (trade signals, SL hits, daily PnL summary)
  - Inbound commands (/status, /kill, /resume, /positions, /daily, /help)

The killswitch (/kill) sets a Redis key that is checked by every scheduler
job and order placement call before acting.

Usage (start the bot polling loop):
    python -m atos.alerts.telegram_bot

Usage (send an alert from anywhere):
    from atos.alerts.telegram_bot import send_alert
    await send_alert("RELIANCE SL hit at ₹2790")
"""

from __future__ import annotations

import logging

from config.settings import settings

logger = logging.getLogger(__name__)

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes

    _TELEGRAM_AVAILABLE = True
except ImportError:
    _TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot not installed — Telegram features disabled")


async def send_alert(message: str) -> None:
    """
    Fire-and-forget: send `message` to the configured TELEGRAM_CHAT_ID.
    Safe to call even if Telegram is not configured (logs warning, does not raise).
    """
    cfg = settings()
    if not _TELEGRAM_AVAILABLE or not cfg.telegram_bot_token or not cfg.telegram_chat_id:
        logger.warning("Telegram not configured — alert suppressed: %s", message[:80])
        return
    try:
        app = Application.builder().token(cfg.telegram_bot_token).build()
        async with app:
            await app.bot.send_message(
                chat_id=cfg.telegram_chat_id,
                text=message,
                parse_mode="HTML",
            )
    except Exception as exc:
        logger.error("Failed to send Telegram alert: %s", exc)


def run_bot() -> None:
    """Start the bot in polling mode (blocking). Run as a background process."""
    if not _TELEGRAM_AVAILABLE:
        raise RuntimeError("python-telegram-bot not installed")

    cfg = settings()
    if not cfg.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in .env")

    from atos.alerts.commands.killswitch import kill_handler, resume_handler
    from atos.alerts.commands.positions import positions_handler
    from atos.alerts.commands.status import status_handler

    app = Application.builder().token(cfg.telegram_bot_token).build()

    app.add_handler(CommandHandler("start", _help_handler))
    app.add_handler(CommandHandler("help", _help_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("kill", kill_handler))
    app.add_handler(CommandHandler("resume", resume_handler))
    app.add_handler(CommandHandler("positions", positions_handler))

    logger.info("ATOS Telegram bot starting polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


async def _help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "<b>ATOS Commands</b>\n\n"
        "/status — System health\n"
        "/positions — Open trades\n"
        "/kill — <b>EMERGENCY: halt all automation</b>\n"
        "/resume — Resume after killswitch\n"
        "/help — This message"
    )
    await update.message.reply_text(text, parse_mode="HTML")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_bot()
