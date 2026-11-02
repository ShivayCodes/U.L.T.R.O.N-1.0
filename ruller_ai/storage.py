"""Small JSON persistence helpers with atomic writes."""
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def read_json(path: Path, default: Any, *, max_bytes: int | None = None) -> Any:
    try:
        if not path.exists():
            return default
        if max_bytes is not None and path.stat().st_size > max_bytes:
            raise RuntimeError(f"Data file is too large: {path}")
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return default
    except (json.JSONDecodeError, OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError(f"Could not read data file {path}: {exc}") from exc


def write_json(path: Path, value: Any, *, sync: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise RuntimeError(f"Could not write data file {path}: {exc}") from exc
