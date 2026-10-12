"""Outlook contacts live, via a local Microsoft 365 MCP server.

Instead of an exported file, the app starts the `@softeria/ms-365-mcp-server`
(MCP over stdio) as a child process and calls its `list-outlook-contacts` tool.
The server brings its own app registration and keeps its own login cache, so
neither an Azure tenant nor a client id of ours is needed.

Requires Node (`npx`). Optional alternative to the file import: both produce the
same neutral `Contact` objects with source id "outlook".
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable
from typing import TypeVar

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from contact_diff_wizard.model import (
    Contact,
    EmailAddress,
    FieldLabel,
    PhoneNumber,
    PostalAddress,
)
from contact_diff_wizard.normalize import norm_email, norm_name, norm_phone
from contact_diff_wizard.sources.outlook_file import (
    _dedupe_emails,
    _dedupe_phones,
    _uid,
)

DEFAULT_COMMAND = "npx"
DEFAULT_ARGS = ("-y", "@softeria/ms-365-mcp-server")

_SELECT = (
    "id,displayName,givenName,middleName,surname,companyName,emailAddresses,"
    "mobilePhone,homePhones,businessPhones,homeAddress,businessAddress,otherAddress"
)

_ADDRESS_FIELDS: list[tuple[str, FieldLabel]] = [
    ("homeAddress", FieldLabel.HOME),
    ("businessAddress", FieldLabel.WORK),
    ("otherAddress", FieldLabel.OTHER),
]

T = TypeVar("T")


class MicrosoftMcpError(RuntimeError):
    """The MCP server is missing, not logged in, or returned an error."""


def _run(coro: Awaitable[T]) -> T:
    # Streamlit's script thread has no running event loop, so asyncio.run is fine.
    return asyncio.run(coro)  # type: ignore[arg-type]


class MicrosoftMcpContactSource:
    id = "outlook"
    display_name = "Outlook"

    def __init__(
        self,
        command: str = DEFAULT_COMMAND,
        args: tuple[str, ...] = DEFAULT_ARGS,
    ) -> None:
        self._params = StdioServerParameters(command=command, args=list(args))

    # --- ContactSource protocol ----------------------------------------
    def login_status(self) -> tuple[bool, str]:
        """(logged_in, account-or-error-message). Never raises."""
        try:
            return _run(self._check_login())
        except FileNotFoundError:
            return False, f"'{self._params.command}' not found (Node.js required)"
        except Exception as exc:  # noqa: BLE001 - surface any startup failure
            return False, str(exc) or type(exc).__name__

    def is_authenticated(self) -> bool:
        return self.login_status()[0]

    def authenticate(self) -> None:
        ok, message = self.login_status()
        if not ok:
            raise MicrosoftMcpError(message)

    def fetch_contacts(self) -> list[Contact]:
        return _run(self._fetch())

    # --- MCP calls -------------------------------------------------------
    async def _call(self, session: ClientSession, tool: str, arguments: dict) -> str:
        res = await session.call_tool(tool, arguments)
        text = "".join(getattr(c, "text", "") for c in res.content)
        if res.is_error:
            raise MicrosoftMcpError(f"{tool}: {text[:300]}")
        return text

    async def _check_login(self) -> tuple[bool, str]:
        async with stdio_client(self._params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                text = await self._call(session, "verify-login", {})
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    return False, text[:300]
                if data.get("success"):
                    user = (data.get("userData") or {}).get("userPrincipalName", "")
                    return True, user
                return False, data.get("message", text[:300])

    async def _fetch(self) -> list[Contact]:
        async with stdio_client(self._params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                text = await self._call(
                    session,
                    "list-outlook-contacts",
                    {"top": 100, "fetchAllPages": True, "select": _SELECT},
                )
        data = json.loads(text)
        items = data.get("value", []) if isinstance(data, dict) else data
        return [c for c in (self._to_contact(i) for i in items) if c is not None]

    # --- mapping ---------------------------------------------------------
    @staticmethod
    def _to_contact(item: dict) -> Contact | None:
        given = norm_name(item.get("givenName") or "")
        family = norm_name(item.get("surname") or "")
        middle = norm_name(item.get("middleName") or "")
        display = norm_name(
            " ".join(p for p in (given, middle, family) if p)
        ) or norm_name(item.get("displayName") or "") or norm_name(
            item.get("companyName") or ""
        )

        emails = _dedupe_emails(
            [
                EmailAddress(address=addr)
                for e in item.get("emailAddresses") or []
                if (addr := norm_email(e.get("address") or ""))
            ]
        )

        phone_sources: list[tuple[str, FieldLabel]] = []
        if item.get("mobilePhone"):
            phone_sources.append((item["mobilePhone"], FieldLabel.MOBILE))
        phone_sources += [(p, FieldLabel.HOME) for p in item.get("homePhones") or []]
        phone_sources += [(p, FieldLabel.WORK) for p in item.get("businessPhones") or []]
        phones = _dedupe_phones(
            [
                PhoneNumber(raw=raw.strip(), e164=norm_phone(raw), label=label)
                for raw, label in phone_sources
                if raw and raw.strip()
            ]
        )

        addresses: list[PostalAddress] = []
        for key, label in _ADDRESS_FIELDS:
            a = item.get(key) or {}
            street = (a.get("street") or "").strip()
            city = (a.get("city") or "").strip()
            postal = (a.get("postalCode") or "").strip()
            region = (a.get("state") or "").strip()
            country = (a.get("countryOrRegion") or "").strip()
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

        if not (display or emails or phones):
            return None

        return Contact(
            source_id="outlook",
            source_uid=item.get("id") or _uid(display, emails, phones),
            display_name=display,
            given_name=given,
            family_name=family,
            organization=norm_name(item.get("companyName") or ""),
            emails=emails,
            phones=phones,
            addresses=addresses,
        )
