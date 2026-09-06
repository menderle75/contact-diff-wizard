"""Field normalization shared by every contact source.

Keep this provider-neutral: sources call these helpers while mapping their raw
payload into the `Contact` model, so matching can rely on consistent values.
"""

from __future__ import annotations

import re

import phonenumbers

DEFAULT_REGION = "DE"  # used when a phone number has no country prefix

# Outlook lets people type notes into a phone field, e.g. "+49 30 1234 (office)"
# or "+49 30 1234 Zentrale". Strip a trailing parenthetical / word note.
_PHONE_NOTE = re.compile(r"\s*\(.*?\)\s*$|\s+[^\d()+\s][^\d()+]*$")


def norm_email(raw: str) -> str:
    """Lowercase + trim. Returns '' for anything without an '@'."""
    e = (raw or "").strip().lower()
    return e if "@" in e else ""


def norm_phone(raw: str, region: str = DEFAULT_REGION) -> str | None:
    """Return E.164 (e.g. '+49301234567') or None if unparseable."""
    if not raw or not raw.strip():
        return None
    candidates = [raw]
    stripped = _PHONE_NOTE.sub("", raw).strip()
    if stripped and stripped != raw.strip():
        candidates.append(stripped)
    for cand in candidates:
        try:
            num = phonenumbers.parse(cand, region)
        except phonenumbers.NumberParseException:
            continue
        if phonenumbers.is_possible_number(num):
            return phonenumbers.format_number(
                num, phonenumbers.PhoneNumberFormat.E164
            )
    return None


def norm_name(raw: str) -> str:
    """Collapse whitespace, strip. Case kept (fuzzy matching lowercases itself)."""
    return " ".join((raw or "").split())
