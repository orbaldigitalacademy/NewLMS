"""Admin router - dashboard stats, user/payment/contact management.

Implements every `/admin/*` endpoint referenced in the frontend `api.js`.
"""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth import require_admin
from database import db
from models.course import Course
from models.enrollment import AdminEnrollRequest
from models.payment import Payment, PaymentReviewRequest
from models.testimonial import Testimonial
from models.user import (
    AdminCreateUser,
    User,
    UserPublic,
    UserRole,
)
from routers.enrollments import _create_enrollment
from utils.security import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_public(user: User) -> UserPublic:
    role = user.role.value if isinstance(user.role, UserRole) else user.role
    return UserPublic(
        id=user.id,
        email=user.email,
        name=user.name,
        role=role,
        avatar_url=user.avatar_url,
        bio=user.bio,
        blocked=user.blocked,
        created_at=user.created_at,
    )


# =====================================================================
# STATS
# =====================================================================
@router.get("/stats")
async def stats(_: User = Depends(require_admin)):
    users_count = await db.users.count_documents({})
    students = await db.users.count_documents({"role": UserRole.STUDENT.value})
    courses = await db.courses.count_documents({})
    published_courses = await db.courses.count_documents({"is_published": True})
    enrollments = await db.enrollments.count_documents({})
    completed = await db.enrollments.count_documents({"is_completed": True})
    payments_success = await db.payments.count_documents({"status": "success"})
    contacts_unread = await db.contacts.count_documents({"is_read": False})

    revenue = 0.0
    async for r in db.payments.aggregate(
        [
            {"$match": {"status": "success"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]
    ):
        revenue = r.get("total", 0) or 0

    return {
        "users": users_count,
        "students": students,
        "courses": courses,
        "published_courses": published_courses,
        "enrollments": enrollments,
        "completed_enrollments": completed,
        "successful_payments": payments_success,
        "revenue": revenue,
        "currency": "NGN",
        "contacts_unread": contacts_unread,
    }


# =====================================================================
# USERS
# =====================================================================
@router.get("/users", response_model=List[UserPublic])
async def list_users(_: User = Depends(require_admin)):
    docs = await db.users.find().sort("created_at", -1).to_list(1000)
    return [_to_public(User.from_mongo(d)) for d in docs]


@router.get("/students", response_model=List[UserPublic])
async def list_students(_: User = Depends(require_admin)):
    docs = (
        await db.users.find({"role": UserRole.STUDENT.value})
        .sort("created_at", -1)
        .to_list(1000)
    )
    return [_to_public(User.from_mongo(d)) for d in docs]


@router.post("/users", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user(payload: AdminCreateUser, _: User = Depends(require_admin)):
    email = payload.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

    user = User(
        email=email,
        name=payload.name,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    await db.users.insert_one(user.to_mongo())
    return _to_public(user)


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, current: User = Depends(require_admin)):
    if user_id == current.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete yourself")
    res = await db.users.delete_one({"_id": user_id})
    if not res.deleted_count:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    # Clean up related documents
    await db.enrollments.delete_many({"user_id": user_id})
    return {"success": True, "message": "User deleted"}


async def _set_blocked(user_id: str, blocked: bool, current: User) -> UserPublic:
    if user_id == current.id and blocked:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot block yourself")

    res = await db.users.update_one(
        {"_id": user_id},
        {"$set": {"blocked": blocked, "updated_at": _now_iso()}},
    )
    if not res.matched_count:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    doc = await db.users.find_one({"_id": user_id})
    return _to_public(User.from_mongo(doc))


@router.put("/users/{user_id}/block", response_model=UserPublic)
async def block_user(user_id: str, current: User = Depends(require_admin)):
    return await _set_blocked(user_id, True, current)


@router.put("/users/{user_id}/unblock", response_model=UserPublic)
async def unblock_user(user_id: str, current: User = Depends(require_admin)):
    return await _set_blocked(user_id, False, current)


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str, role: UserRole, _: User = Depends(require_admin)
):
    res = await db.users.update_one(
        {"_id": user_id},
        {"$set": {"role": role.value, "updated_at": _now_iso()}},
    )
    if not res.matched_count:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return {"success": True}


# =====================================================================
# ENROLL (manual admin enrollment)
# =====================================================================
@router.post("/enroll")
async def admin_enroll(payload: AdminEnrollRequest, _: User = Depends(require_admin)):
    user_doc = await db.users.find_one({"_id": payload.user_id})
    course_doc = await db.courses.find_one({"_id": payload.course_id})
    if not user_doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if not course_doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")

    enrollment = await _create_enrollment(
        User.from_mongo(user_doc), Course.from_mongo(course_doc)
    )
    return {"success": True, "enrollment_id": enrollment.id}


# =====================================================================
# PAYMENTS
# =====================================================================
@router.get("/payments", response_model=List[Payment])
async def list_payments(
    status_filter: Optional[str] = Query(None, alias="status"),
    _: User = Depends(require_admin),
):
    query = {"status": status_filter} if status_filter else {}
    docs = await db.payments.find(query).sort("created_at", -1).to_list(1000)
    return [Payment.from_mongo(d) for d in docs]


@router.put("/payments/{payment_id}/approve")
async def approve_payment(
    payment_id: str,
    review: PaymentReviewRequest,
    current: User = Depends(require_admin),
):
    payment_doc = await db.payments.find_one({"_id": payment_id})
    if not payment_doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")

    payment = Payment.from_mongo(payment_doc)
    if payment.status != "pending":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Payment has already been processed."
        )

    user_doc = await db.users.find_one({"_id": payment.user_id})
    course_doc = await db.courses.find_one({"_id": payment.course_id})
    if not user_doc or not course_doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User or course not found.")

    await db.payments.update_one(
        {"_id": payment.id},
        {
            "$set": {
                "status": "success",
                "reviewed_by": current.id,
                "reviewed_at": _now_iso(),
                "remarks": review.remarks,
                "updated_at": _now_iso(),
            }
        },
    )

    await _create_enrollment(
        User.from_mongo(user_doc), Course.from_mongo(course_doc)
    )

    return {"success": True, "message": "Payment approved successfully."}


@router.put("/payments/{payment_id}/reject")
async def reject_payment(
    payment_id: str,
    review: PaymentReviewRequest,
    current: User = Depends(require_admin),
):
    payment_doc = await db.payments.find_one({"_id": payment_id})
    if not payment_doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")

    payment = Payment.from_mongo(payment_doc)
    if payment.status != "pending":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Payment has already been processed."
        )

    await db.payments.update_one(
        {"_id": payment.id},
        {
            "$set": {
                "status": "rejected",
                "reviewed_by": current.id,
                "reviewed_at": _now_iso(),
                "remarks": review.remarks,
                "updated_at": _now_iso(),
            }
        },
    )

    return {"success": True, "message": "Payment rejected."}


# =====================================================================
# CONTACTS
# =====================================================================
@router.get("/contacts")
async def list_contacts(_: User = Depends(require_admin)):
    docs = await db.contacts.find().sort("created_at", -1).to_list(1000)
    # Return raw dicts (with id mapped from _id) so any legacy fields survive.
    result = []
    for d in docs:
        item = dict(d)
        item["id"] = item.pop("_id", None)
        result.append(item)
    return result


@router.put("/contacts/{contact_id}/read")
async def mark_contact_read(contact_id: str, _: User = Depends(require_admin)):
    res = await db.contacts.update_one(
        {"_id": contact_id},
        {"$set": {"is_read": True, "updated_at": _now_iso()}},
    )
    if not res.matched_count:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contact not found")
    return {"success": True}


# =====================================================================
# TESTIMONIALS
# =====================================================================
@router.get("/testimonials", response_model=List[Testimonial])
async def get_admin_testimonials(_: User = Depends(require_admin)):
    docs = await db.testimonials.find().sort("created_at", -1).to_list(1000)
    return [Testimonial.from_mongo(d) for d in docs]
