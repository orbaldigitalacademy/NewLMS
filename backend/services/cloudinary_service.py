import logging
import os
import time
from pathlib import Path
from typing import Optional

import cloudinary
import cloudinary.uploader
import cloudinary.utils

logger = logging.getLogger(__name__)

# ============================================================
# CLOUDINARY CONFIGURATION
# ============================================================
CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip()
API_KEY = os.getenv("CLOUDINARY_API_KEY", "").strip()
API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "").strip()

def _valid_credential(value: str) -> bool:
    """Check whether a Cloudinary credential is configured."""
    return bool(value) and not value.upper().startswith("PLACEHOLDER")

_configured = all(
    [
        _valid_credential(CLOUD_NAME),
        _valid_credential(API_KEY),
        _valid_credential(API_SECRET),
    ]
)
if _configured:
    cloudinary.config(
        cloud_name=CLOUD_NAME,
        api_key=API_KEY,
        api_secret=API_SECRET,
        secure=True,
    )

    logger.info(
        "Cloudinary configured successfully for cloud '%s'",
        CLOUD_NAME,
    )
else:
    logger.warning(
        "Cloudinary is NOT configured. "
        "Uploads will fail until valid credentials are provided."
    )
# ============================================================
# CONSTANTS
# ============================================================
ALLOWED_RESOURCE_TYPES = {
    "video",
    "image",
    "raw",
}
ALLOWED_FOLDERS = {
    "video": "lms/videos",
    "image": "lms/images",
    "document": "lms/documents",
    "certificate": "lms/certificates",
    "thumbnail": "lms/thumbnails",
}
ALLOWED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".webm",
    ".mkv",
}
ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
}
ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf",
}
# ============================================================
# CONFIGURATION HELPERS
# ============================================================

def is_configured() -> bool:
    """Return True when valid Cloudinary credentials are available."""
    return _configured


def _require_configured() -> None:
    """Raise an error when Cloudinary is not configured."""
    if not _configured:
        raise RuntimeError(
            "Cloudinary is not configured. "
            "Please set CLOUDINARY_CLOUD_NAME, "
            "CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET."
        )
# ============================================================
# RESOURCE TYPE VALIDATION
# ============================================================

def _validate_resource_type(resource_type: str) -> None:
    """Validate Cloudinary resource type."""
    if resource_type not in ALLOWED_RESOURCE_TYPES:
        raise ValueError(
            f"Unsupported resource type '{resource_type}'. "
            f"Allowed types: {', '.join(sorted(ALLOWED_RESOURCE_TYPES))}"
        )

# ============================================================
# FOLDER VALIDATION
# ============================================================

def _validate_folder(folder: str) -> None:
    """Ensure uploads are restricted to LMS folders."""

    allowed = set(ALLOWED_FOLDERS.values())

    if folder not in allowed:
        raise ValueError(
            f"Folder '{folder}' is not allowed. "
            f"Allowed folders: {', '.join(sorted(allowed))}"
        )
# ============================================================
# FILE EXTENSION VALIDATION
# ============================================================

def validate_file_extension(
    filename: str,
    resource_type: str,
) -> None:
    """
    Validate file extension against the Cloudinary resource type.
    """

    extension = Path(filename).suffix.lower()

    if resource_type == "video":
        allowed = ALLOWED_VIDEO_EXTENSIONS

    elif resource_type == "image":
        allowed = ALLOWED_IMAGE_EXTENSIONS

    elif resource_type == "raw":
        allowed = ALLOWED_DOCUMENT_EXTENSIONS

    else:
        raise ValueError(
            f"Unsupported resource type: {resource_type}"
        )

    if extension not in allowed:
        raise ValueError(
            f"File type '{extension}' is not allowed for "
            f"resource type '{resource_type}'."
        )
# ============================================================
# DIRECT SIGNED UPLOAD
# ============================================================

def signature_for_upload(
    resource_type: str = "video",
    folder: str = "lms/videos",
) -> dict:
    """
    Generate a signed Cloudinary upload configuration.

    The browser uses the returned signature to upload directly
    to Cloudinary without sending large files through FastAPI.
    """

    _require_configured()

    _validate_resource_type(resource_type)
    _validate_folder(folder)

    timestamp = int(time.time())

    params_to_sign = {
        "timestamp": timestamp,
        "folder": folder,
    }

    signature = cloudinary.utils.api_sign_request(
        params_to_sign,
        API_SECRET,
    )

    upload_url = (
        f"https://api.cloudinary.com/v1_1/"
        f"{CLOUD_NAME}/{resource_type}/upload"
    )
    return {
        "configured": True,
        "signature": signature,
        "timestamp": timestamp,
        "cloud_name": CLOUD_NAME,
        "api_key": API_KEY,
        "folder": folder,
        "resource_type": resource_type,
        "upload_url": upload_url,
    }
# ============================================================
# BACKEND UPLOAD
# ============================================================

def upload_file(
    file_bytes: bytes,
    filename: str,
    resource_type: str = "image",
    folder: str = "lms/images",
) -> dict:
    """
    Upload a file from the FastAPI backend to Cloudinary.

    Recommended for:
        - Images
        - Thumbnails
        - PDFs
        - Certificates
        - Small assets

    For large videos, prefer signed direct browser uploads.
    """

    _require_configured()

    if not file_bytes:
        raise ValueError("Cannot upload an empty file.")

    _validate_resource_type(resource_type)
    _validate_folder(folder)
    validate_file_extension(filename, resource_type)

    try:
        result = cloudinary.uploader.upload(
            file_bytes,
            resource_type=resource_type,
            folder=folder,
            use_filename=True,
            unique_filename=True,
            overwrite=False,
        )

    except Exception as exc:
        logger.exception(
            "Cloudinary upload failed for '%s'",
            filename,
        )

        raise RuntimeError(
            f"Cloudinary upload failed: {exc}"
        ) from exc

    return {
        "url": result.get("secure_url"),
        "secure_url": result.get("secure_url"),
        "public_id": result.get("public_id"),
        "resource_type": result.get("resource_type"),
        "format": result.get("format"),
        "bytes": result.get("bytes"),
        "duration": result.get("duration"),
        "width": result.get("width"),
        "height": result.get("height"),
    }
# ============================================================
# DELETE ASSET
# ============================================================

def delete_asset(
    public_id: str,
    resource_type: str = "image",
) -> bool:
    """
    Delete an asset from Cloudinary.

    Returns:
        True  -> successfully deleted
        False -> asset was not deleted
    """

    if not public_id:
        return False

    if public_id.startswith("placeholder/"):
        return False

    if not _configured:
        logger.warning(
            "Cloudinary is not configured. "
            "Cannot delete asset '%s'.",
            public_id,
        )
        return False

    _validate_resource_type(resource_type)

    try:
        result = cloudinary.uploader.destroy(
            public_id,
            resource_type=resource_type,
            invalidate=True,
        )

        success = result.get("result") == "ok"

        if not success:
            logger.warning(
                "Cloudinary deletion returned: %s",
                result,
            )

        return success

    except Exception:
        logger.exception(
            "Failed to delete Cloudinary asset '%s'",
            public_id,
        )

        return False
# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_folder_for_type(asset_type: str) -> str:
    """
    Return the appropriate Cloudinary folder for an LMS asset type.

    Examples:
        video      -> lms/videos
        image      -> lms/images
        document   -> lms/documents
        certificate -> lms/certificates
        thumbnail  -> lms/thumbnails
    """

    folder = ALLOWED_FOLDERS.get(asset_type)

    if not folder:
        raise ValueError(
            f"Unknown asset type '{asset_type}'. "
            f"Allowed types: {', '.join(ALLOWED_FOLDERS.keys())}"
        )

    return folder


def get_resource_type(asset_type: str) -> str:
    """
    Convert LMS asset type to Cloudinary resource type.
    """

    mapping = {
        "video": "video",
        "image": "image",
        "thumbnail": "image",
        "document": "raw",
        "certificate": "raw",
    }

    resource_type = mapping.get(asset_type)

    if not resource_type:
        raise ValueError(
            f"Unknown asset type '{asset_type}'."
        )

    return resource_type
