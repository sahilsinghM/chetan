"""Unit tests for PnL and charges calculations."""

from __future__ import annotations

import pytest


class TestCalculateCharges:
    def test_long_delivery_basic(self):
        from atos.journal.pnl import calculate_charges

        charges = calculate_charges(entry=1000.0, exit=1100.0, qty=10, instrument_type="EQ_SWING")
        # Should be positive and roughly ₹50–100 range for this trade
        assert charges > 0
        assert charges < 500  # sanity check — not insane

    def test_intraday_lower_stt(self):
        from atos.journal.pnl import calculate_charges

        charges_delivery = calculate_charges(1000.0, 1100.0, 10, "EQ_SWING")
        charges_intraday = calculate_charges(1000.0, 1100.0, 10, "EQ_INTRADAY")
        # Intraday STT (0.025%) is much lower than delivery STT (0.1%)
        assert charges_intraday < charges_delivery

    def test_charges_scale_with_qty(self):
        from atos.journal.pnl import calculate_charges

        charges_10 = calculate_charges(1000.0, 1100.0, 10, "EQ_SWING")
        charges_20 = calculate_charges(1000.0, 1100.0, 20, "EQ_SWING")
        # Charges should roughly double (brokerage is fixed, but turnover-based charges double)
        # Allow some tolerance for fixed brokerage component
        assert charges_20 > charges_10


class TestRealisedPnl:
    def test_long_profitable(self):
        from atos.journal.pnl import realised_pnl

        gross, charges, net = realised_pnl(
            entry=1000.0, exit=1100.0, qty=10, direction="LONG", instrument_type="EQ_SWING"
        )
        assert gross == pytest.approx(1000.0)  # (1100-1000)*10
        assert charges > 0
        assert net < gross  # net should be less than gross due to charges
        assert net > 0  # still profitable

    def test_long_loss(self):
        from atos.journal.pnl import realised_pnl

        gross, charges, net = realised_pnl(
            entry=1000.0, exit=980.0, qty=10, direction="LONG"
        )
        assert gross == pytest.approx(-200.0)  # (980-1000)*10
        assert net < gross  # charges make it worse

    def test_short_profitable(self):
        from atos.journal.pnl import realised_pnl

        gross, charges, net = realised_pnl(
            entry=1000.0, exit=950.0, qty=10, direction="SHORT"
        )
        assert gross == pytest.approx(500.0)  # (1000-950)*10
        assert net > 0

    def test_short_loss(self):
        from atos.journal.pnl import realised_pnl

        gross, charges, net = realised_pnl(
            entry=1000.0, exit=1050.0, qty=10, direction="SHORT"
        )
        assert gross == pytest.approx(-500.0)
        assert net < 0


class TestPositionSizeFromRisk:
    def test_basic_sizing(self):
        from atos.journal.pnl import position_size_from_risk

        # Capital: ₹5L, risk 1% = ₹5000, risk per share ₹10 → 500 shares
        qty = position_size_from_risk(
            capital=500_000, risk_pct=0.01, entry=1000.0, sl=990.0
        )
        assert qty == 500

    def test_lot_rounding(self):
        from atos.journal.pnl import position_size_from_risk

        # lot_size=25 → should round down to nearest 25
        qty = position_size_from_risk(
            capital=500_000, risk_pct=0.01, entry=1000.0, sl=990.0, lot_size=25
        )
        assert qty % 25 == 0
        assert qty <= 500

    def test_sl_equals_entry_returns_zero(self):
        from atos.journal.pnl import position_size_from_risk

        qty = position_size_from_risk(
            capital=500_000, risk_pct=0.01, entry=1000.0, sl=1000.0
        )
        assert qty == 0

    def test_large_sl_returns_small_qty(self):
        from atos.journal.pnl import position_size_from_risk

        qty = position_size_from_risk(
            capital=100_000, risk_pct=0.01, entry=1000.0, sl=100.0
        )
        assert qty >= 0  # might be 1 or 0 depending on exact math
        assert qty < 5


class TestRiskReward:
    def test_long_2_to_1(self):
        from atos.journal.pnl import risk_reward

        rr = risk_reward(entry=100.0, sl=90.0, target=120.0, direction="LONG")
        assert rr == pytest.approx(2.0)

    def test_short_rr(self):
        from atos.journal.pnl import risk_reward

        rr = risk_reward(entry=100.0, sl=110.0, target=80.0, direction="SHORT")
        assert rr == pytest.approx(2.0)

    def test_zero_risk_returns_zero(self):
        from atos.journal.pnl import risk_reward

        rr = risk_reward(entry=100.0, sl=100.0, target=120.0, direction="LONG")
        assert rr == 0.0
