"""Enrollments router: enroll in free course, view enrollments, progress, certificate."""
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from auth import get_current_user
from database import db
from models.course import Course, Enrollment
from models.user import User
from services.certificate_service import generate_certificate_pdf

router = APIRouter(prefix="/enrollments", tags=["enrollments"])


class EnrollRequest(BaseModel):
    course_id: str


class ProgressRequest(BaseModel):
    lesson_id: str


async def _create_enrollment(user: User, course: Course) -> Enrollment:
    existing = await db.enrollments.find_one(
        {"user_id": user.id, "course_id": course.id}
    )
    if existing:
        return Enrollment.from_mongo(existing)
    enroll = Enrollment(user_id=user.id, course_id=course.id)
    await db.enrollments.insert_one(enroll.to_mongo())
    await db.courses.update_one(
        {"_id": course.id}, {"$inc": {"enrollment_count": 1}}
    )
    return enroll


@router.post("/free", response_model=Enrollment)
async def enroll_free(data: EnrollRequest, user: User = Depends(get_current_user)):
    doc = await db.courses.find_one({"_id": data.course_id})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
    course = Course.from_mongo(doc)
    if course.price > 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Paid course - use payment flow"
        )
    return await _create_enrollment(user, course)


@router.get("/me", response_model=List[Enrollment])
async def my_enrollments(user: User = Depends(get_current_user)):
    docs = await db.enrollments.find({"user_id": user.id}).sort("created_at", -1).to_list(500)
    return [Enrollment.from_mongo(d) for d in docs]


@router.get("/check/{course_id}")
async def is_enrolled(course_id: str, user: User = Depends(get_current_user)):
    doc = await db.enrollments.find_one(
        {"user_id": user.id, "course_id": course_id}
    )
    return {"enrolled": bool(doc), "enrollment": Enrollment.from_mongo(doc) if doc else None}


@router.post("/progress", response_model=Enrollment)
async def update_progress(
    data: ProgressRequest, user: User = Depends(get_current_user)
):
    lesson = await db.lessons.find_one({"_id": data.lesson_id})
    if not lesson:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")

    course_id = lesson["course_id"]
    enrollment_doc = await db.enrollments.find_one(
        {"user_id": user.id, "course_id": course_id}
    )
    if not enrollment_doc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not enrolled")
    enrollment = Enrollment.from_mongo(enrollment_doc)
    if data.lesson_id not in enrollment.completed_lessons:
        enrollment.completed_lessons.append(data.lesson_id)

    total_lessons = await db.lessons.count_documents({"course_id": course_id})
    progress = (
        (len(enrollment.completed_lessons) / total_lessons) * 100
        if total_lessons
        else 0
    )
    is_completed = total_lessons > 0 and len(enrollment.completed_lessons) >= total_lessons

    update = {
        "completed_lessons": enrollment.completed_lessons,
        "progress": round(progress, 2),
        "is_completed": is_completed,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if is_completed and not enrollment.is_completed:
        update["completed_at"] = datetime.now(timezone.utc).isoformat()

    await db.enrollments.update_one(
        {"_id": enrollment.id}, {"$set": update}
    )
    new_doc = await db.enrollments.find_one({"_id": enrollment.id})
    return Enrollment.from_mongo(new_doc)


@router.get("/certificate/{course_id}")
async def download_certificate(course_id: str, user: User = Depends(get_current_user)):
    enrollment_doc = await db.enrollments.find_one(
        {"user_id": user.id, "course_id": course_id}
    )
    if not enrollment_doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Enrollment not found")
    enrollment = Enrollment.from_mongo(enrollment_doc)
    if not enrollment.is_completed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Course not yet completed")

    course_doc = await db.courses.find_one({"_id": course_id})
    course = Course.from_mongo(course_doc)
    pdf_bytes = generate_certificate_pdf(
        student_name=user.name,
        course_title=course.title,
        completion_date=enrollment.completed_at,
    )
    filename = f"certificate-{course.slug}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
