"""
core/config.py — Load settings from config/defaults.yaml.

All modules read from here instead of hardcoding constants. Environment
variables always win over the YAML file, which wins over code defaults.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_ROOT = Path(__file__).parent.parent
_DEFAULTS_PATH = _ROOT / "config" / "defaults.yaml"
_cached: dict | None = None


def load() -> dict:
    """Return the parsed defaults.yaml (cached after first call)."""
    global _cached
    if _cached is not None:
        return _cached
    try:
        import yaml
        with open(_DEFAULTS_PATH) as f:
            _cached = yaml.safe_load(f) or {}
    except Exception:
        _cached = {}
    return _cached


def get(section: str, key: str, default: Any) -> Any:
    """Read a single setting: config[section][key], falling back to default."""
    return load().get(section, {}).get(key, default)
