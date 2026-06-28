#!/usr/bin/env python3
"""Load config.json merged over defaults; resolve all paths to absolute."""
import json
import os

from common import PROJECT_ROOT, resolve_path

DEFAULTS = {
    "model": "sonnet",
    "workers": 4,
    "thumbnail_size": 1024,
    "lookback_days": 7,
    "min_confidence": 0.0,
    "with_parents": False,
    "apply_enabled": True,
    "library_path": None,
    "claude_bin": "claude",
    "secrets_file": "~/.config/photo-keywords/env",
    "data_dir": "data",
    "logs_dir": "logs",
    "reports_dir": "reports",
    "taxonomy_path": "taxonomy.json",
    "timeout": 120,
    "failfast_canary": 3,
}

DEFAULT_CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.json")


def load_config(path=None):
    """Return a config dict with absolute paths and derived file locations."""
    cfg = dict(DEFAULTS)
    path = path or DEFAULT_CONFIG_PATH
    if os.path.exists(path):
        with open(path) as f:
            cfg.update(json.load(f))

    for key in ("data_dir", "logs_dir", "reports_dir", "taxonomy_path"):
        cfg[key] = resolve_path(cfg[key])
    if cfg.get("library_path"):
        cfg["library_path"] = resolve_path(cfg["library_path"])
    cfg["secrets_file"] = os.path.expanduser(cfg["secrets_file"])

    cfg["results_path"] = os.path.join(cfg["data_dir"], "results.jsonl")
    cfg["state_path"] = os.path.join(cfg["data_dir"], "state.json")
    cfg["lock_path"] = os.path.join(cfg["data_dir"], "run.lock")
    cfg["thumbnails_dir"] = os.path.join(cfg["data_dir"], "thumbnails")
    cfg["log_path"] = os.path.join(cfg["logs_dir"], "photo-keywords.log")
    return cfg
