import os
import resend

resend.api_key = os.getenv("RESEND_API_KEY")

EMAIL_FROM = os.getenv(
    "EMAIL_FROM",
    "Orbal Digital Academy <noreply@orbalacademy.com>"
)


def send_verification_email(
    recipient_email: str,
    recipient_name: str,
    verification_url: str,
):
    resend.Emails.send(
        {
            "from": EMAIL_FROM,
            "to": recipient_email,
            "subject": "Verify your Email Address",
            "html": f"""
            <h2>Hello {recipient_name},</h2>

            <p>
            Thank you for registering with
            <b>Orbal Digital Academy</b>.
            </p>

            <p>
            Click the button below to verify your email.
            </p>

            <p>
                <a href="{verification_url}"
                   style="
                        background:#0d6efd;
                        color:white;
                        padding:12px 20px;
                        text-decoration:none;
                        border-radius:6px;
                   ">
                    Verify Email
                </a>
            </p>

            <p>
            If you didn't register, simply ignore this email.
            </p>
            """,
        }
    )
