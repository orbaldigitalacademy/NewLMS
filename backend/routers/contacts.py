"""Contacts router."""
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from auth import require_admin
from database import db
from models.payment import Contact, ContactCreate
from models.user import User

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.post("", response_model=Contact, status_code=201)
async def submit_contact(data: ContactCreate):
    contact = Contact(**data.model_dump())
    await db.contacts.insert_one(contact.to_mongo())
    return contact


@router.get("", response_model=List[Contact])
async def list_contacts(_: User = Depends(require_admin)):
    docs = await db.contacts.find().sort("created_at", -1).to_list(500)
    return [Contact.from_mongo(d) for d in docs]


@router.patch("/{contact_id}/read", response_model=Contact)
async def mark_read(contact_id: str, _: User = Depends(require_admin)):
    doc = await db.contacts.find_one({"_id": contact_id})
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    await db.contacts.update_one(
        {"_id": contact_id},
        {"$set": {"is_read": True, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    new_doc = await db.contacts.find_one({"_id": contact_id})
    return Contact.from_mongo(new_doc)


@router.delete("/{contact_id}", status_code=204)
async def delete_contact(contact_id: str, _: User = Depends(require_admin)):
    await db.contacts.delete_one({"_id": contact_id})
    return None
