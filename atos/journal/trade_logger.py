"""
Trade logger — creates and updates Trade records in the database.

Every state change (entry, partial exit, SL update, full exit) is logged
as a TradeEvent row for audit trail and post-mortem analysis.

Usage:
    from atos.journal.trade_logger import TradeLogger

    with get_db() as db:
        logger = TradeLogger(db)
        trade = logger.create_trade(
            symbol="RELIANCE",
            instrument_type="EQ_SWING",
            direction="LONG",
            entry_price=2850.0,
            sl=2790.0,
            t1=2940.0,
            t2=3050.0,
            qty=35,
        )
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from atos.core.constants import EventType, TradeStatus
from atos.core.models.event_log import EventLog
from atos.core.models.trade import Trade, TradeEvent
from atos.journal.pnl import calculate_charges, realised_pnl
from config.settings import load_params, settings

logger = logging.getLogger(__name__)


class TradeLogger:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_trade(
        self,
        symbol: str,
        instrument_type: str,
        direction: str,
        entry_price: float,
        sl: float,
        t1: float,
        qty: int,
        t2: float | None = None,
        ai_confidence: float | None = None,
        ai_reasoning: str | None = None,
        chart_snapshot: str | None = None,
        indicator_vals: dict | None = None,
        tags: str | None = None,
        strategy: str | None = None,
    ) -> Trade:
        """Create a new OPEN trade record with full context."""
        params = load_params()
        rulebook_ver = params.get("meta", {}).get("version", "1.0.0")

        trade = Trade(
            id=str(uuid.uuid4()),
            symbol=symbol.upper(),
            instrument_type=instrument_type,
            direction=direction,
            strategy=strategy,
            status=TradeStatus.OPEN,
            entry_date=datetime.utcnow(),
            entry_price=entry_price,
            qty=qty,
            qty_remaining=qty,
            sl=sl,
            trail_sl=sl,
            t1=t1,
            t2=t2,
            ai_confidence=ai_confidence,
            ai_reasoning=ai_reasoning,
            chart_snapshot=chart_snapshot,
            indicator_vals=indicator_vals,
            rulebook_ver=rulebook_ver,
            tags=tags,
            is_paper=settings().paper_trade_mode,
        )
        self.db.add(trade)

        self._log_event(
            trade_id=trade.id,
            event_type=EventType.TRADE_OPENED,
            price=entry_price,
            qty=qty,
            note=f"{direction} {symbol} @ {entry_price}",
        )
        self._log_system_event(
            event_type=EventType.TRADE_CREATED,
            trade_id=trade.id,
            symbol=symbol,
            payload={"entry": entry_price, "sl": sl, "t1": t1, "qty": qty},
        )

        logger.info("Trade created: %s %s %s @ %.2f", trade.id[:8], symbol, direction, entry_price)
        return trade

    def close_trade(
        self,
        trade: Trade,
        exit_price: float,
        exit_reason: str,
        qty: int | None = None,
    ) -> Trade:
        """
        Close a trade (fully or partially).

        If qty is None, closes the full remaining quantity.
        """
        qty_to_close = qty or trade.qty_remaining or trade.qty
        gross, charges, net = realised_pnl(
            entry=trade.entry_price,
            exit=exit_price,
            qty=qty_to_close,
            direction=trade.direction,
            instrument_type=trade.instrument_type,
        )

        if qty_to_close < (trade.qty_remaining or trade.qty):
            # Partial exit
            trade.qty_remaining = (trade.qty_remaining or trade.qty) - qty_to_close
            trade.status = TradeStatus.PARTIAL
            self._log_event(
                trade_id=trade.id,
                event_type=EventType.TRADE_PARTIAL_EXIT,
                price=exit_price,
                qty=qty_to_close,
                note=f"Partial exit at {exit_price} reason={exit_reason}",
            )
        else:
            # Full close
            trade.status = TradeStatus.CLOSED
            trade.exit_date = datetime.utcnow()
            trade.exit_price = exit_price
            trade.exit_reason = exit_reason
            trade.gross_pnl = gross
            trade.charges = charges
            trade.net_pnl = net
            trade.qty_remaining = 0
            self._log_event(
                trade_id=trade.id,
                event_type=EventType.TRADE_CLOSED,
                price=exit_price,
                qty=qty_to_close,
                note=f"Full exit at {exit_price} reason={exit_reason} net_pnl={net}",
            )
            self._log_system_event(
                event_type=EventType.TRADE_CLOSED,
                trade_id=trade.id,
                symbol=trade.symbol,
                payload={"exit": exit_price, "reason": exit_reason, "net_pnl": net},
            )

        logger.info(
            "Trade %s %s closed: exit=%.2f reason=%s net=%.2f",
            trade.id[:8],
            trade.symbol,
            exit_price,
            exit_reason,
            net,
        )
        return trade

    def update_sl(self, trade: Trade, new_sl: float) -> Trade:
        """Update the trailing stop-loss level."""
        old_sl = trade.trail_sl
        trade.trail_sl = new_sl
        self._log_event(
            trade_id=trade.id,
            event_type=EventType.TRADE_SL_UPDATED,
            price=new_sl,
            note=f"SL updated {old_sl} → {new_sl}",
        )
        return trade

    # ── Internal helpers ──────────────────────────────────────

    def _log_event(
        self,
        trade_id: str,
        event_type: str,
        price: float | None = None,
        qty: int | None = None,
        note: str | None = None,
        payload: dict | None = None,
    ) -> None:
        event = TradeEvent(
            trade_id=trade_id,
            event_type=event_type,
            price=price,
            qty=qty,
            note=note,
            raw_payload=payload,
        )
        self.db.add(event)

    def _log_system_event(
        self,
        event_type: str,
        symbol: str | None = None,
        trade_id: str | None = None,
        payload: dict | None = None,
    ) -> None:
        entry = EventLog(
            event_type=event_type,
            trade_id=trade_id,
            symbol=symbol,
            source="JOURNAL",
            payload=payload,
        )
        self.db.add(entry)
