"""Common interface every contact source implements.

The matching / diff layer works with a *list* of these, never with a hard-wired
pair of providers. Auth is intentionally hidden behind the source: whether it is
OAuth (Google, Microsoft) or a CardDAV app password (iCloud, later) is not the
matcher's concern.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from contact_diff_wizard.model import Contact


@runtime_checkable
class ContactSource(Protocol):
    #: short, stable identifier, e.g. "google" / "microsoft"
    id: str
    #: human-readable, already localized where it matters, e.g. "Gmail"
    display_name: str

    def is_authenticated(self) -> bool:
        """True if a usable (cached) token/credential is available."""
        ...

    def authenticate(self) -> None:
        """Run the provider's login flow (opens a browser for OAuth)."""

    def fetch_contacts(self) -> list[Contact]:
        """Return all contacts, already mapped into the neutral model."""
