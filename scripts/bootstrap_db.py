#!/usr/bin/env python3
"""
Bootstrap script — run once on a fresh environment.

Steps:
  1. Create the PostgreSQL database if it doesn't exist
  2. Run all Alembic migrations (upgrade head)
  3. Insert initial param_versions row from config/params.yaml
  4. Create required local directories (data/charts, logs)

Usage:
    python scripts/bootstrap_db.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import subprocess

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s — %(message)s",
)
logger = logging.getLogger("bootstrap")


def create_database_if_missing() -> None:
    from config.settings import settings

    cfg = settings()
    # Parse the DATABASE_URL to extract connection components
    # Expected format: postgresql+psycopg2://user:password@host:port/dbname
    url = cfg.database_url.replace("postgresql+psycopg2://", "")
    user_pass, host_db = url.split("@", 1)
    user, password = user_pass.split(":", 1)
    host_port, dbname = host_db.rsplit("/", 1)
    if ":" in host_port:
        host, port = host_port.split(":", 1)
    else:
        host, port = host_port, "5432"

    logger.info("Connecting to PostgreSQL at %s:%s as %s", host, port, user)
    try:
        conn = psycopg2.connect(
            host=host, port=port, user=user, password=password, dbname="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{dbname}"')
            logger.info("Created database: %s", dbname)
        else:
            logger.info("Database already exists: %s", dbname)
        cur.close()
        conn.close()
    except Exception as exc:
        logger.error("Failed to create database: %s", exc)
        raise


def run_migrations() -> None:
    logger.info("Running Alembic migrations...")
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error("Alembic failed:\n%s", result.stderr)
        raise RuntimeError("Migration failed")
    logger.info("Migrations complete:\n%s", result.stdout.strip())


def seed_initial_params() -> None:
    from atos.core.database import engine
    from config.settings import load_params

    params = load_params()
    version = params.get("meta", {}).get("version", "1.0.0")

    with engine.connect() as conn:
        # Check if already seeded
        result = conn.execute(
            text("SELECT COUNT(*) FROM param_versions WHERE version = :v"),
            {"v": version},
        )
        if result.scalar() > 0:
            logger.info("Param version %s already seeded", version)
            return

        conn.execute(
            text(
                "INSERT INTO param_versions (version, is_active, params, change_note, effective_from) "
                "VALUES (:version, TRUE, :params::jsonb, 'Initial seed', CURRENT_DATE)"
            ),
            {"version": version, "params": str(params).replace("'", '"')},
        )
        conn.commit()
        logger.info("Seeded initial param version: %s", version)


def create_local_dirs() -> None:
    dirs = [
        Path("data/charts"),
        Path("data/bhav"),
        Path("logs"),
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    logger.info("Created local directories: %s", [str(d) for d in dirs])


def main() -> None:
    logger.info("=== ATOS Bootstrap ===")
    create_local_dirs()
    create_database_if_missing()
    run_migrations()

    try:
        seed_initial_params()
    except Exception as exc:
        logger.warning("Could not seed initial params (non-fatal): %s", exc)

    logger.info("=== Bootstrap complete — ATOS is ready ===")


if __name__ == "__main__":
    main()
