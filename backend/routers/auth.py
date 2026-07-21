"""Auth router - register, verify email, resend verification, login, me."""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

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

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

EMAIL_FROM = os.getenv(
    "EMAIL_FROM",
    SMTP_USERNAME or "no-reply@orbalacademy.com",
)

EMAIL_FROM_NAME = os.getenv(
    "EMAIL_FROM_NAME",
    "Orbal Digital Academy",
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


def _create_verification_token() -> tuple[str, str, datetime]:
    """
    Return:
        raw_token
        hashed_token
        expiry_datetime
    """

    raw_token = secrets.token_urlsafe(48)
    hashed_token = _hash_verification_token(raw_token)

    expires_at = _utc_now() + timedelta(
        hours=EMAIL_VERIFICATION_EXPIRE_HOURS
    )

    return raw_token, hashed_token, expires_at


def _build_verification_url(raw_token: str) -> str:
    return (
        f"{FRONTEND_URL}/verify-email"
        f"?token={raw_token}"
    )


def send_verification_email(
    recipient_email: str,
    recipient_name: str,
    raw_token: str,
) -> None:
    """
    Send the verification email.

    This function runs as a FastAPI background task after registration.
    """

    if not SMTP_HOST:
        logger.error(
            "Verification email was not sent because SMTP_HOST is missing."
        )
        return

    verification_url = _build_verification_url(raw_token)

    message = EmailMessage()

    message["Subject"] = "Verify your Orbal Digital Academy account"
    message["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
    message["To"] = recipient_email

    text_content = f"""
Hello {recipient_name},

Thank you for registering with Orbal Digital Academy.

Please verify your email address by opening the link below:

{verification_url}

This verification link will expire in {EMAIL_VERIFICATION_EXPIRE_HOURS} hours.

If you did not create this account, you can safely ignore this email.

Orbal Digital Academy
""".strip()

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >
</head>

<body
    style="
        margin: 0;
        padding: 0;
        background-color: #f3f4f6;
        font-family: Arial, Helvetica, sans-serif;
    "
>
    <div style="padding: 32px 16px;">
        <div
            style="
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 16px rgba(0,0,0,0.08);
            "
        >
            <div
                style="
                    background-color: #153e2e;
                    color: #ffffff;
                    padding: 24px;
                    text-align: center;
                "
            >
                <h1 style="margin: 0; font-size: 24px;">
                    Orbal Digital Academy
                </h1>
            </div>

            <div style="padding: 32px;">
                <h2 style="color: #111827;">
                    Verify your email address
                </h2>

                <p style="color: #4b5563; line-height: 1.7;">
                    Hello {recipient_name},
                </p>

                <p style="color: #4b5563; line-height: 1.7;">
                    Thank you for registering with Orbal Digital Academy.
                    Click the button below to verify your email address.
                </p>

                <div style="text-align: center; margin: 32px 0;">
                    <a
                        href="{verification_url}"
                        style="
                            display: inline-block;
                            background-color: #d4a017;
                            color: #ffffff;
                            text-decoration: none;
                            padding: 14px 28px;
                            border-radius: 8px;
                            font-weight: bold;
                        "
                    >
                        Verify Email Address
                    </a>
                </div>

                <p style="color: #4b5563; line-height: 1.7;">
                    This link will expire in
                    {EMAIL_VERIFICATION_EXPIRE_HOURS} hours.
                </p>

                <p style="color: #6b7280; font-size: 14px;">
                    If the button does not work, copy and paste this link
                    into your browser:
                </p>

                <p
                    style="
                        color: #2563eb;
                        font-size: 13px;
                        word-break: break-all;
                    "
                >
                    {verification_url}
                </p>

                <p style="color: #6b7280; font-size: 14px;">
                    If you did not create this account, you can safely
                    ignore this email.
                </p>
            </div>
        </div>
    </div>
</body>
</html>
""".strip()

    message.set_content(text_content)
    message.add_alternative(html_content, subtype="html")

    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(
                SMTP_HOST,
                SMTP_PORT,
                timeout=30,
            ) as smtp:
                if SMTP_USERNAME and SMTP_PASSWORD:
                    smtp.login(SMTP_USERNAME, SMTP_PASSWORD)

                smtp.send_message(message)

        else:
            with smtplib.SMTP(
                SMTP_HOST,
                SMTP_PORT,
                timeout=30,
            ) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()

                if SMTP_USERNAME and SMTP_PASSWORD:
                    smtp.login(SMTP_USERNAME, SMTP_PASSWORD)

                smtp.send_message(message)

        logger.info(
            "Verification email sent successfully to %s",
            recipient_email,
        )

    except Exception:
        logger.exception(
            "Failed to send verification email to %s",
            recipient_email,
        )


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
