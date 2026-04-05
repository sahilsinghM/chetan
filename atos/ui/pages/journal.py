"""
Journal page — trade history with filters, PnL stats, and CSV export.
"""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from atos.core.database import get_db
from atos.core.models.trade import Trade


def render() -> None:
    st.title("📖 Trade Journal")

    # ── Filters ────────────────────────────────────────────────
    with st.expander("🔍 Filters", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.multiselect(
                "Status",
                ["OPEN", "PARTIAL", "CLOSED", "CANCELLED", "PLANNED"],
                default=["OPEN", "PARTIAL", "CLOSED"],
            )
        with col2:
            direction_filter = st.multiselect(
                "Direction", ["LONG", "SHORT"], default=["LONG", "SHORT"]
            )
        with col3:
            instrument_filter = st.multiselect(
                "Instrument",
                ["EQ_SWING", "EQ_INTRADAY", "FUT", "OPT"],
                default=["EQ_SWING", "EQ_INTRADAY"],
            )

        symbol_filter = st.text_input("Symbol (contains)", "").upper()

    # ── Load trades ────────────────────────────────────────────
    with get_db() as db:
        q = db.query(Trade)
        if status_filter:
            q = q.filter(Trade.status.in_(status_filter))
        if direction_filter:
            q = q.filter(Trade.direction.in_(direction_filter))
        if instrument_filter:
            q = q.filter(Trade.instrument_type.in_(instrument_filter))
        if symbol_filter:
            q = q.filter(Trade.symbol.contains(symbol_filter))
        trades = q.order_by(Trade.created_at.desc()).limit(500).all()

    if not trades:
        st.info("No trades found matching filters.")
        return

    # ── Summary stats ──────────────────────────────────────────
    closed = [t for t in trades if t.status == "CLOSED"]
    if closed:
        total_net = sum(t.net_pnl or 0 for t in closed)
        wins = sum(1 for t in closed if (t.net_pnl or 0) > 0)
        win_rate = wins / len(closed) * 100 if closed else 0
        avg_net = total_net / len(closed)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Net PnL", f"₹{total_net:,.0f}")
        c2.metric("Trades (closed)", len(closed))
        c3.metric("Win Rate", f"{win_rate:.0f}%")
        c4.metric("Avg Net PnL", f"₹{avg_net:,.0f}")
        st.divider()

    # ── Trade table ────────────────────────────────────────────
    rows = []
    for t in trades:
        rows.append(
            {
                "ID": t.id[:8],
                "Date": t.entry_date.strftime("%d-%b-%Y") if t.entry_date else "—",
                "Symbol": t.symbol,
                "Dir": t.direction,
                "Type": t.instrument_type,
                "Entry": t.entry_price,
                "Exit": t.exit_price or "—",
                "Qty": t.qty,
                "SL": t.sl,
                "T1": t.t1,
                "Status": t.status,
                "Exit Reason": t.exit_reason or "—",
                "Net PnL": f"₹{t.net_pnl:,.0f}" if t.net_pnl is not None else "—",
                "Confidence": f"{t.ai_confidence:.0%}" if t.ai_confidence else "—",
                "Tags": t.tags or "—",
                "Paper": "📄" if t.is_paper else "💰",
            }
        )
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── CSV export ─────────────────────────────────────────────
    csv = df.to_csv(index=False)
    st.download_button(
        label="⬇️ Export CSV",
        data=csv,
        file_name="atos_journal.csv",
        mime="text/csv",
    )

    # ── Trade detail expander ──────────────────────────────────
    st.divider()
    st.subheader("Trade Detail")
    selected_id = st.selectbox(
        "Select trade to view reasoning",
        options=[t.id[:8] for t in trades],
    )
    if selected_id:
        trade = next((t for t in trades if t.id.startswith(selected_id)), None)
        if trade:
            cols = st.columns(2)
            with cols[0]:
                st.write(f"**Symbol:** {trade.symbol}")
                st.write(f"**Direction:** {trade.direction}")
                st.write(f"**Entry:** ₹{trade.entry_price} | **SL:** ₹{trade.sl}")
                st.write(f"**T1:** ₹{trade.t1} | **T2:** ₹{trade.t2 or 'N/A'}")
                st.write(f"**Qty:** {trade.qty} | **Status:** {trade.status}")
                if trade.net_pnl is not None:
                    st.write(f"**Net PnL:** ₹{trade.net_pnl:,.0f}")
            with cols[1]:
                if trade.ai_reasoning:
                    st.write("**Reasoning:**")
                    st.caption(trade.ai_reasoning)
                if trade.chart_snapshot:
                    from atos.journal.snapshot import load_snapshot

                    img = load_snapshot(trade.chart_snapshot)
                    if img:
                        st.image(img, caption=f"{trade.symbol} chart at entry")
