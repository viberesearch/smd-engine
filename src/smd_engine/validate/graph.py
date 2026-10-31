"""Graph signatures the procedures used to check by hand (method review
31.10.2026, gates Ф В and У В): cycles of `belongs`, `subordinates` and move
sources as errors; the empty places of a functional plan (functional-plan.md
§4) and the typical errors E2, E3, E6/E11, E12 and E14 of a group screen
(qualification-pass.md §3.2) as hints. `flow` may close a cycle (a position
pays into a chain and receives its result), so it is not checked for one."""

from __future__ import annotations

from typing import Any

from smd_engine.profile import SEEN_FROM_KINDS
from smd_engine.validate.context import Ctx, Finding, board_set, hint

# Relation kinds a cycle makes no sense in: membership, subordination.
ACYCLIC = ("belongs", "subordinates")
PLACES = ("position", "place_for_others")
# What a gap linked to a function stands for (functional-plan.md §4): the
# missing payer, input or receiver is written as a gap of these blocks.
PAYER_GAPS = {"position"}
INPUT_GAPS = {"material", "means"}
RECEIVER_GAPS = {"position", "product", "function"}


def _reach(edges: dict[str, set[str]], start: str) -> set[str]:
    seen: set[str] = set()
    stack = list(edges.get(start, ()))
    while stack:
        cur = stack.pop()
        if cur not in seen:
            seen.add(cur)
            stack.extend(edges.get(cur, ()))
    return seen


def cycles(edges: dict[str, set[str]]) -> list[list[str]]:
    """The ids on a cycle, one sorted list per strongly connected part; the
    boards are small, so reachability from every node is enough."""
    reach = {n: _reach(edges, n) for n in edges}
    parts = {
        frozenset(m for m in r if n in reach.get(m, set()))
        for n, r in reach.items()
        if n in r
    }
    return sorted(sorted(p) for p in parts)


@board_set
def check_cycles(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    for kind in ACYCLIC:
        edges: dict[str, set[str]] = {}
        for rel in ctx.record.get("relations", []):
            if rel["kind"] == kind:
                edges.setdefault(rel["from"], set()).add(rel["to"])
        out += [
            Finding(
                "error", part[0], f"'{kind}' relations form a cycle: " + ", ".join(part)
            )
            for part in cycles(edges)
        ]
    # A move from its own result is reported where the move is checked.
    moves: dict[str, set[str]] = {}
    for item in list(ctx.by_id.values()) + list(ctx.theses.values()):
        if "move" in item:
            moves[item["id"]] = set(item["move"]["from"]) - {item["id"]}
    out += [
        Finding("error", part[0], "move sources form a cycle: " + ", ".join(part))
        for part in cycles(moves)
    ]
    return out


def _flows(ctx: Ctx) -> list[dict[str, Any]]:
    return [r for r in ctx.record.get("relations", []) if r["kind"] == "flow"]


def _plan(ctx: Ctx) -> dict[str, list[dict[str, Any]]]:
    """The functions inside each new frame, by frame id."""
    framed = ctx.profile.kinds_shaped("frame")
    return {
        frame["id"]: [
            e
            for e in ctx.by_id.values()
            if e["kind"] == "function" and frame["id"] in e.get("in", [])
        ]
        for frame in ctx.by_id.values()
        if frame["kind"] in framed and frame.get("frame_state") == "new"
    }


def _working(ctx: Ctx) -> list[str]:
    """The positions that work in the activity: not the reflexive position of
    the cycle (`reflected_from`, `stance: reflexive`), which looks back at it."""
    return [
        e["id"]
        for e in ctx.by_id.values()
        if e["kind"] == "position"
        and e.get("stance") != "reflexive"
        and e["id"] != ctx.record.get("reflected_from")
    ]


def _kind(ctx: Ctx, el_id: str) -> str:
    return str(ctx.by_id.get(el_id, {}).get("kind", ""))


def _linked_gaps(ctx: Ctx, el_id: str) -> set[str]:
    """The scheme blocks (`of`) of the gaps linked to an element by a relation."""
    out: set[str] = set()
    for rel in ctx.record.get("relations", []):
        if el_id in (rel["from"], rel["to"]):
            other = ctx.by_id.get(rel["to"] if rel["from"] == el_id else rel["from"])
            if other and other["kind"] == "gap" and "of" in other:
                out.add(other["of"])
    return out


@hint("function-flows")
def hint_function_flows(ctx: Ctx) -> list[Finding]:
    """Each function of the plan: a payer (a `flow` into it from a position or
    place), an input (any `flow` into it) and a receiver (a `flow` from it to
    a position or place), or a gap of the block that stands for it."""
    out: list[Finding] = []
    flows = _flows(ctx)
    seen: set[str] = set()
    for fn in (f for fns in _plan(ctx).values() for f in fns):
        if fn["id"] in seen:
            continue
        seen.add(fn["id"])
        ins = [r["from"] for r in flows if r["to"] == fn["id"]]
        outs = [r["to"] for r in flows if r["from"] == fn["id"]]
        gaps = _linked_gaps(ctx, fn["id"])
        missing = []
        if not ins and not gaps & INPUT_GAPS:
            missing.append("input from nobody")
        if not any(_kind(ctx, i) in PLACES for i in ins) and not gaps & PAYER_GAPS:
            missing.append("no payer")
        if not any(_kind(ctx, o) in PLACES for o in outs) and not gaps & RECEIVER_GAPS:
            missing.append("no receiver")
        if missing:
            out.append(
                Finding(
                    "hint",
                    fn["id"],
                    "; ".join(missing) + ": a `flow` from the payer, from what "
                    "it takes in, to the receiver, or a gap with `of` for the "
                    "empty place",
                )
            )
    return out


@hint("unlinked-functions")
def hint_unlinked_functions(ctx: Ctx) -> list[Finding]:
    """Two functions of a chain with no link between them."""
    out: list[Finding] = []
    flows = _flows(ctx)
    for frame, fns in _plan(ctx).items():
        ids = {f["id"] for f in fns}
        if len(ids) < 2:
            continue
        linked = {
            end
            for r in flows
            if r["from"] in ids and r["to"] in ids
            for end in (r["from"], r["to"])
        }
        loose = [f["id"] for f in fns if f["id"] not in linked]
        if loose:
            out.append(
                Finding(
                    "hint",
                    frame,
                    f"{len(loose)} of {len(fns)} functions are linked by no `flow` "
                    "to another function of the plan: " + ", ".join(loose),
                )
            )
    return out


@hint("idle-positions")
def hint_idle_positions(ctx: Ctx) -> list[Finding]:
    """A position that performs, pays for and receives nothing in the plan.
    Places for others are left out: the plan need not use every one."""
    fns = {f["id"]: f for fs in _plan(ctx).values() for f in fs}
    if not fns:
        return []
    busy = {f["performed_by"] for f in fns.values() if "performed_by" in f}
    for r in _flows(ctx):
        if r["from"] in fns or r["to"] in fns:
            busy |= {r["from"], r["to"]}
    idle = [p for p in _working(ctx) if p not in busy]
    if not idle:
        return []
    home = ctx.profile.home_board.get("position", "positions")
    return [
        Finding(
            "hint",
            home,
            "positions that perform, pay for and receive nothing in the functional "
            "plan: is the position not needed, or is a function missing? "
            + ", ".join(idle),
        )
    ]


@hint("positions-unlinked")
def hint_positions_unlinked(ctx: Ctx) -> list[Finding]:
    """E2: positions with no `shift` or `flow` to another position, a place for
    others or a cooperation."""
    positions = _working(ctx)
    if len(positions) < 2:
        return []
    ends = (*PLACES, "cooperation")
    linked: set[str] = set()
    for r in ctx.record.get("relations", []):
        if r["kind"] in ("shift", "flow") and r["from"] != r["to"]:
            if _kind(ctx, r["from"]) in ends and _kind(ctx, r["to"]) in ends:
                linked |= {r["from"], r["to"]}
    loose = [p for p in positions if p not in linked]
    if not loose:
        return []
    home = ctx.profile.home_board.get("position", "positions")
    return [
        Finding(
            "hint",
            home,
            "positions with no `shift` or `flow` to another position, place or "
            "cooperation: positions drawn without restoring the plan of activity? "
            "(E2): " + ", ".join(loose),
        )
    ]


def _components(ctx: Ctx) -> dict[str, int]:
    """Element id to the number of its part of the board graph: relations,
    transitions, `in`, `performed_by`, move sources and an ontology's
    cooperation with its `valid_for` positions, either way (not `seen_from`:
    E3 asks for a link besides it)."""
    edges: dict[str, set[str]] = {i: set() for i in ctx.by_id}

    def link(a: str, b: str) -> None:
        if a in edges and b in edges:
            edges[a].add(b)
            edges[b].add(a)

    for r in ctx.record.get("relations", []) + ctx.record.get("transitions", []):
        link(r["from"], r["to"])
    for e in ctx.by_id.values():
        for c in e.get("in", []):
            link(e["id"], c)
        if "performed_by" in e:
            link(e["id"], e["performed_by"])
        for src in e.get("move", {}).get("from", []):
            link(e["id"], src)
    for o in ctx.record.get("ontology", []):
        for pos in o["valid_for"]:
            link(o.get("cooperation", ""), pos)
    part: dict[str, int] = {}
    for n, start in enumerate(edges):
        stack = [start]
        while stack:
            cur = stack.pop()
            if cur not in part:
                part[cur] = n
                stack.extend(edges[cur])
    return part


@hint("object-isolated")
def hint_object_isolated(ctx: Ctx) -> list[Finding]:
    """E3: content of an object board linked by no relation, transition, `in`,
    `performed_by` or move, however indirectly, to an element of another
    board."""
    objects = {b.id for b in ctx.profile.boards if b.object}
    if not objects:
        return []
    part = _components(ctx)
    anchored = {part[e["id"]] for e in ctx.by_id.values() if e["board"] not in objects}
    out: list[Finding] = []
    for board in sorted(objects):
        loose = [
            e["id"]
            for e in ctx.by_id.values()
            if e["board"] == board
            and e["kind"] not in ("gap", "note")
            and part[e["id"]] not in anchored
        ]
        if loose:
            out.append(
                Finding(
                    "hint",
                    board,
                    "object content linked to no position or situation by a "
                    "relation or transition: in isolation from them? (E3): "
                    + ", ".join(loose),
                )
            )
    return out


@hint("isolated-facts")
def hint_isolated_facts(ctx: Ctx) -> list[Finding]:
    """E6, E11: facts with no relation, transition, `in` and no thesis."""
    factual = ctx.profile.kinds_where("factual")
    touched: set[str] = set()
    for r in ctx.record.get("relations", []) + ctx.record.get("transitions", []):
        touched |= {r["from"], r["to"]}
    for e in ctx.by_id.values():
        if e.get("in"):
            touched |= {e["id"], *e["in"]}
    for t in ctx.theses.values():
        touched |= set(t.get("feeds", []) + t.get("about", []))
    loose = [
        e["id"]
        for e in ctx.by_id.values()
        if e["kind"] in factual and e["id"] not in touched
    ]
    if not loose:
        return []
    return [
        Finding(
            "hint",
            "facts",
            "facts with no relation, transition or thesis: background laid out "
            "and no conclusion drawn from it? (E6, E11): " + ", ".join(loose),
        )
    ]


@hint("jump-to-frame")
def hint_jump_to_frame(ctx: Ctx) -> list[Finding]:
    """E12: a `shift` to a target position and a new frame, and nothing on the
    situation board (a board with halves) seen from the starting position,
    unless it is the cycle's reflexive position."""
    halved = {b.id for b in ctx.profile.boards if b.halves}
    framed = ctx.profile.kinds_shaped("frame")
    if not halved or not any(
        e["kind"] in framed and e.get("frame_state") == "new"
        for e in ctx.by_id.values()
    ):
        return []
    seen = {e.get("seen_from") for e in ctx.by_id.values() if e["board"] in halved}
    working = set(_working(ctx))
    out: list[Finding] = []
    for r in ctx.record.get("relations", []):
        if r["kind"] == "shift" and r["from"] in working and r["from"] not in seen:
            out.append(
                Finding(
                    "hint",
                    r["from"],
                    f"shifts to '{r['to']}' and a new frame is drawn, but nothing "
                    "on the situation board is seen from it: a jump to the "
                    "organiser of another whole without discussing the situation? "
                    "(E12)",
                )
            )
    return out


def _anchored(ctx: Ctx, el_id: str) -> bool:
    el = ctx.by_id.get(el_id, {})
    return el.get("kind") in (*SEEN_FROM_KINDS, "place_for_others") or bool(
        el.get("seen_from")
    )


@hint("transition-unanchored")
def hint_transition_unanchored(ctx: Ctx) -> list[Finding]:
    """E14: a transition with no end that is a position or seen from one."""
    return [
        Finding(
            "hint",
            f"transition {t['n']}",
            "neither end is a position or seen from one: a jump not anchored in "
            "a position? (E14)",
        )
        for t in ctx.record.get("transitions", [])
        if not _anchored(ctx, t["from"]) and not _anchored(ctx, t["to"])
    ]
