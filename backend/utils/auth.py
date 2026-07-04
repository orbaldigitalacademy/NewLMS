"""Authentication guards."""
import os
from typing import Optional

from fastapi import Header, HTTPException


def require_admin(x_admin_token: Optional[str] = Header(default=None)) -> None:
    expected = os.environ.get("ADMIN_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=500, detail="ADMIN_TOKEN not configured")
    if x_admin_token != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing admin token")
