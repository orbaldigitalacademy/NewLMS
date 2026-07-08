from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from auth import get_current_user
from database import db
from models.user import User, UserPublic
from cloudinary.uploader import upload as cloudinary_upload

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me", response_model=UserPublic)
async def get_my_profile(user: User = Depends(get_current_user)):
    return UserPublic(**user.model_dump())


@router.put("/me", response_model=UserPublic)
async def update_my_profile(
    bio: str | None = None,
    user: User = Depends(get_current_user),
):
    updates = {}

    if bio is not None:
        updates["bio"] = bio

    if updates:
        await db.users.update_one(
            {"_id": user.id},
            {"$set": updates},
        )

    updated = await db.users.find_one({"_id": user.id})
    return UserPublic(**User.from_mongo(updated).model_dump())


@router.post("/avatar", response_model=UserPublic)
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/jpg"]

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPG, PNG, and WEBP images are allowed.",
        )

    result = cloudinary_upload(
        file.file,
        folder="orbal-academy/avatars",
        resource_type="image",
    )

    avatar_url = result.get("secure_url")

    await db.users.update_one(
        {"_id": user.id},
        {"$set": {"avatar_url": avatar_url}},
    )

    updated = await db.users.find_one({"_id": user.id})
    return UserPublic(**User.from_mongo(updated).model_dump())
