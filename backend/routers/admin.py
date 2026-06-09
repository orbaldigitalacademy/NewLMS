"""Admin router - stats, user management."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from auth import require_admin
from database import db
from models.payment import Payment
from models.user import User, UserPublic

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

@router.get("/testimonials")
async def get_admin_testimonials():
    docs = await db.testimonials.find({}).to_list(1000)

    return [
        Testimonial.from_mongo(doc)
        for doc in docs
    ]
