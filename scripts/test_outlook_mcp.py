"""Smoke test: Outlook via MCP server vs. the CSV export.

    python scripts/test_outlook_mcp.py [csv_path]

Fetches the contacts live through the ms365 MCP server and cross-checks them
against the CSV export (counts, email/phone coverage, and the compare() category
split against Gmail). Prints only aggregate numbers.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from contact_diff_wizard.config import load as load_config  # noqa: E402
from contact_diff_wizard.matching.engine import DiffCategory, compare  # noqa: E402
from contact_diff_wizard.sources.google import GoogleContactSource  # noqa: E402
from contact_diff_wizard.sources.microsoft_mcp import (  # noqa: E402
    MicrosoftMcpContactSource,
)
from contact_diff_wizard.sources.outlook_file import OutlookFileContactSource  # noqa: E402


def _stats(label, contacts):
    print(f"  {label:6} contacts={len(contacts):4d}  "
          f"email={sum(1 for c in contacts if c.emails):4d}  "
          f"phone={sum(1 for c in contacts if c.phones):4d}  "
          f"e164={sum(1 for c in contacts if any(p.e164 for p in c.phones)):4d}  "
          f"addr={sum(1 for c in contacts if c.addresses):4d}  "
          f"org={sum(1 for c in contacts if c.organization):4d}")


def _split(groups):
    cats = Counter(g.category for g in groups)
    only_g = sum(1 for g in groups if g.category is DiffCategory.ONLY_IN_ONE
                 and "google" in g.source_ids)
    only_o = sum(1 for g in groups if g.category is DiffCategory.ONLY_IN_ONE
                 and "outlook" in g.source_ids)
    return (only_g, only_o, cats[DiffCategory.IDENTICAL], cats[DiffCategory.DIVERGING])


def main() -> None:
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "outlook-contacts.csv"

    mcp_src = MicrosoftMcpContactSource()
    print("login check …")
    mcp_src.authenticate()
    print("fetching via MCP …")
    via_mcp = mcp_src.fetch_contacts()
    via_csv = OutlookFileContactSource(csv_path).fetch_contacts()

    print("\nfield coverage")
    _stats("MCP", via_mcp)
    _stats("CSV", via_csv)

    emails_mcp = {e.address for c in via_mcp for e in c.emails}
    emails_csv = {e.address for c in via_csv for e in c.emails}
    phones_mcp = {p.e164 for c in via_mcp for p in c.phones if p.e164}
    phones_csv = {p.e164 for c in via_csv for p in c.phones if p.e164}
    print("\nset overlap (MCP vs CSV)")
    print(f"  emails: only MCP={len(emails_mcp - emails_csv)}  "
          f"only CSV={len(emails_csv - emails_mcp)}  both={len(emails_mcp & emails_csv)}")
    print(f"  phones: only MCP={len(phones_mcp - phones_csv)}  "
          f"only CSV={len(phones_csv - phones_mcp)}  both={len(phones_mcp & phones_csv)}")

    cfg = load_config()["google"]
    google = GoogleContactSource(cfg["client_id"], cfg["client_secret"],
                                 cfg["scopes"], "google.token.json")
    print("\ncompare vs Gmail  (only-Gmail, only-Outlook, identical, diverging)")

    class _Fixed:
        id = "outlook"
        display_name = "Outlook"

        def __init__(self, contacts):
            self._c = contacts

        def is_authenticated(self):
            return True

        def authenticate(self):
            pass

        def fetch_contacts(self):
            return self._c

    print("  MCP:", _split(compare([google, _Fixed(via_mcp)])))
    print("  CSV:", _split(compare([google, _Fixed(via_csv)])))


if __name__ == "__main__":
    main()
