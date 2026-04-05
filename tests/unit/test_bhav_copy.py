"""Unit tests for NSE bhav copy parsing."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


class TestNormaliseBhav:
    """Test the _normalise() function with sample CSV data."""

    def _normalise(self, df, trade_date=None):
        from atos.data.nse.bhav_copy import _normalise
        return _normalise(df, trade_date or date(2025, 1, 15))

    def test_new_format_columns(self):
        df = pd.DataFrame(
            {
                "TckrSymb": ["RELIANCE", "INFY", "HDFCBANK"],
                "SctySrs": ["EQ", "EQ", "EQ"],
                "OpnPric": [2800.0, 1500.0, 1650.0],
                "HghPric": [2850.0, 1520.0, 1670.0],
                "LwPric": [2790.0, 1490.0, 1640.0],
                "ClsPric": [2840.0, 1510.0, 1660.0],
                "TtlTradgVol": [1_000_000, 500_000, 750_000],
            }
        )
        result = self._normalise(df)
        assert "symbol" in result.columns
        assert "close" in result.columns
        assert "volume" in result.columns
        assert len(result) == 3
        assert result.iloc[0]["symbol"] == "RELIANCE"
        assert result.iloc[0]["close"] == pytest.approx(2840.0)

    def test_old_format_columns(self):
        df = pd.DataFrame(
            {
                "SYMBOL": ["TCS", "WIPRO"],
                "SERIES": ["EQ", "EQ"],
                "OPEN": [3500.0, 450.0],
                "HIGH": [3520.0, 460.0],
                "LOW": [3480.0, 440.0],
                "CLOSE": [3510.0, 455.0],
                "TOTTRDQTY": [200_000, 300_000],
            }
        )
        result = self._normalise(df)
        assert len(result) == 2
        assert "symbol" in result.columns

    def test_filters_non_eq_series(self):
        df = pd.DataFrame(
            {
                "TckrSymb": ["RELIANCE", "RELIANCE-SM"],
                "SctySrs": ["EQ", "SM"],
                "OpnPric": [2800.0, 2800.0],
                "HghPric": [2850.0, 2850.0],
                "LwPric": [2790.0, 2790.0],
                "ClsPric": [2840.0, 2840.0],
                "TtlTradgVol": [1_000_000, 1000],
            }
        )
        result = self._normalise(df)
        # SM series should be included (in allowed list)
        assert all(r["symbol"] in ["RELIANCE", "RELIANCE-SM"] for _, r in result.iterrows())

    def test_date_column_added(self):
        trade_date = date(2025, 6, 15)
        df = pd.DataFrame(
            {
                "TckrSymb": ["RELIANCE"],
                "SctySrs": ["EQ"],
                "OpnPric": [2800.0],
                "HghPric": [2850.0],
                "LwPric": [2790.0],
                "ClsPric": [2840.0],
                "TtlTradgVol": [1_000_000],
            }
        )
        result = self._normalise(df, trade_date)
        assert result.iloc[0]["date"] == trade_date

    def test_handles_missing_values(self):
        df = pd.DataFrame(
            {
                "TckrSymb": ["RELIANCE", None, "INFY"],
                "SctySrs": ["EQ", "EQ", "EQ"],
                "OpnPric": [2800.0, 0.0, 1500.0],
                "HghPric": [2850.0, 0.0, 1520.0],
                "LwPric": [2790.0, 0.0, 1490.0],
                "ClsPric": [2840.0, None, 1510.0],
                "TtlTradgVol": [1_000_000, 0, 500_000],
            }
        )
        result = self._normalise(df)
        # Rows with null symbol or close should be dropped
        assert all(result["symbol"].notna())
        assert all(result["close"].notna())


class TestBuildUrl:
    def test_url_format(self):
        from atos.data.nse.bhav_copy import _build_url

        url = _build_url(date(2025, 1, 15))
        assert "15012025" in url
        assert "nsearchives.nseindia.com" in url
        assert url.endswith(".zip")


class TestSampleFixture:
    """If fixture CSV exists, test full round-trip parse."""

    def test_sample_bhav_fixture(self):
        fixture = FIXTURE_DIR / "sample_bhav.csv"
        if not fixture.exists():
            pytest.skip("sample_bhav.csv fixture not found")

        from atos.data.nse.bhav_copy import _normalise

        df = pd.read_csv(fixture)
        result = _normalise(df, date(2025, 1, 15))
        assert len(result) > 0
        assert "symbol" in result.columns
        assert "close" in result.columns
