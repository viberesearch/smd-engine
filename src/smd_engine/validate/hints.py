"""Method hints: observations from Girenko's criteria for a group screen
(day 4, 17.10.2026). Each hint has a string id (HINTS in context.py); a
profile names the hints it enables."""

from __future__ import annotations

from typing import Any

from smd_engine.validate.context import Ctx, Finding, hint, is_ai

# Kinds by id are those every profile defines (profile.REQUIRED_KINDS; `entry`
# when the profile enables the hint of that name); frames by their shape.


def _on(ctx: Ctx, board: str, half: str | None = None) -> list[dict[str, Any]]:
    return [
        e
        for e in ctx.by_id.values()
        if e["board"] == board
        and e["kind"] not in ("gap", "note")
        and (half is None or e.get("half") == half)
    ]


@hint("entry")
def hint_entry(ctx: Ctx) -> list[Finding]:
    if any(e["kind"] == "entry" for e in ctx.by_id.values()):
        return []
    return [Finding("hint", "entry", "no entry marked: where did the thinking start?")]


@hint("empty-boards")
def hint_empty_boards(ctx: Ctx) -> list[Finding]:
    """Boards without halves; the halves are the next hint."""
    return [
        Finding(
            "hint", b.id, f"{b.label['en'][:1].lower()}{b.label['en'][1:]} is empty"
        )
        for b in ctx.profile.boards
        if not b.halves and not _on(ctx, b.id)
    ]


@hint("situation-halves")
def hint_situation_halves(ctx: Ctx) -> list[Finding]:
    """An empty half of any halved board, named as the method names the halves
    (small and big situation); a profile whose halved board holds no situation
    leaves this hint off (docs/profiles.md, `hints`)."""
    return [
        Finding("hint", f"{b.id}/{half}", f"{half} situation not laid out")
        for b in ctx.profile.boards
        for half in b.halves
        if not _on(ctx, b.id, half)
    ]


@hint("positions")
def hint_positions(ctx: Ctx) -> list[Finding]:
    els = list(ctx.by_id.values())
    positions = [e for e in els if e["kind"] == "position"]
    places = [e for e in els if e["kind"] == "place_for_others"]
    if len(positions) < 2 and not places:
        home = ctx.profile.home_board.get("position", "positions")
        return [
            Finding(
                "hint",
                home,
                f"{len(positions)} position(s) and no places for others: "
                "positional set looks incomplete",
            )
        ]
    return []


@hint("new-frames")
def hint_new_frames(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    els = list(ctx.by_id.values())
    framed = ctx.profile.kinds_shaped("frame")
    for frame in (
        e for e in els if e["kind"] in framed and e.get("frame_state") == "new"
    ):
        inside = [
            e for e in els if frame["id"] in e.get("in", []) and e["kind"] == "function"
        ]
        if not inside:
            out.append(
                Finding("hint", frame["id"], "new frame has no functional plan inside")
            )
        else:
            unowned = [f["id"] for f in inside if "performed_by" not in f]
            if unowned:
                out.append(
                    Finding(
                        "hint",
                        frame["id"],
                        f"{len(unowned)} of {len(inside)} functions name no position "
                        "that performs them (performed_by): " + ", ".join(unowned),
                    )
                )
    return out


@hint("gaps")
def hint_gaps(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    for gap in (e for e in ctx.by_id.values() if e["kind"] == "gap"):
        out.append(Finding("hint", gap["id"], f"open gap: {gap['label']}"))
        if "of" not in gap:
            out.append(
                Finding(
                    "hint",
                    gap["id"],
                    "gap names no scheme block it is missing from (GP-PP)",
                )
            )
    return out


@hint("open-qualifications")
def hint_open_qualifications(ctx: Ctx) -> list[Finding]:
    open_k = [
        q["id"] for q in ctx.record.get("qualifications", []) if q["status"] != "closed"
    ]
    if open_k:
        return [Finding("hint", "qualifications", "not closed: " + ", ".join(open_k))]
    return []


@hint("candidate-moves")
def hint_candidate_moves(ctx: Ctx) -> list[Finding]:
    candidates = [
        e["id"]
        for e in list(ctx.by_id.values()) + ctx.record.get("theses", [])
        if e.get("move", {}).get("status") == "candidate"
    ]
    if candidates:
        return [
            Finding(
                "hint",
                "moves",
                "candidates awaiting a decision: " + ", ".join(candidates),
            )
        ]
    return []


@hint("problems")
def hint_problems(ctx: Ctx) -> list[Finding]:
    return [
        Finding(
            "hint",
            t["id"],
            "a problem is tied to a block of a named scheme; none given",
        )
        for t in ctx.record.get("theses", [])
        if t["kind"] == "problem" and "of" not in t
    ]


@hint("belts")
def hint_belts(ctx: Ctx) -> list[Finding]:
    """Degenerate forms of thought-activity, read from the belts (GP1987)."""
    theses = ctx.record.get("theses", [])
    if len(theses) < 3:
        return []
    belts = [t["belt"] for t in theses]
    out: list[Finding] = []
    if "m" not in belts and belts.count("mk") * 3 >= len(belts) * 2:
        out.append(
            Finding(
                "hint",
                "theses",
                "mostly thought-communication and no scheme (М): play with words?",
            )
        )
    if "m" in belts and "md" not in belts:
        out.append(
            Finding(
                "hint",
                "theses",
                "schemes (М) with no thought-action (мД): thinking cut off from "
                "the situation?",
            )
        )
    return out


@hint("ontology")
def hint_ontology(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    for o in ctx.record.get("ontology", []):
        if "test" not in o:
            out.append(
                Finding(
                    "hint",
                    o["id"],
                    "an ontology is checked for realizability, not truth: "
                    "name the field test (a hypothesis)",
                )
            )
        if len(o["valid_for"]) > 1 and "cooperation" not in o:
            out.append(
                Finding(
                    "hint",
                    o["id"],
                    "one object for several positions exists only as a construction "
                    "of their cooperation: none named",
                )
            )
    return out


@hint("difficulty")
def hint_difficulty(ctx: Ctx) -> list[Finding]:
    data = ctx.record
    if "revises" in data and not data.get("state", {}).get("difficulty"):
        return [
            Finding(
                "hint",
                "state",
                "a new cycle does not say what failed in the previous one (difficulty)",
            )
        ]
    return []


@hint("revise-if")
def hint_revise_if(ctx: Ctx) -> list[Finding]:
    return [
        Finding(
            "hint",
            h["id"],
            "no result is named that would make us revise the assumption",
        )
        for h in ctx.record.get("hypotheses", [])
        if h["status"] in ("untested", "testing") and not h.get("revise_if")
    ]


@hint("ai-drafts")
def hint_ai_drafts(ctx: Ctx) -> list[Finding]:
    data = ctx.record
    drafted = [
        i["id"]
        for i in data.get("qualifications", []) + data.get("hypotheses", [])
        if is_ai(i.get("voice")) and i.get("status") in ("open", "untested", "testing")
    ]
    if drafted:
        return [
            Finding(
                "hint",
                "ai-drafts",
                "K and H drafted by AI, for a human to keep or drop: "
                + ", ".join(drafted),
            )
        ]
    return []


@hint("ai-variants")
def hint_ai_variants(ctx: Ctx) -> list[Finding]:
    variants = [
        t["id"] for t in ctx.record.get("theses", []) if t["status"] == "ai_variant"
    ]
    if variants:
        return [
            Finding(
                "hint",
                "theses",
                "AI variants awaiting the group: " + ", ".join(variants),
            )
        ]
    return []


@hint("no-new-scheme")
def hint_no_new_scheme(ctx: Ctx) -> list[Finding]:
    """Across two cycles: a reflexive exit should change the scheme."""
    data, previous = ctx.record, ctx.previous
    if previous is None or previous.get("id") != data.get("revises"):
        return []
    # Kinds that make up a scheme; a new cycle with none of them changed repeats itself.
    kinds = [k.id for k in ctx.profile.kinds if k.scheme]

    def scheme(record: dict[str, Any]) -> set[tuple[str, str]]:
        return {
            (e["kind"], e["label"]) for e in record["elements"] if e["kind"] in kinds
        }

    if scheme(data) <= scheme(previous):
        names = ", ".join(kinds[:-1]) + " or " + kinds[-1] if kinds else "scheme"
        return [
            Finding(
                "hint",
                "cycle",
                f"no new {names} since "
                f"'{previous['id']}': reflection without a new scheme?",
            )
        ]
    return []
