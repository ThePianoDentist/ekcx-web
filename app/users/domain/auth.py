from __future__ import annotations

import bcrypt
from sqlalchemy.orm import Session

from app.users.data import repository
from app.users.data.models import User


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(plain: str) -> str:
    hashed = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def authenticate(session: Session, email: str, password: str) -> User | None:
    normalized = normalize_email(email)
    user = repository.find_by_email(session, normalized)
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user