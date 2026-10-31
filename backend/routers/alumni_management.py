"""Alumni content management. Register with app.include_router(router, prefix='/api').
Authentication: reuse the existing alumni.py get_current_user / require_admin / require_alumni.
"""
from datetime import datetime, timezone
from uuid import uuid4
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from database import db
from routers.alumni import require_admin, require_alumni

router = APIRouter(prefix='/alumni-management', tags=['Alumni Management'])
KINDS = ('opportunities', 'events', 'announcements')
COLLECTIONS = {
    'opportunities': 'alumni_opportunities',
    'events': 'alumni_events',
    'announcements': 'alumni_announcements',
}

def now():
    return datetime.now(timezone.utc)

def col(kind):
    if kind not in COLLECTIONS:
        raise HTTPException(404, 'Unknown content type')
    return db[COLLECTIONS[kind]]

def serialize(doc):
    if not doc:
        return None
    return {k: (v.isoformat() if isinstance(v, datetime) else v)
            for k, v in doc.items() if k != '_id'}

class ContentPayload(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=5, max_length=5000)
    status: Literal['draft', 'published', 'archived'] = 'draft'
    organization: str = Field(default='', max_length=160)
    location: str = Field(default='', max_length=160)
    opportunity_type: Literal['job', 'internship', 'freelance', 'scholarship', 'other'] = 'other'
    external_url: str = Field(default='', max_length=500)
    starts_at: str = Field(default='', max_length=40)
    ends_at: str = Field(default='', max_length=40)
    deadline: str = Field(default='', max_length=40)

    @field_validator('external_url')
    @classmethod
    def validate_url(cls, value):
        if value and not value.startswith(('https://', 'http://')):
            raise ValueError('External URL must begin with https:// or http://')
        return value

    @field_validator('starts_at', 'ends_at', 'deadline')
    @classmethod
    def validate_date(cls, value):
        if value:
            try:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError('Date must be ISO 8601, e.g. 2026-11-01T14:00:00+01:00')
        return value

class VisibilityPayload(BaseModel):
    hidden_by_admin: bool

async def create_alumni_management_indexes():
    for name in COLLECTIONS.values():
        collection = db[name]
        await collection.create_index('id', unique=True)
        await collection.create_index([('status', 1), ('created_at', -1)])
    await db.alumni_profiles.create_index([('is_verified', 1), ('is_public', 1), ('hidden_by_admin', 1)])

@router.get('/admin/{kind}')
async def admin_list(kind: str, _admin=Depends(require_admin)):
    docs = await col(kind).find({}).sort('created_at', -1).limit(200).to_list(length=200)
    return {'items': [serialize(d) for d in docs]}

@router.post('/admin/{kind}', status_code=201)
async def create_content(kind: str, payload: ContentPayload, _admin=Depends(require_admin)):
    doc = payload.model_dump()
    doc.update(id=str(uuid4()), created_at=now(), updated_at=now())
    await col(kind).insert_one(doc)
    return serialize(doc)

@router.put('/admin/{kind}/{item_id}')
async def update_content(kind: str, item_id: str, payload: ContentPayload, _admin=Depends(require_admin)):
    updates = payload.model_dump()
    updates['updated_at'] = now()
    result = await col(kind).update_one({'id': item_id}, {'$set': updates})
    if not result.matched_count:
        raise HTTPException(404, 'Content not found')
    return serialize(await col(kind).find_one({'id': item_id}))

@router.delete('/admin/{kind}/{item_id}')
async def delete_content(kind: str, item_id: str, _admin=Depends(require_admin)):
    result = await col(kind).delete_one({'id': item_id})
    if not result.deleted_count:
        raise HTTPException(404, 'Content not found')
    return {'deleted': True}

@router.get('/feed/{kind}')
async def alumni_feed(kind: str, _alumni=Depends(require_alumni)):
    docs = await col(kind).find({'status': 'published'}).sort('created_at', -1).limit(100).to_list(length=100)
    return {'items': [serialize(d) for d in docs]}

@router.get('/admin/directory/visibility')
async def directory_visibility(_admin=Depends(require_admin)):
    docs = await db.alumni_profiles.find({'is_verified': True}).sort('full_name', 1).limit(500).to_list(length=500)
    return {'items': [{'user_id': p.get('user_id'), 'full_name': p.get('full_name', ''),
                       'is_public': bool(p.get('is_public')), 'hidden_by_admin': bool(p.get('hidden_by_admin'))}
                      for p in docs]}

@router.patch('/admin/directory/{user_id}')
async def set_visibility(user_id: str, payload: VisibilityPayload, _admin=Depends(require_admin)):
    result = await db.alumni_profiles.update_one(
        {'user_id': user_id, 'is_verified': True},
        {'$set': {'hidden_by_admin': payload.hidden_by_admin, 'updated_at': now()}}
    )
    if not result.matched_count:
        raise HTTPException(404, 'Verified alumni not found')
    return {'updated': True, 'hidden_by_admin': payload.hidden_by_admin}
