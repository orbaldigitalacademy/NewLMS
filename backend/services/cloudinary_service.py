"""Cloudinary service - uploads images, videos and PDFs.

Falls back to a hosted placeholder if credentials are not configured.
"""
import os
import logging
from typing import Optional

import cloudinary
import cloudinary.uploader

logger = logging.getLogger(__name__)

CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
API_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")

_configured = all(
    [
        CLOUD_NAME and not CLOUD_NAME.startswith("PLACEHOLDER"),
        API_KEY and not API_KEY.startswith("PLACEHOLDER"),
        API_SECRET and not API_SECRET.startswith("PLACEHOLDER"),
    ]
)

if _configured:
    cloudinary.config(
        cloud_name=CLOUD_NAME, api_key=API_KEY, api_secret=API_SECRET, secure=True
    )


def is_configured() -> bool:
    return _configured


def upload_file(
    file_bytes: bytes,
    filename: str,
    resource_type: str = "auto",
    folder: Optional[str] = "lms",
) -> dict:
    """Upload to Cloudinary. Returns {url, public_id, resource_type}."""
    if not _configured:
        # placeholder mode: return data: url not feasible for big files. Use a hosted placeholder.
        logger.warning(
            "Cloudinary not configured. Returning placeholder URL for %s", filename
        )
        # Use a deterministic placeholder based on filename for visual variety
        return {
            "url": f"https://placehold.co/640x360?text={filename[:20]}",
            "public_id": f"placeholder/{filename}",
            "resource_type": resource_type,
        }

    result = cloudinary.uploader.upload(
        file_bytes,
        resource_type=resource_type,
        folder=folder,
        public_id=None,
        use_filename=True,
        unique_filename=True,
        overwrite=False,
    )
    return {
        "url": result.get("secure_url"),
        "public_id": result.get("public_id"),
        "resource_type": result.get("resource_type"),
    }
