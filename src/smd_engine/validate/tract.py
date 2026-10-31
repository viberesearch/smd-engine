"""The visionary tract's checks on its candidates (visionary-tract.md §1, §3,
§5), moved from the procedure into the validator (method review 31.10.2026,
gate У В): the garland, the bridge's sources and `via` on the tract's moves."""

from __future__ import annotations

from smd_engine.validate.context import Ctx, Finding, hint

# The tract's steps 3-6: the element kind each makes and its move.
TRACT_MOVES = {
    ("model", "glue"),
    ("situation", "respecify"),
    ("situation", "rescale"),
    ("goal", "adjoin"),
}


@hint("garland", kinds=("garland",), relations=("belongs",))
def hint_garland(ctx: Ctx) -> list[Finding]:
    """At least two events `belongs` to a garland; events that all cite one
    source are one witness."""
    out: list[Finding] = []
    rels = ctx.record.get("relations", [])
    for g in (e for e in ctx.by_id.values() if e["kind"] == "garland"):
        events = [
            ctx.by_id[r["from"]]
            for r in rels
            if r["kind"] == "belongs" and r["to"] == g["id"] and r["from"] in ctx.by_id
        ]
        if len(events) < 2:
            out.append(
                Finding(
                    "hint",
                    g["id"],
                    f"a garland needs two or more events that `belongs` to it; "
                    f"it has {len(events)}",
                )
            )
            continue
        sources = {c.split("#")[0] for e in events for c in e.get("cites", [])}
        if len(sources) == 1 and all(e.get("cites") for e in events):
            out.append(
                Finding(
                    "hint",
                    g["id"],
                    f"all its events cite one source ('{sources.pop()}'): "
                    "one witness",
                )
            )
    return out


@hint("bridge-from", kinds=("situation", "model", "garland"))
def hint_bridge_from(ctx: Ctx) -> list[Finding]:
    """A bridge (a big situation reached by `respecify`) is drawn from the
    model and the garland."""
    out: list[Finding] = []
    for e in ctx.by_id.values():
        move = e.get("move", {})
        if not (
            e["kind"] == "situation"
            and e.get("half") == "big"
            and move.get("op") == "respecify"
        ):
            continue
        kinds = {ctx.by_id.get(i, {}).get("kind") for i in move["from"]}
        missing = [k for k in ("model", "garland") if k not in kinds]
        if missing:
            out.append(
                Finding(
                    "hint",
                    e["id"],
                    "a bridge reads the big situation through the model and the "
                    "garland; its move is not from a " + " or a ".join(missing),
                )
            )
    return out


@hint("move-via", kinds=("model", "situation", "goal"))
def hint_move_via(ctx: Ctx) -> list[Finding]:
    """`via` names what each candidate move of the tract goes through; a move
    the group made in its talk (ingest-transcript.md §4) needs none."""
    return [
        Finding(
            "hint",
            e["id"],
            f"{e['move']['op']} with no `via`: name the shared substructure, the "
            "changed links, the scale or the added axis",
        )
        for e in ctx.by_id.values()
        if "move" in e
        and e["move"]["status"] == "candidate"
        and (e["kind"], e["move"]["op"]) in TRACT_MOVES
        and not str(e["move"].get("via", "")).strip()
    ]
