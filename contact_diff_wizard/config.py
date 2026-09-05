"""Load `config.toml` (falling back to `config.example.toml`)."""

from __future__ import annotations

import tomllib
from pathlib import Path

_ROOT = Path(__file__).parent.parent


def load() -> dict:
    for name in ("config.toml", "config.example.toml"):
        path = _ROOT / name
        if path.exists():
            return tomllib.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError("No config.toml or config.example.toml found")
