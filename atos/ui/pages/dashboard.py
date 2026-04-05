"""
Dashboard page — live positions and today's PnL summary.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from atos.core.cache import cache
from atos.core.database import check_connection, get_db
from atos.core.models.trade import Trade


def render() -> None:
    st.title("📊 Dashboard")

    # ── System health row ──────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    db_ok = check_connection()
    redis_ok = cache.ping()
    ks_active = cache.is_killswitch_active()

    col1.metric("Database", "✅ OK" if db_ok else "❌ Down")
    col2.metric("Redis", "✅ OK" if redis_ok else "❌ Down")
    col3.metric("Killswitch", "🔴 ACTIVE" if ks_active else "🟢 Off")

    from config.settings import settings
    cfg = settings()
    col4.metric("Mode", "📄 Paper" if cfg.paper_trade_mode else "💰 Live")

    if ks_active:
        st.error("⚠️ KILLSWITCH IS ACTIVE — all automation halted")

    st.divider()

    # ── Open positions ─────────────────────────────────────────
    st.subheader("Open Positions")
    with get_db() as db:
        open_trades = (
            db.query(Trade)
            .filter(Trade.status.in_(["OPEN", "PARTIAL"]))
            .order_by(Trade.entry_date.desc())
            .all()
        )

    if not open_trades:
        st.info("No open positions.")
    else:
        rows = []
        for t in open_trades:
            rows.append(
                {
                    "Symbol": t.symbol,
                    "Direction": t.direction,
                    "Type": t.instrument_type,
                    "Entry": t.entry_price,
                    "SL": t.sl,
                    "T1": t.t1,
                    "Qty (rem)": f"{t.qty_remaining}/{t.qty}",
                    "Unrealised PnL": t.net_pnl or "—",
                    "Paper": "📄" if t.is_paper else "💰",
                    "Since": t.entry_date.strftime("%d-%b %H:%M") if t.entry_date else "—",
                }
            )
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    # ── Today's closed trades PnL ──────────────────────────────
    st.subheader("Today's Closed Trades")
    from datetime import date, datetime

    today_start = datetime.combine(date.today(), datetime.min.time())
    with get_db() as db:
        closed_today = (
            db.query(Trade)
            .filter(
                Trade.status == "CLOSED",
                Trade.exit_date >= today_start,
            )
            .order_by(Trade.exit_date.desc())
            .all()
        )

    if not closed_today:
        st.info("No closed trades today.")
    else:
        total_net = sum(t.net_pnl or 0 for t in closed_today)
        wins = sum(1 for t in closed_today if (t.net_pnl or 0) > 0)
        pnl_color = "normal" if total_net >= 0 else "inverse"

        c1, c2, c3 = st.columns(3)
        c1.metric("Net PnL Today", f"₹{total_net:,.0f}", delta_color=pnl_color)
        c2.metric("Trades", len(closed_today))
        c3.metric("Win Rate", f"{wins}/{len(closed_today)}")

        rows = [
            {
                "Symbol": t.symbol,
                "Direction": t.direction,
                "Entry": t.entry_price,
                "Exit": t.exit_price,
                "Qty": t.qty,
                "Gross PnL": f"₹{t.gross_pnl:,.0f}" if t.gross_pnl else "—",
                "Charges": f"₹{t.charges:,.0f}" if t.charges else "—",
                "Net PnL": f"₹{t.net_pnl:,.0f}" if t.net_pnl else "—",
                "Reason": t.exit_reason,
            }
            for t in closed_today
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
