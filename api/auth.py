"""
Authentication, Password Hashing, and JWT Dependency Management.
"""
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import bcrypt
import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader

from database.connection import get_connection
from .config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES


bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    raw_api_key: Optional[str] = Security(api_key_header)
) -> Dict[str, Any]:
    """
    Validates either a Bearer JWT or an X-API-Key header.
    Returns user context: {"user_id": ..., "org_id": ..., "role": ..., "email": ...}
    Raises 401 on missing or invalid credentials.
    """
    # 1. Check API Key Header if present
    if raw_api_key:
        key_hash = hashlib.sha256(raw_api_key.strip().encode("utf-8")).hexdigest()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, org_id, user_id, name
                    FROM api_keys
                    WHERE key_hash = %s
                    """,
                    (key_hash,)
                )
                key_row = cur.fetchone()
                if key_row:
                    return {
                        "user_id": key_row["user_id"] or "api_key_user",
                        "org_id": key_row["org_id"],
                        "role": "api_key",
                        "auth_method": "api_key"
                    }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key"
        )

    # 2. Check Bearer JWT
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        org_id = payload.get("org_id")
        if not user_id or not org_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        user_role = (payload.get("role") or "viewer").lower()
        return {
            "user_id": user_id,
            "org_id": org_id,
            "role": user_role,
            "email": payload.get("email", ""),
            "auth_method": "jwt"
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


def require_role(allowed_roles: list[str]):
    """
    Enforces server-side Role-Based Access Control (RBAC).
    Allowed roles are typically: ['admin'], ['editor', 'admin'], or ['viewer', 'editor', 'admin'].
    Raises 403 Forbidden if current_user's role is not authorized.
    """
    def dependency(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = (current_user.get("role") or "viewer").lower()
        allowed = [r.lower() for r in allowed_roles]
        if user_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: {', '.join(allowed_roles)}; your role: {user_role}"
            )
        return current_user
    return dependency


require_admin = require_role(["admin"])
require_editor_or_admin = require_role(["editor", "admin"])

