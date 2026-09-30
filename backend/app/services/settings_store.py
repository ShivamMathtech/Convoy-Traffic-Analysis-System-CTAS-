"""Persistent settings store (JSON file, deep-merged over defaults)."""
from __future__ import annotations

import copy
import json
import threading

from app import config

_SETTINGS_FILE = config.STORAGE_DIR / "settings.json"
_lock = threading.Lock()


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_settings() -> dict:
    merged = copy.deepcopy(config.DEFAULT_SETTINGS)
    if _SETTINGS_FILE.exists():
        try:
            user = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
            merged = _deep_merge(merged, user)
        except Exception:  # noqa: BLE001
            pass
    return merged


def save_settings(patch: dict) -> dict:
    with _lock:
        current = load_settings()
        merged = _deep_merge(current, patch)
        _SETTINGS_FILE.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return merged
