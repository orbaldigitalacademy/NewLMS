"""Enrollment model - joins user <-> course."""
from typing import Optional

from pydantic import BaseModel

from .base import BaseDocument


class Enrollment(BaseDocument):
    user_id: str
    course_id: str
    progress: float = 0.0
    is_completed: bool = False
    completed_at: Optional[str] = None


class AdminEnrollRequest(BaseModel):
    user_id: str
    course_id: str
