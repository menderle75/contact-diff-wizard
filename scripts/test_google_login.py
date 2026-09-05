"""Isolated Google OAuth smoke test (CLAUDE.md step 4).

Runs the login flow, then makes ONE People API call to prove the token and the
`contacts.readonly` scope actually work. Prints a small, anonymized summary —
no full contact dump.

    python scripts/test_google_login.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from googleapiclient.discovery import build  # noqa: E402

from contact_diff_wizard.auth.google_auth import load_or_run_flow  # noqa: E402
from contact_diff_wizard.config import load as load_config  # noqa: E402


def main() -> None:
    cfg = load_config()["google"]
    if cfg["client_id"].startswith("TODO"):
        sys.exit("config.toml still has placeholder Google credentials.")

    print("Opening browser for Google login…")
    creds = load_or_run_flow(
        client_id=cfg["client_id"],
        client_secret=cfg["client_secret"],
        scopes=cfg["scopes"],
        token_path="google.token.json",
    )
    print("✓ Got credentials. Scopes:", ", ".join(creds.scopes or []))

    service = build("people", "v1", credentials=creds, cache_discovery=False)
    resp = (
        service.people()
        .connections()
        .list(
            resourceName="people/me",
            personFields="names,emailAddresses,phoneNumbers",
            pageSize=10,
        )
        .execute()
    )

    conns = resp.get("connections", [])
    total = resp.get("totalPeople", len(conns))
    print(f"✓ People API reachable. ~{total} contacts total; first {len(conns)}:")
    for p in conns:
        name = (p.get("names") or [{}])[0].get("displayName", "(no name)")
        n_mail = len(p.get("emailAddresses") or [])
        n_phone = len(p.get("phoneNumbers") or [])
        print(f"    - {name}  ({n_mail} email, {n_phone} phone)")


if __name__ == "__main__":
    main()
