# backend/services/alumni_service.py

from datetime import datetime, timezone
from pymongo import ReturnDocument

from database import db


def utc_now():
    return datetime.now(timezone.utc)


async def check_alumni_eligibility(user_id: str, course_id: str):

    enrollment = await db.enrollments.find_one({
        "user_id": user_id,
        "course_id": course_id
    })

    if not enrollment:
        return {"eligible": False}

    # Require full lesson completion
    lessons_completed = (
        enrollment.get("is_completed") is True
        and float(enrollment.get("progress") or 0) >= 100
    )

    if not lessons_completed:
        return {"eligible": False}

    # Find the published final assessment
    final_quiz = await db.quizzes.find_one({
        "course_id": course_id,
        "quiz_type": "final",
        "is_published": True
    })

    if not final_quiz:
        return {"eligible": False}

    # Check for a successful assessment attempt
    passed_attempt = await db.quiz_attempts.find_one({
        "user_id": user_id,
        "course_id": course_id,
        "quiz_id": final_quiz["_id"],
        "passed": True,
        "score": {
            "$gte": final_quiz.get("passing_score", 0)
        }
    })

    if not passed_attempt:
        return {"eligible": False}

    return {
        "eligible": True,
        "course_id": course_id,
        "enrollment": enrollment
    }


async def activate_alumni(user_id: str, course_id: str):

    eligibility = await check_alumni_eligibility(
        user_id, course_id
    )

    if not eligibility["eligible"]:
        return {"activated": False, "eligible": False}

    now = utc_now().isoformat()

    user = await db.users.find_one({"_id": user_id})

    if not user:
        return {"activated": False, "eligible": False}

    course = await db.courses.find_one({"_id": course_id})

    if not course:
        return {"activated": False, "eligible": False}

    # Create profile once, or add another completed course
    profile = await db.alumni_profiles.find_one_and_update(
        {"user_id": user_id},
        {
            "$setOnInsert": {
                "user_id": user_id,
                "full_name": (
                    user.get("name")
                    or user.get("full_name")
                    or ""
                ),
                "created_at": now,
                "bio": "",
                "professional_title": "",
                "skills": [],
                "linkedin_url": "",
                "github_url": "",
                "portfolio_url": "",
                "is_public": False,
                "welcome_email_status": "pending"
            },
            "$set": {
                "is_verified": True,
                "updated_at": now
            },
            "$addToSet": {
                "completed_course_ids": course_id
            }
        },
        upsert=True,
        return_document=ReturnDocument.AFTER
    )

    return {
        "activated": True,
        "eligible": True,
        "user_id": user_id,
        "course_id": course_id,
        "welcome_email_status": profile.get(
            "welcome_email_status"
        )
    }


async def create_alumni_indexes():

    await db.alumni_profiles.create_index(
        "user_id",
        unique=True
    )

    await db.alumni_profiles.create_index(
        "is_verified"
    )
