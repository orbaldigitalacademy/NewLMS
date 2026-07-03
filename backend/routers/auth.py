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
    UserRole,
)
from utils.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_public(user: User) -> UserPublic:
    role = user.role.value if isinstance(user.role, UserRole) else user.role
    return UserPublic(
        id=user.id,
        email=user.email,
        name=user.name,
        role=role,
        avatar_url=user.avatar_url,
        bio=user.bio,
        blocked=user.blocked,
        created_at=user.created_at,
    )


def _role_value(user: User) -> str:
    return user.role.value if isinstance(user.role, UserRole) else user.role


@router.post("/register", response_model=AuthResponse)
async def register(data: UserRegister):
    email = data.email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

    user = User(
        email=email,
        name=data.name,
        password_hash=hash_password(data.password),
        role=UserRole.STUDENT,
    )
    await db.users.insert_one(user.to_mongo())
    token = create_access_token({"sub": user.id, "role": _role_value(user)})
    return AuthResponse(access_token=token, user=_to_public(user))


@router.post("/login", response_model=AuthResponse)
async def login(data: UserLogin):
    doc = await db.users.find_one({"email": data.email.lower()})
    if not doc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    user = User.from_mongo(doc)
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    if user.blocked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is blocked")

    token = create_access_token({"sub": user.id, "role": _role_value(user)})
    return AuthResponse(access_token=token, user=_to_public(user))


@router.get("/me", response_model=UserPublic)
async def me(user: User = Depends(get_current_user)):
    return _to_public(user)
