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
