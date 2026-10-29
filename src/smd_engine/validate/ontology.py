"""Ontology: valid for named positions, built through a cooperation, tested
for realizability in activity rather than for truth (GP1981)."""

from __future__ import annotations

from typing import Any

from smd_engine.validate.context import Ctx, Finding, board_set, cite_findings


def continuum_ids(o: dict[str, Any]) -> list[tuple[str, str]]:
    """(field, element id) for every id entry of the continuum fields:
    `lives_in`, `covers` and `tempos` (Khaprov, podcast 28.10.2026)."""
    out = [("lives_in", x["id"]) for x in o.get("lives_in", []) if "id" in x]
    out += [("covers", v) for v in o.get("covers", [])]
    out += [("tempos", t["id"]) for t in o.get("tempos", []) if "id" in t]
    return out


@board_set
def check_ontology(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    by_id = ctx.by_id
    seen: set[str] = set()
    for o in ctx.record.get("ontology", []):
        oid = o["id"]
        if oid in seen:
            out.append(Finding("error", oid, "duplicate ontology id"))
        seen.add(oid)
        for pos in o["valid_for"]:
            if by_id.get(pos, {}).get("kind") not in ("position", "place_for_others"):
                out.append(
                    Finding(
                        "error",
                        oid,
                        f"valid_for '{pos}' is not a position or a place for others",
                    )
                )
        for sub in o.get("subjects", []):
            if sub["position"] not in o["valid_for"]:
                out.append(
                    Finding(
                        "warning",
                        oid,
                        f"subject for '{sub['position']}', a position outside valid_for",
                    )
                )
        coop = o.get("cooperation")
        if coop and by_id.get(coop, {}).get("kind") != "cooperation":
            out.append(Finding("error", oid, f"'{coop}' is not a cooperation element"))
        if "test" in o and o["test"] not in ctx.hyps:
            out.append(Finding("error", oid, f"test '{o['test']}' is not a hypothesis"))
        for field, ref in continuum_ids(o):
            if ref not in by_id:
                out.append(
                    Finding(
                        "error",
                        oid,
                        f"{field} '{ref}' is not an element",
                    )
                )
        out += cite_findings(o.get("cites", []), oid, ctx.source_ids)
    return out
