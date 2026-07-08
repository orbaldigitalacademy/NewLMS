"""Testimonials router."""

from datetime import datetime, timezone
from math import ceil

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from auth import get_current_user, require_admin
from database import db
from models.testimonial import (
    Testimonial,
    TestimonialCreate,
    TestimonialUpdate,
)
from models.user import User

router = APIRouter(
    prefix="/testimonials",
    tags=["testimonials"],
)


@router.get("")
async def list_testimonials(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=6, ge=1, le=100),
):
    """
    Public testimonials.
    Only approved testimonials are returned.
    """

    query = {"is_approved": True}

    total = await db.testimonials.count_documents(query)

    docs = (
        await db.testimonials
        .find(query)
        .sort("created_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list(limit)
    )

    return {
        "data": [
            Testimonial.from_mongo(doc)
            for doc in docs
        ],
        "pages": max(1, ceil(total / limit)),
        "total": total,
        "page": page,
    }


@router.get("/average-rating")
async def average_rating():
    """
    Returns average rating for approved testimonials.
    """

    pipeline = [
        {
            "$match": {
                "is_approved": True,
            }
        },
        {
            "$group": {
                "_id": None,
                "average_rating": {
                    "$avg": "$rating"
                },
            }
        },
    ]

    result = await db.testimonials.aggregate(
        pipeline
    ).to_list(1)

    average = (
        round(result[0]["average_rating"], 1)
        if result
        else 0
    )

    return {
        "average_rating": average,
    }


@router.post(
    "",
    response_model=Testimonial,
    status_code=status.HTTP_201_CREATED,
)
async def create_testimonial(
    data: TestimonialCreate,
    user: User = Depends(get_current_user),
):
    testimonial = Testimonial(
        user_id=user.id,
        user_name=user.name,
        avatar_url=data.avatar_url or getattr(user, "avatar_url", None),
        content=data.content,
        video_url=data.video_url,
        rating=data.rating,
        is_approved=False,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    await db.testimonials.insert_one(testimonial.to_mongo())

    return testimonial

@router.get("/admin")
async def admin_list_testimonials(
    is_approved: bool | None = None,
    user: User = Depends(require_admin),
):
    """
    Admin view of all testimonials.
    """

    query = {}

    if is_approved is not None:
        query["is_approved"] = is_approved

    docs = (
        await db.testimonials
        .find(query)
        .sort("created_at", -1)
        .to_list(1000)
    )

    return [
        Testimonial.from_mongo(doc)
        for doc in docs
    ]


@router.patch(
    "/{testimonial_id}",
    response_model=Testimonial,
)
async def update_testimonial(
    testimonial_id: str,
    data: TestimonialUpdate,
    user: User = Depends(require_admin),
):
    """
    Approve/feature testimonials.
    """

    existing = await db.testimonials.find_one(
        {"_id": testimonial_id}
    )

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Testimonial not found",
        )

    updates = data.model_dump(
        exclude_none=True
    )

    updates["updated_at"] = (
        datetime.now(timezone.utc)
        .isoformat()
    )

    await db.testimonials.update_one(
        {"_id": testimonial_id},
        {"$set": updates},
    )

    updated = await db.testimonials.find_one(
        {"_id": testimonial_id}
    )

    return Testimonial.from_mongo(updated)


@router.delete(
    "/{testimonial_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_testimonial(
    testimonial_id: str,
    user: User = Depends(require_admin),
):
    """
    Delete testimonial.
    """

    existing = await db.testimonials.find_one(
        {"_id": testimonial_id}
    )

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Testimonial not found",
        )

    await db.testimonials.delete_one(
        {"_id": testimonial_id}
    )

    return None

@router.get("/api/admin/testimonials")
async def admin_testimonials():
    testimonials = list(
        db.testimonials.find({})
    )

    for t in testimonials:
        t["_id"] = str(t["_id"])

    return testimonials
