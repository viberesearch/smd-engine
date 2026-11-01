"""Walks through the typed links of the boards: from a protagonist through a
conflict object to a resolution object (`smd story paths`), and where no such
walk exists (`--gaps`).

Order of the candidates, lexicographic and without weights: the share of typed
links (more first), the best leverage rank among the open hypotheses on the walk
(the highest-reach hypothesis first, `smd status`; the number of hypotheses on
the walk does not count), fewer items, fewer components of the typed graph
crossed, fewer links walked against their direction, then the ids. A walk that
meets a resolution object before its first conflict object is not a candidate."""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

from smd_engine import redline
from smd_engine.leverage import leverage_order, natural_key
from smd_engine.story.model import Boards, Link

MIN_LEN = 4
MAX_LEN = 9
# Visited states a search may take before it stops and says so.
BUDGET = 2_000_000
INF = 10**9

CONFLICT_KINDS = ("normality_boundary", "garland")
RESOLUTION_KINDS = ("cooperation", "goal")


@dataclass(frozen=True)
class Step:
    """One link of a walk: from `a` to `b`, `forward` when the relation was
    recorded in that direction."""

    a: str
    b: str
    link: Link
    forward: bool


@dataclass
class Candidate:
    path: list[str]
    steps: list[Step]
    conflict: list[str]
    resolution: str
    open: list[str]
    weak: int
    components: int
    backward: int
    key: tuple[Any, ...] = field(default=(), repr=False)

    @property
    def typed_share(self) -> Fraction:
        return Fraction(len(self.steps) - self.weak, len(self.steps))


class Graph:
    """The typed and weak links of the boards as one undirected graph, with the
    conflict and resolution objects marked."""

    def __init__(self, boards: Boards, allow_refers: bool) -> None:
        self.boards = boards
        self.adj: dict[str, list[Step]] = {i: [] for i in boards.elements}
        for link in boards.links:
            if link.weak and not allow_refers:
                continue
            self.adj[link.a].append(Step(link.a, link.b, link, True))
            self.adj[link.b].append(Step(link.b, link.a, link, False))
        self.conflict = conflict_objects(boards)
        self.resolution = {
            i for i, e in boards.elements.items() if e["kind"] in RESOLUTION_KINDS
        }

    def conflict_first(self, path: list[str]) -> bool:
        """The walk meets a conflict object, and no resolution object comes
        before the first one."""
        for item in path[:-1]:
            if item in self.conflict:
                return True
            if item in self.resolution:
                return False
        return False

    def is_resolution(self, path: list[str]) -> bool:
        """A cooperation or a goal, or a function reached from a function when
        both come after the last conflict object (a function chain that follows
        the conflict)."""
        end = self.boards.elements[path[-1]]
        if end["id"] in self.resolution:
            return True
        if end["kind"] != "function" or len(path) < 3:
            return False
        if self.boards.elements[path[-2]]["kind"] != "function":
            return False
        last = max((n for n, i in enumerate(path) if i in self.conflict), default=-1)
        return last < len(path) - 2


def conflict_objects(boards: Boards) -> set[str]:
    """Both ends of an `opposes`, normality boundaries, a series of linked
    events and its members (`belongs`), and red lines whose observations
    breach the line (`redline.py`)."""
    found: set[str] = set()
    kinds = boards.elements
    for link in boards.links:
        if link.kind == "opposes":
            found |= {link.a, link.b}
        if link.kind == "belongs" and kinds[link.b]["kind"] == "garland":
            found |= {link.a, link.b}
    for el_id, el in kinds.items():
        if el["kind"] in CONFLICT_KINDS:
            found.add(el_id)
        if el.get("line") and redline.breaches(el, boards.dates.get(el_id) or None):
            found.add(el_id)
    return found


def components(boards: Boards) -> dict[str, int]:
    """Component number of every element in the graph of typed links."""
    adj = Graph(boards, allow_refers=False).adj
    seen: dict[str, int] = {}
    for start in sorted(adj):
        if start in seen:
            continue
        n = len(set(seen.values()))
        seen[start] = n
        stack = [start]
        while stack:
            for step in adj[stack.pop()]:
                if step.b not in seen:
                    seen[step.b] = n
                    stack.append(step.b)
    return seen


def open_hypotheses(boards: Boards, ids: set[str]) -> list[str]:
    """Hypotheses not yet answered whose targets meet the ids: the untested in
    leverage order, then the ones in testing."""
    order = [lv.id for lv in leverage_order(boards.record)]
    hyps = {h["id"]: h for h in boards.record["hypotheses"]}
    hit = {h for h, v in hyps.items() if set(v.get("targets", [])) & ids}
    untested = [h for h in order if h in hit]
    testing = sorted(
        (h for h in hit if hyps[h]["status"] == "testing"), key=natural_key
    )
    return untested + testing


def enumerate_candidates(
    boards: Boards,
    protagonist: str,
    allow_refers: bool = False,
    limit: int | None = None,
) -> tuple[list[Candidate], bool]:
    """Simple walks of MIN_LEN to MAX_LEN items from the protagonist through a
    conflict object to a resolution object, best first; the flag says the
    search stopped at BUDGET steps."""
    g = Graph(boards, allow_refers)
    comp = components(boards)
    rank = {h: i for i, h in enumerate(open_hypotheses(boards, set(boards.elements)))}
    found: list[Candidate] = []
    steps_taken = 0
    stack: list[tuple[list[str], list[Step]]] = [([protagonist], [])]
    while stack:
        path, steps = stack.pop()
        steps_taken += 1
        if steps_taken > BUDGET:
            return _ranked(found, limit), True
        if len(path) >= MIN_LEN and g.is_resolution(path):
            if g.conflict_first(path):
                found.append(_candidate(boards, g, path, steps, comp, rank))
        if len(path) == MAX_LEN:
            continue
        for step in g.adj[path[-1]]:
            if step.b not in path:
                stack.append((path + [step.b], steps + [step]))
    return _ranked(found, limit), False


def _candidate(
    boards: Boards,
    g: Graph,
    path: list[str],
    steps: list[Step],
    comp: dict[str, int],
    rank: dict[str, int],
) -> Candidate:
    on_path = set(path)
    conflict = [i for i in path if i in g.conflict]
    # an opposes that touches the walk is conflict, both ends (G5)
    for link in boards.links:
        if link.kind == "opposes" and {link.a, link.b} & on_path:
            for end in (link.a, link.b):
                if end not in conflict:
                    conflict.append(end)
    opened = open_hypotheses(boards, on_path)
    best_rank = min((rank[h] if h in rank else len(rank) for h in opened), default=INF)
    cand = Candidate(
        path=path,
        steps=steps,
        conflict=conflict,
        resolution=path[-1],
        open=opened,
        weak=sum(s.link.weak for s in steps),
        components=len({comp[i] for i in path}),
        backward=sum(not s.forward for s in steps),
    )
    cand.key = (
        Fraction(cand.weak, len(steps)),
        best_rank,
        len(path),
        cand.components,
        cand.backward,
        tuple(path),
    )
    return cand


def _ranked(found: list[Candidate], limit: int | None) -> list[Candidate]:
    found.sort(key=lambda c: c.key)
    return found[:limit] if limit else found


def walk_text(cand: Candidate) -> str:
    """The whole walk on one line."""
    out = cand.path[0]
    for s in cand.steps:
        kind = s.link.kind + (f"({s.link.carries})" if s.link.carries else "")
        arrow = f"-{kind}->" if s.forward else f"<-{kind}-"
        if s.link.weak:
            arrow = arrow.replace("-", "~")
        out += f" {arrow} {s.b}"
    return out


def skeleton(
    boards: Boards,
    cand: Candidate,
    audience: str,
    protagonist: str,
    form: str,
) -> dict[str, Any]:
    """A story file with the structure filled and no sentences: the allow-list
    is a suggestion (the walk, its conflict and open hypotheses, the two
    parties) that a human curates."""
    allow = list(
        dict.fromkeys([audience, protagonist, *cand.path, *cand.conflict, *cand.open])
    )
    return {
        "record": "story",
        "schema_version": "0.1",
        "id": f"story-{protagonist}-{form}",
        "boards": boards.stamps,
        "audience": audience,
        "protagonist": protagonist,
        "form": form,
        "allow": allow,
        "path": cand.path,
        "conflict": cand.conflict,
        "resolution": [cand.resolution],
        "open": cand.open,
        "sentences": [],
        "voice": "ai",
        "run": {"procedure": "story"},
    }
