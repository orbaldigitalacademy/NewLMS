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
    completed: bool = True


class ProgressRequest(BaseModel):
    lesson_id: str
    completed: bool = False


async def _create_enrollment(user: User, course: Course) -> Enrollment:
    existing = await db.enrollments.find_one(
        {"user_id": user.id, "course_id": course.id}
    )

    # If already enrolled, make sure access is granted
    if existing:
        await db.enrollments.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "payment_status": "approved",
                    "access_granted": True,
                }
            },
        )

        updated = await db.enrollments.find_one({"_id": existing["_id"]})
        return Enrollment.from_mongo(updated)

    # Create a new enrollment
    enroll = Enrollment(
        user_id=user.id,
        course_id=course.id,
        course_title=course.title,
        course_image=getattr(course, "image_url", None),
        payment_status="approved",
        access_granted=True,
        completed_lessons=[],
        progress=0.0,
    )

    await db.enrollments.insert_one(enroll.to_mongo())

    await db.courses.update_one(
        {"_id": course.id},
        {"$inc": {"enrollment_count": 1}}
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

@router.get("/check-access/{course_id}")
async def check_course_access(
    course_id: str,
    user: User = Depends(get_current_user)
):
    enrollment_doc = await db.enrollments.find_one(
        {
            "user_id": user.id,
            "course_id": course_id
        }
    )

    if not enrollment_doc:
        return {
            "has_access": False,
            "enrolled": False,
            "enrollment": None
        }

    enrollment = Enrollment.from_mongo(enrollment_doc)

    return {
        "has_access": bool(enrollment.access_granted),
        "enrolled": True,
        "enrollment": enrollment
    }
    
@router.post("/progress", response_model=Enrollment)
async def update_progress(
    data: ProgressRequest,
    user: User = Depends(get_current_user)
):
    # Find the lesson
    lesson = await db.lessons.find_one({"_id": data.lesson_id})

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )

    course_id = lesson["course_id"]

    # Find student's enrollment for this course
    enrollment_doc = await db.enrollments.find_one(
        {
            "user_id": user.id,
            "course_id": course_id
        }
    )

    if not enrollment_doc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enrolled in this course"
        )

    # Make sure the student has access
    if not enrollment_doc.get("access_granted", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this course"
        )

    enrollment = Enrollment.from_mongo(enrollment_doc)

    # Mark/unmark lesson
    completed_lessons = list(enrollment.completed_lessons or [])

    if data.completed:
        if data.lesson_id not in completed_lessons:
            completed_lessons.append(data.lesson_id)
    else:
        if data.lesson_id in completed_lessons:
            completed_lessons.remove(data.lesson_id)

    # Calculate progress
    total_lessons = await db.lessons.count_documents(
        {"course_id": course_id}
    )

    progress = (
        (len(completed_lessons) / total_lessons) * 100
        if total_lessons > 0
        else 0
    )

    is_completed = (
        total_lessons > 0
        and len(completed_lessons) >= total_lessons
    )

    update = {
        "completed_lessons": completed_lessons,
        "progress": round(progress, 2),
        "is_completed": is_completed,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Course has just been completed
    if is_completed and not enrollment.is_completed:
        update["completed_at"] = datetime.now(timezone.utc).isoformat()

    # If course was previously completed but a lesson is unchecked,
    # reset the completion date.
    elif not is_completed and enrollment.is_completed:
        update["completed_at"] = None

    await db.enrollments.update_one(
        {"_id": enrollment.id},
        {"$set": update}
    )

    # Return updated enrollment
    new_doc = await db.enrollments.find_one(
        {"_id": enrollment.id}
    )

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
