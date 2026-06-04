from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, Field
from .base import BaseDocument


RoleType = Literal["student", "admin"]


class User(BaseDocument):
    email: EmailStr
    name: str
    password_hash: str
    role: RoleType = "student"
    avatar_url: Optional[str] = None
    bio: Optional[str] = None


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: RoleType
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    created_at: Optional[str] = None


class UserRegister(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
