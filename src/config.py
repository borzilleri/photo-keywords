#!/usr/bin/env python3
"""Load config.json merged over defaults; resolve all paths to absolute XDG locations."""
import json
import os

import common

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
    "secrets_file": None,
    "data_dir": None,
    "state_dir": None,
    "taxonomy_path": None,
    "timeout": 120,
    "failfast_canary": 3,
}


def _config_file_path(explicit):
    """Discovery order: --config arg, $PHOTO_KEYWORDS_CONFIG, then the XDG config dir."""
    if explicit:
        return explicit
    env = os.environ.get("PHOTO_KEYWORDS_CONFIG")
    if env:
        return env
    return os.path.join(common.xdg_config_dir(), "config.json")


def _abspath(p):
    return os.path.abspath(os.path.expanduser(p))


def load_config(path=None):
    """Return a config dict with absolute paths and derived file locations."""
    cfg = dict(DEFAULTS)
    path = _config_file_path(path)
    if os.path.exists(path):
        with open(path) as f:
            cfg.update(json.load(f))

    config_dir = common.xdg_config_dir()
    cfg["data_dir"] = cfg["data_dir"] or common.xdg_data_dir()
    cfg["state_dir"] = cfg["state_dir"] or common.xdg_state_dir()
    cfg["taxonomy_path"] = cfg["taxonomy_path"] or os.path.join(config_dir, "taxonomy.json")
    cfg["secrets_file"] = cfg["secrets_file"] or os.path.join(config_dir, "env")

    for key in ("data_dir", "state_dir", "taxonomy_path", "secrets_file"):
        cfg[key] = _abspath(cfg[key])
    if cfg.get("library_path"):
        cfg["library_path"] = _abspath(cfg["library_path"])

    if not os.path.exists(cfg["taxonomy_path"]):
        cfg["taxonomy_path"] = os.path.join(common.PROJECT_ROOT, "taxonomy.json")

    cfg["results_path"] = os.path.join(cfg["data_dir"], "results.jsonl")
    cfg["thumbnails_dir"] = os.path.join(cfg["data_dir"], "thumbnails")
    cfg["reports_dir"] = os.path.join(cfg["data_dir"], "reports")
    cfg["state_path"] = os.path.join(cfg["state_dir"], "state.json")
    cfg["lock_path"] = os.path.join(cfg["state_dir"], "run.lock")
    cfg["logs_dir"] = os.path.join(cfg["state_dir"], "logs")
    cfg["log_path"] = os.path.join(cfg["logs_dir"], "photo-keywords.log")
    return cfg
