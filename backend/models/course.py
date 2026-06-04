from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from .base import BaseDocument


LevelType = Literal["beginner", "intermediate", "advanced"]


class Course(BaseDocument):
    title: str
    slug: str
    short_description: str
    description: str
    category: str
    level: LevelType = "beginner"
    price: float = 0.0  # in NGN; 0 = free
    currency: str = "NGN"
    thumbnail_url: Optional[str] = None
    instructor_id: str
    instructor_name: str
    tags: List[str] = Field(default_factory=list)
    duration_minutes: int = 0
    is_published: bool = False
    enrollment_count: int = 0


class CourseCreate(BaseModel):
    title: str
    short_description: str
    description: str
    category: str
    level: LevelType = "beginner"
    price: float = 0.0
    thumbnail_url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_published: bool = False


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    short_description: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    level: Optional[LevelType] = None
    price: Optional[float] = None
    thumbnail_url: Optional[str] = None
    tags: Optional[List[str]] = None
    is_published: Optional[bool] = None


class Enrollment(BaseDocument):
    user_id: str
    course_id: str
    progress: float = 0.0  # 0-100
    completed_lessons: List[str] = Field(default_factory=list)
    is_completed: bool = False
    completed_at: Optional[str] = None
    certificate_url: Optional[str] = None
