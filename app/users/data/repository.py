from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.users.data.models import User


def find_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email))


def create_user(session: Session, email: str, password_hash: str) -> User:
    user = User(email=email, password_hash=password_hash)
    session.add(user)
    session.flush()
    return user