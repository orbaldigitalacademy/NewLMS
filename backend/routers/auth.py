"""Auth router - register, verify email, resend verification, login, me."""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import resend


from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    status,
)
from pydantic import BaseModel, EmailStr

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

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:3000",
).rstrip("/")

resend.api_key = os.getenv("RESEND_API_KEY")
EMAIL_FROM = os.getenv(
    "EMAIL_FROM",
    "Orbal Digital Academy <noreply@orbalacademy.com>"
)

EMAIL_VERIFICATION_EXPIRE_HOURS = int(
    os.getenv("EMAIL_VERIFICATION_EXPIRE_HOURS", "24")
)

# -------------------------------------------------------------------
# Response models
# -------------------------------------------------------------------

class MessageResponse(BaseModel):
    message: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
        is_verified=user.is_verified,
        verified_at=user.verified_at,
        created_at=user.created_at,
    )


def _role_value(user: User) -> str:
    return user.role.value if isinstance(user.role, UserRole) else user.role


def _hash_verification_token(token: str) -> str:
    """
    Hash the verification token before saving it in MongoDB.

    The raw token is sent to the user, but only its hash is stored.
    """

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# Configure Resend
resend.api_key = os.getenv("RESEND_API_KEY")

# Sender email (must be verified in Resend)
EMAIL_FROM = os.getenv(
    "EMAIL_FROM",
    "Orbal Digital Academy <noreply@yourdomain.com>"
)


def send_verification_email(
    recipient_email: str,
    recipient_name: str,
    verification_url: str,
) -> bool:
    """
    Sends an email verification message to a newly registered user.

    Args:
        recipient_email: User's email address.
        recipient_name: User's full name.
        verification_url: Email verification link.

    Returns:
        True if successful, False otherwise.
    """

    try:
        response = resend.Emails.send(
            {
                "from": EMAIL_FROM,
                "to": [recipient_email],
                "subject": "Verify Your Email Address",
                "html": f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Email Verification</title>
                </head>
                <body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                            <td align="center">

                                <table width="600" cellpadding="40" cellspacing="0"
                                    style="background:#ffffff;border-radius:8px;margin-top:30px;">

                                    <tr>
                                        <td align="center">

                                            <h1 style="color:#0B5ED7;">
                                                Orbal Digital Academy
                                            </h1>

                                            <h2 style="color:#333;">
                                                Verify Your Email Address
                                            </h2>

                                            <p style="font-size:16px;color:#555;">
                                                Hello <strong>{recipient_name}</strong>,
                                            </p>

                                            <p style="font-size:16px;color:#555;line-height:1.6;">
                                                Thank you for registering with
                                                <strong>Orbal Digital Academy</strong>.
                                            </p>

                                            <p style="font-size:16px;color:#555;line-height:1.6;">
                                                Please verify your email address by clicking
                                                the button below.
                                            </p>

                                            <p style="margin:35px 0;">
                                                <a href="{verification_url}"
                                                    style="
                                                        background:#0B5ED7;
                                                        color:#ffffff;
                                                        padding:14px 28px;
                                                        text-decoration:none;
                                                        border-radius:6px;
                                                        display:inline-block;
                                                        font-weight:bold;
                                                    ">
                                                    Verify Email
                                                </a>
                                            </p>

                                            <p style="font-size:14px;color:#777;">
                                                If the button doesn't work,
                                                copy and paste the following link into your browser:
                                            </p>

                                            <p style="word-break:break-all;">
                                                <a href="{verification_url}">
                                                    {verification_url}
                                                </a>
                                            </p>

                                            <hr style="margin:30px 0;">

                                            <p style="font-size:13px;color:#999;">
                                                If you did not create an account,
                                                you can safely ignore this email.
                                            </p>

                                            <p style="font-size:13px;color:#999;">
                                                &copy; {__import__("datetime").datetime.now().year}
                                                Orbal Digital Academy. All rights reserved.
                                            </p>

                                        </td>
                                    </tr>

                                </table>

                            </td>
                        </tr>
                    </table>
                </body>
                </html>
                """,
                "text": f"""
Hello {recipient_name},

Thank you for registering with Orbal Digital Academy.

Please verify your email by visiting the link below:

{verification_url}

If you did not create this account, you can ignore this email.

Orbal Digital Academy
""",
            }
        )

        print("Verification email sent successfully.")
        print(response)

        return True

    except Exception as e:
        print(f"Failed to send verification email: {e}")
        return False

# -------------------------------------------------------------------
# Register
# -------------------------------------------------------------------

@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: UserRegister,
    background_tasks: BackgroundTasks,
):
    email = data.email.strip().lower()
    name = data.name.strip()

    existing = await db.users.find_one({"email": email})

    if existing:
        existing_user = User.from_mongo(existing)

        if existing_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "An account with this email already exists but has not "
                "been verified. Please resend the verification email."
            ),
        )

    raw_token, hashed_token, expires_at = (
        _create_verification_token()
    )

    user = User(
        email=email,
        name=name,
        password_hash=hash_password(data.password),
        role=UserRole.STUDENT,
        is_verified=False,
        verification_token_hash=hashed_token,
        verification_token_expires_at=expires_at,
        verification_sent_at=_utc_now(),
        verified_at=None,
    )

    await db.users.insert_one(user.to_mongo())

    background_tasks.add_task(
        send_verification_email,
        user.email,
        user.name,
        raw_token,
    )

    return MessageResponse(
        message=(
            "Registration successful. A verification link has been sent "
            "to your email address. Please verify your email before "
            "logging in."
        )
    )


# -------------------------------------------------------------------
# Verify email
# -------------------------------------------------------------------

@router.get(
    "/verify-email",
    response_model=MessageResponse,
)
async def verify_email(
    token: str = Query(
        ...,
        min_length=20,
        description="Email verification token",
    ),
):
    hashed_token = _hash_verification_token(token)
    now = _utc_now()

    document = await db.users.find_one(
        {
            "verification_token_hash": hashed_token,
            "is_verified": False,
        }
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used verification link",
        )

    user = User.from_mongo(document)

    if not user.verification_token_expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification link",
        )

    expires_at = user.verification_token_expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "This verification link has expired. Please request "
                "a new verification email."
            ),
        )

    result = await db.users.update_one(
        {
            "id": user.id,
            "verification_token_hash": hashed_token,
            "is_verified": False,
        },
        {
            "$set": {
                "is_verified": True,
                "verified_at": now,
            },
            "$unset": {
                "verification_token_hash": "",
                "verification_token_expires_at": "",
            },
        },
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification link could not be processed",
        )

    return MessageResponse(
        message=(
            "Your email address has been verified successfully. "
            "You can now log in."
        )
    )


# -------------------------------------------------------------------
# Resend verification email
# -------------------------------------------------------------------

@router.post(
    "/resend-verification",
    response_model=MessageResponse,
)
async def resend_verification(
    data: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
):
    email = data.email.strip().lower()

    document = await db.users.find_one({"email": email})

    # Return a generic response so attackers cannot easily discover
    # whether a particular email is registered.
    generic_message = (
        "If an unverified account exists for this email address, "
        "a new verification link has been sent."
    )

    if not document:
        return MessageResponse(message=generic_message)

    user = User.from_mongo(document)

    if user.is_verified:
        return MessageResponse(message=generic_message)

    now = _utc_now()

    # Prevent repeated requests within 60 seconds.
    if user.verification_sent_at:
        sent_at = user.verification_sent_at

        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)

        seconds_since_last_email = (now - sent_at).total_seconds()

        if seconds_since_last_email < 60:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "Please wait before requesting another "
                    "verification email."
                ),
            )

    raw_token, hashed_token, expires_at = (
        _create_verification_token()
    )

    await db.users.update_one(
        {"id": user.id},
        {
            "$set": {
                "verification_token_hash": hashed_token,
                "verification_token_expires_at": expires_at,
                "verification_sent_at": now,
            }
        },
    )

    background_tasks.add_task(
        send_verification_email,
        user.email,
        user.name,
        raw_token,
    )

    return MessageResponse(message=generic_message)


# -------------------------------------------------------------------
# Login
# -------------------------------------------------------------------

@router.post(
    "/login",
    response_model=AuthResponse,
)
async def login(data: UserLogin):
    email = data.email.strip().lower()

    document = await db.users.find_one({"email": email})

    if not document:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user = User.from_mongo(document)

    if not verify_password(
        data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user.blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been blocked",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Your email address has not been verified. "
                "Please check your email or request a new "
                "verification link."
            ),
        )

    token = create_access_token(
        {
            "sub": user.id,
            "role": _role_value(user),
        }
    )

    return AuthResponse(
        access_token=token,
        user=_to_public(user),
    )


# -------------------------------------------------------------------
# Current user
# -------------------------------------------------------------------

@router.get(
    "/me",
    response_model=UserPublic,
)
async def me(
    user: User = Depends(get_current_user),
):
    return _to_public(user)
