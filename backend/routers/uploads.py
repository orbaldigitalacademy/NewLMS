"""File upload router. Sends files to Cloudinary."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from auth import require_admin
from models.user import User
from services.cloudinary_service import upload_file

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("")
async def upload(
    file: UploadFile = File(...),
    resource_type: str = "auto",
    _: User = Depends(require_admin),
):
    contents = await file.read()
    if not contents:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    result = upload_file(
        file_bytes=contents,
        filename=file.filename or "upload",
        resource_type=resource_type,
    )
    return result
