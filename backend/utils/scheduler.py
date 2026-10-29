"""
Background scheduler.

Handles:
1. Abandoning stale pending payments
2. Sending queued alumni welcome emails
"""

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import db
from services.alumni_email_worker import register_alumni_email_worker

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


# ==========================================
# EXISTING PAYMENT CLEANUP
# ==========================================

async def abandon_stale_payments():
    """Mark payments pending for over 24 hours as abandoned."""

    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=24)
    ).isoformat()

    result = await db.payments.update_many(
        {
            "status": "pending",
            "created_at": {"$lt": cutoff}
        },
        {
            "$set": {"status": "abandoned"}
        }
    )

    if result.modified_count:
        logger.info(
            "Abandoned %d stale payments",
            result.modified_count
        )


# ==========================================
# START BACKGROUND SCHEDULER
# ==========================================

def start_scheduler():

    if scheduler.running:
        return

    scheduler.add_job(
        abandon_stale_payments,
        trigger="interval",
        minutes=30,
        id="abandon_stale_payments",
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )

    register_alumni_email_worker(scheduler)

    scheduler.start()

    logger.info(
        "Scheduler started: payments and alumni emails"
    )


# ==========================================
# STOP BACKGROUND SCHEDULER
# ==========================================

def stop_scheduler():

    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
