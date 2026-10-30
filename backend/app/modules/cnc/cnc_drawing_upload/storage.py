"""Bound private storage for exact CNC STEP bytes."""

import hashlib
import os
import tempfile
import time
from pathlib import Path
from uuid import UUID

from app.config.path_conf import BASE_DIR, STATIC_DIR
from app.modules.cnc.browser.files import STEP_SUFFIXES

PRIVATE_DRAWING_ROOT = BASE_DIR / "private" / "cnc-drawings"
_STALE_TEMP_SECONDS = 24 * 60 * 60


def drawing_path(root: Path, owner_id: int, request_id: UUID, extension: str) -> Path:
    if owner_id <= 0 or extension not in STEP_SUFFIXES:
        raise ValueError("DRAWING_STORAGE_INVALID")
    resolved = root.resolve()
    if resolved.is_relative_to(STATIC_DIR.resolve()):
        raise ValueError("DRAWING_STORAGE_PUBLIC")
    return resolved / str(owner_id) / f"{request_id}{extension}"


def store_drawing(path: Path, content: bytes, sha256: str) -> None:
    """Atomically publish verified bytes; retry never replaces different bytes."""
    owner_dir = path.parent
    owner_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if owner_dir.resolve() != owner_dir or path.is_symlink():
        raise ValueError("DRAWING_STORAGE_INVALID")

    if path.exists():
        if not path.is_file() or path.stat().st_size != len(content) or hashlib.sha256(path.read_bytes()).hexdigest() != sha256:
            raise ValueError("DRAWING_STORAGE_CONFLICT")
        return

    # Clean only this request's abandoned staging files, never final drawings.
    prefix = f".{path.stem}."
    for stale in owner_dir.glob(f"{prefix}*.tmp"):
        try:
            if not stale.is_symlink() and stale.is_file() and stale.stat().st_mtime < time.time() - _STALE_TEMP_SECONDS:
                stale.unlink()
        except OSError:
            pass

    temporary: Path | None = None
    try:
        fd, name = tempfile.mkstemp(dir=owner_dir, prefix=prefix, suffix=".tmp")
        temporary = Path(name)
        with os.fdopen(fd, "wb") as target:
            target.write(content)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def verify_drawing(path: Path, sha256: str, size: int) -> bool:
    """Recheck a ready record without trusting a path or a stale digest."""
    try:
        if path.is_symlink() or path.resolve(strict=True) != path or not path.is_file() or path.stat().st_size != size:
            return False
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest() == sha256
    except OSError:
        return False
