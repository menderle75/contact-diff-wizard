"""Minimal JSON-file i18n.

One flat JSON file per language in this package directory. `t(key)` looks the
key up in the active language and falls back to English, then to the key itself.
"""

from __future__ import annotations

import json
from pathlib import Path

_DIR = Path(__file__).parent
AVAILABLE = ("de", "en")
_FALLBACK = "en"

_cache: dict[str, dict[str, str]] = {}
_active = _FALLBACK


def _load(lang: str) -> dict[str, str]:
    if lang not in _cache:
        path = _DIR / f"{lang}.json"
        _cache[lang] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return _cache[lang]


def set_language(lang: str) -> None:
    global _active
    _active = lang if lang in AVAILABLE else _FALLBACK


def language_name(lang: str) -> str:
    return {"de": "Deutsch", "en": "English"}.get(lang, lang)


def t(key: str, **kwargs: object) -> str:
    text = _load(_active).get(key) or _load(_FALLBACK).get(key) or key
    return text.format(**kwargs) if kwargs else text
