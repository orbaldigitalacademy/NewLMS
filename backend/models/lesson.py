from typing import Optional, List
from pydantic import BaseModel, Field
from .base import BaseDocument


class LessonResource(BaseModel):
    name: str
    url: str
    type: str = "pdf"  # pdf, link, file


class Lesson(BaseDocument):
    course_id: str
    title: str
    description: Optional[str] = None
    order: int = 0
    content_text: Optional[str] = None  # rich text or markdown
    video_url: Optional[str] = None
    duration_minutes: int = 0
    resources: List[LessonResource] = Field(default_factory=list)
    is_preview: bool = False


class LessonCreate(BaseModel):
    course_id: str
    title: str
    description: Optional[str] = None
    order: int = 0
    content_text: Optional[str] = None
    video_url: Optional[str] = None
    duration_minutes: int = 0
    resources: List[LessonResource] = Field(default_factory=list)
    is_preview: bool = False


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    content_text: Optional[str] = None
    video_url: Optional[str] = None
    duration_minutes: Optional[int] = None
    resources: Optional[List[LessonResource]] = None
    is_preview: Optional[bool] = None
