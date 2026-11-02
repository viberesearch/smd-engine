"""Elements an `ids` item points at, grouped by the element their relations lead
to (the question a hypothesis answers). Shared by `pack.html` and `pack.md`."""

from __future__ import annotations

from typing import Any


def ref_groups(
    ontology: dict[str, Any], refs: list[str] | None
) -> list[tuple[str | None, list[tuple[str, str]]]]:
    """[(label of the target or None, [(id, label), ...])]. Groups follow the
    order of their targets among the elements, refs keep the order of the item.
    Refs with no relation come last under the heading None. With no refs, every
    element is offered."""
    names = {e["id"]: e["label"] for e in ontology["elements"]}
    chosen = [r for r in (refs or names) if r in names]
    target: dict[str, str] = {}
    for rel in ontology["relations"]:
        if rel["from"] in names and rel["to"] in names:
            target.setdefault(rel["from"], rel["to"])
    groups: list[tuple[str | None, list[tuple[str, str]]]] = []
    for tid in names:
        members = [(r, names[r]) for r in chosen if target.get(r) == tid]
        if members:
            groups.append((names[tid], members))
    rest = [(r, names[r]) for r in chosen if r not in target]
    if rest:
        groups.append((None, rest))
    return groups
