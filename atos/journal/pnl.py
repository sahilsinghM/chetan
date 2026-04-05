"""
PnL and charges calculator.

NSE equity charges applied:
  - Brokerage: ₹20 flat per order (Dhan)
  - STT: 0.1% on sell side (delivery) / 0.025% on sell side (intraday)
  - Exchange transaction: 0.00345% on both sides
  - SEBI: 0.0001% on both sides
  - GST: 18% on (brokerage + exchange charge + SEBI)
  - Stamp duty: 0.015% on buy side only

All rates are read from config/params.yaml charges section.

Usage:
    from atos.journal.pnl import calculate_charges, realised_pnl

    charges = calculate_charges(
        entry=1000.0, exit=1050.0, qty=10,
        instrument_type="EQ_SWING"
    )
    gross = (exit - entry) * qty  # = 500
    net = gross - charges
"""

from __future__ import annotations

from config.settings import load_params


def _charges_config() -> dict:
    return load_params().get("charges", {})


def calculate_charges(
    entry: float,
    exit: float,
    qty: int,
    instrument_type: str = "EQ_SWING",
) -> float:
    """
    Calculate total NSE charges for a round-trip trade.

    :param entry: Entry price per share
    :param exit: Exit price per share
    :param qty: Number of shares traded
    :param instrument_type: One of EQ_SWING, EQ_INTRADAY, FUT, OPT
    :returns: Total charges in INR (always positive)
    """
    cfg = _charges_config()

    brokerage = cfg.get("brokerage_per_order", 20.0) * 2  # entry + exit orders
    buy_turnover = entry * qty
    sell_turnover = exit * qty

    # STT (sell side only for delivery; sell side for intraday)
    intraday = instrument_type == "EQ_INTRADAY"
    if intraday:
        stt = sell_turnover * cfg.get("stt_intraday_sell_pct", 0.00025)
    else:
        stt = sell_turnover * cfg.get("stt_delivery_sell_pct", 0.001)

    # Exchange transaction charge (both sides)
    exchange_rate = cfg.get("exchange_txn_pct", 0.0000345)
    exchange = (buy_turnover + sell_turnover) * exchange_rate

    # SEBI (both sides)
    sebi_rate = cfg.get("sebi_pct", 0.000001)
    sebi = (buy_turnover + sell_turnover) * sebi_rate

    # GST on brokerage + exchange + SEBI
    gst_base = brokerage + exchange + sebi
    gst = gst_base * cfg.get("gst_pct", 0.18)

    # Stamp duty (buy side only)
    stamp = buy_turnover * cfg.get("stamp_duty_buy_pct", 0.00015)

    total = brokerage + stt + exchange + sebi + gst + stamp
    return round(total, 2)


def realised_pnl(
    entry: float,
    exit: float,
    qty: int,
    direction: str,
    instrument_type: str = "EQ_SWING",
) -> tuple[float, float, float]:
    """
    Calculate gross PnL, charges, and net PnL for a closed trade.

    :param direction: 'LONG' or 'SHORT'
    :returns: (gross_pnl, charges, net_pnl) all in INR
    """
    direction_mult = 1.0 if direction == "LONG" else -1.0
    gross = (exit - entry) * qty * direction_mult
    charges = calculate_charges(entry, exit, qty, instrument_type)
    net = gross - charges
    return round(gross, 2), charges, round(net, 2)


def unrealised_pnl(
    entry: float,
    ltp: float,
    qty_remaining: int,
    direction: str,
) -> float:
    """
    Calculate unrealised PnL for an open position (no charges deducted).

    :param ltp: Last traded price
    :param qty_remaining: Current open quantity (after partial exits)
    """
    direction_mult = 1.0 if direction == "LONG" else -1.0
    return round((ltp - entry) * qty_remaining * direction_mult, 2)


def risk_reward(entry: float, sl: float, target: float, direction: str) -> float:
    """
    Return the risk:reward ratio for a trade setup.
    e.g. 1.0 = 1:1, 2.0 = 1:2 (target is twice the risk)
    """
    if direction == "LONG":
        risk = entry - sl
        reward = target - entry
    else:
        risk = sl - entry
        reward = entry - target
    if risk <= 0:
        return 0.0
    return round(reward / risk, 2)


def position_size_from_risk(
    capital: float,
    risk_pct: float,
    entry: float,
    sl: float,
    lot_size: int = 1,
) -> int:
    """
    Calculate position size based on risk percentage of capital.

    :param capital: Total capital in INR
    :param risk_pct: Fraction of capital to risk (e.g. 0.01 for 1%)
    :param entry: Entry price
    :param sl: Stop-loss price
    :param lot_size: Minimum lot size (1 for equities, varies for F&O)
    :returns: Number of shares to buy (rounded down to nearest lot)
    """
    if entry == sl:
        return 0
    risk_amount = capital * risk_pct
    risk_per_share = abs(entry - sl)
    raw_qty = risk_amount / risk_per_share
    # Round down to nearest lot
    lots = int(raw_qty // lot_size)
    return max(lots * lot_size, 0)
