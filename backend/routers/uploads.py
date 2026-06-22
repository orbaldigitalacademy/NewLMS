from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
    HTTPException,
    status,
)
import cloudinary
import cloudinary.uploader
import logging
import uuid

from auth import get_current_user, require_roles
from models import UserRole

logger = logging.getLogger(__name__)

router = APIRouter()

# =====================================================
# ALLOWED FILE TYPES
# =====================================================

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

# =====================================================
# FILE SIZE LIMITS
# =====================================================

MAX_IMAGE_SIZE = 5 * 1024 * 1024       # 5 MB
MAX_VIDEO_SIZE = 100 * 1024 * 1024     # 100 MB
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024   # 10 MB

# =====================================================
# HELPERS
# =====================================================

def ensure_cloudinary():
    """
    Ensure Cloudinary is configured.
    """
    config = cloudinary.config()

    if not config.cloud_name:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cloudinary is not configured",
        )


async def read_and_validate_file(
    file: UploadFile,
    max_size: int,
):
    """
    Read file contents and validate size.
    """
    contents = await file.read()
    await file.close()

    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded",
        )

    if len(contents) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds {max_size // (1024 * 1024)} MB limit",
        )

    return contents


async def upload_to_cloudinary(
    file: UploadFile,
    resource_type: str,
    folder: str,
    max_size: int,
):
    """
    Upload file to Cloudinary.
    """
    contents = await read_and_validate_file(file, max_size)

    result = cloudinary.uploader.upload(
        contents,
        resource_type=resource_type,
        folder=folder,
        public_id=f"{uuid.uuid4()}",
        overwrite=False,
    )

    return {
        "success": True,
        "url": result.get("secure_url"),
        "public_id": result.get("public_id"),
    }


# =====================================================
# IMAGE UPLOAD
# =====================================================

@api_router.post("/upload/image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    ensure_cloudinary()

    if file.content_type not in IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image format. Allowed: JPG, PNG, GIF, WEBP",
        )

    try:
        return await upload_to_cloudinary(
            file=file,
            resource_type="image",
            folder="lms/images",
            max_size=MAX_IMAGE_SIZE,
        )

    except HTTPException:
        raise

    except Exception:
        logger.exception("Image upload failed")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image",
        )


# =====================================================
# VIDEO UPLOAD
# =====================================================

@api_router.post("/upload/video")
async def upload_video(
    file: UploadFile = File(...),
    current_user: dict = Depends(
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
        return await upload_to_cloudinary(
            file=file,
            resource_type="video",
            folder="lms/videos",
            max_size=MAX_VIDEO_SIZE,
        )

    except HTTPException:
        raise

    except Exception:
        logger.exception("Video upload failed")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload video",
        )


# =====================================================
# DOCUMENT UPLOAD
# =====================================================

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
        resource_type = (
            "image"
            if file.content_type.startswith("image/")
            else "raw"
        )

        return await upload_to_cloudinary(
            file=file,
            resource_type=resource_type,
            folder="lms/proofs",
            max_size=MAX_DOCUMENT_SIZE,
        )

    except HTTPException:
        raise

    except Exception:
        logger.exception("Document upload failed")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document",
        )
