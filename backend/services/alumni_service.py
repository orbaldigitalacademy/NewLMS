"""Graduation eligibility and idempotent alumni activation."""
from datetime import datetime, timezone
from pymongo import ReturnDocument
from database import db


def now():
    return datetime.now(timezone.utc)


async def check_alumni_eligibility(user_id: str, course_id: str) -> bool:
    enrollment = await db.enrollments.find_one({"user_id": user_id, "course_id": course_id})
    if not enrollment or enrollment.get("is_completed") is not True:
        return False
    if float(enrollment.get("progress") or 0) < 100:
        return False
    quiz = await db.quizzes.find_one({"course_id": course_id, "quiz_type": "final", "is_published": True})
    if not quiz:
        return False
    return await db.quiz_attempts.find_one({
        "user_id": user_id, "course_id": course_id,
        "quiz_id": quiz["_id"], "passed": True,
        "score": {"$gte": quiz.get("passing_score", 0)}
    }) is not None


async def activate_alumni(user_id: str, course_id: str):
    if not await check_alumni_eligibility(user_id, course_id):
        return {"eligible": False, "activated": False}
    user = await db.users.find_one({"_id": user_id})
    course = await db.courses.find_one({"_id": course_id})
    if not user or not course:
        return {"eligible": False, "activated": False}
    timestamp = now()
    profile = await db.alumni_profiles.find_one_and_update(
        {"user_id": user_id},
        {"$setOnInsert": {
            "user_id": user_id, "full_name": user.get("name") or user.get("full_name") or "",
            "created_at": timestamp, "is_public": False,
            "bio": "", "professional_title": "", "skills": [],
            "linkedin_url": "", "github_url": "", "portfolio_url": ""
        }, "$set": {"is_verified": True, "updated_at": timestamp},
         "$addToSet": {"completed_course_ids": course_id}},
        upsert=True, return_document=ReturnDocument.AFTER
    )
    # One welcome notification per person, not per course. Unique index enforces this.
    # Do not enqueue for a user without an email; the job would never be deliverable.
    if user.get("email"):
        await db.alumni_email_jobs.update_one(
            {"_id": f"alumni-welcome:{user_id}"},
            {"$setOnInsert": {
                "user_id": user_id, "kind": "alumni_welcome", "status": "pending",
                "attempts": 0, "created_at": timestamp, "next_attempt_at": timestamp,
                "idempotency_key": f"oda-alumni-welcome-{user_id}",
                "recipient_email": user["email"],
                "recipient_name": user.get("name") or user.get("full_name") or "Graduate"
            }}, upsert=True
        )
    return {"eligible": True, "activated": True, "profile_id": str(profile["_id"])}


async def create_alumni_indexes():
    await db.alumni_profiles.create_index("user_id", unique=True)
    await db.alumni_email_jobs.create_index([("status", 1), ("next_attempt_at", 1)])
    await db.alumni_email_jobs.create_index("user_id")
