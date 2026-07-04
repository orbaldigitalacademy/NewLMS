"""Settings routes: bank accounts, payment links, admin email."""
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from database import db
from models.settings import (
    AdminEmailInput,
    BankAccount,
    BankAccountInput,
    BankReorderInput,
    PaymentLink,
    PaymentLinkInput,
    SettingsResponse,
)
from utils.auth import require_admin

router = APIRouter(prefix="/settings", tags=["settings"])

SETTINGS_KEY = {"type": "settings"}


# -------------------- Helpers --------------------
async def _get_or_create_settings() -> dict:
    doc = await db.settings.find_one(SETTINGS_KEY)
    if doc:
        return doc
    now = datetime.now(timezone.utc).isoformat()
    new_doc = {
        "id": str(uuid.uuid4()),
        "type": "settings",
        "banks": [],
        "payment_links": [],
        "admin_email": os.getenv("ADMIN_EMAIL", ""),
        "created_at": now,
        "updated_at": now,
    }
    await db.settings.insert_one(new_doc)
    return new_doc


def _shape(doc: dict) -> SettingsResponse:
    return SettingsResponse(
        bank=[BankAccount(**b) for b in doc.get("bank", [])],
        payment_links=[PaymentLink(**p) for p in doc.get("payment_links", [])],
        admin_email=doc.get("admin_email", ""),
    )


async def _persist(update: dict) -> dict:
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.settings.update_one(SETTINGS_KEY, {"$set": update})
    return await db.settings.find_one(SETTINGS_KEY)


def _bank_payload(payload: BankAccountInput) -> dict:
    return payload.model_dump()


def _link_payload(payload: PaymentLinkInput) -> dict:
    data = payload.model_dump()
    data["url"] = str(data["url"])
    return data


# -------------------- Auth --------------------
@router.post("/auth/verify")
async def verify_admin_token(_: None = Depends(require_admin)):
    return {"ok": True}


# -------------------- Settings --------------------
@router.get("", response_model=SettingsResponse)
async def get_settings():
    doc = await _get_or_create_settings()
    return _shape(doc)


@router.put("/admin-email", response_model=SettingsResponse)
async def update_admin_email(
    payload: AdminEmailInput,
    _: None = Depends(require_admin),
):
    await _get_or_create_settings()
    doc = await _persist({"admin_email": payload.admin_email})
    return _shape(doc)


# ----- Bank accounts -----
@router.put("/bank", response_model=SettingsResponse)
async def add_bank(
    payload: BankAccountInput,
    _: None = Depends(require_admin),
):
    doc = await _get_or_create_settings()
    bank = doc.get("bank", [])
    new_bank = BankAccount(**_bank_payload(payload)).model_dump()
    if not bank:
        new_bank["is_default"] = True
    elif new_bank["is_default"]:
        for b in bank:
            b["is_default"] = False
    bank.append(new_bank)
    updated = await _persist({"bank": bank})
    return _shape(updated)


@router.put("/bank/reorder", response_model=SettingsResponse)
async def reorder_bank(
    payload: BankReorderInput,
    _: None = Depends(require_admin),
):
    doc = await _get_or_create_settings()
    bank = doc.get("bank", [])
    by_id = {b["id"]: b for b in banks}
    if set(payload.ordered_ids) != set(by_id.keys()):
        raise HTTPException(
            status_code=400,
            detail="ordered_ids must contain exactly the existing bank ids",
        )
    reordered = [by_id[i] for i in payload.ordered_ids]
    updated = await _persist({"banks": reordered})
    return _shape(updated)


@router.put("/bank/{bank_id}", response_model=SettingsResponse)
async def update_bank(
    bank_id: str,
    payload: BankAccountInput,
    _: None = Depends(require_admin),
):
    doc = await _get_or_create_settings()
    bank = doc.get("bank", [])
    target = next((b for b in bank if b["id"] == bank_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Bank not found")
    updates = _bank_payload(payload)
    if updates["is_default"]:
        for b in bank:
            b["is_default"] = False
    target.update(updates)
    updated = await _persist({"bank": banks})
    return _shape(updated)


@router.delete("/bank/{bank_id}", response_model=SettingsResponse)
async def delete_bank(
    bank_id: str,
    _: None = Depends(require_admin),
):
    doc = await _get_or_create_settings()
    banks = [b for b in doc.get("bank", []) if b["id"] != bank_id]
    if len(bank) == len(doc.get("bank", [])):
        raise HTTPException(status_code=404, detail="Bank not found")
    if bank and not any(b.get("is_default") for b in bank):
        bank[0]["is_default"] = True
    updated = await _persist({"bank": bank})
    return _shape(updated)


# ----- Payment links -----
@router.post("/payment-links", response_model=SettingsResponse)
async def add_payment_link(
    payload: PaymentLinkInput,
    _: None = Depends(require_admin),
):
    doc = await _get_or_create_settings()
    links = doc.get("payment_links", [])
    new_link = PaymentLink(**_link_payload(payload)).model_dump()
    links.append(new_link)
    updated = await _persist({"payment_links": links})
    return _shape(updated)


@router.put("/payment-links/{link_id}", response_model=SettingsResponse)
async def update_payment_link(
    link_id: str,
    payload: PaymentLinkInput,
    _: None = Depends(require_admin),
):
    doc = await _get_or_create_settings()
    links = doc.get("payment_links", [])
    target = next((item for item in links if item["id"] == link_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Payment link not found")
    target.update(_link_payload(payload))
    updated = await _persist({"payment_links": links})
    return _shape(updated)


@router.delete("/payment-links/{link_id}", response_model=SettingsResponse)
async def delete_payment_link(
    link_id: str,
    _: None = Depends(require_admin),
):
    doc = await _get_or_create_settings()
    links = [item for item in doc.get("payment_links", []) if item["id"] != link_id]
    if len(links) == len(doc.get("payment_links", [])):
        raise HTTPException(status_code=404, detail="Payment link not found")
    updated = await _persist({"payment_links": links})
    return _shape(updated)
