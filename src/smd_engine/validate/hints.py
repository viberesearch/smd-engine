"""Method hints: observations from Girenko's criteria for a group screen
(day 4, 17.10.2026). Each hint has a string id (HINTS in context.py); a
profile names the hints it enables."""

from __future__ import annotations

from typing import Any

from smd_engine.validate.context import Ctx, Finding, hint, is_ai

# Kinds by id are those every profile defines (profile.REQUIRED_KINDS; `entry`
# and `goal` when the profile enables the hint that needs them, HINT_KINDS);
# frames by their shape, facts by the flag `factual`.


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


# Gates Ш8-Ш12: G.P.'s «Программа действий» (GP-Guide11, т. 4, 1981), read
# against т. 5 (GP-T5, 1988); where the two disagree, the later text is cited.
# Procedures that lay read material into a board: the ingestion chain.
INGESTION = ("ingest-transcript", "theses-to-board")


def _object_elements(ctx: Ctx) -> list[dict[str, Any]]:
    """Elements on the boards a profile flags `object`."""
    return [e for b in ctx.profile.boards if b.object for e in _on(ctx, b.id)]


def _seer_stance(ctx: Ctx, el: dict[str, Any]) -> str | None:
    """The `stance` of the position an element is seen from."""
    return ctx.by_id.get(el.get("seen_from", ""), {}).get("stance")


@hint("object-from-inside")
def hint_object_from_inside(ctx: Ctx) -> list[Finding]:
    return [
        Finding(
            "hint",
            e["id"],
            f"drawn from inside the structure ('{e['seen_from']}'): for G.P. a "
            "structure one works in is a condition of action, not an object "
            "(GP-Guide11 ¶36); draw it from an external position after reflection",
        )
        for e in _object_elements(ctx)
        if _seer_stance(ctx, e) == "inside"
    ]


@hint("external-without-reflection")
def hint_external_without_reflection(ctx: Ctx) -> list[Finding]:
    """A revising cycle drawn from outside with no reflexive exit before it."""
    data = ctx.record
    if "revises" not in data or "reflected_from" in data:
        return []
    seers = sorted(
        {
            e["seen_from"]
            for e in _object_elements(ctx)
            if _seer_stance(ctx, e) == "external"
        }
    )
    if not seers:
        return []
    return [
        Finding(
            "hint",
            "reflected_from",
            "the object board is seen from an external position ("
            + ", ".join(seers)
            + ") and the cycle names no reflexive exit: for G.P. the external "
            "position is taken after reflection (GP-Guide11 ¶35, ¶47; GP-T5 p. 150)",
        )
    ]


def _breakdown_linked(ctx: Ctx, goal_id: str) -> bool:
    """A goal linked to a gap by a relation, or named by a difficulty or problem
    thesis in `feeds` or `about`."""
    for rel in ctx.record.get("relations", []):
        ends = {rel["from"], rel["to"]}
        if goal_id in ends and any(
            ctx.by_id.get(end, {}).get("kind") == "gap" for end in ends - {goal_id}
        ):
            return True
    return any(
        t["kind"] in ("difficulty", "problem")
        and goal_id in t.get("feeds", []) + t.get("about", [])
        for t in ctx.theses.values()
    )


@hint("goal-without-breakdown")
def hint_goal_without_breakdown(ctx: Ctx) -> list[Finding]:
    """A goal arises at a breakdown, is passed down, or is a position's own;
    an own goal needs only its position (`seen_from`), warned already."""
    out: list[Finding] = []
    difficulty = ctx.record.get("state", {}).get("difficulty")
    for goal in (e for e in ctx.by_id.values() if e["kind"] == "goal"):
        source = goal.get("goal_source")
        if source == "assigned" and "assigned_by" not in goal:
            out.append(
                Finding(
                    "hint",
                    goal["id"],
                    "an assigned goal names no position that passed it down "
                    "(assigned_by): руководство passes goals down as tasks "
                    "(GP-Guide4 ¶12; GP-T5 p. 169)",
                )
            )
        elif source == "breakdown" and "arises_from" not in goal:
            out.append(
                Finding(
                    "hint",
                    goal["id"],
                    "a goal from a breakdown names none (arises_from): which gap, "
                    "fact or difficulty does it answer? (GP-Guide11 ¶43)",
                )
            )
        elif (
            source is None
            and "arises_from" not in goal
            and not difficulty
            and not _breakdown_linked(ctx, goal["id"])
        ):
            out.append(
                Finding(
                    "hint",
                    goal["id"],
                    "goal with no breakdown: for G.P. a goal arises at a прокол in "
                    "habitual activity (GP-Guide11 ¶43; GP-T5 p. 151, «тупик»). "
                    "Which difficulty or gap does it answer?",
                )
            )
    return out


@hint("position-without-object")
def hint_position_without_object(ctx: Ctx) -> list[Finding]:
    """A functionary is left out: it takes no object of its own (GP-Guide10 ¶7)."""
    represents = {
        r["from"] for r in ctx.record.get("relations", []) if r["kind"] == "represents"
    }
    return [
        Finding(
            "hint",
            e["id"],
            f"acts as {e['acts_as']} and represents no object: which object does "
            "this position take? (GP-Guide10 ¶7, ¶19)",
        )
        for e in ctx.by_id.values()
        if e["kind"] == "position"
        and e.get("acts_as") not in (None, "functionary")
        and e["id"] not in represents
    ]


def _fact_linked(ctx: Ctx, el_id: str) -> bool:
    """A fact (a kind the profile flags `factual`, or `modality: fact`) linked
    to the element by a relation or `in`, either way, or a factual thesis that
    feeds or is about it."""
    factual = ctx.profile.kinds_where("factual")
    linked = set(ctx.by_id[el_id].get("in", []))
    linked |= {e["id"] for e in ctx.by_id.values() if el_id in e.get("in", [])}
    for rel in ctx.record.get("relations", []):
        if el_id in (rel["from"], rel["to"]):
            linked |= {rel["from"], rel["to"]} - {el_id}
    if any(
        ctx.by_id[i]["kind"] in factual or ctx.by_id[i].get("modality") == "fact"
        for i in linked
        if i in ctx.by_id
    ):
        return True
    return any(
        t.get("modality") == "fact" and el_id in t.get("feeds", []) + t.get("about", [])
        for t in ctx.theses.values()
    )


@hint("ought-without-fact")
def hint_ought_without_fact(ctx: Ctx) -> list[Finding]:
    """GP-T5 (1988) drops the forecast of GP-Guide5 ¶7 (1981) as a scientistic
    substitution (p. 251); the natural processes come first (p. 252)."""
    return [
        Finding(
            "hint",
            e["id"],
            "ought with no fact linked to it: for G.P. artificial action starts "
            "from the natural processes, which limit it (GP-T5 p. 252)",
        )
        for e in _object_elements(ctx)
        if e.get("modality") == "ought" and not _fact_linked(ctx, e["id"])
    ]


@hint("design-the-natural")
def hint_design_the_natural(ctx: Ctx) -> list[Finding]:
    return [
        Finding(
            "hint",
            e["id"],
            "ought on a natural process: a natural process cannot be designed, "
            "only used or managed (GP-STS, IT p. 443; GP-T5 p. 231)",
        )
        for e in ctx.by_id.values()
        if e.get("modality") == "ought" and e.get("nature") == "natural"
    ]


@hint("information-without-cell")
def hint_information_without_cell(ctx: Ctx) -> list[Finding]:
    loose = [
        t["id"]
        for t in ctx.record.get("theses", [])
        if not t.get("feeds") and not t.get("about") and t["status"] != "open"
    ]
    if loose:
        return [
            Finding(
                "hint",
                "theses",
                "information not laid into a cell of a scheme (no feeds or about; "
                "GP-Guide11 ¶5): " + ", ".join(loose),
            )
        ]
    return []


@hint("cells-from-information")
def hint_cells_from_information(ctx: Ctx) -> list[Finding]:
    """Across two cycles of ingestion: the cells come before the reading."""
    data, previous = ctx.record, ctx.previous
    if previous is None or previous.get("id") != data.get("revises"):
        return []
    if data.get("run", {}).get("procedure") not in INGESTION:
        return []
    old_theses = {t["id"] for t in previous.get("theses", [])}
    fed = {
        ref
        for t in data.get("theses", [])
        if t["id"] not in old_theses
        for ref in t.get("feeds", [])
    }
    if not fed or fed & {e["id"] for e in previous["elements"]}:
        return []
    return [
        Finding(
            "hint",
            "cycle",
            "every element the new theses feed is new ("
            + ", ".join(sorted(fed))
            + "): were the cells drawn from the information, not before it? "
            "(GP-Guide11 ¶5; GP-T5 p. 233)",
        )
    ]
