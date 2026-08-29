"""Enrollment model - joins user <-> course."""

from typing import List, Optional

from pydantic import BaseModel, Field

from .base import BaseDocument


class Enrollment(BaseDocument):
    user_id: str
    course_id: str

    # Course details
    course_title: str = ""
    course_image: Optional[str] = None

    # Payment & access
    payment_status: str = "approved"
    access_granted: bool = True

    # Learning progress
    progress: float = 0.0
    completed_lessons: List[str] = Field(default_factory=list)
    is_completed: bool = False
    completed_at: Optional[str] = None

    # Assessment progress
    completed_quizzes: List[str] = Field(default_factory=list)
    
    # Final assessment
    final_quiz_id: Optional[str] = None
    final_quiz_score: Optional[float] = None
    
    # Final course completion
    course_completed: bool = False
    course_completed_at: Optional[str] = None
    

class AdminEnrollRequest(BaseModel):
    user_id: str
    course_id: str

