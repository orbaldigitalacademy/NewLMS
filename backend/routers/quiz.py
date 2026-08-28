"""Quiz and assessment router."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from auth import get_current_user, require_admin
from database import db
from models.quiz import (
    Quiz,
    QuizCreate,
    QuizQuestionPublic,
    QuizSubmitRequest,
    QuizUpdate,
    QuizAttempt,
)
from models.user import User


router = APIRouter(
    prefix="/quizzes",
    tags=["quizzes"],
)


def now_utc():
    return datetime.now(timezone.utc)


def quiz_public_response(quiz: Quiz):
    """Remove correct answers before sending quiz to students."""

    return {
        "id": quiz.id,
        "title": quiz.title,
        "description": quiz.description,
        "quiz_type": quiz.quiz_type,
        "course_id": quiz.course_id,
        "lesson_id": quiz.lesson_id,
        "passing_score": quiz.passing_score,
        "max_attempts": quiz.max_attempts,
        "is_published": quiz.is_published,
        "questions": [
            {
                "id": question.id,
                "question": question.question,
                "options": question.options,
            }
            for question in quiz.questions
        ],
    }


async def get_enrollment(user_id: str, course_id: str):
    """Find the student's enrollment for a course."""

    enrollment = await db.enrollments.find_one(
        {
            "user_id": user_id,
            "course_id": course_id,
        }
    )

    return enrollment


async def check_quiz_access(
    quiz: Quiz,
    user: User,
):
    """
    Check whether a student is allowed to access a quiz.

    Lesson quiz:
        Student must have completed the associated lesson.

    Final quiz:
        Student must have completed all lessons in the course.
    """

    enrollment = await get_enrollment(
        user.id,
        quiz.course_id,
    )

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not enrolled in this course",
        )

    # Payment/enrollment approval check
    payment_status = enrollment.get("payment_status")

    if payment_status and payment_status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your enrollment has not been approved",
        )

    completed_lessons = enrollment.get(
        "completed_lessons",
        [],
    )

    # Lesson quiz
    if quiz.quiz_type == "lesson":

        if not quiz.lesson_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lesson quiz is missing lesson_id",
            )

        if quiz.lesson_id not in completed_lessons:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Complete the lesson before taking its quiz",
            )

    # Final course test
    elif quiz.quiz_type == "final":

        lessons = await db.lessons.find(
            {
                "course_id": quiz.course_id
            }
        ).to_list(length=None)

        lesson_ids = [
            lesson["_id"]
            for lesson in lessons
        ]

        missing_lessons = [
            lesson_id
            for lesson_id in lesson_ids
            if lesson_id not in completed_lessons
        ]

        if missing_lessons:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Complete all course lessons before taking the final test",
            )

    return enrollment


# ============================================================
# ADMIN: CREATE QUIZ
# ============================================================

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
async def create_quiz(
    payload: QuizCreate,
    admin: User = Depends(require_admin),
):
    """Create a new quiz."""

    # Validate quiz type
    if payload.quiz_type not in {"lesson", "final"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="quiz_type must be 'lesson' or 'final'",
        )

    # Lesson quizzes must have lesson_id
    if payload.quiz_type == "lesson" and not payload.lesson_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lesson quizzes require lesson_id",
        )

    # Final quizzes should not require a lesson
    if payload.quiz_type == "final":
        payload.lesson_id = None

    # Check course exists
    course = await db.courses.find_one(
        {"_id": payload.course_id}
    )

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    # Check lesson exists
    if payload.lesson_id:

        lesson = await db.lessons.find_one(
            {
                "_id": payload.lesson_id,
                "course_id": payload.course_id,
            }
        )

        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found in this course",
            )

    # Validate questions
    for question in payload.questions:

        if question.correct_answer not in question.options:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Correct answer for question "
                    f"'{question.id}' must be one of its options"
                ),
            )

    quiz = Quiz(
        id=str(uuid4()),
        title=payload.title,
        description=payload.description,
        quiz_type=payload.quiz_type,
        course_id=payload.course_id,
        lesson_id=payload.lesson_id,
        questions=payload.questions,
        passing_score=payload.passing_score,
        max_attempts=payload.max_attempts,
        is_published=payload.is_published,
    )

    await db.quizzes.insert_one(
        quiz.to_mongo()
    )

    return quiz_public_response(quiz)


# ============================================================
# ADMIN: LIST QUIZZES
# ============================================================

@router.get("/admin/all")
async def get_all_quizzes(
    admin: User = Depends(require_admin),
):
    """Return all quizzes for administrators."""

    quizzes = await db.quizzes.find({}).sort(
        "created_at",
        -1,
    ).to_list(length=None)

    return [
        quiz_public_response(
            Quiz.from_mongo(doc)
        )
        for doc in quizzes
    ]


# ============================================================
# ADMIN: UPDATE QUIZ
# ============================================================

@router.put("/{quiz_id}")
async def update_quiz(
    quiz_id: str,
    payload: QuizUpdate,
    admin: User = Depends(require_admin),
):
    """Update an existing quiz."""

    existing = await db.quizzes.find_one(
        {"_id": quiz_id}
    )

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        )

    update_data = payload.model_dump(
        exclude_unset=True
    )

    if "questions" in update_data:

        for question in update_data["questions"]:

            if question["correct_answer"] not in question["options"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Correct answer for question "
                        f"'{question['id']}' must be one of its options"
                    ),
                )

    update_data["updated_at"] = now_utc()

    await db.quizzes.update_one(
        {"_id": quiz_id},
        {
            "$set": update_data
        },
    )

    updated = await db.quizzes.find_one(
        {"_id": quiz_id}
    )

    return quiz_public_response(
        Quiz.from_mongo(updated)
    )


# ============================================================
# ADMIN: DELETE QUIZ
# ============================================================

@router.delete("/{quiz_id}")
async def delete_quiz(
    quiz_id: str,
    admin: User = Depends(require_admin),
):
    """Delete a quiz and its attempts."""

    result = await db.quizzes.delete_one(
        {"_id": quiz_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        )

    # Remove attempts belonging to the quiz
    await db.quiz_attempts.delete_many(
        {"quiz_id": quiz_id}
    )

    return {
        "message": "Quiz deleted successfully"
    }


# ============================================================
# STUDENT: GET QUIZ FOR A LESSON
# ============================================================

@router.get("/lesson/{lesson_id}")
async def get_lesson_quiz(
    lesson_id: str,
    user: User = Depends(get_current_user),
):
    """
    Return the published quiz associated with a lesson.

    Correct answers are never returned.
    """

    lesson = await db.lessons.find_one(
        {"_id": lesson_id}
    )

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    quiz_doc = await db.quizzes.find_one(
        {
            "lesson_id": lesson_id,
            "quiz_type": "lesson",
            "is_published": True,
        }
    )

    if not quiz_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No quiz available for this lesson",
        )

    quiz = Quiz.from_mongo(quiz_doc)

    await check_quiz_access(
        quiz,
        user,
    )

    return quiz_public_response(quiz)


# ============================================================
# STUDENT: GET QUIZ BY ID
# ============================================================

@router.get("/{quiz_id}")
async def get_quiz(
    quiz_id: str,
    user: User = Depends(get_current_user),
):
    """Get a quiz without exposing correct answers."""

    quiz_doc = await db.quizzes.find_one(
        {
            "_id": quiz_id,
            "is_published": True,
        }
    )

    if not quiz_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        )

    quiz = Quiz.from_mongo(quiz_doc)

    await check_quiz_access(
        quiz,
        user,
    )

    # Count attempts
    attempts_count = await db.quiz_attempts.count_documents(
        {
            "quiz_id": quiz.id,
            "user_id": user.id,
        }
    )

    if attempts_count >= quiz.max_attempts:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You have reached the maximum number of attempts",
        )

    response = quiz_public_response(quiz)

    response["attempts_used"] = attempts_count
    response["attempts_remaining"] = max(
        quiz.max_attempts - attempts_count,
        0,
    )

    return response


# ============================================================
# STUDENT: SUBMIT QUIZ
# ============================================================

@router.post("/{quiz_id}/submit")
async def submit_quiz(
    quiz_id: str,
    payload: QuizSubmitRequest,
    user: User = Depends(get_current_user),
):
    """Submit a quiz and calculate the student's score."""

    quiz_doc = await db.quizzes.find_one(
        {
            "_id": quiz_id,
            "is_published": True,
        }
    )

    if not quiz_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        )

    quiz = Quiz.from_mongo(quiz_doc)

    # Check access
    await check_quiz_access(
        quiz,
        user,
    )

    # Check attempts
    attempts_count = await db.quiz_attempts.count_documents(
        {
            "quiz_id": quiz.id,
            "user_id": user.id,
        }
    )

    if attempts_count >= quiz.max_attempts:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Maximum quiz attempts reached",
        )

    # Ensure answers only contain actual question IDs
    question_map = {
        question.id: question
        for question in quiz.questions
    }

    for question_id in payload.answers:

        if question_id not in question_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid question ID: {question_id}",
            )

    # Calculate score
    total_questions = len(quiz.questions)

    if total_questions == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quiz contains no questions",
        )

    correct_count = 0

    for question in quiz.questions:

        submitted_answer = payload.answers.get(
            question.id
        )

        if submitted_answer == question.correct_answer:
            correct_count += 1

    score = round(
        (correct_count / total_questions) * 100,
        2,
    )

    passed = score >= quiz.passing_score

    attempt = QuizAttempt(
        id=str(uuid4()),
        quiz_id=quiz.id,
        course_id=quiz.course_id,
        lesson_id=quiz.lesson_id,
        user_id=user.id,
        answers=payload.answers,
        score=score,
        passed=passed,
    )

    await db.quiz_attempts.insert_one(
        attempt.to_mongo()
    )

    # --------------------------------------------------------
    # If a lesson quiz is passed, record quiz completion.
    # --------------------------------------------------------

    if passed and quiz.quiz_type == "lesson":

        await db.enrollments.update_one(
            {
                "user_id": user.id,
                "course_id": quiz.course_id,
            },
            {
                "$addToSet": {
                    "completed_quizzes": quiz.id
                }
            },
        )

    # --------------------------------------------------------
    # If final test is passed, mark course as completed.
    # --------------------------------------------------------

    if passed and quiz.quiz_type == "final":

        await db.enrollments.update_one(
            {
                "user_id": user.id,
                "course_id": quiz.course_id,
            },
            {
                "$set": {
                    "course_completed": True,
                    "course_completed_at": now_utc(),
                    "final_quiz_id": quiz.id,
                    "final_quiz_score": score,
                }
            },
        )

    return {
        "attempt_id": attempt.id,
        "quiz_id": quiz.id,
        "score": score,
        "passed": passed,
        "passing_score": quiz.passing_score,
        "correct_answers": correct_count,
        "total_questions": total_questions,
        "attempts_used": attempts_count + 1,
        "attempts_remaining": max(
            quiz.max_attempts - (attempts_count + 1),
            0,
        ),
        "message": (
            "Congratulations! You passed the quiz."
            if passed
            else "You did not pass the quiz. You can try again."
        ),
    }


# ============================================================
# STUDENT: GET MY ATTEMPTS
# ============================================================

@router.get("/{quiz_id}/attempts")
async def get_my_attempts(
    quiz_id: str,
    user: User = Depends(get_current_user),
):
    """Return the student's attempts for a quiz."""

    quiz = await db.quizzes.find_one(
        {"_id": quiz_id}
    )

    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        )

    attempts = await db.quiz_attempts.find(
        {
            "quiz_id": quiz_id,
            "user_id": user.id,
        }
    ).sort(
        "submitted_at",
        -1,
    ).to_list(length=None)

    return [
        {
            "id": attempt["_id"],
            "score": attempt["score"],
            "passed": attempt["passed"],
            "submitted_at": attempt["submitted_at"],
        }
        for attempt in attempts
    ]


# ============================================================
# ADMIN: VIEW ATTEMPTS
# ============================================================

@router.get("/{quiz_id}/attempts/all")
async def get_all_attempts(
    quiz_id: str,
    admin: User = Depends(require_admin),
):
    """Return all student attempts for a quiz."""

    attempts = await db.quiz_attempts.find(
        {
            "quiz_id": quiz_id
        }
    ).sort(
        "submitted_at",
        -1,
    ).to_list(length=None)

    return [
        {
            "id": attempt["_id"],
            "user_id": attempt["user_id"],
            "quiz_id": attempt["quiz_id"],
            "course_id": attempt["course_id"],
            "lesson_id": attempt.get("lesson_id"),
            "score": attempt["score"],
            "passed": attempt["passed"],
            "submitted_at": attempt["submitted_at"],
        }
        for attempt in attempts
    ]
