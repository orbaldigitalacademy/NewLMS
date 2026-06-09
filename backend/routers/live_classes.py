from datetime import datetime, timezone
from typing import Optional
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


# ==================================================
# HELPERS
# ==================================================

def get_live_class_status(
    start_time,
    end_time
):
    now = datetime.now(timezone.utc)

    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time)

    if isinstance(end_time, str):
        end_time = datetime.fromisoformat(end_time)

    if start_time <= now <= end_time:
        return LiveClassStatus.LIVE

    if now > end_time:
        return LiveClassStatus.COMPLETED

    return LiveClassStatus.SCHEDULED

def require_instructor_or_admin(user):
    role = user.role

    if role not in ["admin", "instructor"]:
        raise HTTPException(
            status_code=403,
            detail="Permission denied"
        )
# ==================================================
# CREATE LIVE CLASS
# ==================================================

@router.post("")
async def create_live_class(
    payload: dict,
    current_user=Depends(get_current_user)
):
    require_instructor_or_admin(current_user)

    live_class = {
        "id": str(uuid.uuid4()),
        "title": payload.get("title"),
        "description": payload.get("description", ""),
        "course_id": payload.get("course_id"),
        "meeting_url": payload.get("meeting_url"),
        "room_name": payload.get("room_name"),
        "start_time": payload.get("start_time"),
        "end_time": payload.get("end_time"),
        "recording_url": "",
        "recording_available": False,
        "created_by": current_user["id"],
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    live_class["status"] = get_live_class_status(
        live_class["start_time"],
        live_class["end_time"]
    )

    await db.live_classes.insert_one(
        live_class
    )

    return {
        "message": "Live class created",
        "id": live_class["id"]
    }


# ==================================================
# UPDATE LIVE CLASS
# ==================================================

@router.put("/{class_id}")
async def update_live_class(
    class_id: str,
    payload: dict,
    current_user=Depends(get_current_user)
):
    require_instructor_or_admin(current_user)

    existing = await db.live_classes.find_one(
        {"id": class_id}
    )

    if not existing:
        raise HTTPException(
            status_code=404,
            detail="Class not found"
        )

    payload["updated_at"] = datetime.now(
        timezone.utc
    ).isoformat()

    await db.live_classes.update_one(
        {"id": class_id},
        {"$set": payload}
    )

    return {
        "message": "Live class updated"
    }


# ==================================================
# DELETE LIVE CLASS (SOFT DELETE)
# ==================================================

@router.delete("/{class_id}")
async def delete_live_class(
    class_id: str,
    current_user=Depends(get_current_user)
):
    require_instructor_or_admin(current_user)

    result = await db.live_classes.update_one(
        {"id": class_id},
        {
            "$set": {
                "deleted": True,
                "deleted_at": datetime.now(
                    timezone.utc
                ).isoformat()
            }
        }
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Class not found"
        )

    return {
        "message": "Live class deleted"
    }


# ==================================================
# GET CLASSES FOR COURSE
# ==================================================

@router.get("/courses/{course_id}")
async def get_course_live_classes(
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
        {
            "course_id": course_id,
            "deleted": {"$ne": True}
        },
        {"_id": 0}
    ).sort(
        "start_time",
        1
    ).to_list(length=100)

    for cls in classes:
        cls["status"] = get_live_class_status(
            cls["start_time"],
            cls["end_time"]
        )

    return classes


# ==================================================
# GET SINGLE LIVE CLASS
# ==================================================

@router.get("/{class_id}")
async def get_live_class(
    class_id: str,
    current_user=Depends(get_current_user)
):
    live_class = await db.live_classes.find_one(
        {
            "id": class_id,
            "deleted": {"$ne": True}
        },
        {"_id": 0}
    )

    if not live_class:
        raise HTTPException(
            status_code=404,
            detail="Class not found"
        )

    live_class["status"] = get_live_class_status(
        live_class["start_time"],
        live_class["end_time"]
    )

    return live_class


# ==================================================
# JOIN LIVE CLASS
# ==================================================

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

    status = get_live_class_status(
        live_class["start_time"],
        live_class["end_time"]
    )

    if status != LiveClassStatus.LIVE:
        raise HTTPException(
            status_code=400,
            detail="Class is not live"
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
        "status": status
    }


# ==================================================
# LEAVE LIVE CLASS
# ==================================================

@router.post("/{class_id}/leave")
async def leave_live_class(
    class_id: str,
    current_user=Depends(get_current_user)
):
    attendance = await db.attendance.find_one({
        "class_id": class_id,
        "user_id": current_user["id"],
        "left_at": {"$exists": False}
    })

    if not attendance:
        raise HTTPException(
            status_code=404,
            detail="Attendance record not found"
        )

    leave_time = datetime.now(
        timezone.utc
    )

    join_time = datetime.fromisoformat(
        attendance["joined_at"]
    )

    duration = (
        leave_time - join_time
    ).total_seconds() / 60

    await db.attendance.update_one(
        {"id": attendance["id"]},
        {
            "$set": {
                "left_at": leave_time.isoformat(),
                "duration_minutes": round(
                    duration,
                    2
                )
            }
        }
    )

    return {
        "message": "Attendance updated",
        "duration_minutes": round(
            duration,
            2
        )
    }


# ==================================================
# ATTENDANCE REPORT
# ==================================================

@router.get("/{class_id}/attendance")
async def get_attendance(
    class_id: str,
    current_user=Depends(get_current_user)
):
    require_instructor_or_admin(
        current_user
    )

    records = await db.attendance.find(
        {"class_id": class_id},
        {"_id": 0}
    ).to_list(length=1000)

    return records


# ==================================================
# ADD RECORDING
# ==================================================

@router.put("/{class_id}/recording")
async def add_recording(
    class_id: str,
    payload: dict,
    current_user=Depends(get_current_user)
):
    require_instructor_or_admin(
        current_user
    )

    recording_url = payload.get(
        "recording_url"
    )

    if not recording_url:
        raise HTTPException(
            status_code=400,
            detail="Recording URL required"
        )

    await db.live_classes.update_one(
        {"id": class_id},
        {
            "$set": {
                "recording_url": recording_url,
                "recording_available": True
            }
        }
    )

    return {
        "message": "Recording added"
    }


# ==================================================
# UPCOMING CLASSES
# ==================================================

@router.get("")
async def get_upcoming_live_classes(
    current_user=Depends(get_current_user)
):
    classes = await db.live_classes.find(
        {
            "deleted": {"$ne": True}
        },
        {"_id": 0}
    ).sort(
        "start_time",
        1
    ).to_list(length=100)

    for cls in classes:
        cls["status"] = get_live_class_status(
            cls["start_time"],
            cls["end_time"]
        )

    return classes
