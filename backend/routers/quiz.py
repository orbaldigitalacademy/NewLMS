"""Quiz and assessment router."""
from datetime import datetime, timezone, timedelta
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
    if "questions" in update_data and (
        await db.quiz_exam_sessions.count_documents({"quiz_id": quiz_id}, limit=1)
        or await db.quiz_attempts.count_documents({"quiz_id": quiz_id}, limit=1)
    ):
        raise HTTPException(409, "Cannot modify questions after exam sessions exist")
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
    await db.quiz_question_topics.delete_one({"_id": quiz_id})
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
    duration_minutes: int = Field(default=120, ge=1, le=480)
    subject_counts: dict[str, int] = Field(default_factory=dict)


SUBJECTS = ("Excel", "Power BI", "Tableau", "SQL", "Python", "SPSS")


def utc_date(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def public_session_status(session):
    return {
        "session_id": session["_id"],
        "deadline_at": utc_date(session["deadline_at"]).isoformat(),
        "server_time": now_utc().isoformat(),
        "saved_answers": session.get("saved_answers", {}),
        "session_state": session["state"],
        "duration_minutes": session.get("duration_minutes", 120),
    }


def choose_questions(quiz, settings, previous_ids, topics):
    count = exam_count(quiz, settings)
    pool = [q for q in quiz.questions if q.id not in previous_ids]
    if len(pool) < count:
        raise HTTPException(409, "Not enough unseen questions for this attempt")
    randomizer = secrets.SystemRandom()
    counts = settings.subject_counts
    if not counts:
        return randomizer.sample(pool, count) if settings.randomize_questions else pool[:count]
    selected = []
    chosen = set()
    for subject in SUBJECTS:
        need = counts.get(subject, 0)
        eligible = [q for q in pool if topics.get(q.id) == subject]
        if len(eligible) < need:
            raise HTTPException(409, f"Not enough unseen {subject} questions: need {need}, have {len(eligible)}")
        drawn = randomizer.sample(eligible, need) if settings.randomize_questions else eligible[:need]
        selected.extend(drawn)
        chosen.update(q.id for q in drawn)
    if len(selected) != count:
        raise HTTPException(409, "Subject counts must sum to the exam size")
    if settings.randomize_questions:
        randomizer.shuffle(selected)
    return selected


async def finalize_session(quiz, user, session, *, timed_out=False, submitted_answers=None):
    """One authoritative grading path for manual and timed-out submissions."""
    sid = session["_id"]
    deadline = utc_date(session["deadline_at"])
    if not timed_out and now_utc() >= deadline:
        timed_out = True
    locked = await db.quiz_exam_sessions.find_one_and_update(
        {"_id": sid, "state": "active"},
        {"$set": {"state": "submitting", "submitted_at": now_utc()}},
        return_document=ReturnDocument.AFTER,
    )
    if not locked:
        existing = await db.quiz_attempts.find_one({"session_id": sid})
        if existing:
            return attempt_result(existing, quiz, already_submitted=True)
        raise HTTPException(409, "Exam submission is being processed; retry shortly")
    if now_utc() >= utc_date(locked["deadline_at"]):
        timed_out = True
    selected_ids = locked["question_ids"]
    qmap = {q.id: q for q in quiz.questions}
    if any(qid not in qmap for qid in selected_ids):
        await db.quiz_exam_sessions.update_one({"_id": sid, "state": "submitting"}, {"$set": {"state": "active"}})
        raise HTTPException(409, "Question bank changed after exam began")
    answers = dict(locked.get("saved_answers", {}))
    # Manual final submission may include a last un-saved change.
    # Once the timer expires, only previously saved answers count.
    if not timed_out and submitted_answers is not None:
        if any(qid not in selected_ids for qid in submitted_answers):
            await db.quiz_exam_sessions.update_one({"_id": sid, "state": "submitting"}, {"$set": {"state": "active"}})
            raise HTTPException(400, "Submitted answers contain unassigned questions")
        answers.update(submitted_answers)
    correct = sum(is_answer_correct(qmap[qid], answers.get(qid)) for qid in selected_ids)
    score = round(100 * correct / len(selected_ids), 2)
    passed = score >= quiz.passing_score
    attempt = QuizAttempt(
        id=sid, quiz_id=quiz.id, course_id=quiz.course_id,
        lesson_id=quiz.lesson_id, user_id=user.id, answers=answers,
        score=score, passed=passed,
    )
    doc = attempt.to_mongo()
    doc.update({"question_ids": selected_ids, "session_id": sid,
                "timed_out": timed_out, "correct_count": correct})
    try:
        await db.quiz_attempts.update_one({"session_id": sid}, {"$setOnInsert": doc}, upsert=True)
        await db.quiz_exam_sessions.update_one(
            {"_id": sid}, {"$set": {"state": "submitted", "saved_answers": answers, "timed_out": timed_out}}
        )
    except Exception:
        # A retry can recover if an insert succeeded before a later failure.
        if not await db.quiz_attempts.find_one({"session_id": sid}):
            await db.quiz_exam_sessions.update_one({"_id": sid, "state": "submitting"}, {"$set": {"state": "active"}})
        raise
    if passed and quiz.quiz_type == "lesson":
        await db.enrollments.update_one(
            {"user_id": user.id, "course_id": quiz.course_id},
            {"$addToSet": {"completed_quizzes": quiz.id}}
        )
    if passed and quiz.quiz_type == "final":
        await db.enrollments.update_one(
            {"user_id": user.id, "course_id": quiz.course_id},
            {"$set": {"course_completed": True, "course_completed_at": now_utc(),
                      "final_quiz_id": quiz.id, "final_quiz_score": score}}
        )
        try:
            await activate_alumni(user_id=user.id, course_id=quiz.course_id)
        except Exception:
            logger.exception("Alumni activation failed for %s", user.id)
    return attempt_result(doc, quiz)


def attempt_result(doc, quiz, already_submitted=False):
    return {
        "attempt_id": doc["_id"], "quiz_id": quiz.id, "score": doc["score"],
        "passed": doc["passed"], "passing_score": quiz.passing_score,
        "correct_answers": doc.get("correct_count"),
        "total_questions": len(doc.get("question_ids", [])),
        "timed_out": doc.get("timed_out", False),
        "already_submitted": already_submitted,
        "message": "You passed the examination" if doc["passed"] else "Examination not passed",
    }


class AnswerSave(BaseModel):
    session_id: str
    question_id: str
    answer: str


def default_settings(quiz):
    return ExamSettings(questions_per_attempt=len(quiz.questions)).model_dump()


async def load_exam_settings(quiz):
    config = await db.quiz_exam_settings.find_one({"_id": quiz.id})
    return ExamSettings.model_validate(config or default_settings(quiz))


def exam_count(quiz, settings):
    return settings.questions_per_attempt or len(quiz.questions)


async def assigned_exam(quiz, user):
    attempts_used = await db.quiz_attempts.count_documents({"quiz_id": quiz.id, "user_id": user.id})
    if attempts_used >= quiz.max_attempts:
        raise HTTPException(403, "Maximum quiz attempts reached")
    settings = await load_exam_settings(quiz)
    count = exam_count(quiz, settings)
    if count < 1 or count > len(quiz.questions):
        raise HTTPException(409, "Invalid exam size")
    session_id = f"{quiz.id}:{user.id}:{attempts_used + 1}"
    session = await db.quiz_exam_sessions.find_one({"_id": session_id})
    if session is None:
        previous = await db.quiz_attempts.find({"quiz_id": quiz.id, "user_id": user.id}).to_list(length=None)
        excluded = set()
        if settings.exclude_previous_questions:
            for old in previous:
                excluded.update(old.get("question_ids", []))
        topic_doc = await db.quiz_question_topics.find_one({"_id": quiz.id}) or {}
        sampled = choose_questions(quiz, settings, excluded, topic_doc.get("topics", {}))
        option_orders = {}
        if settings.shuffle_options:
            for q in sampled:
                if q.question_type in ("mcq", "truefalse"):
                    option_orders[q.id] = secrets.SystemRandom().sample(list(q.options), len(q.options))
        created = now_utc()
        proposed = {
            "_id": session_id, "quiz_id": quiz.id, "user_id": user.id,
            "attempt_number": attempts_used + 1, "state": "active",
            "question_ids": [q.id for q in sampled], "option_orders": option_orders,
            "saved_answers": {}, "created_at": created,
            "duration_minutes": settings.duration_minutes,
            "deadline_at": created + timedelta(minutes=settings.duration_minutes),
        }
        try:
            await db.quiz_exam_sessions.update_one(
                {"_id": session_id}, {"$setOnInsert": proposed}, upsert=True
            )
        except DuplicateKeyError:
            pass
        session = await db.quiz_exam_sessions.find_one({"_id": session_id})
    if session["state"] != "active":
        raise HTTPException(409, "This exam has already been submitted")
    if now_utc() >= utc_date(session["deadline_at"]):
        await finalize_session(quiz, user, session, timed_out=True)
        raise HTTPException(410, "Exam time expired; saved answers have been graded")
    selected_map = {q.id: q for q in quiz.questions}
    if any(qid not in selected_map for qid in session["question_ids"]):
        raise HTTPException(409, "Question bank changed after attempt began")
    response = quiz_public_response(quiz, include_questions=False)
    response["questions"] = [
        {"id": selected_map[qid].id,
         "question": selected_map[qid].question,
         "question_type": selected_map[qid].question_type,
         "options": session.get("option_orders", {}).get(qid, selected_map[qid].options)}
        for qid in session["question_ids"]
    ]
    response["attempts_used"] = attempts_used
    response["attempts_remaining"] = max(quiz.max_attempts - attempts_used, 0)
    response.update(public_session_status(session))
    return response


@router.get("/admin/{quiz_id}/exam-settings")
async def get_exam_settings(quiz_id: str, admin: User = Depends(require_admin)):
    doc = await db.quizzes.find_one({"_id": quiz_id})
    if not doc:
        raise HTTPException(404, "Quiz not found")
    quiz = Quiz.from_mongo(doc)
    settings = (await load_exam_settings(quiz)).model_dump()
    topic_doc = await db.quiz_question_topics.find_one({"_id": quiz_id}) or {}
    topics = topic_doc.get("topics", {})
    settings["subject_available"] = {
        subject: sum(1 for q in quiz.questions if topics.get(q.id) == subject)
        for subject in SUBJECTS
    }
    return settings


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
    if payload.subject_counts:
        if any(k not in SUBJECTS or not isinstance(v, int) or v < 0 for k, v in payload.subject_counts.items()):
            raise HTTPException(400, "Invalid subject allocation")
        if sum(payload.subject_counts.values()) != count:
            raise HTTPException(400, "Subject counts must sum to questions per attempt")
        topics_doc = await db.quiz_question_topics.find_one({"_id": quiz_id}) or {}
        topics = topics_doc.get("topics", {})
        for subject, needed in payload.subject_counts.items():
            available = sum(1 for q in quiz.questions if topics.get(q.id) == subject)
            required = needed * (quiz.max_attempts if payload.exclude_previous_questions else 1)
            if available < required:
                raise HTTPException(400, f"{subject}: need {required} bank questions, have {available}")
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
@router.put("/{quiz_id}/answers")
async def save_exam_answer(
    quiz_id: str, payload: AnswerSave, user: User = Depends(get_current_user),
):
    quiz_doc = await db.quizzes.find_one({"_id": quiz_id, "is_published": True})
    if not quiz_doc:
        raise HTTPException(404, "Quiz not found")
    quiz = Quiz.from_mongo(quiz_doc)
    await check_quiz_access(quiz, user)
    session = await db.quiz_exam_sessions.find_one({"_id": payload.session_id, "quiz_id": quiz_id, "user_id": user.id})
    if not session or session["state"] != "active":
        raise HTTPException(409, "No active exam session")
    if now_utc() >= utc_date(session["deadline_at"]):
        await finalize_session(quiz, user, session, timed_out=True)
        raise HTTPException(410, "Exam time expired; saved answers were graded")
    if payload.question_id not in session["question_ids"]:
        raise HTTPException(400, "Question is not assigned to this attempt")
    if len(payload.answer) > 10000:
        raise HTTPException(400, "Answer is too long")
    # Validate exact text for MCQs, and disallow MongoDB unsafe field keys.
    if not payload.question_id.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(400, "Unsafe question ID; use alphanumeric IDs, hyphens or underscores")
    q = next((q for q in quiz.questions if q.id == payload.question_id), None)
    if not q:
        raise HTTPException(409, "Question bank changed")
    if q.question_type in ("mcq", "truefalse") and payload.answer not in q.options and payload.answer != "":
        raise HTTPException(400, "Answer must be one of the available options")
    result = await db.quiz_exam_sessions.update_one(
        {"_id": payload.session_id, "state": "active", "deadline_at": {"$gt": now_utc()}},
        {"$set": {f"saved_answers.{payload.question_id}": payload.answer, "last_saved_at": now_utc()}},
    )
    if not result.matched_count:
        raise HTTPException(409, "Exam ended before answer could be saved")
    return {"saved": True, "question_id": payload.question_id, "server_time": now_utc().isoformat()}


@router.post("/{quiz_id}/submit")
async def submit_quiz(
    quiz_id: str, payload: QuizSubmitRequest,
    user: User = Depends(get_current_user),
):
    quiz_doc = await db.quizzes.find_one({"_id": quiz_id, "is_published": True})
    if not quiz_doc:
        raise HTTPException(404, "Quiz not found")
    quiz = Quiz.from_mongo(quiz_doc)
    await check_quiz_access(quiz, user)
    attempts = await db.quiz_attempts.count_documents({"quiz_id": quiz.id, "user_id": user.id})
    sid = f"{quiz.id}:{user.id}:{attempts + 1}"
    session = await db.quiz_exam_sessions.find_one({"_id": sid})
    if not session:
        # An already completed submission may be retried by the browser.
        latest = await db.quiz_exam_sessions.find_one(
            {"quiz_id": quiz.id, "user_id": user.id, "state": "submitted"},
            sort=[("attempt_number", -1)],
        )
        if latest:
            existing = await db.quiz_attempts.find_one({"session_id": latest["_id"]})
            if existing:
                return attempt_result(existing, quiz, already_submitted=True)
        raise HTTPException(409, "Start the examination first")
    return await finalize_session(
        quiz, user, session, submitted_answers=payload.answers,
        timed_out=now_utc() >= utc_date(session["deadline_at"]),
    )


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
            "timed_out": attempt.get("timed_out", False),
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
            "timed_out": attempt.get("timed_out", False),
            "submitted_at": attempt["submitted_at"],
        }
        for attempt in attempts
    ]

# ============================================================
# ADMIN: IMPORT JSON QUESTIONS (for your existing import button)
# ============================================================
@router.post("/admin/{quiz_id}/tag-data-analytics-200")
async def tag_existing_data_analytics_200(
    quiz_id: str, admin: User = Depends(require_admin),
):
    """One-time category backfill for the previously provided DA001-DA200 bank."""
    doc = await db.quizzes.find_one({"_id": quiz_id})
    if not doc:
        raise HTTPException(404, "Quiz not found")
    if (await db.quiz_exam_sessions.count_documents({"quiz_id": quiz_id}, limit=1)
            or await db.quiz_attempts.count_documents({"quiz_id": quiz_id}, limit=1)):
        raise HTTPException(409, "Cannot tag questions after attempts start")
    ids = {q["id"] for q in doc.get("questions", [])}
    expected = {f"DA{i:03}" for i in range(1, 201)}
    if not expected.issubset(ids):
        raise HTTPException(400, "Expected all DA001 through DA200 IDs in this quiz")
    def subject_for(n):
        if n <= 40: return "Excel"
        if n <= 75: return "Power BI"
        if n <= 105: return "Tableau"
        if n <= 145: return "SQL"
        if n <= 175: return "Python"
        return "SPSS"
    topics = {f"DA{i:03}": subject_for(i) for i in range(1,201)}
    await db.quiz_question_topics.update_one(
        {"_id": quiz_id}, {"$set": {"topics": topics}}, upsert=True
    )
    return {"tagged": 200, "subject_available": {
        sub: sum(v == sub for v in topics.values()) for sub in SUBJECTS
    }}


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
    topics_to_add = {}
    clean_questions = []
    for q in questions:
        subject = q.get("subject")
        if subject is not None:
            if subject not in SUBJECTS:
                raise HTTPException(400, f"Unsupported subject: {subject}")
            topics_to_add[q["id"]] = subject
        clean_questions.append({k: v for k, v in q.items() if k != "subject"})
    try:
        validated = QuizUpdate.model_validate({"questions": previous + clean_questions})
        parsed = [q.model_dump() for q in validated.questions]
    except ValidationError as exc:
        raise HTTPException(422, "Imported questions do not match the Quiz model: " + str(exc)[:600])
    result = await db.quizzes.update_one(
        {"_id": quiz_id, "questions": previous},
        {"$set": {"questions": parsed, "updated_at": now_utc()}},
    )
    if not result.matched_count:
        raise HTTPException(409, "Quiz was changed during import; retry")
    if topics_to_add:
        await db.quiz_question_topics.update_one(
            {"_id": quiz_id}, {"$set": {f"topics.{qid}": subject for qid, subject in topics_to_add.items()}}, upsert=True
        )
    return {"message": "Questions imported successfully", "imported": len(questions),
            "total_questions": len(parsed), "quiz_id": quiz_id}
