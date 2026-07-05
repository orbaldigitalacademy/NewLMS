"""Status check routes."""
from datetime import datetime
from typing import List

from fastapi import APIRouter

from database import db
from models.status import StatusCheck, StatusCheckCreate

router = APIRouter(tags=["status"])


@router.get("/")
async def root():
    return {"message": "Hello World"}


@router.post("/status", response_model=StatusCheck)
async def create_status_check(payload: StatusCheckCreate):
    obj = StatusCheck(**payload.model_dump())
    doc = obj.model_dump()
    doc["timestamp"] = doc["timestamp"].isoformat()
    await db.status_checks.insert_one(doc)
    return obj


@router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    for c in checks:
        if isinstance(c["timestamp"], str):
            c["timestamp"] = datetime.fromisoformat(c["timestamp"])
    return checks
