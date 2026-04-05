"""
Shared pytest fixtures for ATOS tests.

For unit tests: uses SQLite in-memory DB (no Postgres required).
For integration tests (marked @pytest.mark.integration): requires real Postgres.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure repo root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment BEFORE importing anything that reads settings
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DHAN_CLIENT_ID", "test_client")
os.environ.setdefault("DHAN_ACCESS_TOKEN", "test_token")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test_bot_token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test_chat_id")
os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")
os.environ.setdefault("PAPER_TRADE_MODE", "true")


@pytest.fixture(scope="session")
def db_engine():
    """SQLite in-memory engine with all ATOS tables created."""
    from sqlalchemy import create_engine
    from atos.core.database import Base
    import atos.core.models  # noqa: F401 — register all models

    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(db_engine):
    """Provide a transactional SQLAlchemy session that rolls back after each test."""
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def mock_dhan_client():
    """Mock DhanClient for unit tests — no real API calls."""
    client = MagicMock()
    client.get_ltp.return_value = 2850.0
    client.place_market_order.return_value = {"order_id": "PAPER_TEST", "status": "PAPER"}
    client.get_positions.return_value = []
    client.is_available.return_value = True
    return client


@pytest.fixture
def mock_redis(mocker):
    """Mock Redis client to avoid requiring a running Redis instance."""
    mock = MagicMock()
    mock.ping.return_value = True
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = 1
    mocker.patch("atos.core.cache.redis.from_url", return_value=mock)
    return mock
