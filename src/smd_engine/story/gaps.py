"""Where a story has no typed walk, and the links that would make one.

For a pair (audience, protagonist) the report says whether a walk of typed
links exists. If not, it looks for the cheapest way to get one: typing a
`refers` that exists, adding a link between two items that a thesis, a
hypothesis, a qualification or an ontology record already name together, or,
failing both, joining the nearest items by a new link. A suggestion carries a
kind and, for a flow, what it carries. It is a candidate for the group to
confirm or drop; the engine adds nothing to a board."""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

from smd_engine.story.model import Boards
from smd_engine.story.paths import (
    MAX_LEN,
    MIN_LEN,
    Candidate,
    Graph,
    enumerate_candidates,
    walk_text,
)

ACTORS = ("position", "place_for_others")
SITUATION = ("situation", "signal", "fact", "garland", "note", "other")
# The cost of a route is a vector compared lexicographically, with no weights:
# joins between boards, joins within a board, links between items that a record
# names together, typed refers, then hops. A typed link adds one hop only.
Cost = tuple[int, int, int, int, int]
ZERO: Cost = (0, 0, 0, 0, 0)
STEP_OTHER: Cost = (1, 0, 0, 0, 1)
STEP_BOARD: Cost = (0, 1, 0, 0, 1)
STEP_MENTION: Cost = (0, 0, 1, 0, 1)
STEP_REFERS: Cost = (0, 0, 0, 1, 1)
STEP_TYPED: Cost = (0, 0, 0, 0, 1)


def _plus(a: Cost, b: Cost) -> Cost:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2], a[3] + b[3], a[4] + b[4])


@dataclass
class Missing:
    """A link to add or to type, in the direction of the walk."""

    a: str
    b: str
    now: str  # refers | named together | none
    kind: str
    carries: str | None
    why: str
    # records that name both ends together, when `now` is "named together"
    evidence: list[str] = field(default_factory=list)


@dataclass
class GapReport:
    audience: str
    protagonist: str
    typed: list[Candidate] = field(default_factory=list)
    truncated: bool = False
    weak: int = 0
    status: str = "gap"  # path | gap
    reasons: list[str] = field(default_factory=list)
    missing: list[Missing] = field(default_factory=list)
    route: list[str] = field(default_factory=list)
    # the protagonist's component of the typed graph and what lies in it
    component: int = 0
    conflict: list[str] = field(default_factory=list)
    resolution: list[str] = field(default_factory=list)


def suggest(boards: Boards, a: str, b: str) -> tuple[str, str, str, str | None]:
    """The link that most likely joins a and b, by the kinds of its ends:
    (from, to, kind, carries). The direction may be turned from the order of
    the walk. A guess for a human to confirm."""
    ka, kb = boards.elements[a]["kind"], boards.elements[b]["kind"]
    reads = SITUATION + ("normality_boundary",)
    if kb == "normality_boundary" and ka in SITUATION:
        return a, b, "opposes", None
    if ka == "normality_boundary" and kb in SITUATION:
        return b, a, "opposes", None
    if ka in reads and kb in ("goal", "cooperation", "function") + ACTORS:
        return a, b, "flow", "information"
    if kb in reads and ka in ("goal", "cooperation", "function") + ACTORS:
        return b, a, "flow", "information"
    if ka in SITUATION and kb in SITUATION:
        return a, b, "belongs", None
    if ka == "position" and kb == "position":
        return a, b, "shift", None
    if ka in ACTORS and kb == "function":
        return a, b, "flow", "money"
    if ka == "function" and kb in ACTORS:
        return a, b, "flow", "product"
    if ka == "function" and kb == "function":
        return a, b, "flow", "product"
    if kb == "cooperation" and (ka in ACTORS or ka == "function"):
        return a, b, "flow", "information"
    if ka == "cooperation" and (kb in ACTORS or kb == "function"):
        return a, b, "flow", "product"
    if kb == "goal" and ka in ("function", "cooperation"):
        return a, b, "produces", None
    if ka == "goal" and kb in ("function", "cooperation"):
        return b, a, "produces", None
    if kb == "goal" and ka in ACTORS:
        return a, b, "uses", None
    if ka == "goal" and kb in ACTORS:
        return b, a, "uses", None
    if ka == "function" and kb in ("standard", "model", "concept", "frame"):
        return a, b, "uses", None
    if kb == "function" and ka in ("standard", "model", "concept", "frame"):
        return b, a, "uses", None
    return a, b, "flow", "information"


def _mentions(boards: Boards) -> dict[frozenset[str], list[str]]:
    """Pairs of elements that a thesis, hypothesis, qualification or ontology
    record names together, with the ids of the records that do."""
    pairs: dict[frozenset[str], list[str]] = {}
    rec = boards.record
    groups: list[tuple[str, list[str]]] = []
    groups += [
        (t["id"], t.get("feeds", []) + t.get("about", [])) for t in rec["theses"]
    ]
    groups += [(h["id"], h.get("targets", [])) for h in rec["hypotheses"]]
    groups += [(q["id"], q.get("targets", [])) for q in rec["qualifications"]]
    groups += [
        (o["id"], o.get("valid_for", []) + o.get("covers", [])) for o in rec["ontology"]
    ]
    for item, group in groups:
        known = sorted({i for i in group if i in boards.elements})
        for pair in combinations(known, 2):
            pairs.setdefault(frozenset(pair), []).append(item)
    return pairs


Reach = tuple[dict[str, Cost], dict[str, tuple[str, str]]]


def _spread(
    boards: Boards,
    g_all: Graph,
    mention_adj: dict[str, set[str]],
    start: str,
    blocked: set[str],
) -> Reach:
    """Dijkstra from `start` over the links of the boards (a typed link adds a
    hop, a refers is counted as a refers), the pairs named together and a join
    of any two items; the cost is a vector (see Cost). Returns the cost of every
    item reached and the step into it (the previous item, how the step is made:
    "" typed, "refers", "named together", "none")."""
    ids = [i for i in sorted(boards.elements) if i not in blocked]
    best: dict[str, Cost] = {start: ZERO}
    came: dict[str, tuple[str, str]] = {}
    heap: list[tuple[Cost, str]] = [(ZERO, start)]
    while heap:
        cost, node = heapq.heappop(heap)
        if best[node] != cost:
            continue
        moves: list[tuple[Cost, str, str]] = []
        for s in g_all.adj[node]:
            if s.link.weak:
                moves.append((STEP_REFERS, s.b, "refers"))
            else:
                moves.append((STEP_TYPED, s.b, ""))
        moves += [
            (STEP_MENTION, o, "named together") for o in mention_adj.get(node, ())
        ]
        for other in ids:
            same = boards.elements[node]["board"] == boards.elements[other]["board"]
            moves.append((STEP_BOARD if same else STEP_OTHER, other, "none"))
        for step, other, how in moves:
            if other in blocked or other == node:
                continue
            new = _plus(cost, step)
            if other not in best or new < best[other]:
                best[other] = new
                came[other] = (node, how)
                heapq.heappush(heap, (new, other))
    return best, came


def _route(came: dict[str, tuple[str, str]], end: str) -> list[tuple[str, str, str]]:
    """The steps into `end`, in order: (from, to, how)."""
    steps: list[tuple[str, str, str]] = []
    while end in came:
        prev, how = came[end]
        steps.append((prev, end, how))
        end = prev
    steps.reverse()
    return steps


def _cheapest(
    boards: Boards, g_all: Graph, start: str, mentions: dict[frozenset[str], list[str]]
) -> tuple[list[tuple[str, str, str]], list[str]] | None:
    """The cheapest simple route from the start through a conflict object to a
    resolution object over every kind of link and join: all its steps
    (from, to, how) and its items. Stage one reaches a conflict object, stage
    two goes on to a resolution object without touching the items of stage
    one."""
    mention_adj: dict[str, set[str]] = {}
    for pair in mentions:
        a, b = sorted(pair)
        mention_adj.setdefault(a, set()).add(b)
        mention_adj.setdefault(b, set()).add(a)
    first_best, first_came = _spread(boards, g_all, mention_adj, start, set())
    chosen: tuple[Any, ...] | None = None
    for c in sorted(g_all.conflict):
        if c not in first_best:
            continue
        head = _route(first_came, c)
        used = {start} | {b for _, b, _ in head}
        best, came = _spread(boards, g_all, mention_adj, c, used - {c})
        for r in sorted(g_all.resolution):
            if r == c or r not in best or r in used:
                continue
            tail = _route(came, r)
            if boards.elements[r]["kind"] == "function" and (
                len(tail) < 1 or boards.elements[tail[-1][0]]["kind"] != "function"
            ):
                continue
            cost = _plus(first_best[c], best[r])
            route = [start] + [b for _, b, _ in head + tail]
            fits = 0 if MIN_LEN <= len(route) <= MAX_LEN else 1
            key = (fits, cost, route)
            if chosen is None or key < chosen[:3]:
                chosen = (*key, head + tail)
    if chosen is None:
        return None
    return [s for s in chosen[3] if s[2]], chosen[2]


def gap_report(
    boards: Boards, audience: str, protagonist: str, limit: int = 3
) -> GapReport:
    """Whether a typed walk exists for the pair and, if not, the links the
    cheapest way to one lacks."""
    report = GapReport(audience, protagonist)
    typed_graph = Graph(boards, allow_refers=False)
    reached = _component(typed_graph, protagonist)
    report.component = len(reached)
    report.conflict = sorted(reached & typed_graph.conflict)
    report.resolution = sorted(reached & typed_graph.resolution)
    report.typed, report.truncated = enumerate_candidates(
        boards, protagonist, allow_refers=False, limit=limit
    )
    if report.typed:
        report.status = "path"
        return report
    weak, _ = enumerate_candidates(boards, protagonist, allow_refers=True, limit=1)
    all_graph = Graph(boards, allow_refers=True)
    found = _cheapest(boards, all_graph, protagonist, _mentions(boards))
    if weak:
        report.weak = weak[0].weak
        report.reasons.append(
            f"walks exist only through refers; best: {walk_text(weak[0])}"
        )
    if not found:
        report.reasons.append("no route from the protagonist to a resolution object")
        return report
    steps, route = found
    report.route = route
    if len(route) < MIN_LEN:
        report.reasons.append(
            f"the cheapest route has {len(route)} items, fewer than {MIN_LEN}"
        )
    if len(route) > MAX_LEN:
        report.reasons.append(
            f"the cheapest route has {len(route)} items, more than {MAX_LEN}"
        )
    mentions = _mentions(boards)
    for a, b, now in steps:
        frm, to, kind, carries = suggest(boards, a, b)
        report.missing.append(
            Missing(
                frm,
                to,
                now,
                kind,
                carries,
                _why(boards, a, b, now),
                mentions.get(frozenset((a, b)), []) if now == "named together" else [],
            )
        )
    return report


def _component(g: Graph, start: str) -> set[str]:
    seen = {start}
    stack = [start]
    while stack:
        for step in g.adj[stack.pop()]:
            if step.b not in seen:
                seen.add(step.b)
                stack.append(step.b)
    return seen


def _why(boards: Boards, a: str, b: str, now: str) -> str:
    if now == "refers":
        return "a refers links them; type it if it carries meaning"
    if now == "named together":
        return "a thesis, hypothesis, K or ontology record names both"
    same = boards.elements[a]["board"] == boards.elements[b]["board"]
    return "nothing links them" + (", same board" if same else ", other boards")


def report_dict(rep: GapReport) -> dict[str, Any]:
    return {
        "audience": rep.audience,
        "protagonist": rep.protagonist,
        "status": rep.status,
        "typed_walks": len(rep.typed),
        "reasons": rep.reasons,
        "component": rep.component,
        "conflict_in_component": rep.conflict,
        "resolution_in_component": rep.resolution,
        "route": rep.route,
        "missing": [m.__dict__ for m in rep.missing],
    }
