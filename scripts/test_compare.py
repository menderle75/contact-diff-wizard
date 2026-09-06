"""End-to-end compare: Gmail (live) x Outlook (file).

    python scripts/test_compare.py [outlook_file] [fuzzy_threshold]

Prints category counts, the fuzzy-score distribution (to help tune the
threshold), and a few masked sample diffs. No full contact dump.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from contact_diff_wizard.config import load as load_config  # noqa: E402
from contact_diff_wizard.matching.engine import (  # noqa: E402
    DiffCategory,
    compare,
)
from contact_diff_wizard.sources.google import GoogleContactSource  # noqa: E402
from contact_diff_wizard.sources.outlook_file import OutlookFileContactSource  # noqa: E402


def _mask(s: str) -> str:
    s = re.sub(r"\d", "#", s or "")
    return re.sub(r"[^\s@.#+()/,–-]", "•", s)


def main() -> None:
    outlook_path = sys.argv[1] if len(sys.argv) > 1 else "outlook-contacts.csv"
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 90.0

    cfg = load_config()["google"]
    google = GoogleContactSource(
        client_id=cfg["client_id"],
        client_secret=cfg["client_secret"],
        scopes=cfg["scopes"],
        token_path="google.token.json",
    )
    outlook = OutlookFileContactSource(outlook_path)

    print("Fetching Gmail (may open a browser the first time)…")
    probe: list = []
    groups = compare([google, outlook], fuzzy_threshold=threshold, _fuzzy_probe=probe)

    n_google = sum(len(g.members_of("google")) for g in groups)
    n_outlook = sum(len(g.members_of("outlook")) for g in groups)
    print(f"\nGmail contacts:   {n_google}")
    print(f"Outlook contacts: {n_outlook}")
    print(f"Match groups:     {len(groups)}\n")

    cats = Counter(g.category for g in groups)
    only_g = sum(1 for g in groups
                 if g.category is DiffCategory.ONLY_IN_ONE and "google" in g.source_ids)
    only_o = sum(1 for g in groups
                 if g.category is DiffCategory.ONLY_IN_ONE and "outlook" in g.source_ids)
    print(f"  only in Gmail        : {only_g}")
    print(f"  only in Outlook      : {only_o}")
    print(f"  in both, identical   : {cats[DiffCategory.IDENTICAL]}")
    print(f"  in both, diverging   : {cats[DiffCategory.DIVERGING]}")

    reasons = Counter(g.match_reason.split(":")[0] for g in groups
                      if len(g.source_ids) > 1)
    print(f"  matched by           : {dict(reasons)}")

    # fuzzy score distribution
    print("\n  fuzzy best-candidate score distribution (cross-source singletons):")
    buckets = Counter()
    for score, _, _ in probe:
        buckets[min(int(score) // 5 * 5, 100)] += 1
    for lo in sorted(buckets):
        bar = "#" * min(buckets[lo], 60)
        print(f"    {lo:3d}-{lo + 4:3d}: {buckets[lo]:4d} {bar}")
    near = sorted((p for p in probe if 80 <= p[0] < 98), reverse=True)[:12]
    if near:
        print("\n  borderline pairs (score 80–98), masked:")
        for score, a, b in near:
            print(f"    {score:5.1f}  {_mask(a):26}  ~  {_mask(b)}")

    # diverging: which fields
    diverging = [g for g in groups if g.category is DiffCategory.DIVERGING]
    field_hits = Counter(d.field_name for g in diverging for d in g.field_diffs)
    print(f"\n  diverging groups: {len(diverging)}; field appears in a diff:")
    for fname, n in field_hits.most_common():
        print(f"    {n:4d}  {fname}")

    multi = [g for g in groups
             if len(g.members_of("google")) > 1 or len(g.members_of("outlook")) > 1]
    print(f"\n  groups merging multiple contacts from one source: {len(multi)} "
          "(possible in-source duplicates)")


if __name__ == "__main__":
    main()
