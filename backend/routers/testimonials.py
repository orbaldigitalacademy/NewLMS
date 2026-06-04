"""Testimonials router."""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth import get_current_user, require_admin
from database import db
from models.testimonial import Testimonial, TestimonialCreate, TestimonialUpdate
from models.user import User

router = APIRouter(prefix="/testimonials", tags=["testimonials"])


@router.get("", response_model=List[Testimonial])
async def list_testimonials(
    is_approved: Optional[bool] = Query(default=True),
    featured_only: bool = False,
):
    filt: dict = {}
    if is_approved is not None:
        filt["is_approved"] = is_approved
    if featured_only:
        filt["is_featured"] = True
    docs = await db.testimonials.find(filt).sort("created_at", -1).to_list(500)
    return [Testimonial.from_mongo(d) for d in docs]


@router.post("", response_model=Testimonial, status_code=201)
async def create_testimonial(
    data: TestimonialCreate, user: User = Depends(get_current_user)
):
    testimonial = Testimonial(
        user_id=user.id,
        name=data.name or user.name,
        role=data.role,
        avatar_url=data.avatar_url or user.avatar_url,
        quote=data.quote,
        rating=data.rating,
        course_id=data.course_id,
        is_approved=False,
    )
    await db.testimonials.insert_one(testimonial.to_mongo())
    return testimonial


@router.patch("/{testimonial_id}", response_model=Testimonial)
async def update_testimonial(
    testimonial_id: str, data: TestimonialUpdate, _: User = Depends(require_admin)
):
    doc = await db.testimonials.find_one({"_id": testimonial_id})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Testimonial not found")
    updates = data.model_dump(exclude_none=True)
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.testimonials.update_one({"_id": testimonial_id}, {"$set": updates})
    new_doc = await db.testimonials.find_one({"_id": testimonial_id})
    return Testimonial.from_mongo(new_doc)


@router.delete("/{testimonial_id}", status_code=204)
async def delete_testimonial(testimonial_id: str, _: User = Depends(require_admin)):
    await db.testimonials.delete_one({"_id": testimonial_id})
    return None
