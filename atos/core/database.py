"""
SQLAlchemy engine and session factory.

Usage:
    from atos.core.database import get_db

    with get_db() as db:
        db.add(some_model)
        # auto-committed on exit, rolled back on exception
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config.settings import settings


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


def _make_engine():
    url = settings().database_url
    kwargs: dict = {
        "pool_pre_ping": True,
        "echo": (settings().environment == "development"),
    }
    # SQLite (used in tests) doesn't support pool_size / max_overflow
    if not url.startswith("sqlite"):
        kwargs["pool_size"] = 5
        kwargs["max_overflow"] = 10
    return create_engine(url, **kwargs)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Yield a database session, auto-committing on clean exit and
    rolling back on exception.

    Usage::

        with get_db() as db:
            db.add(trade)
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_connection() -> bool:
    """Return True if the database is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
