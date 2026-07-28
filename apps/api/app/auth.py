from __future__ import annotations

import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta

import jwt

from .config import settings
from .db import connect
from .errors import DomainError
from .services import new_id, now, row


ITERATIONS = 600_000


def _derive(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS).hex()


def _hash_password(password: str, salt: bytes | None = None) -> str:
    if len(password) < 12:
        raise DomainError("WEAK_PASSWORD", "Use a password with at least 12 characters.", status_code=422)
    salt = salt or os.urandom(16)
    return f"{salt.hex()}:{_derive(password, salt)}"


def _verify_password(password: str, stored: str) -> bool:
    salt_hex, expected = stored.split(":", 1)
    actual = _derive(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(actual, expected)


def create_account(email: str, password: str, display_name: str) -> dict:
    normalized = email.strip().lower()
    if "@" not in normalized or len(display_name.strip()) < 2:
        raise DomainError("INVALID_ACCOUNT", "Provide a valid email address and display name.", status_code=422)
    user_id, organization_id, created = new_id(), new_id(), now()
    with connect() as conn:
        if conn.execute("SELECT 1 FROM users WHERE email=?", (normalized,)).fetchone():
            raise DomainError("EMAIL_IN_USE", "An account already uses this email.", status_code=409)
        conn.execute("INSERT INTO users VALUES(?,?,?,?,?,NULL)", (user_id, normalized, display_name.strip(), _hash_password(password), created))
        conn.execute("INSERT INTO organizations VALUES(?,?,?)", (organization_id, f"{display_name.strip()}'s workspace", created))
        conn.execute("INSERT INTO organization_memberships VALUES(?,?,?,?)", (organization_id, user_id, "owner", created))
    return issue_token({"id": user_id, "email": normalized, "display_name": display_name.strip()})


def issue_token(user: dict) -> dict:
    expires = datetime.now(UTC) + timedelta(minutes=settings.access_token_minutes)
    encoded = jwt.encode({"sub": user["id"], "email": user["email"], "exp": expires, "iat": datetime.now(UTC), "aud": "curriculumos"}, settings.secret, algorithm="HS256")
    return {"access_token": encoded, "token_type": "bearer", "expires_at": expires.isoformat(), "user": {"id": user["id"], "email": user["email"], "display_name": user["display_name"]}}


def authenticate(email: str, password: str) -> dict:
    with connect() as conn:
        user = row(conn.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone())
    if not user or user["disabled_at"] or not _verify_password(password, user["password_hash"]):
        raise DomainError("INVALID_CREDENTIALS", "Email or password is incorrect.", status_code=401)
    return issue_token(user)


def current_user(token: str) -> dict:
    try:
        claims = jwt.decode(token, settings.secret, algorithms=["HS256"], audience="curriculumos")
    except jwt.PyJWTError as exc:
        raise DomainError("INVALID_TOKEN", "Sign in again to continue.", status_code=401) from exc
    with connect() as conn:
        user = row(conn.execute("SELECT id,email,display_name,disabled_at FROM users WHERE id=?", (claims["sub"],)).fetchone())
    if not user or user["disabled_at"]:
        raise DomainError("INVALID_TOKEN", "This account is unavailable.", status_code=401)
    return user
