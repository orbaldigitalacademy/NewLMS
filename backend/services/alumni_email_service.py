# backend/services/alumni_email_service.py

import os
import html
import logging
import httpx

from datetime import datetime, timezone
from database import db

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
ALUMNI_EMAIL_FROM = os.getenv(
    "ALUMNI_EMAIL_FROM",
    "Orbal Digital Academy <alumni@orbalacademy.com>"
)

ALUMNI_DASHBOARD_URL = (
    "https://www.orbalacademy.com/alumni/dashboard"
)


async def send_alumni_welcome_email(user_id: str):

    # Atomically claim a pending email
    profile = await db.alumni_profiles.find_one_and_update(
        {
            "user_id": user_id,
            "welcome_email_status": {"$in": ["pending", "failed"]}
        },
        {
            "$set": {
                "welcome_email_status": "sending",
                "email_attempted_at": datetime.now(
                    timezone.utc
                ).isoformat()
            }
        }
    )

    if not profile:
        return {"status": "already_sent_or_processing"}

    try:
        if not RESEND_API_KEY:
            raise RuntimeError("RESEND_API_KEY is missing")

        user = await db.users.find_one({"_id": user_id})

        if not user or not user.get("email"):
            raise ValueError("Graduate email address not found")

        student_name = html.escape(
            user.get("name")
            or user.get("full_name")
            or "Graduate"
        )

        email_html = f"""
        <html>
          <body style="font-family:Arial,sans-serif;
                       background:#f3f6fa;padding:30px;">
            <div style="max-width:600px;margin:auto;
                        background:white;border-radius:12px;
                        overflow:hidden;">

              <div style="background:#102B5B;
                          color:white;padding:28px;
                          text-align:center;">
                <h2>ORBAL DIGITAL ACADEMY</h2>
                <p>Official Alumni Network</p>
              </div>

              <div style="padding:32px;color:#253047;">
                <h2 style="color:#14532D;">
                  Congratulations, {student_name}!
                </h2>

                <p>
                  We are delighted to officially welcome you
                  to the Orbal Digital Academy Alumni Network.
                </p>

                <p>
                  Having successfully completed your training
                  and passed your final assessment, your Alumni
                  Portal has now been activated.
                </p>

                <p>Your alumni membership provides access to:</p>

                <ul>
                  <li>Professional alumni profile</li>
                  <li>Portfolio and project showcase</li>
                  <li>Career and internship opportunities</li>
                  <li>Professional networking</li>
                  <li>Alumni events and updates</li>
                </ul>

                <div style="text-align:center;margin:32px 0;">
                  <a href="{ALUMNI_DASHBOARD_URL}"
                     style="background:#102B5B;color:white;
                            padding:14px 24px;
                            text-decoration:none;
                            border-radius:6px;">
                    Access Alumni Dashboard
                  </a>
                </div>

                <p>
                  Sign in using your existing LMS credentials.
                </p>

                <p>
                  We are proud of your achievement!
                </p>

                <p>
                  Warm regards,<br>
                  <strong>Orbal Digital Academy Team</strong>
                </p>
              </div>
            </div>
          </body>
        </html>
        """

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": f"alumni-welcome-{user_id}"
                },
                json={
                    "from": ALUMNI_EMAIL_FROM,
                    "to": [user["email"]],
                    "subject": (
                        "Congratulations! Your Orbal Digital "
                        "Academy Alumni Portal Is Activated"
                    ),
                    "html": email_html
                }
            )

            response.raise_for_status()
            result = response.json()

        await db.alumni_profiles.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "welcome_email_status": "sent",
                    "welcome_email_sent_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "welcome_email_id": result.get("id")
                }
            }
        )

        return {"status": "sent"}

    except Exception as exc:
        logger.exception(
            "Alumni welcome email failed for %s",
            user_id
        )

        await db.alumni_profiles.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "welcome_email_status": "failed",
                    "welcome_email_error": str(exc)
                }
            }
        )

        return {"status": "failed"}
