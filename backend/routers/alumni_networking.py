"""ODA Alumni Networking and Mentorship.
Register: app.include_router(router, prefix='/api')
Call create_alumni_networking_indexes() during application startup.
"""
from datetime import datetime, timezone
from uuid import uuid4
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from database import db
from routers.alumni import require_alumni, public_fields

router = APIRouter(prefix='/alumni-networking', tags=['Alumni Networking'])

def now():
    return datetime.now(timezone.utc)

def serialize(doc):
    return {k: (v.isoformat() if isinstance(v, datetime) else v)
            for k, v in doc.items() if k != '_id'}

def uid(profile):
    return str(profile['user_id'])

class MentorRegistration(BaseModel):
    is_available: bool = False
    expertise: list[str] = Field(default_factory=list, max_length=12)
    mentoring_bio: str = Field(default='', max_length=1000)
    max_mentees: int = Field(default=3, ge=1, le=20)

class MentorshipRequest(BaseModel):
    mentor_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=20, max_length=1200)

class Decision(BaseModel):
    status: Literal['accepted', 'declined', 'cancelled']

async def create_alumni_networking_indexes():
    await db.alumni_mentors.create_index('user_id', unique=True)
    await db.alumni_mentors.create_index([('is_available', 1), ('updated_at', -1)])
    await db.alumni_mentorship_requests.create_index('id', unique=True)
    await db.alumni_mentorship_requests.create_index([('mentor_id', 1), ('status', 1)])
    await db.alumni_mentorship_requests.create_index([('mentee_id', 1), ('created_at', -1)])
    await db.alumni_mentorship_requests.create_index(
        [('mentor_id', 1), ('mentee_id', 1)],
        unique=True,
        partialFilterExpression={'status': {'$in': ['pending', 'accepted']}},
        name='one_active_request_per_pair',
    )

@router.get('/discover')
async def discover(q: str = Query(default='', max_length=80), profile=Depends(require_alumni)):
    # Reuse public directory consent and administrative visibility rules.
    query = {'is_verified': True, 'is_public': True, 'hidden_by_admin': {'$ne': True}}
    if q.strip():
        import re
        pattern = re.escape(q.strip())
        query['$or'] = [{field: {'$regex': pattern, '$options': 'i'}}
                        for field in ('full_name', 'professional_title', 'skills')]
    docs = await db.alumni_profiles.find(query).sort('full_name', 1).limit(100).to_list(length=100)
    return {'items': [public_fields(d) for d in docs]}

@router.get('/mentors')
async def mentors(profile=Depends(require_alumni)):
    docs = await db.alumni_mentors.find({'is_available': True}).sort('updated_at', -1).limit(100).to_list(length=100)
    ids = [d['user_id'] for d in docs]
    profiles = await db.alumni_profiles.find({
        'user_id': {'$in': ids}, 'is_verified': True,
        'is_public': True, 'hidden_by_admin': {'$ne': True},
    }).to_list(length=100)
    by_id = {p['user_id']: p for p in profiles}
    items = []
    for d in docs:
        p = by_id.get(d['user_id'])
        if p:
            items.append({**public_fields(p), 'expertise': d.get('expertise', []),
                          'mentoring_bio': d.get('mentoring_bio', ''),
                          'max_mentees': d.get('max_mentees', 3)})
    return {'items': items}

@router.get('/mentor/me')
async def my_mentor_settings(profile=Depends(require_alumni)):
    doc = await db.alumni_mentors.find_one({'user_id': uid(profile)})
    return {'is_available': bool(doc and doc.get('is_available')),
            'expertise': (doc or {}).get('expertise', []),
            'mentoring_bio': (doc or {}).get('mentoring_bio', ''),
            'max_mentees': (doc or {}).get('max_mentees', 3)}

@router.put('/mentor/me')
async def save_mentor_settings(payload: MentorRegistration, profile=Depends(require_alumni)):
    # Publishing a mentor profile requires opting into public alumni directory too.
    if payload.is_available and (not profile.get('is_public') or profile.get('hidden_by_admin')):
        raise HTTPException(400, 'Enable public directory visibility and ensure your profile is not hidden before becoming an available mentor')
    data = payload.model_dump()
    data['expertise'] = list(dict.fromkeys(s.strip()[:80] for s in data['expertise'] if s.strip()))
    data['updated_at'] = now()
    await db.alumni_mentors.update_one({'user_id': uid(profile)},
                                       {'$set': data, '$setOnInsert': {'created_at': now()}}, upsert=True)
    return {'saved': True}

@router.post('/requests', status_code=201)
async def request_mentorship(payload: MentorshipRequest, profile=Depends(require_alumni)):
    mentee_id = uid(profile)
    if payload.mentor_id == mentee_id:
        raise HTTPException(400, 'You cannot request yourself as a mentor')
    mentor = await db.alumni_mentors.find_one({'user_id': payload.mentor_id, 'is_available': True})
    visible = await db.alumni_profiles.find_one({'user_id': payload.mentor_id,
        'is_verified': True, 'is_public': True, 'hidden_by_admin': {'$ne': True}})
    if not mentor or not visible:
        raise HTTPException(404, 'Mentor unavailable')
    active = await db.alumni_mentorship_requests.count_documents({
        'mentor_id': payload.mentor_id, 'status': 'accepted'})
    if active >= mentor.get('max_mentees', 3):
        raise HTTPException(409, 'Mentor is at capacity')
    doc = {'id': str(uuid4()), 'mentor_id': payload.mentor_id, 'mentee_id': mentee_id,
           'message': payload.message.strip(), 'status': 'pending',
           'created_at': now(), 'updated_at': now()}
    try:
        await db.alumni_mentorship_requests.insert_one(doc)
    except Exception as exc:
        from pymongo.errors import DuplicateKeyError
        if isinstance(exc, DuplicateKeyError):
            raise HTTPException(409, 'You already have a pending or accepted request for this mentor') from exc
        raise
    return serialize(doc)

@router.get('/requests/me')
async def my_requests(profile=Depends(require_alumni)):
    me = uid(profile)
    docs = await db.alumni_mentorship_requests.find({'$or': [{'mentor_id': me}, {'mentee_id': me}]}).sort('created_at', -1).limit(200).to_list(length=200)
    return {'items': [serialize(d) for d in docs]}

@router.patch('/requests/{request_id}')
async def decide_request(request_id: str, payload: Decision, profile=Depends(require_alumni)):
    me = uid(profile)
    doc = await db.alumni_mentorship_requests.find_one({'id': request_id})
    if not doc:
        raise HTTPException(404, 'Request not found')
    if payload.status == 'cancelled':
        if doc['mentee_id'] != me or doc['status'] not in ('pending', 'accepted'):
            raise HTTPException(403, 'Only the mentee can cancel an active request')
    else:
        if doc['mentor_id'] != me or doc['status'] != 'pending':
            raise HTTPException(403, 'Only the mentor can decide a pending request')
        if payload.status == 'accepted':
            mentor = await db.alumni_mentors.find_one({'user_id': me, 'is_available': True})
            if not mentor:
                raise HTTPException(409, 'Mentor is unavailable')
            active = await db.alumni_mentorship_requests.count_documents({'mentor_id': me, 'status': 'accepted'})
            if active >= mentor.get('max_mentees', 3):
                raise HTTPException(409, 'Mentor is at capacity')
    result = await db.alumni_mentorship_requests.update_one(
        {'id': request_id, 'status': doc['status']},
        {'$set': {'status': payload.status, 'updated_at': now()}})
    if not result.modified_count:
        raise HTTPException(409, 'Request changed; refresh and try again')
    return {'updated': True, 'status': payload.status}
