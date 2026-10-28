"""Enrollments router: enroll in free course, view enrollments, progress, certificate."""
from datetime import datetime, timezone
from typing import List
from uuid import uuid4
from pymongo import ReturnDocument

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from auth import get_current_user
from database import db
from models.course import Course
from models.enrollment import Enrollment
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

    # Check whether the student is already enrolled
    existing = await db.enrollments.find_one({
        "user_id": user.id,
        "course_id": course.id
    })

    # -----------------------------------------
    # EXISTING ENROLLMENT
    # -----------------------------------------
    if existing:

        await db.enrollments.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "payment_status": "approved",
                    "access_granted": True,
                }
            }
        )

        # Preserve existing enrollment date
        # Initialize it only if missing
        if "enrollment_date" not in existing:
            await db.enrollments.update_one(
                {
                    "_id": existing["_id"],
                    "enrollment_date": {"$exists": False}
                },
                {
                    "$set": {
                        "enrollment_date": (
                            existing.get("created_at")
                            or datetime.now(timezone.utc)
                        )
                    }
                }
            )

        updated = await db.enrollments.find_one({
            "_id": existing["_id"]
        })

        return Enrollment.from_mongo(updated)

    # -----------------------------------------
    # NEW ENROLLMENT
    # -----------------------------------------

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

    enrollment_data = enroll.to_mongo()

    # Store enrollment date permanently
    enrollment_data["enrollment_date"] = datetime.now(timezone.utc)

    await db.enrollments.insert_one(enrollment_data)

    # Update course enrollment count
    await db.courses.update_one(
        {"_id": course.id},
        {
            "$inc": {
                "enrollment_count": 1
            }
        }
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
async def download_certificate(
    course_id: str,
    user: User = Depends(get_current_user)
):
    # 1. Verify student enrollment
    enrollment_doc = await db.enrollments.find_one({
        "user_id": user.id,
        "course_id": course_id
    })

    if not enrollment_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found"
        )

    enrollment = Enrollment.from_mongo(enrollment_doc)

    # 2. Verify required course lessons are completed
    if not enrollment.is_completed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Complete all required lessons before downloading your certificate."
        )

    # 3. Find the published final assessment
    final_quiz_doc = await db.quizzes.find_one({
        "course_id": course_id,
        "quiz_type": "final",
        "is_published": True
    })

    if not final_quiz_doc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Final Assessment has not been published."
        )

    # 4. Verify the student passed the final assessment
    passed_attempt = await db.quiz_attempts.find_one({
        "user_id": user.id,
        "course_id": course_id,
        "quiz_id": final_quiz_doc["_id"],
        "passed": True
    })

    if not passed_attempt:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must pass the Final Assessment before downloading your certificate."
        )

    # 5. Retrieve course information
    course_doc = await db.courses.find_one({
        "_id": course_id
    })

    if not course_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    course = Course.from_mongo(course_doc)

    # 6. Create or retrieve certificate record
    certificate_id = f"ODA-{uuid4().hex[:16].upper()}"

    certificate = await db.certificates.find_one_and_update(
        {
            "student_id": user.id,
            "course_id": course_id
        },
        {
            "$setOnInsert": {
                "certificate_id": certificate_id,
                "student_id": user.id,
                "student_name": user.name,
                "course_id": course_id,
                "course_title": course.title,
                "issued_at": datetime.now(timezone.utc),
                "status": "valid",
            }
        },
        upsert=True,
        return_document=ReturnDocument.AFTER
    )

    # 7. Generate verification URL
    verification_url = (
        f"https://www.orbalacademy.com/verify/"
        f"{certificate['certificate_id']}"
    )
    # Retrieve the actual enrollment date
    enrollment_date = (
        enrollment_doc.get("enrollment_date")
        or enrollment_doc.get("created_at")
    )

    # Retrieve the certificate award date
    award_date = certificate.get("issued_at")
    
    print("ENROLLMENT DATE:", enrollment_date)
    print("AWARD DATE:", award_date)

    # 8. Generate PDF
    pdf_bytes = generate_certificate_pdf(
        student_name=user.name,
        course_title=course.title,
        completion_date=award_date,
        certificate_id=certificate["certificate_id"],
        verification_url=verification_url,
        enrollment_date=enrollment_date,
    )

    # Verify PDF was generated correctly
    if not isinstance(pdf_bytes, bytes):
        raise HTTPException(
            status_code=500,
            detail="Certificate generator did not return PDF bytes."
        )

    if not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=500,
            detail="Certificate generator returned invalid PDF data."
        )

    filename = f"certificate-{course.slug}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
    
async def create_certificate_indexes():
    await db.certificates.create_index(
        "certificate_id",
        unique=True
    )

    await db.certificates.create_index(
        [
            ("student_id", 1),
            ("course_id", 1)
        ],
        unique=True
    ) 

@router.get("/certificate-eligibility/{course_id}")
async def certificate_eligibility(
    course_id: str,
    user: User = Depends(get_current_user)
):
    enrollment_doc = await db.enrollments.find_one({
        "user_id": user.id,
        "course_id": course_id
    })

    if not enrollment_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found"
        )

    enrollment = Enrollment.from_mongo(enrollment_doc)

    final_quiz_doc = await db.quizzes.find_one({
        "course_id": course_id,
        "quiz_type": "final",
        "is_published": True
    })

    final_passed = False

    if final_quiz_doc:
        passed_attempt = await db.quiz_attempts.find_one({
            "user_id": user.id,
            "course_id": course_id,
            "quiz_id": final_quiz_doc["_id"],
            "passed": True
        })

        final_passed = passed_attempt is not None

    eligible = bool(
        enrollment.is_completed and final_passed
    )

    return {
        "course_id": course_id,
        "lessons_completed": bool(enrollment.is_completed),
        "final_assessment_published": final_quiz_doc is not None,
        "final_assessment_passed": final_passed,
        "certificate_eligible": eligible
    }
# ============================================================
# PUBLIC CERTIFICATE VERIFICATION
# ============================================================

@router.get("/certificates/verify/{certificate_id}")
async def verify_certificate(certificate_id: str):

    # 1. Find certificate by its unique ID
    certificate = await db.certificates.find_one({
        "certificate_id": certificate_id
    })

    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found"
        )

    # 2. Check certificate status
    certificate_status = certificate.get("status", "unknown")

    if certificate_status != "valid":
        return {
            "valid": False,
            "certificate_id": certificate_id,
            "status": certificate_status,
            "message": "This certificate is not currently valid."
        }

    # 3. Return public verification information
    issued_at = certificate.get("issued_at")

    return {
        "valid": True,
        "certificate_id": certificate["certificate_id"],
        "student_name": certificate.get("student_name"),
        "course_title": certificate.get("course_title"),
        "issued_at": (
            issued_at.isoformat()
            if isinstance(issued_at, datetime)
            else issued_at
        ),
        "status": certificate_status,
        "issued_by": "Orbal Digital Academy",
        "message": "Certificate successfully verified"
    }
