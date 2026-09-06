"""Turn `MatchGroup`s into rows and side-by-side comparisons for the UI.

Keeps the Streamlit layer dumb: it renders what these functions return.
"""

from __future__ import annotations

import csv
import io

from contact_diff_wizard.matching.engine import DiffCategory, MatchGroup
from contact_diff_wizard.model import Contact

# field order + presentation metadata
FIELD_ORDER = ["name", "organization", "emails", "phones", "addresses"]
FIELD_ICON = {
    "name": "👤",
    "organization": "🏢",
    "emails": "✉️",
    "phones": "☎️",
    "addresses": "📍",
}
FIELD_LABEL = {
    "name": "Name",
    "organization": "Organisation",
    "emails": "E-Mail",
    "phones": "Telefon",
    "addresses": "Adresse",
}


# ---------------------------------------------------------------------------
# value extraction
def _fmt_address(c: Contact) -> list[str]:
    out = []
    for a in c.addresses:
        line = ", ".join(
            p for p in (a.street, f"{a.postal_code} {a.city}".strip(),
                        a.region, a.country) if p and p.strip()
        )
        if line:
            out.append(line)
    return out


def field_values(contacts: list[Contact], field: str) -> list[str]:
    """Merged, de-duplicated display values for one field across contacts."""
    seen: list[str] = []

    def add(v: str) -> None:
        v = v.strip()
        if v and v not in seen:
            seen.append(v)

    for c in contacts:
        if field == "name":
            add(c.display_name)
        elif field == "organization":
            add(c.organization)
        elif field == "emails":
            for e in c.emails:
                add(e.address)
        elif field == "phones":
            for p in c.phones:
                add(p.e164 or p.raw)
        elif field == "addresses":
            for line in _fmt_address(c):
                add(line)
    return seen


# ---------------------------------------------------------------------------
# master list
def _diff_fields(g: MatchGroup) -> list[str]:
    present = {d.field_name for d in g.field_diffs}
    return [f for f in FIELD_ORDER if f in present]


def master_rows(indexed_groups: list[tuple[int, MatchGroup]], category: str,
                left: str = "google", right: str = "outlook") -> list[dict]:
    """One row per group. `indexed_groups` carries the original group index so
    the UI can map a selected row back to its group."""
    rows = []
    for idx, g in indexed_groups:
        name = next((c.display_name for c in g.members if c.display_name), "—")
        org = next((c.organization for c in g.members if c.organization), "")
        if category == "view.diverging":
            df = _diff_fields(g)
            row = {
                "_idx": idx,
                "Name": name,
                "Δ": " ".join(FIELD_ICON[f] for f in df),
                "#": len(df),
                "Organisation": org,
            }
        elif category == "view.identical":
            row = {
                "_idx": idx, "Name": name, "Organisation": org,
                "E-Mail": ", ".join(field_values(g.members, "emails")),
                "Telefon": ", ".join(field_values(g.members, "phones")),
            }
        else:  # only in one source
            row = {
                "_idx": idx, "Name": name, "Organisation": org,
                "E-Mail": ", ".join(field_values(g.members, "emails")),
                "Telefon": ", ".join(field_values(g.members, "phones")),
            }
        rows.append(row)
    rows.sort(key=lambda r: (-(r.get("#", 0)), r["Name"].casefold()))
    return rows


# ---------------------------------------------------------------------------
# detail: side-by-side comparison
def comparison(g: MatchGroup, left: str = "google", right: str = "outlook") -> dict:
    """Structured left/right comparison for one group.

    Returns {name, diff_rows, same_rows} where each row is
    {field, icon, label, left, right, only_one}.
    """
    left_cs = g.members_of(left)
    right_cs = g.members_of(right)
    differing = {d.field_name for d in g.field_diffs}

    diff_rows, same_rows = [], []
    for f in FIELD_ORDER:
        lvals = field_values(left_cs, f)
        rvals = field_values(right_cs, f)
        if not lvals and not rvals:
            continue
        row = {
            "field": f,
            "icon": FIELD_ICON[f],
            "label": FIELD_LABEL[f],
            "left": lvals,
            "right": rvals,
            "only_one": bool(lvals) != bool(rvals),
        }
        if f in differing or (row["only_one"] and g.category is DiffCategory.DIVERGING):
            diff_rows.append(row)
        else:
            same_rows.append(row)

    name = next((c.display_name for c in g.members if c.display_name), "—")
    return {"name": name, "diff_rows": diff_rows, "same_rows": same_rows,
            "category": g.category, "match_reason": g.match_reason}


# ---------------------------------------------------------------------------
def category_counts(groups: list[MatchGroup]) -> dict[str, int]:
    def n(cat, sid=None):
        return sum(
            1 for g in groups
            if g.category is cat and (sid is None or sid in g.source_ids)
        )
    return {
        "only_google": n(DiffCategory.ONLY_IN_ONE, "google"),
        "only_outlook": n(DiffCategory.ONLY_IN_ONE, "outlook"),
        "identical": n(DiffCategory.IDENTICAL),
        "diverging": n(DiffCategory.DIVERGING),
    }


def in_category(g: MatchGroup, category: str) -> bool:
    if category == "view.only_google":
        return g.category is DiffCategory.ONLY_IN_ONE and "google" in g.source_ids
    if category == "view.only_outlook":
        return g.category is DiffCategory.ONLY_IN_ONE and "outlook" in g.source_ids
    if category == "view.identical":
        return g.category is DiffCategory.IDENTICAL
    return g.category is DiffCategory.DIVERGING


# ---------------------------------------------------------------------------
def decisions_csv(rows: list[dict]) -> str:
    """rows: {Kontakt, Feld, Entscheidung, Wert Gmail, Wert Outlook}."""
    buf = io.StringIO()
    w = csv.DictWriter(
        buf, fieldnames=["Kontakt", "Feld", "Entscheidung", "Wert Gmail", "Wert Outlook"]
    )
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()
