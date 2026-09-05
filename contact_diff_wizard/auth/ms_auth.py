"""Microsoft OAuth via MSAL (public client, interactive).

Stub. Planned implementation:
  - msal.PublicClientApplication(client_id, authority, token_cache=...)
  - try acquire_token_silent first, fall back to acquire_token_interactive
  - persist the SerializableTokenCache to a gitignored file
"""

from __future__ import annotations


def acquire_token(client_id: str, authority: str, scopes: list[str],
                  token_path: str) -> str:
    """Return a valid Graph access token, logging in if needed."""
    raise NotImplementedError
