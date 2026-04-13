"""
Internal adapter that wraps vendored EmergencyStorage commands.
"""

import asyncio
import os
import subprocess
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel


app = FastAPI(title="BabylonPiles Mirrorer", version="1.0.0")

MIRROR_ROOT = Path(os.getenv("MIRROR_ROOT", "/mnt/babylonpiles/piles"))
MIRROR_LOG_DIR = Path(os.getenv("MIRROR_LOG_DIR", "/mnt/babylonpiles/data/mirror_logs"))
EMERGENCY_STORAGE_ROOT = Path(os.getenv("EMERGENCY_STORAGE_ROOT", "/vendor/EmergencyStorage"))

COMMAND_FLAGS: Dict[Tuple[str, str], str] = {
    ("openstreetmap", "planet"): "--openstreetmap",
    ("internet_archive", "software"): "--ia-software",
    ("internet_archive", "music"): "--ia-music",
    ("internet_archive", "movies"): "--ia-movies",
    ("internet_archive", "texts"): "--ia-texts",
}


class MirrorExecutionRequest(BaseModel):
    run_id: int
    provider: str
    variant: str
    destination_subpath: str


def _ensure_paths():
    MIRROR_ROOT.mkdir(parents=True, exist_ok=True)
    MIRROR_LOG_DIR.mkdir(parents=True, exist_ok=True)


def _directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                continue
    return total


def _tail_file(path: Path, tail: int) -> str:
    lines = deque(maxlen=tail)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            lines.append(line.rstrip("\n"))
    return "\n".join(lines)


def _extract_error_message(log_path: Path) -> Optional[str]:
    if not log_path.exists():
        return None
    content = _tail_file(log_path, 20).strip()
    return content[-1000:] if content else None


def _resolve_destination(destination_subpath: str) -> Path:
    root = MIRROR_ROOT.resolve()
    destination = (root / Path(destination_subpath)).resolve()
    if destination != root and root not in destination.parents:
        raise HTTPException(status_code=400, detail="Invalid destination_subpath")
    return destination


def _build_command(provider: str, variant: str, destination_path: Path):
    flag = COMMAND_FLAGS.get((provider, variant))
    if flag is None:
        raise HTTPException(status_code=400, detail="Unsupported provider/variant")
    return [
        "bash",
        str(EMERGENCY_STORAGE_ROOT / "emergency_storage.sh"),
        flag,
        str(destination_path),
    ]


def _execute_command(command, log_path: Path):
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    with log_path.open("w", encoding="utf-8", errors="replace") as log_handle:
        log_handle.write(f"[{datetime.utcnow().isoformat()}] Running: {' '.join(command)}\n")
        log_handle.flush()
        result = subprocess.run(
            command,
            cwd=str(EMERGENCY_STORAGE_ROOT),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
            env=env,
        )
    return result.returncode


@app.on_event("startup")
async def on_startup():
    _ensure_paths()


@app.get("/health")
async def health():
    _ensure_paths()
    return {"status": "healthy"}


@app.post("/api/v1/run")
async def run_mirror(request: MirrorExecutionRequest):
    _ensure_paths()

    destination_path = _resolve_destination(request.destination_subpath)
    destination_path.mkdir(parents=True, exist_ok=True)
    log_path = MIRROR_LOG_DIR / f"{request.run_id}.log"

    before_size = _directory_size(destination_path)
    command = _build_command(request.provider, request.variant, destination_path)
    exit_code = await asyncio.to_thread(_execute_command, command, log_path)
    after_size = _directory_size(destination_path)

    return {
        "success": exit_code == 0,
        "exit_code": exit_code,
        "bytes_downloaded": max(after_size - before_size, 0),
        "log_path": str(log_path),
        "error_message": None if exit_code == 0 else _extract_error_message(log_path),
    }


@app.get("/api/v1/runs/{run_id}/logs")
async def get_run_logs(run_id: int, tail: int = Query(default=40, ge=1, le=500)):
    _ensure_paths()
    log_path = MIRROR_LOG_DIR / f"{run_id}.log"
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Log not found")

    return {
        "run_id": run_id,
        "log_path": str(log_path),
        "content": _tail_file(log_path, tail),
    }
