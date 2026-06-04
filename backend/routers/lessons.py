"""Lessons router."""
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from auth import get_current_user, get_optional_user, require_admin
from database import db
from models.lesson import Lesson, LessonCreate, LessonUpdate
from models.user import User

router = APIRouter(prefix="/lessons", tags=["lessons"])


@router.get("/by-course/{course_id}", response_model=List[Lesson])
async def lessons_for_course(
    course_id: str, user: User | None = Depends(get_optional_user)
):
    docs = await db.lessons.find({"course_id": course_id}).sort("order", 1).to_list(500)
    lessons = [Lesson.from_mongo(d) for d in docs]
    # If not enrolled, hide non-preview content
    if user is None:
        is_enrolled = False
    else:
        is_enrolled = (
            user.role == "admin"
            or bool(
                await db.enrollments.find_one(
                    {"user_id": user.id, "course_id": course_id}
                )
            )
        )
    if not is_enrolled:
        for l in lessons:
            if not l.is_preview:
                l.content_text = None
                l.video_url = None
                l.resources = []
    return lessons


@router.get("/{lesson_id}", response_model=Lesson)
async def get_lesson(lesson_id: str, user: User = Depends(get_current_user)):
    doc = await db.lessons.find_one({"_id": lesson_id})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")
    lesson = Lesson.from_mongo(doc)
    is_enrolled = user.role == "admin" or bool(
        await db.enrollments.find_one(
            {"user_id": user.id, "course_id": lesson.course_id}
        )
    )
    if not is_enrolled and not lesson.is_preview:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Enroll in the course to view")
    return lesson


@router.post("", response_model=Lesson, status_code=201)
async def create_lesson(data: LessonCreate, _: User = Depends(require_admin)):
    course = await db.courses.find_one({"_id": data.course_id})
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
    lesson = Lesson(**data.model_dump())
    await db.lessons.insert_one(lesson.to_mongo())
    return lesson


@router.patch("/{lesson_id}", response_model=Lesson)
async def update_lesson(
    lesson_id: str, data: LessonUpdate, _: User = Depends(require_admin)
):
    doc = await db.lessons.find_one({"_id": lesson_id})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")
    updates = data.model_dump(exclude_none=True)
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    if "resources" in updates:
        updates["resources"] = [r if isinstance(r, dict) else r.model_dump() for r in updates["resources"]]
    await db.lessons.update_one({"_id": lesson_id}, {"$set": updates})
    new_doc = await db.lessons.find_one({"_id": lesson_id})
    return Lesson.from_mongo(new_doc)


@router.delete("/{lesson_id}", status_code=204)
async def delete_lesson(lesson_id: str, _: User = Depends(require_admin)):
    await db.lessons.delete_one({"_id": lesson_id})
    return None
