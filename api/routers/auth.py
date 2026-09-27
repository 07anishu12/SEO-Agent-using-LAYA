"""
Authentication Router: Registration, Login, and API Key Management.
"""
import hashlib
import secrets
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status

from typing import List
from database.connection import get_connection
from ..auth import hash_password, verify_password, create_access_token, get_current_user, require_admin, require_editor_or_admin
from ..schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    UserCreateRequest,
    UserRoleUpdateRequest,
    AuthResponse,
    UserInfo,
    ApiKeyCreateRequest,
    ApiKeyResponse
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register_user(req: UserRegisterRequest):
    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A valid email is required")
    if len(req.password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 6 characters")

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Check existing email
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

            # Determine Org
            org_id = None
            if req.org_slug:
                cur.execute("SELECT id FROM orgs WHERE slug = %s", (req.org_slug.strip().lower(),))
                org_row = cur.fetchone()
                if org_row:
                    org_id = org_row["id"]

            if not org_id:
                org_id = f"org_{uuid4().hex[:12]}"
                slug = (req.org_slug or f"org-{uuid4().hex[:8]}").strip().lower()
                name = req.org_name or f"Organization {email.split('@')[0]}"
                cur.execute(
                    """
                    INSERT INTO orgs (id, name, slug)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (org_id, name, slug)
                )

            # Create User
            user_id = f"user_{uuid4().hex[:12]}"
            pw_hash = hash_password(req.password)
            cur.execute(
                """
                INSERT INTO users (id, org_id, email, password_hash, role)
                VALUES (%s, %s, %s, %s, 'admin')
                """,
                (user_id, org_id, email, pw_hash)
            )
        conn.commit()

    token = create_access_token({
        "sub": user_id,
        "org_id": org_id,
        "role": "admin",
        "email": email
    })

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserInfo(id=user_id, email=email, org_id=org_id, role="admin")
    )


@router.post("/login", response_model=AuthResponse)
def login_user(req: UserLoginRequest):
    email = req.email.strip().lower()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, org_id, email, password_hash, role FROM users WHERE email = %s",
                (email,)
            )
            user = cur.fetchone()

    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = create_access_token({
        "sub": user["id"],
        "org_id": user["org_id"],
        "role": user["role"],
        "email": user["email"]
    })

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserInfo(
            id=user["id"],
            email=user["email"],
            org_id=user["org_id"],
            role=user["role"]
        )
    )


@router.post("/api-keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    req: ApiKeyCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    key_id = f"key_{uuid4().hex[:12]}"
    raw_key = f"sjev_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    org_id = current_user["org_id"]
    user_id = current_user["user_id"] if current_user.get("user_id") != "api_key_user" else None

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO api_keys (id, org_id, user_id, key_hash, name)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (key_id, org_id, user_id, key_hash, req.name.strip())
            )
        conn.commit()

    return ApiKeyResponse(
        id=key_id,
        name=req.name.strip(),
        api_key=raw_key,
        created_at=datetime.now(timezone.utc)
    )


@router.get("/users", response_model=List[UserInfo])
def list_org_users(current_user: dict = Depends(get_current_user)):
    """List all users belonging to the current user's organization."""
    org_id = current_user["org_id"]
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, org_id, role FROM users WHERE org_id = %s ORDER BY created_at ASC",
                (org_id,)
            )
            rows = cur.fetchall()
    return [UserInfo(id=r["id"], email=r["email"], org_id=r["org_id"], role=r["role"]) for r in rows]


@router.post("/users", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
def create_org_user(
    req: UserCreateRequest,
    current_user: dict = Depends(require_admin)
):
    """Admin-only: Create or invite a new user with a specific role (viewer, editor, admin) in this org."""
    org_id = current_user["org_id"]
    role = req.role.strip().lower()
    if role not in ("viewer", "editor", "admin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be one of: viewer, editor, admin"
        )
    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A valid email is required")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

            user_id = f"user_{uuid4().hex[:12]}"
            pw_hash = hash_password(req.password)
            cur.execute(
                """
                INSERT INTO users (id, org_id, email, password_hash, role)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, org_id, email, pw_hash, role)
            )
        conn.commit()

    return UserInfo(id=user_id, email=email, org_id=org_id, role=role)


@router.patch("/users/{user_id}/role", response_model=UserInfo)
def update_user_role(
    user_id: str,
    req: UserRoleUpdateRequest,
    current_user: dict = Depends(require_admin)
):
    """Admin-only: Update a user's role within the organization."""
    org_id = current_user["org_id"]
    role = req.role.strip().lower()
    if role not in ("viewer", "editor", "admin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be one of: viewer, editor, admin"
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, org_id, role FROM users WHERE id = %s AND org_id = %s",
                (user_id, org_id)
            )
            user = cur.fetchone()
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

            cur.execute(
                "UPDATE users SET role = %s WHERE id = %s AND org_id = %s",
                (role, user_id, org_id)
            )
        conn.commit()

    return UserInfo(id=user_id, email=user["email"], org_id=org_id, role=role)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    current_user: dict = Depends(require_admin)
):
    """Admin-only: Delete a user from the organization."""
    org_id = current_user["org_id"]
    if current_user["user_id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM users WHERE id = %s AND org_id = %s",
                (user_id, org_id)
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        conn.commit()

    return None

