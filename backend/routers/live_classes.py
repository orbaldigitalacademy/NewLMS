from datetime import datetime, timezone
import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from auth import get_current_user
from database import db
from models.live_class import LiveClassStatus

router = APIRouter(
    prefix="/live-classes",
    tags=["live-classes"],
)

@router.get("/sync-status")
async def sync_live_class_status_route():

    now = datetime.now(timezone.utc)

    classes = await db.live_classes.find(
        {}
    ).to_list(length=500)

    for live_class in classes:

        start = datetime.fromisoformat(
            live_class["start_time"]
        )

        end = datetime.fromisoformat(
            live_class["end_time"]
        )

        if start <= now <= end:
            status = LiveClassStatus.LIVE

        elif now > end:
            status = LiveClassStatus.COMPLETED

        else:
            status = LiveClassStatus.SCHEDULED

        await db.live_classes.update_one(
            {"id": live_class["id"]},
            {"$set": {"status": status}}
        )

    return {"message": "Sync completed"}

    @router.get("/courses/{course_id}")
async def get_live_classes(
    course_id: str,
    current_user=Depends(get_current_user)
):
    enrollment = await db.enrollments.find_one({
        "user_id": current_user["id"],
        "course_id": course_id,
        "access_granted": True
    })

    if not enrollment:
        raise HTTPException(
            status_code=403,
            detail="No access"
        )

    classes = await db.live_classes.find(
        {"course_id": course_id},
        {"_id": 0}
    ).sort(
        "start_time",
        1
    ).to_list(length=100)

    return classes

    @router.post("/{class_id}/join")
async def join_live_class(
    class_id: str,
    current_user=Depends(get_current_user)
):
    live_class = await db.live_classes.find_one(
        {"id": class_id}
    )

    if not live_class:
        raise HTTPException(
            status_code=404,
            detail="Class not found"
        )

    enrollment = await db.enrollments.find_one({
        "user_id": current_user["id"],
        "course_id": live_class["course_id"],
        "access_granted": True
    })

    if not enrollment:
        raise HTTPException(
            status_code=403,
            detail="No access"
        )

    existing_attendance = await db.attendance.find_one({
        "class_id": class_id,
        "user_id": current_user["id"],
        "left_at": {"$exists": False}
    })

    if not existing_attendance:
        await db.attendance.insert_one({
            "id": str(uuid.uuid4()),
            "class_id": class_id,
            "user_id": current_user["id"],
            "joined_at": datetime.now(
                timezone.utc
            ).isoformat()
        })

    return {
        "meeting_url": live_class["meeting_url"],
        "status": live_class["status"]
    }
