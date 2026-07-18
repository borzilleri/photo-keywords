#!/usr/bin/env python3
"""Shared helpers: project paths, logging, binary resolution, secrets."""
import logging
import os
import shutil
import sys
from logging.handlers import RotatingFileHandler

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_NAME = "photo-keywords"


def resolve_path(p, root=PROJECT_ROOT):
    """Expand ~ and resolve a possibly-relative path against the project root."""
    p = os.path.expanduser(p)
    return p if os.path.isabs(p) else os.path.join(root, p)


def _xdg_dir(env_var, default_rel):
    """Per-user XDG base dir (honoring the env var) with the app name appended."""
    base = os.environ.get(env_var) or os.path.join(os.path.expanduser("~"), default_rel)
    return os.path.join(base, APP_NAME)


def xdg_config_dir():
    return _xdg_dir("XDG_CONFIG_HOME", ".config")


def xdg_data_dir():
    return _xdg_dir("XDG_DATA_HOME", ".local/share")


def xdg_state_dir():
    return _xdg_dir("XDG_STATE_HOME", ".local/state")


def osxphotos_cmd():
    """Invoke osxphotos via the current interpreter so it resolves under launchd."""
    return [sys.executable, "-m", "osxphotos"]


def resolve_claude(claude_bin):
    """Absolute path to the claude binary, or None if not found."""
    if os.path.isabs(claude_bin):
        return claude_bin if os.path.exists(claude_bin) else None
    return shutil.which(claude_bin)


def load_env_file(path):
    """Parse a KEY=VALUE secrets file into a dict (ignores blanks and # comments)."""
    env = {}
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return env
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def setup_logging(log_path, name="photo-keywords", level=logging.INFO, console=True):
    """Logger with a size-rotating file handler (+ optional console)."""
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=5)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    if console:
        out = logging.StreamHandler(sys.stdout)
        out.setFormatter(fmt)
        out.addFilter(lambda r: r.levelno < logging.WARNING)
        logger.addHandler(out)
        err = logging.StreamHandler(sys.stderr)
        err.setFormatter(fmt)
        err.setLevel(logging.WARNING)
        logger.addHandler(err)
    return logger
