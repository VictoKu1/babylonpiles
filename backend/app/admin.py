"""Operator-only account setup: python -m app.admin create --username admin."""
import argparse
import asyncio
import getpass
import sys
from sqlalchemy import select
from app.core.database import init_db, AsyncSessionLocal, close_db
from app.core.passwords import hash_password
from app.models.user import User


async def manage_account(action: str, username: str, password: str):
    if not 1 <= len(username) <= 50 or not 12 <= len(password) <= 1024:
        raise ValueError("Use a username up to 50 characters and a password of 12–1024 characters")
    await init_db()
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
        if action == "create":
            if user:
                raise ValueError("Account already exists; use reset-password")
            user = User(username=username, role="admin", is_active=True)
            db.add(user)
        elif not user:
            raise ValueError("Account does not exist")
        user.hashed_password = await asyncio.to_thread(hash_password, password)
        await db.commit()
    await close_db()


def main():
    parser = argparse.ArgumentParser(description="Create an administrator or reset an account password locally")
    parser.add_argument("action", choices=["create", "reset-password"])
    parser.add_argument("--username", required=True)
    parser.add_argument("--password-stdin", action="store_true", help="Read a password from stdin instead of the terminal")
    args = parser.parse_args()
    password = sys.stdin.readline().rstrip("\r\n") if args.password_stdin else getpass.getpass("Password: ")
    if not args.password_stdin and password != getpass.getpass("Confirm password: "):
        parser.error("Passwords do not match")
    try:
        asyncio.run(manage_account(args.action, args.username, password))
    except ValueError as exc:
        parser.error(str(exc))
    print("Account updated successfully.")


if __name__ == "__main__":
    main()
