"""Salted password hashes; plaintext is accepted only by the one-time migration."""
import base64
import hashlib
import hmac
import secrets

ROUNDS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ROUNDS)
    return f"pbkdf2_sha256${ROUNDS}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def is_password_hash(value: str) -> bool:
    try:
        algorithm, rounds, salt, digest = value.split("$")
        return (algorithm == "pbkdf2_sha256" and int(rounds) == ROUNDS
                and len(base64.b64decode(salt, validate=True)) == 16
                and len(base64.b64decode(digest, validate=True)) == 32)
    except (ValueError, TypeError):
        return False


def verify_password(password: str, stored: str) -> bool:
    if not is_password_hash(stored):
        return False
    _, rounds, salt, expected = stored.split("$")
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), base64.b64decode(salt), int(rounds))
    return hmac.compare_digest(actual, base64.b64decode(expected))
