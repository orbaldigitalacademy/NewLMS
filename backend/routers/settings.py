"""Settings router."""
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from auth import require_admin
from database import db
from models.settings import SettingsResponse, SettingsUpdate
from models.user import User

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/bank", response_model=SettingsResponse)
async def get_bank_settings():
    settings = await db.settings.find_one(
        {"type": "bank"},
        {"_id": 0}
    )

    if not settings:
        return SettingsResponse(
            bank_name=os.getenv("BANK_NAME", ""),
            account_number=os.getenv("ACCOUNT_NUMBER", ""),
            account_name=os.getenv("ACCOUNT_NAME", ""),
            admin_email=os.getenv("ADMIN_EMAIL", ""),
        )

    return SettingsResponse(
        bank_name=settings.get("bank_name", ""),
        account_number=settings.get("account_number", ""),
        account_name=settings.get("account_name", ""),
        admin_email=settings.get("admin_email", ""),
    )


@router.put("/bank", response_model=SettingsResponse)
async def update_bank_settings(
    settings_data: SettingsUpdate,
    _: User = Depends(require_admin),
):
    update_data = {
        key: value
        for key, value in settings_data.model_dump().items()
        if value is not None
    }

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No settings supplied",
        )

    now = datetime.now(timezone.utc).isoformat()

    existing = await db.settings.find_one(
        {"type": "bank"}
    )

    if existing:
        await db.settings.update_one(
            {"type": "bank"},
            {
                "$set": {
                    **update_data,
                    "updated_at": now,
                }
            },
        )
    else:
        await db.settings.insert_one(
            {
                "id": str(uuid.uuid4()),
                "type": "bank",
                **update_data,
                "created_at": now,
                "updated_at": now,
            }
        )

    settings = await db.settings.find_one(
        {"type": "bank"},
        {"_id": 0},
    )

    return SettingsResponse(
        bank_name=settings.get("bank_name", ""),
        account_number=settings.get("account_number", ""),
        account_name=settings.get("account_name", ""),
        admin_email=settings.get("admin_email", ""),
    )