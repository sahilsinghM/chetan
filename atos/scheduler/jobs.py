"""
APScheduler job definitions and daemon entry point.

Jobs defined here:
  - bhav_copy_job     : 6:05 PM Mon–Fri — download + ingest NSE bhav copy
  - candle_refresh_job: Every 5 min during market hours — (Phase 2+)
  - screener_job      : 8:00 AM Mon–Fri — (Phase 2 stub)
  - weekly_review_job : Sunday 7:00 PM — (Phase 5 stub)

Every job checks the killswitch at start. If active, the job logs and skips.

Run as daemon:
    python -m atos.scheduler.jobs
"""

from __future__ import annotations

import logging
from datetime import date, datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from atos.core.cache import cache
from atos.core.constants import EventType
from atos.core.database import get_db
from atos.core.models.event_log import EventLog

logger = logging.getLogger(__name__)


def _killswitch_guard(job_name: str) -> bool:
    """Return True if the killswitch is active (job should skip)."""
    if cache.is_killswitch_active():
        logger.warning("Job %s skipped — killswitch is active", job_name)
        return True
    return False


def bhav_copy_job() -> None:
    """Download and ingest today's NSE bhav copy."""
    if _killswitch_guard("bhav_copy_job"):
        return

    logger.info("bhav_copy_job: starting for %s", date.today())
    try:
        from atos.data.nse.bhav_copy import download_and_ingest_bhav

        with get_db() as db:
            rows = download_and_ingest_bhav(date.today(), db)
            db.add(
                EventLog(
                    event_type=EventType.BHAV_COPY_INGESTED,
                    source="SCHEDULER",
                    payload={"date": date.today().isoformat(), "rows": rows},
                )
            )
        logger.info("bhav_copy_job: ingested %d rows", rows)

        try:
            import asyncio
            from atos.alerts.telegram_bot import send_alert
            asyncio.run(send_alert(f"✅ Bhav copy ingested: {rows} rows for {date.today()}"))
        except Exception:
            pass

    except Exception as exc:
        logger.error("bhav_copy_job failed: %s", exc, exc_info=True)
        try:
            import asyncio
            from atos.alerts.telegram_bot import send_alert
            asyncio.run(send_alert(f"❌ Bhav copy ingestion FAILED: {exc}"))
        except Exception:
            pass


def candle_refresh_job() -> None:
    """Refresh intraday candles for watchlist symbols. (Phase 2 implementation)"""
    if _killswitch_guard("candle_refresh_job"):
        return

    now = datetime.now()
    # Only run during market hours
    if now.hour < 9 or (now.hour == 9 and now.minute < 15):
        return
    if now.hour >= 15 and now.minute >= 35:
        return

    logger.debug("candle_refresh_job: Phase 2 not yet implemented")


def screener_job() -> None:
    """Run the screener engine and alert on candidates. (Phase 2)"""
    if _killswitch_guard("screener_job"):
        return
    logger.debug("screener_job: Phase 2 not yet implemented")


def weekly_review_job() -> None:
    """Run weekly post-mortem via Claude. (Phase 5)"""
    if _killswitch_guard("weekly_review_job"):
        return
    logger.debug("weekly_review_job: Phase 5 not yet implemented")


def create_scheduler() -> BlockingScheduler:
    """Create and configure the APScheduler instance."""
    scheduler = BlockingScheduler(timezone="Asia/Kolkata")

    # Bhav copy: 6:05 PM on trading days
    scheduler.add_job(
        bhav_copy_job,
        CronTrigger(hour=18, minute=5, day_of_week="mon-fri", timezone="Asia/Kolkata"),
        id="bhav_copy",
        coalesce=True,
        max_instances=1,
        misfire_grace_time=600,
    )

    # Candle refresh: every 5 minutes, Mon–Fri
    scheduler.add_job(
        candle_refresh_job,
        CronTrigger(
            hour="9-15",
            minute="*/5",
            day_of_week="mon-fri",
            timezone="Asia/Kolkata",
        ),
        id="candle_refresh",
        coalesce=True,
        max_instances=1,
        misfire_grace_time=60,
    )

    # Morning screener: 8:00 AM on trading days (Phase 2)
    scheduler.add_job(
        screener_job,
        CronTrigger(hour=8, minute=0, day_of_week="mon-fri", timezone="Asia/Kolkata"),
        id="screener",
        coalesce=True,
        max_instances=1,
    )

    # Weekly review: Sunday 7:00 PM (Phase 5)
    scheduler.add_job(
        weekly_review_job,
        CronTrigger(day_of_week="sun", hour=19, minute=0, timezone="Asia/Kolkata"),
        id="weekly_review",
        coalesce=True,
    )

    return scheduler


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    logger.info("Starting ATOS scheduler daemon...")
    scheduler = create_scheduler()
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
        scheduler.shutdown()
