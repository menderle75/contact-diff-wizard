"""Gmail contacts via the Google People API.

Auth is the loopback OAuth flow in `contact_diff_wizard.auth.google_auth`; this
module only fetches and maps. All contacts are pulled with pagination and mapped
into the neutral `Contact` model.
"""

from __future__ import annotations

from googleapiclient.discovery import build

from contact_diff_wizard.auth.google_auth import load_or_run_flow
from contact_diff_wizard.model import (
    Contact,
    EmailAddress,
    FieldLabel,
    PhoneNumber,
    PostalAddress,
)
from contact_diff_wizard.normalize import norm_email, norm_name, norm_phone

_PERSON_FIELDS = "names,emailAddresses,phoneNumbers,addresses,organizations"
_PAGE_SIZE = 1000

_LABELS: dict[str, FieldLabel] = {
    "home": FieldLabel.HOME,
    "work": FieldLabel.WORK,
    "mobile": FieldLabel.MOBILE,
}


def _label(entry: dict) -> FieldLabel:
    return _LABELS.get((entry.get("type") or "").lower(), FieldLabel.OTHER)


class GoogleContactSource:
    id = "google"
    display_name = "Gmail"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        scopes: list[str],
        token_path: str = "google.token.json",
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._scopes = scopes
        self._token_path = token_path
        self._creds = None

    def is_authenticated(self) -> bool:
        from pathlib import Path

        return Path(self._token_path).exists()

    def authenticate(self) -> None:
        self._creds = load_or_run_flow(
            self._client_id, self._client_secret, self._scopes, self._token_path
        )

    def fetch_contacts(self) -> list[Contact]:
        if self._creds is None:
            self.authenticate()

        service = build("people", "v1", credentials=self._creds, cache_discovery=False)
        contacts: list[Contact] = []
        page_token: str | None = None

        while True:
            resp = (
                service.people()
                .connections()
                .list(
                    resourceName="people/me",
                    personFields=_PERSON_FIELDS,
                    pageSize=_PAGE_SIZE,
                    pageToken=page_token,
                )
                .execute()
            )
            for person in resp.get("connections", []):
                contacts.append(self._to_contact(person))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        return contacts

    @staticmethod
    def _to_contact(person: dict) -> Contact:
        names = person.get("names") or []
        primary_name = names[0] if names else {}
        given = norm_name(primary_name.get("givenName", ""))
        family = norm_name(primary_name.get("familyName", ""))
        display = norm_name(primary_name.get("displayName", "")) or norm_name(
            f"{given} {family}"
        )

        orgs = person.get("organizations") or []
        organization = norm_name(orgs[0].get("name", "")) if orgs else ""

        emails: list[EmailAddress] = []
        seen_email: set[str] = set()
        for e in person.get("emailAddresses") or []:
            addr = norm_email(e.get("value", ""))
            if addr and addr not in seen_email:
                seen_email.add(addr)
                emails.append(EmailAddress(address=addr, label=_label(e)))

        phones: list[PhoneNumber] = []
        seen_phone: set[str] = set()
        for p in person.get("phoneNumbers") or []:
            raw = (p.get("value") or "").strip()
            if not raw:
                continue
            e164 = norm_phone(raw)
            key = e164 or raw
            if key in seen_phone:
                continue
            seen_phone.add(key)
            phones.append(PhoneNumber(raw=raw, e164=e164, label=_label(p)))

        addresses: list[PostalAddress] = []
        for a in person.get("addresses") or []:
            addresses.append(
                PostalAddress(
                    street=norm_name(a.get("streetAddress", "") or ""),
                    city=norm_name(a.get("city", "") or ""),
                    postal_code=norm_name(a.get("postalCode", "") or ""),
                    region=norm_name(a.get("region", "") or ""),
                    country=norm_name(a.get("country", "") or ""),
                    label=_label(a),
                )
            )

        return Contact(
            source_id="google",
            source_uid=person.get("resourceName", ""),
            display_name=display,
            given_name=given,
            family_name=family,
            organization=organization,
            emails=emails,
            phones=phones,
            addresses=addresses,
        )
