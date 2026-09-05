"""Provider-agnostic contact data model.

Every contact source (Google, Microsoft, later iCloud / CardDAV, ...) maps its
own payload into these neutral structures. Nothing downstream (matching, diff,
UI) should ever see a Google- or Outlook-specific field name.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FieldLabel(str, Enum):
    """Neutral label for a typed value (phone, email, address)."""

    HOME = "home"
    WORK = "work"
    MOBILE = "mobile"
    OTHER = "other"


@dataclass(frozen=True)
class EmailAddress:
    address: str  # normalized: lowercase, trimmed
    label: FieldLabel = FieldLabel.OTHER


@dataclass(frozen=True)
class PhoneNumber:
    # `e164` is the normalized form (via `phonenumbers`) used for matching;
    # `raw` keeps what the provider actually stored, for display.
    raw: str
    e164: str | None = None
    label: FieldLabel = FieldLabel.OTHER


@dataclass(frozen=True)
class PostalAddress:
    street: str = ""
    city: str = ""
    postal_code: str = ""
    region: str = ""
    country: str = ""
    label: FieldLabel = FieldLabel.OTHER


@dataclass
class Contact:
    """One person as seen in exactly one source."""

    source_id: str  # which ContactSource this came from, e.g. "google"
    source_uid: str  # stable id within that source (resourceName / Graph id)

    display_name: str = ""
    given_name: str = ""
    family_name: str = ""
    organization: str = ""

    emails: list[EmailAddress] = field(default_factory=list)
    phones: list[PhoneNumber] = field(default_factory=list)
    addresses: list[PostalAddress] = field(default_factory=list)

    # Anything we deliberately do not model yet, kept for debugging / display.
    extra: dict = field(default_factory=dict)

    @property
    def primary_email(self) -> str | None:
        return self.emails[0].address if self.emails else None
