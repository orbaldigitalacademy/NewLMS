from typing import Optional
from pydantic import BaseModel, Field
from .base import BaseDocument


class Testimonial(BaseDocument):
    user_id: Optional[str] = None
    name: str
    role: Optional[str] = None
    avatar_url: Optional[str] = None
    quote: str
    rating: int = Field(default=5, ge=1, le=5)
    course_id: Optional[str] = None
    is_approved: bool = False
    is_featured: bool = False


class TestimonialCreate(BaseModel):
    name: str
    role: Optional[str] = None
    avatar_url: Optional[str] = None
    quote: str
    rating: int = 5
    course_id: Optional[str] = None


class TestimonialUpdate(BaseModel):
    is_approved: Optional[bool] = None
    is_featured: Optional[bool] = None
