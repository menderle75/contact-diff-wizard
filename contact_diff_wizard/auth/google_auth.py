"""Google OAuth — Authorization Code + PKCE via a local loopback redirect.

Uses google-auth-oauthlib's InstalledAppFlow: it spins up a throwaway local
web server, opens the system browser to Google's consent screen, catches the
redirect with the authorization code, and exchanges it for credentials. The
resulting credentials (incl. refresh token) are cached to a gitignored JSON
file and silently refreshed on later starts.
"""

from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
_TOKEN_URI = "https://oauth2.googleapis.com/token"


def _client_config(client_id: str, client_secret: str) -> dict:
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": _AUTH_URI,
            "token_uri": _TOKEN_URI,
        }
    }


def load_or_run_flow(
    client_id: str,
    client_secret: str,
    scopes: list[str],
    token_path: str,
) -> Credentials:
    """Return valid Credentials, running the browser login only if needed."""
    path = Path(token_path)
    creds: Credentials | None = None

    if path.exists():
        creds = Credentials.from_authorized_user_file(str(path), scopes)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        path.write_text(creds.to_json(), encoding="utf-8")
        return creds

    flow = InstalledAppFlow.from_client_config(
        _client_config(client_id, client_secret), scopes
    )
    # port=0 -> pick a free port; redirect URI becomes http://localhost:<port>/
    creds = flow.run_local_server(port=0, prompt="consent")
    path.write_text(creds.to_json(), encoding="utf-8")
    return creds
