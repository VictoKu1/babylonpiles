"""One canonical path policy for managed content and permission keys.

HTTP frameworks already decode URLs. Never decode a path a second time here.
"""
import os
import re
from pathlib import Path, PureWindowsPath

RESERVED_NAMES = frozenset({".permissions.json", ".metadata.json"})
_ENCODED_BYTE = re.compile(r"%[0-9a-fA-F]{2}")
_WINDOWS_DEVICES = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)


def validate_name(value: str) -> str:
    """Require a single, unambiguous user-controlled filename component."""
    if not isinstance(value, str) or not value or value in {".", ".."}:
        raise ValueError("Invalid filename")
    if any(c in value for c in ("/", "\\", ":")) or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("Invalid filename")
    if value.endswith((".", " ")) or _ENCODED_BYTE.search(value) or _WINDOWS_DEVICES.match(value):
        raise ValueError("Ambiguous filename")
    if value.casefold() in RESERVED_NAMES or value.casefold().startswith(".transfer-"):
        raise ValueError("Reserved filename")
    return value


def _reject_symlinks(path: Path) -> None:
    for item in (path, *path.parents):
        if item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction()):
            raise ValueError("Symbolic links are not allowed")


def resolve_path(root, relative, allow_root: bool = False) -> Path:
    """Resolve a canonical relative path within root, rejecting every symlink."""
    relative = os.fspath(relative)
    if not isinstance(relative, str):
        raise ValueError("Invalid path")
    root_path = Path(root).absolute()
    _reject_symlinks(root_path)
    root_path = root_path.resolve()
    if relative == "" and allow_root:
        return root_path
    if not relative or relative.startswith("/") or PureWindowsPath(relative).drive:
        raise ValueError("A relative content path is required")
    parts = relative.split("/")
    for part in parts:
        validate_name(part)
    target = root_path.joinpath(*parts)
    _reject_symlinks(target)
    resolved = target.resolve()
    if not resolved.is_relative_to(root_path) or (resolved == root_path and not allow_root):
        raise ValueError("Path is outside the content root")
    return resolved


def canonical_key(root, relative) -> str:
    return resolve_path(root, relative).relative_to(Path(root).resolve()).as_posix()


def validate_stored_path(root, path) -> Path:
    """Validate database paths before reads, writes, backup or deletion."""
    value = os.fspath(path)
    candidate = Path(value)
    if candidate.is_absolute():
        try:
            relative = candidate.relative_to(Path(root).absolute()).as_posix()
        except ValueError as exc:
            raise ValueError("Stored file is outside the content root") from exc
        # Path normalizes '.' and repeated separators; stored paths must not alias.
        if any(part in {".", ".."} for part in value.replace("\\", "/").split("/")):
            raise ValueError("Invalid stored path")
    else:
        relative = value
    return resolve_path(root, relative)
