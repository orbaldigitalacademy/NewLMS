from datetime import datetime, timezone


async def check_alumni_eligibility(db, user_id: str):

    enrollments = await db.enrollments.find({
        "user_id": user_id
    }).to_list(length=None)

    for enrollment in enrollments:

        if float(enrollment.get("progress") or 0) < 100:
            continue

        course_id = enrollment["course_id"]

        final_quizzes = await db.quizzes.find({
            "course_id": course_id,
            "quiz_type": "final",
            "is_published": True
        }).to_list(length=None)

        for quiz in final_quizzes:

            attempts = await db.quiz_attempts.find({
                "user_id": user_id,
                "quiz_id": quiz["id"]
            }).sort("created_at", -1).limit(1).to_list(1)

            if not attempts:
                continue

            last_attempt = attempts[0]

            if (
                last_attempt.get("passed") is True
                and float(last_attempt.get("score") or 0)
                >= float(quiz.get("pass_mark") or 0)
            ):
                return {
                    "eligible": True,
                    "course_id": course_id,
                    "graduated_at": (
                        enrollment.get("completed_at")
                        or datetime.now(timezone.utc).isoformat()
                    )
                }

    return {
        "eligible": False,
        "course_id": None,
        "graduated_at": None
    }
