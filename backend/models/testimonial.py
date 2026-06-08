"""Testimonial models."""

from typing import Optional
from pydantic import BaseModel, Field

from .base import BaseDocument


class Testimonial(BaseDocument):
    user_id: Optional[str] = None
    user_name: str
    avatar_url: Optional[str] = None
    content: str
    video_url: Optional[str] = None

    rating: int = Field(
        default=5,
        ge=1,
        le=5,
    )

    is_approved: bool = False
    is_featured: bool = False


class TestimonialCreate(BaseModel):
    content: str
    video_url: Optional[str] = None
    avatar_url: Optional[str] = None

    rating: int = Field(
        default=5,
        ge=1,
        le=5,
    )

class TestimonialUpdate(BaseModel):
    is_approved: Optional[bool] = None
    is_featured: Optional[bool] = None
