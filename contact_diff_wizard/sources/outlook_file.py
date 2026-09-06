"""Outlook contacts from an exported file (no Microsoft Graph / Azure needed).

Supported inputs:
  * CSV  - the native export of Outlook.com ("Manage > Export contacts") and
           classic Outlook Desktop ("comma separated values"). Fixed English
           column names regardless of UI language.
  * vCard - .vcf, one or many cards concatenated.

Everything is mapped into the neutral `Contact` model so the matcher never sees
an Outlook-specific field name.
"""

from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path

import vobject

from contact_diff_wizard.model import (
    Contact,
    EmailAddress,
    FieldLabel,
    PhoneNumber,
    PostalAddress,
)
from contact_diff_wizard.normalize import norm_email, norm_name, norm_phone

# CSV phone column -> neutral label
_CSV_PHONE_COLUMNS: dict[str, FieldLabel] = {
    "Mobile Phone": FieldLabel.MOBILE,
    "Home Phone": FieldLabel.HOME,
    "Home Phone 2": FieldLabel.HOME,
    "Business Phone": FieldLabel.WORK,
    "Business Phone 2": FieldLabel.WORK,
    "Other Phone": FieldLabel.OTHER,
    "Primary Phone": FieldLabel.OTHER,
}

_CSV_EMAIL_COLUMNS = ["E-mail Address", "E-mail 2 Address", "E-mail 3 Address"]

# CSV address column prefix -> neutral label
_CSV_ADDRESS_GROUPS: list[tuple[str, FieldLabel]] = [
    ("Business", FieldLabel.WORK),
    ("Home", FieldLabel.HOME),
    ("Other", FieldLabel.OTHER),
]

# vCard TYPE param -> neutral label
_VCARD_LABELS: dict[str, FieldLabel] = {
    "CELL": FieldLabel.MOBILE,
    "MOBILE": FieldLabel.MOBILE,
    "HOME": FieldLabel.HOME,
    "WORK": FieldLabel.WORK,
}


class OutlookFileContactSource:
    id = "outlook"
    display_name = "Outlook"

    def __init__(
        self,
        path: str | Path | None = None,
        *,
        data: bytes | None = None,
        filename: str = "",
    ) -> None:
        if (path is None) == (data is None):
            raise ValueError("pass exactly one of `path` or `data`")
        self._path = Path(path) if path is not None else None
        self._data = data
        self._filename = filename or (self._path.name if self._path else "")

    @classmethod
    def from_upload(cls, data: bytes, filename: str) -> OutlookFileContactSource:
        """Build from an in-memory upload (e.g. Streamlit file_uploader)."""
        return cls(data=data, filename=filename)

    # --- ContactSource protocol ----------------------------------------
    def is_authenticated(self) -> bool:
        return self._data is not None or (self._path is not None and self._path.is_file())

    def authenticate(self) -> None:
        if self._data is None and not (self._path and self._path.is_file()):
            raise FileNotFoundError(self._path)

    def fetch_contacts(self) -> list[Contact]:
        data = self._data if self._data is not None else self._path.read_bytes()
        return parse_bytes(data, filename=self._filename)


def parse_bytes(data: bytes, filename: str = "") -> list[Contact]:
    """Detect CSV vs vCard and parse. `filename` is only a hint."""
    text = data.decode("utf-8-sig", errors="replace")
    head = text.lstrip()[:200].upper()
    is_vcard = head.startswith("BEGIN:VCARD") or filename.lower().endswith(".vcf")
    return _parse_vcard(text) if is_vcard else _parse_csv(text)


def _dedupe_emails(emails: list[EmailAddress]) -> list[EmailAddress]:
    seen: set[str] = set()
    out: list[EmailAddress] = []
    for e in emails:
        if e.address not in seen:
            seen.add(e.address)
            out.append(e)
    return out


def _dedupe_phones(phones: list[PhoneNumber]) -> list[PhoneNumber]:
    seen: set[str] = set()
    out: list[PhoneNumber] = []
    for p in phones:
        key = p.e164 or p.raw.strip()
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def _uid(display_name: str, emails: list[EmailAddress], phones: list[PhoneNumber]) -> str:
    basis = "|".join(
        [display_name]
        + sorted(e.address for e in emails)
        + sorted(p.e164 or p.raw for p in phones)
    )
    return "outlook-" + hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]


def _parse_csv(text: str) -> list[Contact]:
    reader = csv.DictReader(io.StringIO(text))
    contacts: list[Contact] = []

    for row in reader:
        get = lambda k: (row.get(k) or "").strip()  # noqa: E731

        given = norm_name(get("First Name"))
        family = norm_name(get("Last Name"))
        middle = norm_name(get("Middle Name"))
        display = norm_name(" ".join(p for p in (given, middle, family) if p))
        if not display:
            display = norm_name(get("Nickname")) or norm_name(get("Company"))

        emails = [
            EmailAddress(address=norm_email(get(col)))
            for col in _CSV_EMAIL_COLUMNS
            if norm_email(get(col))
        ]

        phones: list[PhoneNumber] = []
        for col, label in _CSV_PHONE_COLUMNS.items():
            raw = get(col)
            if raw:
                phones.append(PhoneNumber(raw=raw, e164=norm_phone(raw), label=label))

        addresses: list[PostalAddress] = []
        for prefix, label in _CSV_ADDRESS_GROUPS:
            street = get(f"{prefix} Street")
            city = get(f"{prefix} City")
            postal = get(f"{prefix} Postal Code")
            region = get(f"{prefix} State")
            country = get(f"{prefix} Country/Region")
            if any((street, city, postal, region, country)):
                addresses.append(
                    PostalAddress(
                        street=street,
                        city=city,
                        postal_code=postal,
                        region=region,
                        country=country,
                        label=label,
                    )
                )

        emails = _dedupe_emails(emails)
        phones = _dedupe_phones(phones)

        if not (display or emails or phones):
            continue  # skip empty rows

        contacts.append(
            Contact(
                source_id="outlook",
                source_uid=_uid(display, emails, phones),
                display_name=display,
                given_name=given,
                family_name=family,
                organization=norm_name(get("Company")),
                emails=emails,
                phones=phones,
                addresses=addresses,
            )
        )

    return contacts


def _parse_vcard(text: str) -> list[Contact]:
    contacts: list[Contact] = []

    for card in vobject.readComponents(text):
        display = norm_name(getattr(card, "fn", None).value if hasattr(card, "fn") else "")
        given = family = ""
        if hasattr(card, "n"):
            n = card.n.value
            given = norm_name(getattr(n, "given", "") or "")
            family = norm_name(getattr(n, "family", "") or "")
        if not display:
            display = norm_name(f"{given} {family}")

        org = ""
        if hasattr(card, "org") and card.org.value:
            org = norm_name(
                card.org.value[0] if isinstance(card.org.value, list) else str(card.org.value)
            )

        emails = []
        for e in card.contents.get("email", []):
            addr = norm_email(e.value)
            if addr:
                emails.append(EmailAddress(address=addr, label=_type_label(e)))

        phones = []
        for t in card.contents.get("tel", []):
            phones.append(
                PhoneNumber(raw=t.value, e164=norm_phone(t.value), label=_type_label(t))
            )

        addresses = []
        for a in card.contents.get("adr", []):
            v = a.value
            addresses.append(
                PostalAddress(
                    street=norm_name(getattr(v, "street", "") or ""),
                    city=norm_name(getattr(v, "city", "") or ""),
                    postal_code=norm_name(getattr(v, "code", "") or ""),
                    region=norm_name(getattr(v, "region", "") or ""),
                    country=norm_name(getattr(v, "country", "") or ""),
                    label=_type_label(a),
                )
            )

        emails = _dedupe_emails(emails)
        phones = _dedupe_phones(phones)

        if not (display or emails or phones):
            continue

        contacts.append(
            Contact(
                source_id="outlook",
                source_uid=_uid(display, emails, phones),
                display_name=display,
                given_name=given,
                family_name=family,
                organization=org,
                emails=emails,
                phones=phones,
                addresses=addresses,
            )
        )

    return contacts


def _type_label(component) -> FieldLabel:
    for t in getattr(component, "type_paramlist", []):
        key = str(t).upper()
        if key in _VCARD_LABELS:
            return _VCARD_LABELS[key]
    return FieldLabel.OTHER
