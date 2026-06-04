"""Background scheduler. Used for clean-up tasks like abandoning stale pending payments."""
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import db

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def abandon_stale_payments():
    """Mark payments still pending after 1 hour as abandoned."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    result = await db.payments.update_many(
        {"status": "pending", "created_at": {"$lt": cutoff}},
        {"$set": {"status": "abandoned"}},
    )
    if result.modified_count:
        logger.info("Abandoned %d stale payments", result.modified_count)


def start_scheduler():
    if scheduler.running:
        return
    scheduler.add_job(abandon_stale_payments, "interval", minutes=30, id="abandon_stale_payments")
    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
