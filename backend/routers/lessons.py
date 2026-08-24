"""Lessons router."""
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from auth import get_current_user, get_optional_user, require_admin
from services.cloudinary_service import delete_asset
from database import db
from models.lesson import Lesson, LessonCreate, LessonUpdate, ReorderItem
from models.user import User

router = APIRouter(prefix="/lessons", tags=["lessons"])


async def _is_enrolled(user: User | None, course_id: str) -> bool:
    if user is None:
        return False
    if user.role == "admin":
        return True
    return bool(await db.enrollments.find_one({"user_id": user.id, "course_id": course_id}))


@router.get("/by-course/{course_id}", response_model=List[Lesson])
async def lessons_for_course(course_id: str, user: User | None = Depends(get_optional_user)):
    docs = await db.lessons.find({"course_id": course_id}).sort("order", 1).to_list(500)
    lessons = [Lesson.from_mongo(d) for d in docs]

    enrolled = await _is_enrolled(user, course_id)
    if not enrolled:
        for lesson in lessons:
            if not lesson.is_preview:
                lesson.content_text = None
                lesson.video_url = None
                lesson.video_public_id = None
                lesson.resources = []
    return lessons


@router.get("/{lesson_id}", response_model=Lesson)
async def get_lesson(lesson_id: str, user: User = Depends(get_current_user)):
    doc = await db.lessons.find_one({"_id": lesson_id})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")
    lesson = Lesson.from_mongo(doc)
    if not lesson.is_preview and not await _is_enrolled(user, lesson.course_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Enroll in the course to view this lesson")
    return lesson


@router.post("", response_model=Lesson, status_code=201)
async def create_lesson(data: LessonCreate, _: User = Depends(require_admin)):
    if not await db.courses.find_one({"_id": data.course_id}):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
    lesson = Lesson(**data.model_dump())
    await db.lessons.insert_one(lesson.to_mongo())
    return lesson


@router.patch("/reorder", status_code=200)
async def reorder_lessons(items: List[ReorderItem], _: User = Depends(require_admin)):
    for item in items:
        await db.lessons.update_one(
            {"_id": item.id},
            {"$set": {"order": item.order, "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
    return {"updated": len(items)}


@router.patch("/{lesson_id}", response_model=Lesson)
async def update_lesson(lesson_id: str, data: LessonUpdate, _: User = Depends(require_admin)):
    doc = await db.lessons.find_one({"_id": lesson_id})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")

    updates = data.model_dump(exclude_none=True)

    # If the video is being replaced, clean up the old Cloudinary asset.
    old_public_id = doc.get("video_public_id")
    new_public_id = updates.get("video_public_id")
    if old_public_id and new_public_id and old_public_id != new_public_id:
        delete_asset(old_public_id, "video")

    if "resources" in updates:
        updates["resources"] = [
            r if isinstance(r, dict) else r.model_dump() for r in updates["resources"]
        ]
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    await db.lessons.update_one({"_id": lesson_id}, {"$set": updates})
    return Lesson.from_mongo(await db.lessons.find_one({"_id": lesson_id}))


@router.delete("/{lesson_id}", status_code=204)
async def delete_lesson(lesson_id: str, _: User = Depends(require_admin)):
    doc = await db.lessons.find_one({"_id": lesson_id})
    if doc and doc.get("video_public_id"):
        delete_asset(doc["video_public_id"], "video")
    await db.lessons.delete_one({"_id": lesson_id})
    return None
