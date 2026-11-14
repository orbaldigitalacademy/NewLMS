"""Alumni endpoints for the ODA React frontend.

Adjust the get_current_user import to match your existing project.
Admin checks below assume the user document has role='admin' or is_admin=True.
"""
import asyncio
import io

import cloudinary.uploader

from PIL import Image, UnidentifiedImageError
from fastapi import UploadFile, File
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from database import db
from auth import get_current_user  # ADAPT to your project's existing import

router = APIRouter(prefix="/alumni", tags=["Alumni"])


def utcnow():
    return datetime.now(timezone.utc)


def user_id_of(user):
    if isinstance(user, dict):
        return str(user.get("id") or user.get("_id") or "")
    return str(getattr(user, "id", None) or getattr(user, "_id", "") or "")


def is_admin(user):
    if isinstance(user, dict):
        return user.get("role") == "admin" or user.get("is_admin") is True
    return getattr(user, "role", None) == "admin" or getattr(user, "is_admin", False) is True


async def require_admin(user=Depends(get_current_user)):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def require_alumni(user=Depends(get_current_user)):
    uid = user_id_of(user)
    if not uid:
        raise HTTPException(status_code=401, detail="Authentication required")
    profile = await db.alumni_profiles.find_one({"user_id": uid, "is_verified": True})
    if not profile:
        raise HTTPException(status_code=403, detail="Verified alumni access required")
    return profile


class AlumniUpdate(BaseModel):
    professional_title: str = Field(default="", max_length=150)
    bio: str = Field(default="", max_length=1200)
    skills: list[str] = Field(default_factory=list, max_length=30)
    linkedin_url: str = Field(default="", max_length=300)
    github_url: str = Field(default="", max_length=300)
    portfolio_url: str = Field(default="", max_length=300)
    is_public: bool = True
    name_title: str = Field(default="", max_length=20)
    city: str = Field(default="", max_length=100)
    country: str = Field(default="", max_length=100)
    phone_number: str = Field(default="", max_length=30)
    @field_validator("linkedin_url", "github_url", "portfolio_url")
    @classmethod
    def valid_url(cls, value):
        if value and not value.startswith(("https://", "http://")):
            raise ValueError("Links must begin with https:// or http://")
        return value


def public_fields(p):
    return {
        "user_id": p.get("user_id"),
        "full_name": p.get("full_name", ""),
        "professional_title": p.get("professional_title", ""),
        "bio": p.get("bio", ""),
        "skills": p.get("skills", []),
        "linkedin_url": p.get("linkedin_url", ""),
        "github_url": p.get("github_url", ""),
        "portfolio_url": p.get("portfolio_url", ""),
        "profile_image_url": p.get("profile_image_url", ""),
        "name_title": p.get("name_title", ""),
        "city": p.get("city", ""),
        "country": p.get("country", ""),
        "phone_number": p.get("phone_number", ""),
    }

def private_fields(p):
    result = public_fields(p)

    result.update({
        "is_verified": bool(p.get("is_verified")),
        "is_public": bool(p.get("is_public", True)),
        "hidden_by_admin": bool(p.get("hidden_by_admin", False)),
        "completed_course_ids": p.get("completed_course_ids", []),
    })

    return result

@router.get("/public")
async def alumni_directory():
    profiles = await db.alumni_profiles.find({
        "is_verified": True, "is_public": True, "hidden_by_admin": {"$ne": True}  
    }).sort("full_name", 1).limit(200).to_list(length=200)
    return {"items": [public_fields(p) for p in profiles]}


@router.get("/me")
async def my_alumni_profile(profile=Depends(require_alumni)):
    return private_fields(profile)


@router.patch("/me")
async def update_my_alumni_profile(
    payload: AlumniUpdate,
    profile=Depends(require_alumni),
):
    updates = payload.model_dump()
    # The React form sends blank URL strings; treat those as empty values.
    for key in ("linkedin_url", "github_url", "portfolio_url"):
        updates[key] = str(updates[key]) if updates[key] else ""
    updates["skills"] = [s.strip()[:80] for s in updates["skills"] if s.strip()][:30]
    updates["updated_at"] = utcnow()
    await db.alumni_profiles.update_one(
        {"user_id": profile["user_id"], "is_verified": True},
        {"$set": updates},
    )
    updated = await db.alumni_profiles.find_one({"user_id": profile["user_id"]})
    return private_fields(updated)


@router.get("/admin")
async def list_alumni(_admin=Depends(require_admin)):
    profiles = await db.alumni_profiles.find({}).sort("created_at", -1).limit(500).to_list(length=500)
    items = []
    for profile in profiles:
        uid = profile.get("user_id")
        user = await db.users.find_one({"_id": uid}, {"email": 1})
        job = await db.alumni_email_jobs.find_one({"_id": f"alumni-welcome:{uid}"})
        item = private_fields(profile)
        item.update({
            "email": (user or {}).get("email", ""),
            "email_status": (job or {}).get("status", "No job"),
        })
        items.append(item)
    return {"items": items}


@router.post("/admin/{user_id}/resend")
async def resend_alumni_welcome(user_id: str, _admin=Depends(require_admin)):
    profile = await db.alumni_profiles.find_one({"user_id": user_id, "is_verified": True})
    if not profile:
        raise HTTPException(status_code=404, detail="Verified alumni not found")
    user = await db.users.find_one({"_id": user_id})
    if not user or not user.get("email"):
        raise HTTPException(status_code=422, detail="Alumnus has no deliverable email address")
    # Admin explicitly requested another email: use a fresh unique job and idempotency key.
    token = uuid4().hex
    stamp = utcnow()
    job = {
        "_id": f"alumni-welcome-resend:{user_id}:{token}",
        "user_id": user_id,
        "kind": "alumni_welcome",
        "status": "pending",
        "attempts": 0,
        "created_at": stamp,
        "next_attempt_at": stamp,
        "idempotency_key": f"oda-alumni-resend-{token}",
        "recipient_email": user["email"],
        "recipient_name": user.get("name") or user.get("full_name") or profile.get("full_name") or "Graduate",
    }
    await db.alumni_email_jobs.insert_one(job)
    return {"queued": True, "status": "pending"}


# ============================================
# ALUMNI PROFILE PICTURE UPLOAD
# ============================================

MAX_PROFILE_IMAGE_SIZE = 5 * 1024 * 1024

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}


@router.post("/me/profile-picture")
async def upload_alumni_profile_picture(
    file: UploadFile = File(...),
    profile=Depends(require_alumni),
):
    # 1. Validate declared file type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG and WebP images are allowed",
        )

    # 2. Read file with size limit
    contents = await file.read(MAX_PROFILE_IMAGE_SIZE + 1)

    if len(contents) > MAX_PROFILE_IMAGE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Profile picture must not exceed 5MB",
        )

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty",
        )

    # 3. Validate actual image contents
    try:
        with Image.open(io.BytesIO(contents)) as img:
            if img.format != ALLOWED_IMAGE_TYPES[file.content_type]:
                raise ValueError("File content does not match its type")

            img.verify()

    except (
        UnidentifiedImageError,
        ValueError,
        OSError,
        Image.DecompressionBombError,
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid image file",
        )

    # 4. Upload to Cloudinary
    try:
        result = await asyncio.to_thread(
            cloudinary.uploader.upload,
            contents,
            folder="lms/alumni/profile-pictures",
            resource_type="image",
            overwrite=False,
            unique_filename=True,
            use_filename=False,
        )

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Unable to upload profile picture to Cloudinary",
        )

    image_url = result.get("secure_url")
    public_id = result.get("public_id")

    if not image_url or not public_id:
        raise HTTPException(
            status_code=502,
            detail="Cloudinary returned incomplete image information",
        )

    # 5. Save image information in MongoDB
    update_result = await db.alumni_profiles.update_one(
        {
            "user_id": profile["user_id"],
            "is_verified": True,
        },
        {
            "$set": {
                "profile_image_url": image_url,
                "profile_image_public_id": public_id,
                "updated_at": utcnow(),
            }
        },
    )

    if update_result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Alumni profile not found",
        )

    return {
        "message": "Profile picture uploaded successfully",
        "profile_image_url": image_url,
    }

