"""Auth router - register, verify email, resend verification, login, me."""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.parse import urlencode

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
    "PASSWORD_RESET_EMAIL_FROM"
)

EMAIL_VERIFICATION_EXPIRE_HOURS = int(
    os.getenv("EMAIL_VERIFICATION_EXPIRE_HOURS", "24")
)

# -------------------------------------------------------------------
# Response models
# -------------------------------------------------------------------

class MessageResponse(BaseModel):
    message: str


class RegisterRequest(UserRegister):
    next: str | None = None


class ResendVerificationRequest(BaseModel):
    email: EmailStr
    next: str | None = None


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
    Hash a verification token before saving it in MongoDB.

    The raw token is sent to the user, but only its hash is stored.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _create_verification_token() -> tuple[str, str, datetime]:
    """
    Generate a secure verification token.

    Returns:
        raw_token:
            Sent to the user's email inside the verification URL.

        hashed_token:
            Stored in MongoDB instead of the raw token.

        expires_at:
            UTC date and time when the verification link expires.
    """
    raw_token = secrets.token_urlsafe(32)
    hashed_token = _hash_verification_token(raw_token)

    expires_at = _utc_now() + timedelta(
        hours=EMAIL_VERIFICATION_EXPIRE_HOURS
    )

    return raw_token, hashed_token, expires_at


def _safe_next_path(next_path: str | None) -> str:
    """Return a safe internal frontend path for post-verification redirect."""
    if not next_path:
        return "/dashboard"

    next_path = next_path.strip()

    # Permit only internal paths such as /courses/course-slug.
    # Reject protocol-relative URLs such as //malicious-site.com.
    if not next_path.startswith("/") or next_path.startswith("//"):
        return "/dashboard"

    return next_path


def _build_verification_url(
    raw_token: str,
    next_path: str | None = None,
) -> str:
    """Build the frontend verification URL with a safe return path."""
    query = urlencode(
        {
            "token": raw_token,
            "next": _safe_next_path(next_path),
        }
    )
    return f"{FRONTEND_URL}/verify-email?{query}"

# -------------------------------------------------------------------
# Email sender
# -------------------------------------------------------------------

def send_verification_email(
    recipient_email: str,
    recipient_name: str,
    verification_url: str,
) -> bool:
    """
    Send an email-verification link using Resend.
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
                <body style="
                    margin: 0;
                    padding: 0;
                    background: #f4f4f4;
                    font-family: Arial, sans-serif;
                ">
                    <table
                        width="100%"
                        cellpadding="0"
                        cellspacing="0"
                    >
                        <tr>
                            <td align="center">
                                <table
                                    width="600"
                                    cellpadding="40"
                                    cellspacing="0"
                                    style="
                                        background: #ffffff;
                                        border-radius: 8px;
                                        margin-top: 30px;
                                    "
                                >
                                    <tr>
                                        <td align="center">
                                            <h1 style="color: #0B5ED7;">
                                                Orbal Digital Academy
                                            </h1>

                                            <h2 style="color: #333333;">
                                                Verify Your Email Address
                                            </h2>

                                            <p style="
                                                font-size: 16px;
                                                color: #555555;
                                            ">
                                                Hello
                                                <strong>
                                                    {recipient_name}
                                                </strong>,
                                            </p>

                                            <p style="
                                                font-size: 16px;
                                                color: #555555;
                                                line-height: 1.6;
                                            ">
                                                Thank you for registering
                                                with Orbal Digital Academy.
                                            </p>

                                            <p style="
                                                font-size: 16px;
                                                color: #555555;
                                                line-height: 1.6;
                                            ">
                                                Click the button below to
                                                verify your email address.
                                            </p>

                                            <p style="margin: 35px 0;">
                                                <a
                                                    href="{verification_url}"
                                                    style="
                                                        background: #0B5ED7;
                                                        color: #ffffff;
                                                        padding: 14px 28px;
                                                        text-decoration: none;
                                                        border-radius: 6px;
                                                        display: inline-block;
                                                        font-weight: bold;
                                                    "
                                                >
                                                    Verify Email
                                                </a>
                                            </p>

                                            <p style="
                                                font-size: 14px;
                                                color: #777777;
                                            ">
                                                If the button does not work,
                                                copy and paste this link into
                                                your browser:
                                            </p>

                                            <p style="word-break: break-all;">
                                                <a href="{verification_url}">
                                                    {verification_url}
                                                </a>
                                            </p>

                                            <hr style="margin: 30px 0;">

                                            <p style="
                                                font-size: 13px;
                                                color: #999999;
                                            ">
                                                If you did not create this
                                                account, you can ignore this
                                                email.
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

Verify your email address using this link:

{verification_url}

If you did not create this account, you can ignore this email.

Orbal Digital Academy
                """,
            }
        )

        logger.info(
            "Verification email sent to %s. Response: %s",
            recipient_email,
            response,
        )

        return True

    except Exception:
        logger.exception(
            "Failed to send verification email to %s",
            recipient_email,
        )
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
    data: RegisterRequest,
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

    verification_url = _build_verification_url(raw_token, data.next)

    background_tasks.add_task(
        send_verification_email,
        user.email,
        user.name,
        verification_url,
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

@router.get("/verify-email")
async def verify_email(token: str):
    token_hash = _hash_verification_token(token)

    user = await db.users.find_one(
        {"verification_token_hash": token_hash}
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification link.",
        )

    result = await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "is_verified": True,
                "verified_at": datetime.now(timezone.utc),
            },
            "$unset": {
                "verification_token_hash": "",
                "verification_token_expires_at": "",
            },
        },
    )

    if result.modified_count == 0 and not user.get("is_verified", False):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification could not be completed.",
        )

    # Create the token only after the database has been updated
    access_token = create_access_token(
        {
            "sub": str(user["_id"]),
            "email": user["email"],
            "role": user.get("role", "student"),
        }
    )

    return {
        "message": "Email verified successfully.",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "name": user.get("name"),
            "role": user.get("role", "student"),
            "is_verified": True,
        },
    }

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

    # Use a generic message so attackers cannot determine whether
    # an email address is registered.
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

        seconds_since_last_email = (
            now - sent_at
        ).total_seconds()

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

    verification_url = _build_verification_url(raw_token, data.next)

    background_tasks.add_task(
        send_verification_email,
        user.email,
        user.name,
        verification_url,
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


# ============================================================
# FORGOT PASSWORD & RESET PASSWORD
# Orbal Digital Academy LMS
# ============================================================

import html
from urllib.parse import quote

RESET_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("RESET_TOKEN_EXPIRE_MINUTES", "30")
)

RESET_REQUEST_COOLDOWN_SECONDS = 60


# ------------------------------------------------------------
# Request models
# ------------------------------------------------------------

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# ------------------------------------------------------------
# Generate secure password reset token
# ------------------------------------------------------------

def _create_password_reset_token():
    raw_token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    expires_at = _utc_now() + timedelta(
        minutes=RESET_TOKEN_EXPIRE_MINUTES
    )

    return raw_token, token_hash, expires_at


# ------------------------------------------------------------
# Send password reset email using Resend
# ------------------------------------------------------------

def send_password_reset_email(
    recipient_email: str,
    recipient_name: str,
    reset_url: str,
) -> bool:

    try:
        safe_name = html.escape(recipient_name)

        email_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport"
                  content="width=device-width, initial-scale=1">
        </head>

        <body style="
            margin:0;
            padding:0;
            background:#f4f6fa;
            font-family:Arial,Helvetica,sans-serif;
            color:#17253e;
        ">

        <table role="presentation"
               width="100%"
               cellpadding="0"
               cellspacing="0">

            <tr>
                <td align="center" style="padding:30px 12px;">

                    <table role="presentation"
                           width="100%"
                           cellpadding="0"
                           cellspacing="0"
                           style="
                               max-width:600px;
                               background:#ffffff;
                               border-radius:12px;
                               overflow:hidden;
                           ">

                        <tr>
                            <td style="
                                background:#17315c;
                                padding:30px;
                                text-align:center;
                            ">

                                <h1 style="
                                    color:#ffffff;
                                    margin:0;
                                    font-size:25px;
                                ">
                                    ORBAL DIGITAL ACADEMY
                                </h1>

                                <p style="
                                    color:#dce7fa;
                                    font-size:14px;
                                ">
                                    Learning Management System
                                </p>

                            </td>
                        </tr>

                        <tr>
                            <td style="padding:35px 30px;">

                                <h2 style="
                                    color:#17315c;
                                    margin-top:0;
                                ">
                                    Reset Your Password
                                </h2>

                                <p>Hello <strong>{safe_name}</strong>,</p>

                                <p style="line-height:1.7;">
                                    We received a request to reset
                                    the password associated with
                                    your Orbal Digital Academy account.
                                </p>

                                <p style="line-height:1.7;">
                                    Click the button below to
                                    create a new password.
                                </p>

                                <div style="
                                    text-align:center;
                                    margin:35px 0;
                                ">

                                    <a href="{reset_url}"
                                       style="
                                           background:#0B5ED7;
                                           color:#ffffff;
                                           padding:15px 30px;
                                           border-radius:7px;
                                           text-decoration:none;
                                           font-weight:bold;
                                           display:inline-block;
                                       ">
                                        Reset My Password
                                    </a>

                                </div>

                                <p style="
                                    font-size:14px;
                                    color:#666666;
                                ">
                                    This password reset link will
                                    expire in
                                    {RESET_TOKEN_EXPIRE_MINUTES}
                                    minutes.
                                </p>

                                <p style="
                                    font-size:14px;
                                    color:#666666;
                                ">
                                    If you did not request a
                                    password reset, you can
                                    safely ignore this email.
                                </p>

                                <hr style="
                                    border:0;
                                    border-top:1px solid #eeeeee;
                                    margin:30px 0;
                                ">

                                <p style="
                                    font-size:12px;
                                    color:#888888;
                                ">
                                    For assistance, contact
                                    Orbal Digital Academy support.
                                </p>

                            </td>
                        </tr>

                        <tr>
                            <td style="
                                background:#f1f4f8;
                                text-align:center;
                                padding:20px;
                                font-size:12px;
                                color:#777777;
                            ">
                                © Orbal Digital Academy.
                                All rights reserved.
                            </td>
                        </tr>

                    </table>

                </td>
            </tr>

        </table>

        </body>
        </html>
        """

        response = resend.Emails.send({
            "from": EMAIL_FROM,
            "to": [recipient_email],
            "subject": (
                "Reset Your Password | "
                "Orbal Digital Academy"
            ),
            "html": email_html,
            "text": (
                f"Hello {recipient_name},\n\n"
                "We received a request to reset your password.\n\n"
                f"Reset your password here:\n{reset_url}\n\n"
                f"This link expires in "
                f"{RESET_TOKEN_EXPIRE_MINUTES} minutes.\n\n"
                "If you did not request this, ignore this email.\n\n"
                "Orbal Digital Academy"
            ),
        })

        logger.info(
            "Password reset email accepted by Resend for %s",
            recipient_email
        )

        return True

    except Exception:
        logger.exception(
            "Failed to send password reset email to %s",
            recipient_email
        )
        return False


# ------------------------------------------------------------
# FORGOT PASSWORD ENDPOINT
# ------------------------------------------------------------

@router.post(
    "/forgot-password",
    response_model=MessageResponse
)
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
):

    email = data.email.strip().lower()

    generic_message = (
        "If an account exists with this email address, "
        "a password reset link will be sent."
    )

    document = await db.users.find_one({
        "email": email
    })

    # Do not disclose whether the account exists.
    if not document:
        return MessageResponse(message=generic_message)

    now = _utc_now()

    last_sent = document.get("password_reset_sent_at")

    if last_sent:
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(
                tzinfo=timezone.utc
            )

        seconds_elapsed = (
            now - last_sent
        ).total_seconds()

        if seconds_elapsed < RESET_REQUEST_COOLDOWN_SECONDS:
            return MessageResponse(message=generic_message)

    raw_token, token_hash, expires_at = (
        _create_password_reset_token()
    )

    # Atomic cooldown check: only one concurrent request
    # can claim the reset window for this user.
    cutoff = now - timedelta(
        seconds=RESET_REQUEST_COOLDOWN_SECONDS
    )

    result = await db.users.update_one(
        {
            "_id": document["_id"],
            "$or": [
                {"password_reset_sent_at": {"$exists": False}},
                {"password_reset_sent_at": {"$lte": cutoff}}
            ]
        },
        {
            "$set": {
                "password_reset_token_hash": token_hash,
                "password_reset_expires_at": expires_at,
                "password_reset_sent_at": now
            }
        }
    )

    if result.modified_count == 0:
        return MessageResponse(message=generic_message)

    reset_url = (
        f"{FRONTEND_URL}/reset-password"
        f"?token={quote(raw_token, safe='')}"
    )

    background_tasks.add_task(
        send_password_reset_email,
        email,
        document.get("name", "Student"),
        reset_url
    )

    return MessageResponse(message=generic_message)


# ------------------------------------------------------------
# RESET PASSWORD ENDPOINT
# ------------------------------------------------------------

@router.post(
    "/reset-password",
    response_model=MessageResponse
)
async def reset_password(data: ResetPasswordRequest):

    if len(data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least 8 characters."
        )

    if len(data.new_password) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must not exceed 128 characters."
        )

    if not data.token or len(data.token) > 256:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset link."
        )

    token_hash = hashlib.sha256(
        data.token.encode("utf-8")
    ).hexdigest()

    now = _utc_now()

    # Hash password before consuming the token.
    new_password_hash = hash_password(
        data.new_password
    )

    # Atomically verify expiry and consume the token.
    # This prevents two requests from using one token.
    result = await db.users.update_one(
        {
            "password_reset_token_hash": token_hash,
            "password_reset_expires_at": {
                "$gt": now
            }
        },
        {
            "$set": {
                "password_hash": new_password_hash,
                "password_changed_at": now
            },
            "$unset": {
                "password_reset_token_hash": "",
                "password_reset_expires_at": "",
                "password_reset_sent_at": ""
            }
        }
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid or expired password reset link. "
                "Please request a new one."
            )
        )

    return MessageResponse(
        message=(
            "Your password has been reset successfully. "
            "You can now log in with your new password."
        )
    )
