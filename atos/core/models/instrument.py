"""Instrument / universe table."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, String, func
from sqlalchemy.orm import Mapped, mapped_column

from atos.core.database import Base


class Instrument(Base):
    __tablename__ = "instruments"

    symbol: Mapped[str] = mapped_column(String, primary_key=True)
    isin: Mapped[str | None] = mapped_column(String, unique=True)
    company_name: Mapped[str | None] = mapped_column(String)
    sector: Mapped[str | None] = mapped_column(String)
    series: Mapped[str] = mapped_column(String, default="EQ")
    exchange: Mapped[str] = mapped_column(String, default="NSE")
    lot_size: Mapped[int] = mapped_column(default=1)
    tick_size: Mapped[float] = mapped_column(default=0.05)
    is_fno: Mapped[bool] = mapped_column(Boolean, default=False)
    is_nse500: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Instrument {self.symbol}>"
