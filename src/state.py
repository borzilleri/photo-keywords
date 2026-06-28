#!/usr/bin/env python3
"""Run state: an import-time watermark and a single-run lockfile."""
import json
import os
from contextlib import contextmanager
from datetime import datetime


class AlreadyRunning(Exception):
    """Raised when another run holds the lock."""


def load_watermark(state_path):
    """Return the stored watermark datetime, or None if unset."""
    if not os.path.exists(state_path):
        return None
    with open(state_path) as f:
        wm = json.load(f).get("watermark")
    return datetime.fromisoformat(wm) if wm else None


def save_watermark(state_path, dt):
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w") as f:
        json.dump({"watermark": dt.isoformat() if dt else None}, f)


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@contextmanager
def run_lock(lock_path):
    """Hold a PID lockfile for the duration; raise AlreadyRunning if one is active."""
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    if os.path.exists(lock_path):
        try:
            pid = int(open(lock_path).read().strip())
        except (ValueError, OSError):
            pid = None
        if pid and _alive(pid):
            raise AlreadyRunning(f"another run is active (pid {pid})")
    with open(lock_path, "w") as f:
        f.write(str(os.getpid()))
    try:
        yield
    finally:
        try:
            os.remove(lock_path)
        except OSError:
            pass
