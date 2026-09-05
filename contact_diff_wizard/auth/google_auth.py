"""Google OAuth (Authorization Code + PKCE, loopback redirect).

Stub. Planned implementation:
  - build an InstalledAppFlow from the fixed client_id / client_secret
  - flow.run_local_server(port=0) opens the browser, catches the code
  - persist Credentials to a gitignored token file, refresh on next start
"""

from __future__ import annotations


def load_or_run_flow(client_id: str, client_secret: str, scopes: list[str],
                     token_path: str):
    """Return valid google.oauth2.credentials.Credentials, logging in if needed."""
    raise NotImplementedError
