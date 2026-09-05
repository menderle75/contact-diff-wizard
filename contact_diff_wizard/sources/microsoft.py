"""Outlook contacts via Microsoft Graph.

Stub — implemented in a later step. Auth: MSAL public-client flow
(`acquire_token_interactive`), token cached via MSAL's SerializableTokenCache
to a gitignored file.
"""

from __future__ import annotations

from contact_diff_wizard.model import Contact

GRAPH_CONTACTS_URL = "https://graph.microsoft.com/v1.0/me/contacts"


class MicrosoftContactSource:
    id = "microsoft"
    display_name = "Outlook"

    def __init__(self, client_id: str, authority: str, scopes: list[str],
                 token_path: str = "microsoft.token.json") -> None:
        self._client_id = client_id
        self._authority = authority
        self._scopes = scopes
        self._token_path = token_path

    def is_authenticated(self) -> bool:
        raise NotImplementedError

    def authenticate(self) -> None:
        raise NotImplementedError

    def fetch_contacts(self) -> list[Contact]:
        raise NotImplementedError

    @staticmethod
    def _to_contact(item: dict) -> Contact:
        """Map one Graph `contact` resource into the neutral model."""
        raise NotImplementedError
