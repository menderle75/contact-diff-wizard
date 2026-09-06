"""Turn `MatchGroup`s into flat rows for the UI.

Keeps the Streamlit layer dumb: it only renders tables of dicts produced here.
"""

from __future__ import annotations

from contact_diff_wizard.matching.engine import DiffCategory, MatchGroup
from contact_diff_wizard.model import Contact


def _emails(c: Contact) -> str:
    return ", ".join(e.address for e in c.emails)


def _phones(c: Contact) -> str:
    return ", ".join(p.e164 or p.raw for p in c.phones)


def _contact_row(c: Contact) -> dict:
    return {
        "Name": c.display_name,
        "Organisation": c.organization,
        "E-Mail": _emails(c),
        "Telefon": _phones(c),
    }


def only_in(groups: list[MatchGroup], source_id: str) -> list[dict]:
    rows = []
    for g in groups:
        if g.category is DiffCategory.ONLY_IN_ONE and source_id in g.source_ids:
            rows.extend(_contact_row(c) for c in g.members)
    rows.sort(key=lambda r: r["Name"].casefold())
    return rows


def identical(groups: list[MatchGroup]) -> list[dict]:
    rows = []
    for g in groups:
        if g.category is DiffCategory.IDENTICAL:
            # one representative row (fields agree by definition)
            rows.append(_contact_row(g.members[0]))
    rows.sort(key=lambda r: r["Name"].casefold())
    return rows


_FIELD_LABELS = {
    "name": "Name",
    "organization": "Organisation",
    "emails": "E-Mail",
    "phones": "Telefon",
    "addresses": "Adresse",
}


def diverging_rows(
    groups: list[MatchGroup],
    left: str = "google",
    right: str = "outlook",
    left_label: str = "Gmail",
    right_label: str = "Outlook",
) -> list[dict]:
    """One row per differing field of each diverging contact."""
    rows = []
    for g in groups:
        if g.category is not DiffCategory.DIVERGING:
            continue
        who = next((c.display_name for c in g.members if c.display_name), "—")
        for d in g.field_diffs:
            rows.append(
                {
                    "Kontakt": who,
                    "Feld": _FIELD_LABELS.get(d.field_name, d.field_name),
                    left_label: d.values_by_source.get(left, "—"),
                    right_label: d.values_by_source.get(right, "—"),
                }
            )
    rows.sort(key=lambda r: (r["Kontakt"].casefold(), r["Feld"]))
    return rows


def category_counts(groups: list[MatchGroup]) -> dict[str, int]:
    only_g = sum(1 for g in groups
                 if g.category is DiffCategory.ONLY_IN_ONE and "google" in g.source_ids)
    only_o = sum(1 for g in groups
                 if g.category is DiffCategory.ONLY_IN_ONE and "outlook" in g.source_ids)
    identical_n = sum(1 for g in groups if g.category is DiffCategory.IDENTICAL)
    diverging_n = sum(1 for g in groups if g.category is DiffCategory.DIVERGING)
    return {
        "only_google": only_g,
        "only_outlook": only_o,
        "identical": identical_n,
        "diverging": diverging_n,
    }
