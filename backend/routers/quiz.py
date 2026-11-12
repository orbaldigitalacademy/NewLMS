"""Quiz and assessment router."""
from datetime import datetime, timezone
from uuid import uuid4
import secrets
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from pydantic import BaseModel, Field, ValidationError
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
from services.alumni_service import activate_alumni
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/quizzes",
    tags=["quizzes"],
)


def now_utc():
    return datetime.now(timezone.utc)


def validate_question(
    question_id: str,
    question_type: str,
    options: list,
    correct_answer: str,
):
    """Validate a single question based on its type.

    Raises HTTPException on invalid input.
    """
    if question_type in ("mcq", "truefalse"):
        if len(options) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Question '{question_id}' needs at least 2 options",
            )
        if correct_answer not in options:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Correct answer for question "
                    f"'{question_id}' must be one of its options"
                ),
            )
    elif question_type == "short":
        if not correct_answer or not correct_answer.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Short-answer question '{question_id}' "
                    f"needs a correct answer"
                ),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid question_type '{question_type}' "
                f"for question '{question_id}'"
            ),
        )


def is_answer_correct(question, submitted_answer):
    """Compare a submitted answer to the correct one.

    Short-answer questions are matched case-insensitively (trimmed).
    Multiple-choice / True-False require an exact match.
    """
    if submitted_answer is None:
        return False

    if question.question_type == "short":
        return (
            submitted_answer.strip().lower()
            == question.correct_answer.strip().lower()
        )

    return submitted_answer == question.correct_answer


def quiz_public_response(quiz: Quiz, include_questions=True):
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
        "question_count": len(quiz.questions),
        "questions": [
            {
                "id": question.id,
                "question": question.question,
                "question_type": question.question_type,
                "options": question.options,
            }
            for question in quiz.questions
        ] if include_questions else [],
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
        validate_question(
            question.id,
            question.question_type,
            question.options,
            question.correct_answer,
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
        if (await db.quiz_exam_sessions.count_documents({"quiz_id": quiz_id}, limit=1)
                or await db.quiz_attempts.count_documents({"quiz_id": quiz_id}, limit=1)):
            raise HTTPException(409, "Cannot change questions after an exam session or attempt exists")
        for question in update_data["questions"]:
            validate_question(
                question["id"],
                question.get("question_type", "mcq"),
                question.get("options", []),
                question["correct_answer"],
            )
    if "max_attempts" in update_data and update_data["max_attempts"] != existing.get("max_attempts"):
        if (await db.quiz_exam_sessions.count_documents({"quiz_id": quiz_id}, limit=1)
                or await db.quiz_attempts.count_documents({"quiz_id": quiz_id}, limit=1)):
            raise HTTPException(409, "Cannot change max attempts after exam sessions exist")
        setting_doc = await db.quiz_exam_settings.find_one({"_id": quiz_id})
        if setting_doc and setting_doc.get("exclude_previous_questions"):
            current_count = setting_doc.get("questions_per_attempt") or len(existing.get("questions", []))
            if current_count * update_data["max_attempts"] > len(existing.get("questions", [])):
                raise HTTPException(400, "Not enough questions for non-repeating attempts")
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
    await db.quiz_exam_sessions.delete_many({"quiz_id": quiz_id})
    await db.quiz_exam_settings.delete_one({"_id": quiz_id})
    return {
        "message": "Quiz deleted successfully"
    }


# ============================================================
# RANDOM EXAM CONFIGURATION AND SESSION HELPERS
# Settings are stored separately to keep models/quiz.py unchanged.
# Sessions are persisted server-side; refreshes do not redraw questions.
# ============================================================

class ExamSettings(BaseModel):
    questions_per_attempt: int = Field(default=0, ge=0, le=500)
    randomize_questions: bool = False
    shuffle_options: bool = False
    exclude_previous_questions: bool = False


def default_settings(quiz):
    return ExamSettings(questions_per_attempt=len(quiz.questions)).model_dump()


async def load_exam_settings(quiz):
    config = await db.quiz_exam_settings.find_one({"_id": quiz.id})
    return ExamSettings.model_validate(config or default_settings(quiz))


def exam_count(quiz, settings):
    return settings.questions_per_attempt or len(quiz.questions)


async def assigned_exam(quiz, user):
    """Create or recover this user's one active session for the next attempt."""
    attempts_used = await db.quiz_attempts.count_documents({
        "quiz_id": quiz.id, "user_id": user.id
    })
    if attempts_used >= quiz.max_attempts:
        raise HTTPException(403, "You have reached the maximum number of attempts")

    settings = await load_exam_settings(quiz)
    count = exam_count(quiz, settings)
    if count < 1 or count > len(quiz.questions):
        raise HTTPException(409, "Question bank is smaller than the exam size")

    # Deterministic key means concurrent GET requests converge on one session.
    session_id = f"{quiz.id}:{user.id}:{attempts_used + 1}"
    session = await db.quiz_exam_sessions.find_one({"_id": session_id})
    if session is None:
        previous_ids = set()
        if settings.exclude_previous_questions:
            previous = await db.quiz_exam_sessions.find({
                "quiz_id": quiz.id, "user_id": user.id,
                "state": "submitted",
            }).to_list(length=None)
            for old in previous:
                previous_ids.update(old.get("question_ids", []))
            # Also respect prior attempts recorded with selected question IDs.
            legacy = await db.quiz_attempts.find({
                "quiz_id": quiz.id, "user_id": user.id,
            }).to_list(length=None)
            for old in legacy:
                previous_ids.update(old.get("question_ids", []))

        pool = [q for q in quiz.questions if q.id not in previous_ids]
        if len(pool) < count:
            raise HTTPException(
                409, "Not enough unseen questions for another attempt. "
                     "Add more questions or change the exam settings."
            )
        sampled = (
            secrets.SystemRandom().sample(pool, count)
            if settings.randomize_questions else pool[:count]
        )
        option_orders = {}
        if settings.shuffle_options:
            for q in sampled:
                if q.question_type in ("mcq", "truefalse"):
                    option_orders[q.id] = secrets.SystemRandom().sample(
                        list(q.options), len(q.options)
                    )
        proposed = {
            "_id": session_id, "quiz_id": quiz.id, "user_id": user.id,
            "attempt_number": attempts_used + 1,
            "state": "active", "question_ids": [q.id for q in sampled],
            "option_orders": option_orders, "created_at": now_utc(),
        }
        # Atomic upsert; identical _id guarantees one authoritative selection.
        try:
            await db.quiz_exam_sessions.update_one(
                {"_id": session_id}, {"$setOnInsert": proposed}, upsert=True
            )
        except DuplicateKeyError:
            # Another simultaneous request inserted the authoritative session.
            pass
        session = await db.quiz_exam_sessions.find_one({"_id": session_id})

    if session["state"] != "active":
        raise HTTPException(409, "This attempt is already being submitted")
    selected_map = {q.id: q for q in quiz.questions}
    if any(qid not in selected_map for qid in session["question_ids"]):
        raise HTTPException(409, "Exam bank changed after attempt started")

    response = quiz_public_response(quiz, include_questions=False)
    response["questions"] = [
        {
            "id": selected_map[qid].id,
            "question": selected_map[qid].question,
            "question_type": selected_map[qid].question_type,
            "options": session.get("option_orders", {}).get(
                qid, selected_map[qid].options
            ),
        }
        for qid in session["question_ids"]
    ]
    response["attempts_used"] = attempts_used
    response["attempts_remaining"] = max(quiz.max_attempts - attempts_used, 0)
    response["session_id"] = session_id
    return response


@router.get("/admin/{quiz_id}/exam-settings")
async def get_exam_settings(quiz_id: str, admin: User = Depends(require_admin)):
    doc = await db.quizzes.find_one({"_id": quiz_id})
    if not doc:
        raise HTTPException(404, "Quiz not found")
    quiz = Quiz.from_mongo(doc)
    return (await load_exam_settings(quiz)).model_dump()


@router.put("/admin/{quiz_id}/exam-settings")
async def save_exam_settings(
    quiz_id: str, payload: ExamSettings,
    admin: User = Depends(require_admin),
):
    doc = await db.quizzes.find_one({"_id": quiz_id})
    if not doc:
        raise HTTPException(404, "Quiz not found")
    quiz = Quiz.from_mongo(doc)
    count = exam_count(quiz, payload)
    if count < 1 or count > len(quiz.questions):
        raise HTTPException(400, "Questions per attempt must be between 1 and bank size")
    if payload.exclude_previous_questions and count * quiz.max_attempts > len(quiz.questions):
        raise HTTPException(
            400, f"For {quiz.max_attempts} non-overlapping attempts of {count} "
                 f"questions, import at least {count * quiz.max_attempts} questions."
        )
    # Prevent a new configuration from changing already assigned exams.
    if await db.quiz_exam_sessions.count_documents({"quiz_id": quiz_id}, limit=1):
        raise HTTPException(409, "Exam sessions already exist. Create a new quiz to change these settings.")
    if await db.quiz_attempts.count_documents({"quiz_id": quiz_id}, limit=1):
        raise HTTPException(409, "Student attempts already exist. Create a new quiz to change these settings.")
    settings = payload.model_dump()
    await db.quiz_exam_settings.update_one(
        {"_id": quiz_id}, {"$set": settings}, upsert=True
    )
    return settings


# ============================================================
# STUDENT: GET ALL QUIZZES FOR A COURSE
# ============================================================
@router.get("/course/{course_id}")
async def get_course_quizzes(
    course_id: str,
    user: User = Depends(get_current_user),
):
    """
    Return all published quizzes belonging to a course.
    Correct answers are never returned.
    """

    # Check that the student is enrolled
    enrollment = await get_enrollment(
        user.id,
        course_id,
    )

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not enrolled in this course",
        )

    # Check enrollment approval
    payment_status = enrollment.get("payment_status")

    if payment_status and payment_status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your enrollment has not been approved",
        )

    # Get all published quizzes for this course
    quiz_docs = await db.quizzes.find(
        {
            "course_id": course_id,
            "is_published": True,
        }
    ).sort(
        "created_at",
        1,
    ).to_list(length=None)

    return [
        quiz_public_response(
            Quiz.from_mongo(doc), include_questions=False
        )
        for doc in quiz_docs
    ]


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
    return await assigned_exam(quiz, user)


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
    return await assigned_exam(quiz, user)

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
    # A GET of the exam creates the persistent assigned question set.
    # If the student posts without GET, reject instead of silently sampling.
    attempts_count = await db.quiz_attempts.count_documents({
        "quiz_id": quiz.id, "user_id": user.id,
    })
    if attempts_count >= quiz.max_attempts:
        raise HTTPException(403, "Maximum quiz attempts reached")
    session_id = f"{quiz.id}:{user.id}:{attempts_count + 1}"
    session = await db.quiz_exam_sessions.find_one({"_id": session_id})
    if not session or session.get("state") != "active":
        raise HTTPException(409, "Open the exam first; no active attempt found")

    selected_ids = session["question_ids"]
    question_map = {q.id: q for q in quiz.questions}
    if any(qid not in question_map for qid in selected_ids):
        raise HTTPException(409, "Exam question bank changed")
    if any(qid not in selected_ids for qid in payload.answers):
        raise HTTPException(400, "Answers contain questions not assigned to this attempt")
    total_questions = len(selected_ids)
    if not total_questions:
        raise HTTPException(400, "Exam contains no assigned questions")

    correct_count = sum(
        is_answer_correct(question_map[qid], payload.answers.get(qid))
        for qid in selected_ids
    )
    score = round(correct_count / total_questions * 100, 2)
    passed = score >= quiz.passing_score

    # Acquire submission lock atomically; blocks simultaneous double submission.
    locked = await db.quiz_exam_sessions.find_one_and_update(
        {"_id": session_id, "state": "active"},
        {"$set": {"state": "submitting", "submitted_at": now_utc()}},
        return_document=ReturnDocument.AFTER,
    )
    if not locked:
        raise HTTPException(409, "This examination has already been submitted")

    attempt = QuizAttempt(
        id=str(uuid4()), quiz_id=quiz.id,
        course_id=quiz.course_id, lesson_id=quiz.lesson_id,
        user_id=user.id, answers=payload.answers, score=score, passed=passed,
    )
    attempt_doc = attempt.to_mongo()
    attempt_doc["question_ids"] = selected_ids
    attempt_doc["session_id"] = session_id
    try:
        await db.quiz_attempts.insert_one(attempt_doc)
    except Exception:
        await db.quiz_exam_sessions.update_one(
            {"_id": session_id, "state": "submitting"},
            {"$set": {"state": "active"}, "$unset": {"submitted_at": ""}},
        )
        raise
    await db.quiz_exam_sessions.update_one(
        {"_id": session_id}, {"$set": {"state": "submitted"}}
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
    # Activate alumni after successful final assessment
    if passed and quiz.quiz_type == "final":
        try:
            await activate_alumni(
                user_id=user.id,
                course_id=quiz.course_id
            )
        except Exception:
            logger.exception(
                "Alumni activation failed for user %s, course %s",
                user.id,
                quiz.course_id
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

# ============================================================
# ADMIN: IMPORT JSON QUESTIONS (for your existing import button)
# ============================================================
@router.post("/{quiz_id}/import-questions")
async def import_questions(
    quiz_id: str, questions: list[dict], admin: User = Depends(require_admin)
):
    existing = await db.quizzes.find_one({"_id": quiz_id})
    if not existing:
        raise HTTPException(404, "Quiz not found")
    if await db.quiz_exam_sessions.count_documents({"quiz_id": quiz_id}, limit=1):
        raise HTTPException(409, "Cannot import after an examination session has started")
    if await db.quiz_attempts.count_documents({"quiz_id": quiz_id}, limit=1):
        raise HTTPException(409, "Cannot import after student attempts exist")
    if not questions or len(questions) > 500:
        raise HTTPException(400, "Import 1 to 500 questions at a time")
    previous = existing.get("questions", [])
    seen_ids = {q["id"] for q in previous}
    seen_text = {q["question"].strip().casefold() for q in previous}
    for position, q in enumerate(questions, 1):
        if not isinstance(q, dict):
            raise HTTPException(400, f"Question {position} must be an object")
        question_id, question_text = q.get("id"), q.get("question")
        if not isinstance(question_id, str) or not question_id.strip():
            raise HTTPException(400, f"Question {position} requires an id")
        if not isinstance(question_text, str) or not question_text.strip():
            raise HTTPException(400, f"Question {position} requires text")
        key = question_text.strip().casefold()
        if question_id in seen_ids or key in seen_text:
            raise HTTPException(409, f"Duplicate question at position {position}")
        seen_ids.add(question_id)
        seen_text.add(key)
        validate_question(
            question_id, q.get("question_type", "mcq"),
            q.get("options", []), q.get("correct_answer", ""),
        )
    try:
        validated = QuizUpdate.model_validate({"questions": previous + questions})
        parsed = [q.model_dump() for q in validated.questions]
    except ValidationError as exc:
        raise HTTPException(422, "Imported questions do not match the Quiz model: " + str(exc)[:600])
    result = await db.quizzes.update_one(
        {"_id": quiz_id, "questions": previous},
        {"$set": {"questions": parsed, "updated_at": now_utc()}},
    )
    if not result.matched_count:
        raise HTTPException(409, "Quiz was changed during import; retry")
    return {"message": "Questions imported successfully", "imported": len(questions),
            "total_questions": len(parsed), "quiz_id": quiz_id}
