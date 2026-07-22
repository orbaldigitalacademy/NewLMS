"""User model + auth request/response schemas."""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from .base import BaseDocument


class UserRole(str, Enum):
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"


class User(BaseDocument):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    password_hash: str
    role: UserRole = UserRole.STUDENT
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    blocked: bool = False
    
    is_verified: bool = False
    verification_token_hash: Optional[str] = None
    verification_token_expires_at: Optional[datetime] = None
    verification_sent_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: UserRole
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    blocked: bool = False

    is_verified: bool = False
    verified_at: Optional[datetime] = None
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
    
def to_mongo(self) -> dict:
    return self.model_dump(mode="json")

    @classmethod
    def from_mongo(cls, document: dict):
        return cls(**document)
