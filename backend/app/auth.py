from __future__ import annotations

import os
import time
from dataclasses import dataclass

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


@dataclass(frozen=True)
class AuthSettings:
    admin_user: str
    admin_password_hash: str
    session_secret: str
    session_max_age_seconds: int


def get_auth_settings() -> AuthSettings:
    admin_user = os.environ.get("ADMIN_USER", "admin")
    admin_password_hash = os.environ.get("ADMIN_PASSWORD_HASH", "")
    session_secret = os.environ.get("SESSION_SECRET", "")
    max_age = int(os.environ.get("SESSION_MAX_AGE_SECONDS", "28800"))  # 8h

    return AuthSettings(
        admin_user=admin_user,
        admin_password_hash=admin_password_hash,
        session_secret=session_secret,
        session_max_age_seconds=max_age,
    )


def verify_password(plain_password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    return pwd_context.verify(plain_password, password_hash)


def new_expiry_ts(max_age_seconds: int) -> int:
    return int(time.time()) + max_age_seconds
