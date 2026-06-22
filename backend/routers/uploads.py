```python
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
import cloudinary
import cloudinary.uploader
import logging

from auth import get_current_user, require_roles
from models import UserRole

logger = logging.getLogger(__name__)

api_router = APIRouter()

# ==============================
# FILE TYPES
# ==============================

IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}

VIDEO_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-msvideo",
}

DOCUMENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}


def ensure_cloudinary():
    if not cloudinary.config().cloud_name:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cloudinary not configured",
        )


# ==============================
# IMAGE UPLOAD
# ==============================

@api_router.post("/upload/image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    ensure_cloudinary()

    if file.content_type not in IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image format",
        )

    try:
        contents = await file.read()

        result = cloudinary.uploader.upload(
            contents,
            resource_type="image",
            folder="lms/images",
        )

        return {
            "success": True,
            "url": result["secure_url"],
            "public_id": result["public_id"],
        }

    except Exception as e:
        logger.exception(f"Image upload failed: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image",
        )


# ==============================
# VIDEO UPLOAD
# ==============================

@api_router.post("/upload/video")
async def upload_video(
    file: UploadFile = File(...),
    user: dict = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.INSTRUCTOR,
        )
    ),
):
    ensure_cloudinary()

    if file.content_type not in VIDEO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported video format",
        )

    try:
        contents = await file.read()

        result = cloudinary.uploader.upload(
            contents,
            resource_type="video",
            folder="lms/videos",
        )

        return {
            "success": True,
            "url": result["secure_url"],
            "public_id": result["public_id"],
        }

    except Exception as e:
        logger.exception(f"Video upload failed: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload video",
        )


# ==============================
# DOCUMENT UPLOAD
# ==============================

@api_router.post("/upload/document")
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    ensure_cloudinary()

    if file.content_type not in DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF, JPG and PNG files are allowed",
        )

    try:
        contents = await file.read()

        resource_type = (
            "image"
            if file.content_type.startswith("image/")
            else "raw"
        )

        result = cloudinary.uploader.upload(
            contents,
            resource_type=resource_type,
            folder="lms/proofs",
        )

        return {
            "success": True,
            "url": result["secure_url"],
            "public_id": result["public_id"],
        }

    except Exception as e:
        logger.exception(f"Document upload failed: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document",
        )
```
