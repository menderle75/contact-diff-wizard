"""Gmail contacts via the Google People API.

Stub — implemented in a later step. Auth: google-auth-oauthlib loopback flow
(`InstalledAppFlow.run_local_server`), token cached to a gitignored file.
"""

from __future__ import annotations

from contact_diff_wizard.model import Contact


class GoogleContactSource:
    id = "google"
    display_name = "Gmail"

    def __init__(self, client_id: str, client_secret: str, scopes: list[str],
                 token_path: str = "google.token.json") -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._scopes = scopes
        self._token_path = token_path

    def is_authenticated(self) -> bool:
        raise NotImplementedError

    def authenticate(self) -> None:
        raise NotImplementedError

    def fetch_contacts(self) -> list[Contact]:
        raise NotImplementedError

    @staticmethod
    def _to_contact(person: dict) -> Contact:
        """Map one People API `person` resource into the neutral model."""
        raise NotImplementedError
