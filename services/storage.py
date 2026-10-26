"""
services/storage.py — Low-level JSON file storage for Medi Slot.

All data is stored as JSON arrays in plain text files (*.txt).
This module provides safe read/write helpers.

LIMITATIONS (documented for future migration):
- Not safe for multiple simultaneous writers on different processes.
- No transactions or rollback support.
- File-level locking is used to reduce corruption risk within a single process.
- Migrate to SQLite or a relational database for production use.
"""

import json
import os
import threading
from pathlib import Path

# Per-file threading locks so concurrent Flask threads don't corrupt data.
_locks: dict[str, threading.Lock] = {}
_locks_meta = threading.Lock()


def _get_lock(filepath: str) -> threading.Lock:
    with _locks_meta:
        if filepath not in _locks:
            _locks[filepath] = threading.Lock()
        return _locks[filepath]


# ---------------------------------------------------------------------------
# Core read / write
# ---------------------------------------------------------------------------

def read_json(filepath) -> list:
    """
    Read a JSON array from *filepath*.
    Returns an empty list if the file is missing.
    Raises ValueError if the file exists but contains invalid JSON.
    Raises TypeError if the file contains valid JSON that is not a list.
    """
    path = Path(filepath)
    if not path.exists():
        return []
    lock = _get_lock(str(path))
    with lock:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"File {filepath} contains invalid JSON and cannot be read safely. "
                f"Details: {exc}"
            )
        if not isinstance(data, list):
            raise TypeError(
                f"File {filepath} contains valid JSON but is not an array. "
                "Manual inspection required."
            )
        return data


def write_json(filepath, data: list) -> None:
    """
    Write *data* (a list) to *filepath* as formatted JSON.
    Uses an atomic write-then-rename pattern to reduce corruption risk.
    """
    if not isinstance(data, list):
        raise TypeError("write_json requires a list.")
    path = Path(filepath)
    lock = _get_lock(str(path))
    tmp_path = path.with_suffix(".tmp")
    with lock:
        try:
            tmp_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            os.replace(tmp_path, path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise


def init_file_if_missing(filepath) -> None:
    """
    Create *filepath* as an empty JSON array ONLY if it does not already exist.
    Never overwrites an existing file.
    """
    path = Path(filepath)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, [])


# ---------------------------------------------------------------------------
# Record helpers
# ---------------------------------------------------------------------------

def find_by_id(filepath, record_id) -> dict | None:
    """Return the first record whose 'id' matches *record_id*, or None."""
    records = read_json(filepath)
    for record in records:
        if record.get("id") == record_id:
            return record
    return None


def find_by_field(filepath, field: str, value) -> list:
    """Return all records whose *field* equals *value*."""
    return [r for r in read_json(filepath) if r.get(field) == value]


def find_one_by_field(filepath, field: str, value) -> dict | None:
    """Return the first record whose *field* equals *value*, or None."""
    for r in read_json(filepath):
        if r.get(field) == value:
            return r
    return None


def append_record(filepath, record: dict) -> None:
    """Append *record* to the JSON array at *filepath*."""
    data = read_json(filepath)
    data.append(record)
    write_json(filepath, data)


def update_record(filepath, record_id, updates: dict) -> bool:
    """
    Find the record with *record_id* and merge *updates* into it.
    Returns True if found and updated, False if not found.
    """
    data = read_json(filepath)
    for i, record in enumerate(data):
        if record.get("id") == record_id:
            data[i] = {**record, **updates}
            write_json(filepath, data)
            return True
    return False


def next_int_id(filepath) -> int:
    """Return max(existing int ids) + 1, or 1 if the file is empty."""
    data = read_json(filepath)
    ids = [r.get("id") for r in data if isinstance(r.get("id"), int)]
    return max(ids, default=0) + 1
