"""Secret loading shared by backend and internal services (standard library only)."""

import os
from pathlib import Path
import secrets
import stat
import tempfile


def _validate_secret(value: str) -> str:
    placeholders = ("your-secret-key", "change-in-production", "change-me", "changeme")
    if (
        not 32 <= len(value) <= 4096
        or not value.isascii()
        or any(character.isspace() or ord(character) < 33 for character in value)
        or any(marker in value.lower() for marker in placeholders)
    ):
        raise ValueError("Secrets must contain at least 32 non-whitespace ASCII characters and cannot be placeholders")
    return value


def _check_parents(path: Path) -> None:
    for component in reversed(path.parents):
        try:
            mode = component.lstat().st_mode
        except FileNotFoundError:
            continue
        if not stat.S_ISDIR(mode) or stat.S_ISLNK(mode):
            raise ValueError("Secret parent directories must be real directories")


def _read_secret(path: Path) -> str:
    _check_parents(path)
    try:
        info = path.lstat()
    except FileNotFoundError:
        raise
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("Secret path must be a regular file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        actual = os.fstat(handle.fileno())
        if not stat.S_ISREG(actual.st_mode) or (actual.st_dev, actual.st_ino) != (info.st_dev, info.st_ino):
            raise ValueError("Secret file changed while opening")
        if os.name != "nt" and (stat.S_IMODE(actual.st_mode) & 0o077):
            raise ValueError("Secret file permissions must exclude group and other access")
        try:
            value = handle.read(4097).decode("ascii")
        except UnicodeError as exc:
            raise ValueError("Secret must contain ASCII characters") from exc
    return _validate_secret(value)


def load_secret(env_name: str, path: Path) -> str:
    """Use a strong explicit value, or atomically create/reuse a private key file.

    A fully written temporary inode is hard-linked into place without replacing an
    existing key. Concurrent processes therefore agree on one complete credential.
    Keys belong in a trusted state directory, never in user-uploaded content.
    """
    if env_name in os.environ:
        return _validate_secret(os.environ[env_name])
    path = Path(os.path.abspath(path))
    _check_parents(path)
    try:
        return _read_secret(path)
    except FileNotFoundError:
        pass

    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    _check_parents(path)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            os.chmod(temporary_path, 0o600)
            handle.write(secrets.token_urlsafe(48).encode("ascii"))
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_path, path)
        except FileExistsError:
            pass
        return _read_secret(path)
    finally:
        temporary_path.unlink(missing_ok=True)
