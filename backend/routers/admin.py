"""Admin router - stats, user management."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime

from auth import require_roles

from database import db

from models import (
    Payment,
    PaymentReviewRequest,
    User,
    UserRole,
    Course,
)

from auth import require_admin
from database import db
from models.payment import Payment
from models.user import User, UserPublic
from models.testimonial import Testimonial

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def stats(_: User = Depends(require_admin)):
    users_count = await db.users.count_documents({})
    students = await db.users.count_documents({"role": "student"})
    courses = await db.courses.count_documents({})
    published_courses = await db.courses.count_documents({"is_published": True})
    enrollments = await db.enrollments.count_documents({})
    completed = await db.enrollments.count_documents({"is_completed": True})
    payments_success = await db.payments.count_documents({"status": "success"})

    # revenue
    revenue_cursor = db.payments.aggregate(
        [
            {"$match": {"status": "success"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]
    )
    revenue = 0.0
    async for r in revenue_cursor:
        revenue = r.get("total", 0)

    contacts_unread = await db.contacts.count_documents({"is_read": False})

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


@router.get("/users", response_model=List[UserPublic])
async def list_users(_: User = Depends(require_admin)):
    docs = await db.users.find().sort("created_at", -1).to_list(1000)
    return [
        UserPublic(
            id=d["_id"],
            email=d["email"],
            name=d["name"],
            role=d.get("role", "student"),
            avatar_url=d.get("avatar_url"),
            bio=d.get("bio"),
            created_at=d.get("created_at"),
        )
        for d in docs
    ]


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str, role: str, _: User = Depends(require_admin)
):
    if role not in {"student", "admin"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid role")
    res = await db.users.update_one({"_id": user_id}, {"$set": {"role": role}})
    if not res.matched_count:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return {"ok": True}


@router.get("/payments", response_model=List[Payment])
async def list_payments(_: User = Depends(require_admin)):
    docs = await db.payments.find().sort("created_at", -1).to_list(1000)
    return [Payment.from_mongo(d) for d in docs]

@router.put("/payments/{payment_id}/approve")
async def approve_payment(
    payment_id: str,
    review: PaymentReviewRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    payment_doc = await db.payments.find_one({"_id": payment_id})

    if not payment_doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Payment not found",
        )

    payment = Payment.from_mongo(payment_doc)

    if payment.status != "pending":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Payment has already been processed.",
        )

    user_doc = await db.users.find_one({"_id": payment.user_id})
    course_doc = await db.courses.find_one({"_id": payment.course_id})

    if not user_doc or not course_doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "User or course not found.",
        )

    await db.payments.update_one(
        {"_id": payment.id},
        {
            "$set": {
                "status": "success",
                "reviewed_by": current_user.id,
                "reviewed_at": datetime.now().isoformat(),
                "remarks": review.remarks,
            }
        },
    )

    await _create_enrollment(
        User.from_mongo(user_doc),
        Course.from_mongo(course_doc),
    )

    return {
        "success": True,
        "message": "Payment approved successfully.",
    }

@router.put("/payments/{payment_id}/reject")
async def reject_payment(
    payment_id: str,
    review: PaymentReviewRequest,
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    ),
):
    payment_doc = await db.payments.find_one(
        {"_id": payment_id}
    )

    # Payment not found
    if not payment_doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Payment not found",
        )

    # Convert Mongo document to Payment model
    payment = Payment.from_mongo(payment_doc)

    # Prevent rejecting an already processed payment
    if payment.status != "pending":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Payment has already been processed.",
        )

    # Update payment
    await db.payments.update_one(
        {"_id": payment.id},
        {
            "$set": {
                "status": "rejected",
                "reviewed_by": current_user.id,
                "reviewed_at": datetime.now().isoformat(),
                "remarks": review.remarks,
            }
        },
    )

    return {
        "success": True,
        "message": "Payment rejected.",
    }

@router.get("/testimonials")
async def get_admin_testimonials():
    docs = await db.testimonials.find({}).to_list(1000)

    return [
        Testimonial.from_mongo(doc)
        for doc in docs
    ]
