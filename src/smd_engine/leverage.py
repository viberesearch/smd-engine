"""Hypothesis leverage: which untested hypothesis a refutation would reach furthest.

A proposal for the group, never a decision. For each `untested` hypothesis the
reach is the set of board items a refutation would touch:
- its `targets` (elements);
- its `qualifications` (K);
- the ontology records whose `test` is this hypothesis;
- the theses that `feeds` or are `about` one of its targets;
- the elements one relation away from a target (either end of a relation).

The score is the size of that set. The order is by score, largest first; ties
by id, numbers read as numbers (H2 before H10). Same record, same order: there
is no probability and no weight in it (docs/commands.md, `smd status`)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# The kinds of item in a reach, in the order they are listed.
CATEGORIES = ("targets", "K", "O", "T", "near")


@dataclass(frozen=True)
class Leverage:
    id: str
    score: int
    # how many items of each category the reach holds (CATEGORIES)
    counts: dict[str, int]


def natural_key(text: str) -> list[tuple[int, int, str]]:
    """A sort key that reads digit runs as numbers: H2 before H10."""
    return [
        (0, int(part), "") if part.isdigit() else (1, 0, part)
        for part in re.split(r"(\d+)", text)
        if part
    ]


def reach(record: dict[str, Any], hypothesis: dict[str, Any]) -> dict[str, set[str]]:
    """The items a refutation of `hypothesis` would reach, by category."""
    targets = set(hypothesis.get("targets", []))
    found: dict[str, set[str]] = {
        "targets": set(targets),
        "K": set(hypothesis.get("qualifications", [])),
        "O": {
            o["id"]
            for o in record.get("ontology", [])
            if o.get("test") == hypothesis["id"]
        },
        "T": {
            t["id"]
            for t in record.get("theses", [])
            if targets & (set(t.get("feeds", [])) | set(t.get("about", [])))
        },
        "near": set(),
    }
    for rel in record.get("relations", []):
        if rel["from"] in targets:
            found["near"].add(rel["to"])
        if rel["to"] in targets:
            found["near"].add(rel["from"])
    # an element is counted once, as a target if it is one
    found["near"] -= targets
    return found


def leverage_order(record: dict[str, Any]) -> list[Leverage]:
    """The untested hypotheses of the record, the largest reach first."""
    order = []
    for h in record.get("hypotheses", []):
        if h.get("status") != "untested":
            continue
        found = reach(record, h)
        order.append(
            Leverage(
                h["id"],
                sum(len(v) for v in found.values()),
                {k: len(found[k]) for k in CATEGORIES},
            )
        )
    return sorted(order, key=lambda x: (-x.score, natural_key(x.id)))
