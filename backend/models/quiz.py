"""Quiz and assessment models."""
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


def utc_now():
    return datetime.now(timezone.utc)


class QuizQuestion(BaseModel):
    """A quiz question.

    question_type:
        mcq       -> multiple choice (2+ options, correct_answer in options)
        truefalse -> True / False (options = ["True", "False"])
        short     -> short text answer (no options; free-text compared to
                     correct_answer case-insensitively)
    """

    id: str
    question: str
    question_type: str = "mcq"
    # Empty for short-answer questions.
    options: List[str] = Field(default_factory=list)
    correct_answer: str


class QuizQuestionPublic(BaseModel):
    """Question representation returned to students.

    Notice that correct_answer is deliberately excluded.
    """

    id: str
    question: str
    question_type: str = "mcq"
    options: List[str] = Field(default_factory=list)


class QuizCreate(BaseModel):
    title: str
    description: Optional[str] = None
    # lesson = quiz attached to a lesson
    # final = course/final assessment
    quiz_type: str = "lesson"
    course_id: str
    lesson_id: Optional[str] = None
    questions: List[QuizQuestion]
    # Percentage required to pass
    passing_score: float = 70.0
    # Maximum number of attempts
    max_attempts: int = 3
    is_published: bool = True


class QuizUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    quiz_type: Optional[str] = None
    course_id: Optional[str] = None
    lesson_id: Optional[str] = None
    questions: Optional[List[QuizQuestion]] = None
    passing_score: Optional[float] = None
    max_attempts: Optional[int] = None
    is_published: Optional[bool] = None


class Quiz(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    quiz_type: str = "lesson"
    course_id: str
    lesson_id: Optional[str] = None
    questions: List[QuizQuestion]
    passing_score: float = 70.0
    max_attempts: int = 3
    is_published: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def to_mongo(self):
        return {
            "_id": self.id,
            "title": self.title,
            "description": self.description,
            "quiz_type": self.quiz_type,
            "course_id": self.course_id,
            "lesson_id": self.lesson_id,
            "questions": [
                question.model_dump()
                for question in self.questions
            ],
            "passing_score": self.passing_score,
            "max_attempts": self.max_attempts,
            "is_published": self.is_published,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_mongo(cls, doc):
        return cls(
            id=doc["_id"],
            title=doc["title"],
            description=doc.get("description"),
            quiz_type=doc.get("quiz_type", "lesson"),
            course_id=doc["course_id"],
            lesson_id=doc.get("lesson_id"),
            questions=[
                QuizQuestion(**question)
                for question in doc.get("questions", [])
            ],
            passing_score=doc.get("passing_score", 70.0),
            max_attempts=doc.get("max_attempts", 3),
            is_published=doc.get("is_published", True),
            created_at=doc.get("created_at", utc_now()),
            updated_at=doc.get("updated_at", utc_now()),
        )


class QuizSubmitRequest(BaseModel):
    answers: dict[str, str]


class QuizAttempt(BaseModel):
    id: str
    quiz_id: str
    course_id: str
    lesson_id: Optional[str] = None
    user_id: str
    answers: dict[str, str]
    score: float
    passed: bool
    submitted_at: datetime = Field(default_factory=utc_now)

    def to_mongo(self):
        return {
            "_id": self.id,
            "quiz_id": self.quiz_id,
            "course_id": self.course_id,
            "lesson_id": self.lesson_id,
            "user_id": self.user_id,
            "answers": self.answers,
            "score": self.score,
            "passed": self.passed,
            "submitted_at": self.submitted_at,
        }

    @classmethod
    def from_mongo(cls, doc):
        return cls(
            id=doc["_id"],
            quiz_id=doc["quiz_id"],
            course_id=doc["course_id"],
            lesson_id=doc.get("lesson_id"),
            user_id=doc["user_id"],
            answers=doc.get("answers", {}),
            score=doc["score"],
            passed=doc["passed"],
            submitted_at=doc.get("submitted_at", utc_now()),
        )
