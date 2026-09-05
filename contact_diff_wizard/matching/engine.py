"""Match contacts across N sources and classify the differences.

Matching strategy (see CLAUDE.md):
  1. primary key   -> normalized email address
  2. secondary key -> normalized phone number (E.164 via `phonenumbers`)
  3. tertiary      -> fuzzy name similarity (rapidfuzz), only when 1 + 2 miss;
                      threshold to be tuned against real test data, not guessed.

Stub — implemented in a later step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from contact_diff_wizard.model import Contact
from contact_diff_wizard.sources.base import ContactSource


class DiffCategory(str, Enum):
    ONLY_IN_ONE = "only_in_one"          # present in exactly one source
    IDENTICAL = "identical"              # in >1 source, all fields equal
    DIVERGING = "diverging"              # in >1 source, some fields differ


@dataclass
class FieldDiff:
    field_name: str
    values_by_source: dict[str, object]  # source id -> value


@dataclass
class MatchGroup:
    """One real-world person, as seen across one or more sources."""

    category: DiffCategory
    contacts_by_source: dict[str, Contact]
    field_diffs: list[FieldDiff] = field(default_factory=list)


def compare(sources: list[ContactSource]) -> list[MatchGroup]:
    """Fetch from every source, match, and return the classified groups."""
    raise NotImplementedError
