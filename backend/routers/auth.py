"""Auth router - register, login, me."""
from fastapi import APIRouter, Depends, HTTPException, status

from auth import get_current_user
from database import db
from models.user import (
    AuthResponse,
    User,
    UserLogin,
    UserPublic,
    UserRegister,
)
from utils.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_public(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        avatar_url=user.avatar_url,
        bio=user.bio,
        created_at=user.created_at,
    )


@router.post("/register", response_model=AuthResponse)
async def register(data: UserRegister):
    existing = await db.users.find_one({"email": data.email.lower()})
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

    user = User(
        email=data.email.lower(),
        name=data.name,
        password_hash=hash_password(data.password),
        role="student",
    )
    await db.users.insert_one(user.to_mongo())
    token = create_access_token({"sub": user.id, "role": user.role})
    return AuthResponse(access_token=token, user=_to_public(user))


@router.post("/login", response_model=AuthResponse)
async def login(data: UserLogin):
    doc = await db.users.find_one({"email": data.email.lower()})
    if not doc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    user = User.from_mongo(doc)
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    token = create_access_token({"sub": user.id, "role": user.role})
    return AuthResponse(access_token=token, user=_to_public(user))


@router.get("/me", response_model=UserPublic)
async def me(user: User = Depends(get_current_user)):
    return _to_public(user)
