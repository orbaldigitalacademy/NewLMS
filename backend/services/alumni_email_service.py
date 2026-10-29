"""Resend API transport. Acceptance by Resend is not inbox delivery."""
import html
import os
import httpx

DASHBOARD_URL = os.getenv("ALUMNI_DASHBOARD_URL", "https://www.orbalacademy.com/alumni/dashboard")


async def send_welcome_email(job: dict) -> str:
    api_key = os.getenv("RESEND_API_KEY")
    sender = os.getenv("ALUMNI_EMAIL_FROM")
    if not api_key or not sender:
        raise RuntimeError("RESEND_API_KEY and ALUMNI_EMAIL_FROM are required")
    name = html.escape(job.get("recipient_name") or "Graduate")
    url = html.escape(DASHBOARD_URL, quote=True)
    body = f"""<!doctype html><html><body style="margin:0;background:#f2f5fa;font-family:Arial,sans-serif;color:#253047">
    <div style="max-width:620px;margin:28px auto;background:white;border-radius:12px;overflow:hidden">
    <div style="background:#102B5B;color:white;padding:28px;text-align:center"><h2>ORBAL DIGITAL ACADEMY</h2><p>Alumni Network</p></div>
    <div style="padding:30px"><h2 style="color:#14532D">Congratulations, {name}!</h2>
    <p>You have completed your course requirements and passed your final assessment. Your Alumni Portal is now active.</p>
    <p>Build your professional profile, showcase your portfolio, and explore alumni career opportunities.</p>
    <p style="text-align:center;margin:30px 0"><a href="{url}" style="background:#102B5B;color:white;padding:14px 22px;border-radius:6px;text-decoration:none">Open Alumni Dashboard</a></p>
    <p>Sign in using your existing LMS credentials.</p><p>Warm regards,<br><b>Orbal Digital Academy Team</b></p></div></div></body></html>"""
    async with httpx.AsyncClient(timeout=25) as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
                     "Idempotency-Key": job["idempotency_key"]},
            json={"from": sender, "to": [job["recipient_email"]],
                  "subject": "Welcome to the Orbal Digital Academy Alumni Network!", "html": body}
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("id"):
            raise RuntimeError("Resend did not return a message ID")
        return payload["id"]
