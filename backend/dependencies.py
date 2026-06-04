"""Common dependencies shared by routers."""
from auth import get_current_user, require_admin, get_optional_user  # noqa: F401
from database import db  # noqa: F401
