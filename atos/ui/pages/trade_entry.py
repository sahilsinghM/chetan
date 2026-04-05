"""
Paper trade entry form.

Allows manual logging of trades with full context:
entry/SL/targets, reasoning, and optional chart snapshot capture.
"""

from __future__ import annotations

import streamlit as st

from atos.core.database import get_db
from atos.journal.pnl import position_size_from_risk, risk_reward
from atos.journal.trade_logger import TradeLogger


def render() -> None:
    st.title("📝 Log Paper Trade")

    from config.settings import load_params, settings

    params = load_params()
    cfg = settings()

    if not cfg.paper_trade_mode:
        st.warning("⚠️ Live mode is ON — trades entered here will be marked paper=False.")

    # ── Suggested position size calculator ────────────────────
    with st.expander("💡 Position Size Calculator", expanded=False):
        capital = st.number_input(
            "Capital (₹)",
            value=float(params["risk"]["capital_base"]),
            step=10000.0,
        )
        risk_pct = st.slider(
            "Risk per trade (%)",
            min_value=0.1,
            max_value=3.0,
            value=float(params["risk"]["max_risk_per_trade_pct"]),
            step=0.1,
        )
        calc_entry = st.number_input("Entry price", value=1000.0, step=1.0)
        calc_sl = st.number_input("Stop-loss price", value=980.0, step=1.0)
        suggested_qty = position_size_from_risk(
            capital=capital, risk_pct=risk_pct / 100, entry=calc_entry, sl=calc_sl
        )
        st.info(f"Suggested qty: **{suggested_qty} shares** — risking ₹{capital * risk_pct / 100:,.0f}")

    st.divider()

    # ── Trade entry form ───────────────────────────────────────
    with st.form("trade_entry_form"):
        col1, col2 = st.columns(2)

        with col1:
            symbol = st.text_input("Symbol *", placeholder="RELIANCE").upper().strip()
            direction = st.selectbox("Direction *", ["LONG", "SHORT"])
            instrument_type = st.selectbox(
                "Instrument Type *",
                ["EQ_SWING", "EQ_INTRADAY", "FUT", "OPT"],
            )
            strategy = st.text_input("Strategy", placeholder="MOMENTUM_BREAKOUT")

        with col2:
            entry_price = st.number_input("Entry Price *", min_value=0.01, step=0.5)
            sl = st.number_input("Stop-Loss *", min_value=0.01, step=0.5)
            t1 = st.number_input("Target 1 *", min_value=0.01, step=0.5)
            t2 = st.number_input("Target 2 (optional)", min_value=0.0, step=0.5, value=0.0)

        col3, col4 = st.columns(2)
        with col3:
            qty = st.number_input("Quantity *", min_value=1, step=1, value=suggested_qty or 1)
        with col4:
            ai_confidence = st.slider("Confidence", 0.0, 1.0, 0.70, 0.05)

        reasoning = st.text_area(
            "Reasoning / Notes",
            placeholder="Why is this a valid setup? Key levels, pattern, catalyst...",
            height=120,
        )
        tags = st.text_input("Tags (comma-separated)", placeholder="breakout, ema_aligned, high_volume")

        capture_chart = st.checkbox("Capture TradingView chart screenshot", value=False)

        submitted = st.form_submit_button("Log Trade", type="primary")

    if submitted:
        # ── Validation ─────────────────────────────────────────
        errors = []
        if not symbol:
            errors.append("Symbol is required")
        if entry_price <= 0:
            errors.append("Entry price must be > 0")
        if sl <= 0:
            errors.append("Stop-loss must be > 0")
        if t1 <= 0:
            errors.append("Target 1 must be > 0")
        if qty < 1:
            errors.append("Quantity must be ≥ 1")
        if direction == "LONG" and sl >= entry_price:
            errors.append("For LONG: SL must be below entry price")
        if direction == "LONG" and t1 <= entry_price:
            errors.append("For LONG: T1 must be above entry price")
        if direction == "SHORT" and sl <= entry_price:
            errors.append("For SHORT: SL must be above entry price")
        if direction == "SHORT" and t1 >= entry_price:
            errors.append("For SHORT: T1 must be below entry price")

        if errors:
            for e in errors:
                st.error(e)
            return

        # ── Chart capture (optional) ───────────────────────────
        snapshot_path: str | None = None
        if capture_chart:
            with st.spinner("Capturing TradingView chart..."):
                try:
                    from atos.data.tradingview.chart_capture import capture_chart as cap_chart
                    from atos.journal.snapshot import save_snapshot

                    png_bytes = cap_chart(symbol, "1D")
                    snapshot_path = save_snapshot(symbol, "1D", png_bytes)
                    st.image(png_bytes, caption=f"{symbol} Daily Chart", use_container_width=True)
                except Exception as exc:
                    st.warning(f"Chart capture failed: {exc} — trade will be logged without snapshot")

        # ── Save trade ─────────────────────────────────────────
        try:
            with get_db() as db:
                tl = TradeLogger(db)
                trade = tl.create_trade(
                    symbol=symbol,
                    instrument_type=instrument_type,
                    direction=direction,
                    entry_price=entry_price,
                    sl=sl,
                    t1=t1,
                    t2=t2 if t2 > 0 else None,
                    qty=qty,
                    ai_confidence=ai_confidence,
                    ai_reasoning=reasoning or None,
                    chart_snapshot=snapshot_path,
                    tags=tags or None,
                    strategy=strategy or None,
                )

            rr = risk_reward(entry_price, sl, t1, direction)
            st.success(
                f"✅ Trade logged: **{symbol}** {direction} x{qty} @ ₹{entry_price}  "
                f"| SL ₹{sl} | T1 ₹{t1} | R:R = 1:{rr:.1f}  \n"
                f"Trade ID: `{trade.id}`"
            )

            # Send Telegram alert
            try:
                import asyncio

                from atos.alerts.telegram_bot import send_alert

                sign = "📈" if direction == "LONG" else "📉"
                msg = (
                    f"{sign} <b>New Trade: {symbol}</b>\n"
                    f"Direction: {direction} | Type: {instrument_type}\n"
                    f"Entry: ₹{entry_price} | SL: ₹{sl} | T1: ₹{t1}\n"
                    f"Qty: {qty} | Confidence: {ai_confidence:.0%} | R:R 1:{rr}\n"
                    f"📄 Paper trade"
                )
                asyncio.run(send_alert(msg))
            except Exception:
                pass  # alert failure is non-critical

        except Exception as exc:
            st.error(f"Failed to save trade: {exc}")
