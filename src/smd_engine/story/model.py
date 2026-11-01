"""The boards a story reads: board sets merged, their typed links, and the text
and epistemic level of every id a sentence may cite.

A story is a view. Nothing here writes a board."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any

from smd_engine import redline
from smd_engine.records import RecordError, load_record
from smd_engine.story.numbers import Date, parse
from smd_engine.validate import validate_record

# The epistemic levels, weakest first (G2).
LEVELS = ("hypothesis", "unverified", "stated", "checked")
# A link that does not say what passes or what is made: weak, marked as such.
WEAK_KINDS = ("refers",)
# The lists of a board set that a story can cite, merged across board sets.
LISTS = ("elements", "relations", "hypotheses", "theses", "qualifications", "ontology")
# Fields that hold ids or structure, not what an item says.
STRUCTURE = {
    "id",
    "board",
    "half",
    "kind",
    "from",
    "to",
    "seen_from",
    "performed_by",
    "in",
    "cites",
    "geom",
    "targets",
    "qualifications",
    "feeds",
    "about",
    "raises",
    "valid_for",
    "cooperation",
    "test",
    "covers",
    "artefacts",
    "artefact",
    "raised_in",
    "resolved_in",
    "closed_in",
    "arises_from",
    "assigned_by",
    "lineage",
    "tags",
}
# Thesis statuses that count as said by the group or accepted by it.
THESIS_STATED = {"voiced", "refined"}


@dataclass(frozen=True)
class Link:
    """A relation of the boards, between two elements."""

    a: str
    b: str
    kind: str
    carries: str | None = None
    label: str = ""

    @property
    def weak(self) -> bool:
        return self.kind in WEAK_KINDS


@dataclass
class Boards:
    """Board sets read together."""

    record: dict[str, Any]
    stamps: list[dict[str, str]]
    elements: dict[str, dict[str, Any]]
    # every id a sentence can cite -> (family, item)
    items: dict[str, tuple[str, dict[str, Any]]]
    links: list[Link]
    dates: dict[str, str] = field(default_factory=dict)
    _numbers: dict[str, tuple[set[Fraction], set[Date]]] = field(default_factory=dict)

    def label(self, item_id: str) -> str:
        """What the item says about itself, for lists."""
        item = self.items[item_id][1]
        for key in ("label", "claim", "assumes", "text", "object"):
            if item.get(key):
                return " ".join(str(item[key]).split())
        return item_id

    def level(self, item_id: str) -> str:
        """The strongest level a sentence resting on this id may claim."""
        family, item = self.items[item_id]
        if family == "hypothesis":
            return (
                "checked"
                if item.get("status") in ("confirmed", "refuted")
                else ("hypothesis")
            )
        if family == "thesis":
            return "stated" if item.get("status") in THESIS_STATED else "hypothesis"
        if family == "qualification":
            return "stated" if item.get("status") == "closed" else "hypothesis"
        if family == "ontology":
            test = self.items.get(str(item.get("test", "")))
            return self.level(item["test"]) if test else "stated"
        return str(item.get("epistemic", "stated"))

    def numbers(self, item_id: str) -> set[Fraction]:
        """Every loose number the item holds, in its words and its fields; for a
        red line also the days its breaches span. Parts of dates are not
        among them."""
        return self._facts(item_id)[0]

    def date_facts(self, item_id: str) -> set[Date]:
        """Every whole date the item holds, in its words and fields; for a red
        line also the first and last day of its breaches."""
        return self._facts(item_id)[1]

    def _facts(self, item_id: str) -> tuple[set[Fraction], set[Date]]:
        if item_id not in self._numbers:
            family, item = self.items[item_id]
            # " | " keeps a date from forming across two fields
            numbers, dates = parse(" | ".join(_strings(item)))
            found, known = set(numbers), set(dates)
            if family == "element" and item.get("line"):
                for b in redline.breaches(item, self.dates.get(item_id) or None):
                    more, days = parse(f"{b.days} | {b.start} | {b.end}")
                    found |= set(more)
                    known |= set(days)
            self._numbers[item_id] = (found, known)
        return self._numbers[item_id]


def _strings(value: Any) -> list[str]:
    """The words and numbers of an item as text; ids and structure left out."""
    if isinstance(value, dict):
        return [s for k, v in value.items() if k not in STRUCTURE for s in _strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    if isinstance(value, bool) or value is None:
        return []
    return [str(value)]


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_boards(
    paths: list[Path],
    source_kinds: dict[str, str] | None = None,
    taxonomies: dict[str, set[str]] | None = None,
) -> Boards:
    """Read and validate board sets and merge them. An error in a board set, or
    one id in two of them, is a RecordError. With the kinds of a source
    manifest (source id to kind) the citations are checked, with taxonomies the
    tags, as `smd validate` does."""
    source_ids = None if source_kinds is None else set(source_kinds)
    merged: dict[str, Any] = {k: [] for k in LISTS}
    stamps: list[dict[str, str]] = []
    owner: dict[str, str] = {}
    dates: dict[str, str] = {}
    for path in paths:
        data = load_record(path)
        if data["record"] != "board_set":
            raise RecordError(f"{path}: a story reads board sets")
        findings = validate_record(data, source_ids, None, taxonomies, source_kinds)
        errors = [f for f in findings if f.level == "error"]
        if errors:
            raise RecordError(f"{path}: invalid board set: {errors[0]}")
        stamps.append(
            {
                "id": data["id"],
                "version": str(data.get("state", {}).get("version", data["cycle"])),
                "sha256": sha256_of(path),
            }
        )
        for key in LISTS:
            for item in data.get(key, []):
                if key != "relations":
                    other = owner.setdefault(item["id"], data["id"])
                    if other != data["id"]:
                        raise RecordError(
                            f"id {item['id']} is in board sets {other} and "
                            f"{data['id']}: a story reads board sets of one case "
                            "that do not repeat ids"
                        )
                    dates[item["id"]] = str(data.get("date", ""))
                merged[key].append(item)
    for key, value in (
        ("record", "board_set"),
        ("id", "+".join(s["id"] for s in stamps)),
    ):
        merged[key] = value
    return _index(merged, stamps, dates)


def _index(
    record: dict[str, Any], stamps: list[dict[str, str]], dates: dict[str, str]
) -> Boards:
    elements = {e["id"]: e for e in record["elements"]}
    items: dict[str, tuple[str, dict[str, Any]]] = {}
    for family, key in (
        ("element", "elements"),
        ("hypothesis", "hypotheses"),
        ("thesis", "theses"),
        ("qualification", "qualifications"),
        ("ontology", "ontology"),
    ):
        for item in record[key]:
            items[item["id"]] = (family, item)
    links = [
        Link(r["from"], r["to"], r["kind"], r.get("carries"), r.get("label", ""))
        for r in record["relations"]
        if r["from"] in elements and r["to"] in elements
    ]
    return Boards(record, stamps, elements, items, links, dates)
