"""Telegram /positions command handler."""

from __future__ import annotations

import logging

from atos.core.database import get_db
from atos.core.models.trade import Trade

logger = logging.getLogger(__name__)


async def positions_handler(update, context) -> None:
    """/positions — List all open trades with entry/SL/target."""
    with get_db() as db:
        open_trades = (
            db.query(Trade)
            .filter(Trade.status.in_(["OPEN", "PARTIAL"]))
            .order_by(Trade.entry_date.desc())
            .all()
        )

    if not open_trades:
        await update.message.reply_text("No open positions.")
        return

    lines = ["<b>Open Positions</b>\n"]
    for t in open_trades:
        pnl_str = ""
        if t.net_pnl is not None:
            sign = "+" if t.net_pnl >= 0 else ""
            pnl_str = f" | PnL: {sign}₹{t.net_pnl:.0f}"

        lines.append(
            f"<b>{t.symbol}</b> {t.direction} {t.instrument_type}\n"
            f"  Entry: ₹{t.entry_price or '?'} | SL: ₹{t.sl or '?'} | T1: ₹{t.t1 or '?'}{pnl_str}\n"
            f"  Qty: {t.qty_remaining}/{t.qty} | {'📄' if t.is_paper else '💰'}"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
