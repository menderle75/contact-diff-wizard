"""Smoke test for the Outlook file importer.

    python scripts/test_outlook_import.py [path]     (default: outlook-contacts.csv)

Prints an anonymized summary — counts and field-coverage, plus 5 sample
contacts with names/domains masked.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from contact_diff_wizard.sources.outlook_file import OutlookFileContactSource  # noqa: E402


def _mask(s: str) -> str:
    s = re.sub(r"\d", "#", s)
    return re.sub(r"[^\s@.#+()/-]", "•", s)


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "outlook-contacts.csv"
    contacts = OutlookFileContactSource(path).fetch_contacts()

    print(f"Parsed {len(contacts)} contacts from {path}\n")

    with_email = sum(1 for c in contacts if c.emails)
    with_phone = sum(1 for c in contacts if c.phones)
    with_e164 = sum(1 for c in contacts if any(p.e164 for p in c.phones))
    with_addr = sum(1 for c in contacts if c.addresses)
    no_name = sum(1 for c in contacts if not c.display_name)
    print(f"  with >=1 email      : {with_email}")
    print(f"  with >=1 phone      : {with_phone}")
    print(f"  phone parsed to E164: {with_e164}")
    print(f"  with >=1 address    : {with_addr}")
    print(f"  without display name: {no_name}")

    total_phones = sum(len(c.phones) for c in contacts)
    unparsed = [p.raw for c in contacts for p in c.phones if not p.e164]
    print(f"\n  phone numbers total : {total_phones}, unparsed: {len(unparsed)}")
    if unparsed:
        print("  unparsed samples    :", [_mask(x) for x in unparsed[:8]])

    label_counts = Counter(p.label.value for c in contacts for p in c.phones)
    print("  phone label split   :", dict(label_counts))

    print("\n  sample contacts (masked):")
    for c in contacts[:5]:
        doms = [e.address.split("@", 1)[1] for e in c.emails if "@" in e.address]
        print(
            f"    - {_mask(c.display_name):28} "
            f"org={_mask(c.organization)[:20]:20} "
            f"emails={doms} "
            f"phones={[p.e164 or _mask(p.raw) for p in c.phones]}"
        )


if __name__ == "__main__":
    main()
