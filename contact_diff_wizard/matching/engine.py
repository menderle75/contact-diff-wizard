"""Match contacts across N sources and classify the differences.

Matching strategy (see CLAUDE.md):
  1. primary key   -> normalized email address (exact)
  2. secondary key -> normalized phone number, E.164 (exact)
  3. tertiary      -> fuzzy display-name similarity (rapidfuzz), ONLY between
                      contacts that stayed unmatched after 1 + 2, only across
                      different sources, and only when the best candidate is
                      unambiguous (clear gap to the runner-up).

The fuzzy threshold is deliberately a parameter — it must be tuned against real
data, not guessed. `scripts/test_compare.py` prints the score distribution to
support that.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from rapidfuzz import fuzz, process

from contact_diff_wizard.model import Contact
from contact_diff_wizard.sources.base import ContactSource

# ---------------------------------------------------------------------------
# tuning knobs
DEFAULT_FUZZY_THRESHOLD = 90.0   # 0..100, rapidfuzz token_sort_ratio
FUZZY_MIN_GAP = 8.0              # best must beat runner-up by this much
NAME_EQUIV_THRESHOLD = 85.0      # names this similar count as "the same name"
PHONE_MATCH_MIN_NAME_SIM = 45.0  # below this, a shared phone != same person
# ---------------------------------------------------------------------------

# Honorifics / titles that one source keeps in the display name and the other
# drops (Google People often prefixes "Herr"/"Frau"; the Outlook CSV puts them
# in a separate "Title" column we don't fold into the name). Stripped for
# comparison only — the original display name is kept for display.
_HONORIFICS = {
    "herr", "frau", "hr", "fr", "fräulein", "frl", "frl.",
    "dr", "dr.", "prof", "prof.", "med", "med.", "dipl", "dipl.",
    "ing", "ing.", "mag", "mag.", "phd", "msc", "bsc",
    "mr", "mr.", "mrs", "mrs.", "ms", "ms.", "mx", "mx.",
}
_NAME_PUNCT = str.maketrans({",": " ", ".": " ", "-": " ", "_": " "})


def _name_for_compare(s: str) -> str:
    toks = s.casefold().translate(_NAME_PUNCT).split()
    while toks and toks[0] in _HONORIFICS:
        toks.pop(0)
    while toks and toks[-1] in _HONORIFICS:
        toks.pop()
    return " ".join(toks)


def _names_equivalent(a: str, b: str) -> bool:
    ca, cb = _name_for_compare(a), _name_for_compare(b)
    if not ca or not cb:
        return True  # one side unnamed -> not a conflict
    return fuzz.token_sort_ratio(ca, cb) >= NAME_EQUIV_THRESHOLD


class DiffCategory(str, Enum):
    ONLY_IN_ONE = "only_in_one"   # present in exactly one source
    IDENTICAL = "identical"       # in >1 source, all compared fields equal
    DIVERGING = "diverging"       # in >1 source, some fields differ


@dataclass
class FieldDiff:
    field_name: str
    values_by_source: dict[str, str]   # source id -> human-readable value


@dataclass
class MatchGroup:
    """One real-world person, as seen across one or more sources."""

    category: DiffCategory
    members: list[Contact]                       # 1..n, may repeat a source
    field_diffs: list[FieldDiff] = field(default_factory=list)
    match_reason: str = ""                       # "email" | "phone" | "fuzzy:NN"

    @property
    def source_ids(self) -> set[str]:
        return {c.source_id for c in self.members}

    def members_of(self, source_id: str) -> list[Contact]:
        return [c for c in self.members if c.source_id == source_id]


# ---------------------------------------------------------------------------
# union-find over contact indices
class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


# ---------------------------------------------------------------------------
# field extraction for the diff
def _email_set(c: Contact) -> set[str]:
    return {e.address for e in c.emails if e.address}


def _phone_set(c: Contact) -> set[str]:
    return {p.e164 for p in c.phones if p.e164}


ADDRESS_EQUIV_THRESHOLD = 82.0  # token_sort_ratio above which two addresses
#                                 count as "the same address, formatted differently"


def _addr_set(c: Contact) -> set[str]:
    """Normalized address strings: alnum tokens, sorted, lowercased.

    Sorting the tokens makes the comparison order-insensitive (Google and
    Outlook put street / number / city / country in different orders).
    """
    out = set()
    for a in c.addresses:
        raw = " ".join(
            p for p in (a.street, a.postal_code, a.city, a.region, a.country) if p
        )
        toks = sorted(t for t in re.split(r"[^0-9a-zäöüß]+", raw.casefold()) if t)
        if toks:
            out.add(" ".join(toks))
    return out


def _addr_norm(a) -> str:
    raw = " ".join(
        p for p in (a.street, a.postal_code, a.city, a.region, a.country) if p
    )
    toks = sorted(t for t in re.split(r"[^0-9a-zäöüß]+", raw.casefold()) if t)
    return " ".join(toks)


def _addr_by_label(contacts: list[Contact]) -> dict[str, set[str]]:
    """label value -> set of normalized address strings, merged across contacts."""
    out: dict[str, set[str]] = {}
    for c in contacts:
        for a in c.addresses:
            key = _addr_norm(a)
            if key:
                out.setdefault(a.label.value, set()).add(key)
    return out


def _addr_sets_equivalent(sets: list[set[str]]) -> bool:
    """True if every address in each set has a fuzzy partner in every other set."""
    for i in range(len(sets)):
        for j in range(len(sets)):
            if i == j:
                continue
            for a in sets[i]:
                if not any(
                    fuzz.token_sort_ratio(a, b) >= ADDRESS_EQUIV_THRESHOLD
                    for b in sets[j]
                ):
                    return False
    return True


def addresses_equivalent(a: list, b: list) -> bool:
    """a, b: lists of PostalAddress already filtered to the same label.

    True if they describe the same place(s) (formatting/order ignored). Empty
    on one side only -> not equivalent; empty on both -> equivalent.
    """
    sa = {k for k in (_addr_norm(x) for x in a) if k}
    sb = {k for k in (_addr_norm(x) for x in b) if k}
    if not sa or not sb:
        return not sa and not sb
    return _addr_sets_equivalent([sa, sb])


def addresses_differ(left: list[Contact], right: list[Contact]) -> bool:
    """Compare addresses *per label* (home↔home, work↔work).

    A divergence is only a genuine conflict when both sides carry an address of
    the *same* type and those differ. An address type present on just one side
    is extra information, not a conflict — and a private address must never be
    diffed against a business address.
    """
    lbl_left = _addr_by_label(left)
    lbl_right = _addr_by_label(right)
    for label in set(lbl_left) & set(lbl_right):
        if not _addr_sets_equivalent([lbl_left[label], lbl_right[label]]):
            return True
    return False


def _org_key(c: Contact) -> str:
    return c.organization.casefold()


def _merge_sets(contacts: list[Contact], fn) -> set[str]:
    out: set[str] = set()
    for c in contacts:
        out |= fn(c)
    return out


def _compare_group(members: list[Contact], source_ids: list[str]) -> list[FieldDiff]:
    """Compare each field across sources; emit a FieldDiff where they disagree."""
    by_source: dict[str, list[Contact]] = {
        sid: [c for c in members if c.source_id == sid] for sid in source_ids
    }
    diffs: list[FieldDiff] = []

    # --- names: disagree only if no cross-source pair is even fuzzily equal
    named = {sid: [c.display_name for c in cs if c.display_name]
             for sid, cs in by_source.items()}
    with_names = [sid for sid, ns in named.items() if ns]
    if len(with_names) > 1:
        any_equiv = any(
            _names_equivalent(a, b)
            for x in range(len(with_names))
            for y in range(x + 1, len(with_names))
            for a in named[with_names[x]]
            for b in named[with_names[y]]
        )
        if not any_equiv:
            diffs.append(FieldDiff(
                "name",
                {sid: " / ".join(sorted(set(ns))) if ns else "—"
                 for sid, ns in named.items()},
            ))

    # --- organization: same rule
    orgs = {sid: {_org_key(c) for c in cs if c.organization}
            for sid, cs in by_source.items()}
    present = [o for o in orgs.values() if o]
    if len(present) > 1 and not set.intersection(*present):
        diffs.append(FieldDiff(
            "organization",
            {sid: " / ".join(sorted(c.organization for c in cs if c.organization))
             for sid, cs in by_source.items()},
        ))

    # --- emails + phones: exact set comparison
    for fname, fn in (("emails", _email_set), ("phones", _phone_set)):
        sets_by_source = {sid: _merge_sets(cs, fn) for sid, cs in by_source.items()}
        non_empty = [s for s in sets_by_source.values() if s]
        if len(non_empty) < 2:
            continue  # only one source has any value -> not a "divergence"
        if any(a != b for a in non_empty for b in non_empty):
            diffs.append(FieldDiff(
                fname,
                {sid: ", ".join(sorted(s)) if s else "—"
                 for sid, s in sets_by_source.items()},
            ))

    # --- addresses: compared per label (see addresses_differ)
    src_with_addr = [sid for sid, cs in by_source.items()
                     if any(c.addresses for c in cs)]
    if any(
        addresses_differ(by_source[src_with_addr[i]], by_source[src_with_addr[j]])
        for i in range(len(src_with_addr))
        for j in range(i + 1, len(src_with_addr))
    ):
        diffs.append(FieldDiff(
            "addresses",
            {sid: ", ".join(sorted(_merge_sets(cs, _addr_set))) or "—"
             for sid, cs in by_source.items()},
        ))

    return diffs


# ---------------------------------------------------------------------------
def compare(
    sources: list[ContactSource],
    fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD,
    _fuzzy_probe: list | None = None,
) -> list[MatchGroup]:
    """Fetch from every source, match, and return the classified groups.

    `_fuzzy_probe`, if given, is filled with (score, name_a, name_b) tuples for
    every cross-source best-candidate pair considered — used only for threshold
    tuning in the test script.
    """
    all_contacts: list[Contact] = []
    for src in sources:
        all_contacts.extend(src.fetch_contacts())

    n = len(all_contacts)
    uf = _UnionFind(n)
    reason: dict[int, str] = {}

    # --- 1: exact email -------------------------------------------------
    email_buckets: dict[str, list[int]] = {}
    for i, c in enumerate(all_contacts):
        for val in _email_set(c):
            email_buckets.setdefault(val, []).append(i)
    for idxs in email_buckets.values():
        for j in idxs[1:]:
            uf.union(idxs[0], j)
            reason.setdefault(uf.find(idxs[0]), "email")

    # --- 2: exact phone (E.164), but a shared number only means "same
    #        person" when the names are at least loosely compatible — a
    #        household landline is not a match.
    phone_buckets: dict[str, list[int]] = {}
    for i, c in enumerate(all_contacts):
        for val in _phone_set(c):
            phone_buckets.setdefault(val, []).append(i)
    for idxs in phone_buckets.values():
        for a_pos in range(len(idxs)):
            for b_pos in range(a_pos + 1, len(idxs)):
                i, j = idxs[a_pos], idxs[b_pos]
                if uf.find(i) == uf.find(j):
                    continue
                na = _name_for_compare(all_contacts[i].display_name)
                nb = _name_for_compare(all_contacts[j].display_name)
                if na and nb and fuzz.token_set_ratio(na, nb) < PHONE_MATCH_MIN_NAME_SIM:
                    continue
                uf.union(i, j)
                reason.setdefault(uf.find(i), "phone")

    # --- 3: fuzzy name, only for still-singleton contacts ---------------
    comp_size: dict[int, int] = {}
    for i in range(n):
        comp_size[uf.find(i)] = comp_size.get(uf.find(i), 0) + 1
    singletons = [i for i in range(n) if comp_size[uf.find(i)] == 1
                  and all_contacts[i].display_name]

    by_src: dict[str, list[int]] = {}
    for i in singletons:
        by_src.setdefault(all_contacts[i].source_id, []).append(i)

    src_ids = list(by_src)
    for a in range(len(src_ids)):
        for b in range(a + 1, len(src_ids)):
            left = by_src[src_ids[a]]
            right = by_src[src_ids[b]]
            right_keys = [_name_for_compare(all_contacts[i].display_name) for i in right]
            for i in left:
                key = _name_for_compare(all_contacts[i].display_name)
                if not key:
                    continue
                ranked = process.extract(
                    key, right_keys, scorer=fuzz.token_sort_ratio, limit=2
                )
                if not ranked:
                    continue
                best = ranked[0]
                if _fuzzy_probe is not None:
                    _fuzzy_probe.append(
                        (best[1], all_contacts[i].display_name,
                         all_contacts[right[best[2]]].display_name)
                    )
                runner = ranked[1][1] if len(ranked) > 1 else 0.0
                if best[1] >= fuzzy_threshold and (best[1] - runner) >= FUZZY_MIN_GAP:
                    j = right[best[2]]
                    uf.union(i, j)
                    reason.setdefault(uf.find(i), f"fuzzy:{int(best[1])}")

    # --- assemble groups ----------------------------------------------
    groups_idx: dict[int, list[int]] = {}
    for i in range(n):
        groups_idx.setdefault(uf.find(i), []).append(i)

    all_source_ids = [s.id for s in sources]
    result: list[MatchGroup] = []
    for root, idxs in groups_idx.items():
        members = [all_contacts[i] for i in idxs]
        present_sources = {c.source_id for c in members}
        if len(present_sources) == 1:
            result.append(MatchGroup(DiffCategory.ONLY_IN_ONE, members,
                                     match_reason=reason.get(root, "")))
            continue
        diffs = _compare_group(members, all_source_ids)
        cat = DiffCategory.DIVERGING if diffs else DiffCategory.IDENTICAL
        result.append(MatchGroup(cat, members, diffs, reason.get(root, "")))

    return result
