"""Ontology: valid for named positions, built through a cooperation, tested
for realizability in activity rather than for truth (GP1981)."""

from __future__ import annotations

from typing import Any

from smd_engine.validate.context import (
    Ctx,
    Finding,
    board_set,
    cite_findings,
    hint,
    is_ai,
)

# The loss column of a translation table (stakeholder-ontology.md §5), by its
# header, and the cells that name no loss.
LOSS_COLUMNS = ("что теряется", "what is lost")
NO_LOSS = ("", "-", "—", "none", "нет", "n/a")


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
        subjects = {sub["position"] for sub in o.get("subjects", [])}
        for pos in o["valid_for"]:
            if pos not in subjects:
                out.append(
                    Finding(
                        "warning",
                        oid,
                        f"valid_for '{pos}' has no subject (subjects)",
                        "procedures/positional-construction.md §5",
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


@hint("ai-cooperation")
def hint_ai_cooperation(ctx: Ctx) -> list[Finding]:
    """An AI-drafted cooperation with no K on it (positional-construction.md
    §5: the K is mandatory)."""
    targeted = {t for q in ctx.ks.values() for t in q.get("targets", [])}
    return [
        Finding(
            "hint",
            e["id"],
            "a cooperation drafted by AI and no K on it asking the human to name "
            "or correct how the activities connect",
        )
        for e in ctx.by_id.values()
        if e["kind"] == "cooperation"
        and is_ai(e.get("voice"))
        and e["id"] not in targeted
    ]


@hint("cooperation-flows")
def hint_cooperation_flows(ctx: Ctx) -> list[Finding]:
    """Each position an ontology is valid for gives to or takes from its
    cooperation by a `flow`."""
    out: list[Finding] = []
    for o in ctx.record.get("ontology", []):
        coop = o.get("cooperation")
        if coop not in ctx.by_id:
            continue
        linked = {
            end
            for r in ctx.record.get("relations", [])
            if r["kind"] == "flow" and coop in (r["from"], r["to"])
            for end in (r["from"], r["to"])
        }
        loose = [p for p in o["valid_for"] if p not in linked]
        if loose:
            out.append(
                Finding(
                    "hint",
                    o["id"],
                    f"valid for positions with no `flow` to or from the cooperation "
                    f"'{coop}' (what each gives or takes): " + ", ".join(loose),
                )
            )
    return out


@hint("translation-loss")
def hint_translation_loss(ctx: Ctx) -> list[Finding]:
    """A translation table whose loss column («что теряется») is empty or
    "none" in a row."""
    out: list[Finding] = []
    for e in ctx.by_id.values():
        columns = [c.strip().lower() for c in e.get("detail", {}).get("columns", [])]
        col = next((n for n, c in enumerate(columns) if c in LOSS_COLUMNS), None)
        if col is None:
            continue
        rows = [
            str(n)
            for n, row in enumerate(e["detail"]["rows"], 1)
            if col < len(row) and str(row[col]).strip().lower() in NO_LOSS
        ]
        if rows:
            out.append(
                Finding(
                    "hint",
                    e["id"],
                    "a translation names a loss in every row, or the holder's "
                    "answer that there is none, with its address; rows "
                    + ", ".join(rows),
                )
            )
    return out
