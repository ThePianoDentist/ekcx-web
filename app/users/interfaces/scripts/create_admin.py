from __future__ import annotations

import argparse
import secrets
import sys

from sqlalchemy.exc import IntegrityError

from app.db.session import get_session_factory
from app.users.data import repository
from app.users.domain.auth import hash_password, normalize_email


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create an admin user with a generated password.")
    parser.add_argument("email", help="Admin email (used as username)")
    args = parser.parse_args(argv)

    email = normalize_email(args.email)
    if not email:
        print("Email is required.", file=sys.stderr)
        return 1

    password = secrets.token_urlsafe(16)
    password_hash = hash_password(password)

    factory = get_session_factory()
    session = factory()
    try:
        repository.create_user(session, email, password_hash)
        session.commit()
    except IntegrityError:
        session.rollback()
        print(f"User already exists: {email}", file=sys.stderr)
        return 1
    finally:
        session.close()

    print(f"Created admin: {email}")
    print(f"Password (send securely; shown once): {password}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())