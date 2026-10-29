"""Persistent MongoDB email queue processor with atomic lease and retry."""
import logging
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from pymongo import ReturnDocument
from database import db
from services.alumni_email_service import send_alumni_welcome_email

log = logging.getLogger(__name__)
MAX_ATTEMPTS = 6
LEASE_SECONDS = 120


def utcnow():
    return datetime.now(timezone.utc)


async def process_alumni_email_jobs(batch_size: int = 10):
    """Safe to invoke repeatedly; only one worker can claim a given job at a time."""
    for _ in range(batch_size):
        stamp = utcnow()
        token = uuid4().hex
        job = await db.alumni_email_jobs.find_one_and_update(
            {"$or": [
                {"status": "pending", "next_attempt_at": {"$lte": stamp}},
                {"status": "retry", "next_attempt_at": {"$lte": stamp}},
                {"status": "sending", "lease_until": {"$lte": stamp}}
            ], "attempts": {"$lt": MAX_ATTEMPTS}},
            {"$set": {"status": "sending", "lease_until": stamp + timedelta(seconds=LEASE_SECONDS),
                      "lock_token": token, "last_attempt_at": stamp}, "$inc": {"attempts": 1}},
            sort=[("next_attempt_at", 1)], return_document=ReturnDocument.AFTER
        )
        if not job:
            break
        try:
            message_id = await send_welcome_email(job)
            await db.alumni_email_jobs.update_one(
                {"_id": job["_id"], "lock_token": token, "status": "sending"},
                {"$set": {"status": "accepted", "resend_email_id": message_id,
                          "accepted_at": utcnow()},
                 "$unset": {"lease_until": "", "lock_token": "", "last_error": ""}}
            )
        except Exception as exc:
            log.exception("Alumni welcome email failed for job %s", job["_id"])
            attempts = job["attempts"]
            terminal = attempts >= MAX_ATTEMPTS
            # 1, 2, 4, 8, 16, 32 minutes (capped)
            delay = min(60 * (2 ** (attempts - 1)), 3600)
            await db.alumni_email_jobs.update_one(
                {"_id": job["_id"], "lock_token": token, "status": "sending"},
                {"$set": {"status": "failed" if terminal else "retry",
                          "next_attempt_at": utcnow() + timedelta(seconds=delay),
                          "last_error": str(exc)[:500]},
                 "$unset": {"lease_until": "", "lock_token": ""}}
            )


def register_alumni_email_worker(scheduler):
    """Call BEFORE the existing scheduler.start(); do not start another scheduler."""
    scheduler.add_job(
        process_alumni_email_jobs, trigger="interval", seconds=60,
        id="alumni_welcome_email_worker", replace_existing=True,
        max_instances=1, coalesce=True
    )
