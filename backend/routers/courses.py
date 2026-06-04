"""Courses router."""
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth import get_current_user, get_optional_user, require_admin
from database import db
from models.course import Course, CourseCreate, CourseUpdate
from models.user import User

router = APIRouter(prefix="/courses", tags=["courses"])


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    return re.sub(r"[\s-]+", "-", s)[:80]


@router.get("", response_model=List[Course])
async def list_courses(
    category: Optional[str] = None,
    level: Optional[str] = None,
    q: Optional[str] = None,
    is_published: Optional[bool] = Query(default=True),
):
    filt: dict = {}
    if is_published is not None:
        filt["is_published"] = is_published
    if category:
        filt["category"] = category
    if level:
        filt["level"] = level
    if q:
        filt["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"short_description": {"$regex": q, "$options": "i"}},
            {"tags": {"$regex": q, "$options": "i"}},
        ]
    docs = await db.courses.find(filt).sort("created_at", -1).to_list(500)
    return [Course.from_mongo(d) for d in docs]


@router.get("/categories", response_model=List[str])
async def list_categories():
    cats = await db.courses.distinct("category", {"is_published": True})
    return sorted([c for c in cats if c])


@router.get("/{course_id}", response_model=Course)
async def get_course(course_id: str):
    doc = await db.courses.find_one({"_id": course_id})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
    return Course.from_mongo(doc)


@router.get("/slug/{slug}", response_model=Course)
async def get_course_by_slug(slug: str):
    doc = await db.courses.find_one({"slug": slug})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
    return Course.from_mongo(doc)


@router.post("", response_model=Course, status_code=201)
async def create_course(data: CourseCreate, admin: User = Depends(require_admin)):
    slug = slugify(data.title)
    existing = await db.courses.find_one({"slug": slug})
    if existing:
        slug = f"{slug}-{str(existing.get('_id', ''))[:6]}"

    course = Course(
        **data.model_dump(),
        slug=slug,
        instructor_id=admin.id,
        instructor_name=admin.name,
    )
    await db.courses.insert_one(course.to_mongo())
    return course


@router.patch("/{course_id}", response_model=Course)
async def update_course(
    course_id: str, data: CourseUpdate, _: User = Depends(require_admin)
):
    doc = await db.courses.find_one({"_id": course_id})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
    updates = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    from datetime import datetime, timezone

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.courses.update_one({"_id": course_id}, {"$set": updates})
    new_doc = await db.courses.find_one({"_id": course_id})
    return Course.from_mongo(new_doc)


@router.delete("/{course_id}", status_code=204)
async def delete_course(course_id: str, _: User = Depends(require_admin)):
    await db.lessons.delete_many({"course_id": course_id})
    await db.courses.delete_one({"_id": course_id})
    return None
