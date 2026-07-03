"""Auth dependencies - resolve current user from Bearer JWT."""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from database import db
from models.user import User, UserRole
from utils.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing auth token")

    try:
        payload = decode_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token payload")

    doc = await db.users.find_one({"_id": user_id})
    if not doc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    user = User.from_mongo(doc)
    if user.blocked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is blocked")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN.value and user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return user


def require_roles(*allowed_roles):
    """Dependency factory to restrict endpoint to a set of UserRole values."""
    allowed_values = {r.value if isinstance(r, UserRole) else r for r in allowed_roles}

    async def role_checker(user: User = Depends(get_current_user)) -> User:
        role_value = user.role.value if isinstance(user.role, UserRole) else user.role
        if role_value not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user

    return role_checker


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[User]:
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            return None
        doc = await db.users.find_one({"_id": user_id})
        if not doc:
            return None
        user = User.from_mongo(doc)
        return None if user.blocked else user
    except Exception:
        return None
