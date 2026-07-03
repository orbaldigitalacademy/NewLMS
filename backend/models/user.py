"""User model + auth request/response schemas."""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from .base import BaseDocument


class UserRole(str, Enum):
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"


class User(BaseDocument):
    email: EmailStr
    name: str
    password_hash: str
    role: UserRole = UserRole.STUDENT
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    blocked: bool = False


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: UserRole
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    blocked: bool = False
    created_at: Optional[str] = None


class UserRegister(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class AdminCreateUser(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=6)
    role: UserRole = UserRole.STUDENT


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
