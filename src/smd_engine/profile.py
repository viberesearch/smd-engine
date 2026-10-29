"""Method profiles: the boards, kinds, relations and hints a record follows.

A profile is a YAML file in `profiles/` (packaged in the wheel under
`assets/profiles`). A board set names its profile in `profile`;
`program-three-boards` when absent. The format is in docs/profiles.md.
"""

from __future__ import annotations

import re
from math import inf
from dataclasses import dataclass, field, replace
from functools import cache
from importlib import resources
from itertools import combinations
from pathlib import Path
from typing import Any

import yaml

from smd_engine.render.frames_text import STEPS
from smd_engine.screen import (
    BOARD_TOP,
    MARGIN,
    WIDTH,
    inside,
    outline,
    overlap,
    record_regions,
    triangle_parts,
)

DEFAULT_PROFILE = "program-three-boards"
HALVES = ("small", "big")  # the schema's enum for `half`
SHAPES = {
    "marker",
    "figure",
    "ellipse",
    "question",
    "frame",
    "heading",
    "paragraph",
    "box",
}
SCREENS = ("regions", "triangles")
COLOUR = re.compile(r"#[0-9a-fA-F]{6}")
# The id of a board a record makes of a template: the schema's id less the
# dot, which separates a board from its half (`s.small`).
RECORD_BOARD_ID = re.compile(r"[a-z0-9][a-z0-9_-]*")
# The layers `smd graph` draws above and below the board planes, keyed like a
# board (render/graph.py `planes`, assets/graph.js): no board takes these ids.
RESERVED_BOARD_IDS = ("records", "sources")
FRAME_PICKS = {"old-frames", "new-frames"}
PICK_KEYS = {"kinds", "board", "half", "frame_state"}
FRAME_STATES = ("old", "new")  # the schema's enum for `frame_state`
TOP_KEYS = {
    "id",
    "title",
    "screen",
    "boards",
    "kinds",
    "relations",
    "hints",
    "compare_groups",
    "compare_skip",
    "reading",
    "sessionflow",
}
BOARD_KEYS = {"id", "label", "halves", "region", "colour", "split"}
BOARD_FLAGS = ("object",)
# A board template (`per_record: true`): no region or halves; the kinds its
# boards take; each record declares its own boards of it (`boards` in a record).
TEMPLATE_KEYS = {"id", "label", "colour", "kinds", "unfolds", "per_record"}
TEMPLATE_FLAGS = ("object", "needs_position")
KIND_KEYS = {"id", "label", "home", "shape"}
KIND_FLAGS = (
    "needs_position",
    "container",
    "role",
    "scheme",
    "skeleton",
    "light_off",
    "stance",
    "factual",
)
STEP_KEYS = {"step", "board", "pick"}
RELATION_KEYS = {"id", "label"}
# Relation kinds the engine labels itself (render/graph.py EDGE_KINDS): a
# profile lists them by id; any other relation kind comes with its label.
ENGINE_RELATIONS = (
    "shift",
    "flow",
    "produces",
    "uses",
    "belongs",
    "opposes",
    "refers",
    "represents",
    "other",
)
# Kind ids the engine names in its checks, switches and fold counters
# (docs/profiles.md, "Ids every profile defines"); a hint may need one more.
REQUIRED_KINDS = (
    "position",
    "place_for_others",
    "function",
    "cooperation",
    "gap",
    "note",
)
HINT_KINDS = {"entry": "entry", "goal-without-breakdown": "goal"}
# The SessionFlow questions render/sessionflow.py fills from the profile.
SESSIONFLOW_BLOCKS = ("who", "where", "what_for")
# Reading steps `smd frames` has a title and lead for: the step texts of
# render/frames_text.py less the frames it adds after the reading.
READING_STEPS = frozenset(
    k for k, v in STEPS["en"].items() if isinstance(v, tuple) and k in STEPS["ru"]
) - {"transitions", "k", "full", "cycle"}

Pick = dict[str, Any] | str  # element filter, or a named pick (old-frames, new-frames)
Region = tuple[float, float, float, float]


class ProfileError(ValueError):
    """A profile is unknown or its file is malformed."""


@dataclass(frozen=True)
class Board:
    id: str
    label: dict[str, str]
    halves: tuple[str, ...]  # empty for a board without halves
    region: Region
    colour: tuple[str, str]  # background, ink
    split: float = 0.0  # x where two halves meet: `split`, or the region's middle
    object: bool = False  # subject-object talk on it is warned
    template: str = ""  # a board a record makes of a template: the template's id


@dataclass(frozen=True)
class Template:
    """A board template (`per_record: true`): each record makes its own boards
    of it, which take its kinds; `unfolds` limits the kinds of the element a
    board of it unfolds (any kind when empty)."""

    id: str
    label: dict[str, str]
    colour: tuple[str, str]  # background, ink
    kinds: tuple[str, ...]
    unfolds: tuple[str, ...] = ()
    object: bool = False
    needs_position: bool = False  # a board of it names `seen_from`


@dataclass(frozen=True)
class Kind:
    id: str
    label: dict[str, str]
    home: str | None
    needs_position: bool
    container: bool
    role: bool
    scheme: bool
    shape: str
    skeleton: bool
    light_off: bool = False  # left off the lighter screen (--light)
    stance: bool = False  # takes the field `stance`: a position (GP-Guide11 ¶35)
    factual: bool = False  # records a fact: a breakdown a goal can arise from


@dataclass(frozen=True)
class Step:
    """A reading step: its id, the board or half it is cut to, what it adds.
    A step on a template is repeated for each record board of it: such a step
    keeps the id of the template's step in `template_step`, whose texts
    (render/frames_text.py) it takes, and is named by its board."""

    id: str
    board: str
    pick: Pick
    template_step: str = ""


# eq=False: load_profile reads each profile once, so identity is equality, and
# hash() works (a generated __hash__ would fail on the dict fields).
@dataclass(frozen=True, eq=False)
class Profile:
    id: str
    title: dict[str, str]
    boards: tuple[Board, ...]
    kinds: tuple[Kind, ...]  # in layout order
    relations: tuple[str, ...]
    hints: tuple[str, ...]
    compare_groups: dict[str, tuple[str, ...]]
    reading: tuple[Step, ...]
    sessionflow: dict[str, tuple[dict[str, Any], ...]] | None = None
    screen: str = "regions"
    compare_skip: tuple[str, ...] = ()
    # labels {ru, en} of the relation kinds outside ENGINE_RELATIONS
    relation_labels: dict[str, dict[str, str]] = field(default_factory=dict)
    # board templates (`per_record`), and every reading step as written, the
    # steps of a template's boards included (`reading` holds the expanded ones)
    templates: tuple[Template, ...] = ()
    steps: tuple[Step, ...] = ()
    _boards: dict[str, Board] = field(default_factory=dict, repr=False)
    _kinds: dict[str, Kind] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._boards.update({b.id: b for b in self.boards})
        self._kinds.update({k.id: k for k in self.kinds})

    def board(self, board_id: str) -> Board:
        return self._boards[board_id]

    def kind(self, kind_id: str) -> Kind:
        return self._kinds[kind_id]

    def has_board(self, board_id: str) -> bool:
        return board_id in self._boards

    def template(self, template_id: str) -> Template | None:
        return next((t for t in self.templates if t.id == template_id), None)

    def board_or_template(self, board_id: str) -> Board | Template:
        """A board, or a template: what a kind's `home` may name."""
        return self.template(board_id) or self.board(board_id)

    @property
    def record_boards(self) -> tuple[Board, ...]:
        """The boards a record made of the templates, in the record's order."""
        return tuple(b for b in self.boards if b.template)

    def has_kind(self, kind_id: str) -> bool:
        return kind_id in self._kinds

    def kinds_where(self, flag: str) -> set[str]:
        """Kind ids whose boolean `flag` is set."""
        return {k.id for k in self.kinds if getattr(k, flag)}

    def kinds_shaped(self, shape: str) -> set[str]:
        """Kind ids the screen draws with `shape`."""
        return {k.id for k in self.kinds if k.shape == shape}

    @property
    def home_board(self) -> dict[str, str]:
        return {k.id: k.home for k in self.kinds if k.home}

    @property
    def kind_order(self) -> list[str]:
        return [k.id for k in self.kinds]

    @property
    def rows(self) -> list[list[Board]]:
        return rows_of(self.boards)

    @property
    def subject_boards(self) -> list[str]:
        """Where subject-object talk belongs: the home boards of the roles."""
        return sorted({k.home for k in self.kinds if k.role and k.home})

    def board_label(self, board_id: str, lang: str) -> str:
        return self.board(board_id).label[lang]

    def kind_label(self, kind_id: str, lang: str) -> str:
        return self.kind(kind_id).label[lang]


def rows_of(boards: tuple[Board, ...]) -> list[list[Board]]:
    """The boards in rows, top down, in profile order within a row: a board
    joins the row above when its region starts above that row's lowest edge."""
    out: list[list[Board]] = []
    for b in sorted(boards, key=lambda b: b.region[1]):
        if out and b.region[1] < max(r.region[3] for r in out[-1]):
            out[-1].append(b)
        else:
            out.append([b])
    order = {b.id: n for n, b in enumerate(boards)}
    return [sorted(row, key=lambda b: order[b.id]) for row in out]


def matches(el: dict[str, Any], pick: dict[str, Any]) -> bool:
    """Whether an element passes a filter of `kinds`, `board`, `half`, `frame_state`."""
    if "kinds" in pick and el["kind"] not in pick["kinds"]:
        return False
    return all(
        el.get(key) == pick[key]
        for key in ("board", "half", "frame_state")
        if key in pick
    )


def profiles_dir() -> Path:
    """Profile files: packaged in the wheel, or the repository in a dev checkout."""
    packaged = Path(str(resources.files("smd_engine"))) / "assets" / "profiles"
    if packaged.is_dir():
        return packaged
    return Path(__file__).resolve().parents[2] / "profiles"


def profile_ids() -> list[str]:
    return sorted(p.stem for p in profiles_dir().glob("*.yaml"))


def _labels(raw: Any, where: str) -> dict[str, str]:
    if not isinstance(raw, dict) or not {"ru", "en"} <= raw.keys():
        raise ProfileError(f"{where}: label needs ru and en")
    return {"ru": str(raw["ru"]), "en": str(raw["en"])}


def _keys(raw: dict[str, Any], allowed: set[str], where: str) -> None:
    unknown = sorted(str(k) for k in raw.keys() - allowed)
    if unknown:
        raise ProfileError(f"{where}: unknown keys {unknown}")


def _flags(raw: dict[str, Any], names: tuple[str, ...], where: str) -> dict[str, bool]:
    flags = {f: raw.get(f, False) for f in names}
    not_bool = [f for f, v in flags.items() if not isinstance(v, bool)]
    if not_bool:
        raise ProfileError(f"{where}: {', '.join(not_bool)} must be true or false")
    return flags


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _board(raw: dict[str, Any], where: str) -> Board:
    _keys(raw, BOARD_KEYS | set(BOARD_FLAGS), where)
    flags = _flags(raw, BOARD_FLAGS, where)
    halves = raw.get("halves", "none")
    if halves in ("none", None):
        halves = []
    if (
        not isinstance(halves, list)
        or not all(h in HALVES for h in halves)
        or len(set(halves)) != len(halves)
    ):
        raise ProfileError(
            f"{where}: halves is none or a list of distinct halves among "
            f"{', '.join(HALVES)}"
        )
    region = tuple(raw["region"])  # numbers as written: screen units
    colour = tuple(str(c) for c in raw["colour"])
    if len(region) != 4 or not all(map(_number, region)) or len(colour) != 2:
        raise ProfileError(f"{where}: region takes 4 numbers, colour 2 colours")
    if not all(COLOUR.fullmatch(c) for c in colour):
        raise ProfileError(f"{where}: a colour is written #rrggbb")
    x0, y0, x1, y1 = region
    left, top, right, _ = MARGIN
    if not (
        x0 < x1 and y0 < y1 and inside(outline(region), (0, BOARD_TOP, WIDTH, inf))
    ):
        raise ProfileError(
            f"{where}: region must lie on the screen with the board drawn around it: "
            f"{left:g} <= x0 < x1 <= {WIDTH - right:g}, {BOARD_TOP + top:g} <= y0 < y1"
        )
    ordered = tuple(h for h in HALVES if h in halves)
    split = raw.get("split", (x0 + x1) / 2)
    if "split" in raw and (len(ordered) != 2 or not _number(split)):
        raise ProfileError(f"{where}: split is a number, for a board with two halves")
    if len(ordered) == 2 and not x0 + 10 < split < x1 - 10:
        raise ProfileError(
            f"{where}: split must lie inside the region, more than 10 from each edge"
        )
    return Board(
        str(raw["id"]),
        _labels(raw.get("label"), where),
        ordered,
        (x0, y0, x1, y1),
        (colour[0], colour[1]),
        float(split),
        flags["object"],
    )


def _template(raw: dict[str, Any], where: str) -> Template:
    """A board template: a label, a colour and the kinds its boards take; no
    region or halves, since each record places its own boards of it."""
    _keys(raw, TEMPLATE_KEYS | set(TEMPLATE_FLAGS), where)
    flags = _flags(raw, TEMPLATE_FLAGS, where)
    if raw["per_record"] is not True:
        raise ProfileError(f"{where}: per_record must be true")
    colour = tuple(str(c) for c in raw["colour"])
    if len(colour) != 2 or not all(COLOUR.fullmatch(c) for c in colour):
        raise ProfileError(f"{where}: colour takes 2 colours, each #rrggbb")
    kinds = _strings(raw.get("kinds"), f"{where}: kinds")
    if not kinds:
        raise ProfileError(f"{where}: a template takes at least one kind")
    return Template(
        str(raw["id"]),
        _labels(raw.get("label"), where),
        (colour[0], colour[1]),
        kinds,
        _strings(raw.get("unfolds", []), f"{where}: unfolds"),
        flags["object"],
        flags["needs_position"],
    )


def _list(
    data: dict[str, Any], key: str, where: str, required: bool = False
) -> list[Any]:
    """A list section of the file; an optional one may be absent."""
    value = data.get(key)
    if value is None and not required:
        return []
    if not isinstance(value, list):
        raise ProfileError(f"{where}: {key} must be a list")
    return value


def _mappings(items: list[Any], where: str) -> list[dict[str, Any]]:
    if not all(isinstance(i, dict) for i in items):
        raise ProfileError(f"{where} must be mappings")
    return items


def _strings(value: Any, where: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ProfileError(f"{where} must be a list of strings")
    return tuple(value)


def _unique(ids: list[str], what: str, where: str) -> None:
    twice = sorted({i for i in ids if ids.count(i) > 1})
    if twice:
        raise ProfileError(f"{where}: duplicate {what} ids {twice}")


def _known(names: tuple[str, ...], kinds: set[str], where: str) -> tuple[str, ...]:
    unknown = sorted(set(names) - kinds)
    if unknown:
        raise ProfileError(f"{where}: unknown kinds {unknown}")
    return names


def _kind(raw: dict[str, Any], boards: set[str], where: str) -> Kind:
    _keys(raw, KIND_KEYS | set(KIND_FLAGS), where)
    flags = _flags(raw, KIND_FLAGS, where)
    if raw.get("home") is not None and raw["home"] not in boards:
        raise ProfileError(
            f"{where}: home '{raw['home']}' is neither a board nor a template"
        )
    if raw.get("shape") not in SHAPES:
        raise ProfileError(f"{where}: shape must be one of {', '.join(sorted(SHAPES))}")
    return Kind(
        str(raw["id"]),
        _labels(raw.get("label"), where),
        raw.get("home"),
        shape=str(raw["shape"]),
        **flags,
    )


def _pick(
    raw: Any, where: str, boards: dict[str, Board], kinds: set[str]
) -> dict[str, Any]:
    """An element filter: known keys, a list of known kinds, a known board and
    one of its halves, a frame state."""
    if not isinstance(raw, dict):
        raise ProfileError(
            f"{where}: a pick is a mapping of {', '.join(sorted(PICK_KEYS))}"
        )
    _keys(raw, PICK_KEYS, where)
    if not raw:
        raise ProfileError(f"{where}: an empty pick would match every element")
    if "kinds" in raw:
        _known(_strings(raw["kinds"], f"{where}: kinds"), kinds, where)
    board = raw.get("board")
    if "board" in raw and board not in boards:
        raise ProfileError(f"{where}: unknown board {board!r}")
    if "half" in raw:
        on = [boards[board]] if board is not None else list(boards.values())
        if raw["half"] not in {h for b in on for h in b.halves}:
            raise ProfileError(f"{where}: unknown half {raw['half']!r}")
    if raw.get("frame_state", "old") not in FRAME_STATES:
        raise ProfileError(f"{where}: frame_state must be old or new")
    return raw


def _reading(
    items: list[Any],
    name: str,
    boards: dict[str, Board],
    kinds: set[str],
    templates: dict[str, Template],
) -> tuple[Step, ...]:
    """The reading steps as written. A step whose board is a template is read
    once per board a record makes of it; its pick is a filter, narrowed to
    that board (a `board` in it names the template)."""
    steps: list[Step] = []
    for raw in _mappings(items, f"{name}: reading steps"):
        step = str(raw["step"])
        where = f"{name}: reading step {step}"
        _keys(raw, STEP_KEYS, where)
        if step not in READING_STEPS:
            raise ProfileError(
                f"{name}: reading step '{step}' has no texts in smd frames; "
                f"known: {', '.join(sorted(READING_STEPS))}"
            )
        board, _, half = str(raw["board"]).partition(".")
        template = board in templates and not half
        if not template and (
            board not in boards or (half and half not in boards[board].halves)
        ):
            raise ProfileError(
                f"{where}: board '{raw['board']}' is neither a board nor a half"
            )
        pick = raw["pick"]
        if template:
            if (
                not isinstance(pick, dict)
                or pick.get("board", board) != board
                or "half" in pick
            ):
                raise ProfileError(
                    f"{where}: a step on a template takes a filter without half, "
                    "whose board, if given, is the template"
                )
            rest = {k: v for k, v in pick.items() if k != "board"}
            if rest:
                _pick(rest, where, boards, kinds)
        elif not (isinstance(pick, str) and pick in FRAME_PICKS):
            if isinstance(pick, str):
                raise ProfileError(
                    f"{where}: a named pick is one of {', '.join(sorted(FRAME_PICKS))}"
                )
            pick = _pick(pick, where, boards, kinds)
        steps.append(Step(step, str(raw["board"]), pick))
    _unique([s.id for s in steps], "reading step", name)
    return tuple(steps)


def _sessionflow(
    flow: Any, name: str, boards: dict[str, Board], kinds: set[str]
) -> dict[str, tuple[dict[str, Any], ...]] | None:
    """The picks of each SessionFlow question; None when the profile has none."""
    if flow is None:
        return None
    if not isinstance(flow, dict):
        raise ProfileError(f"{name}: sessionflow must be a mapping")
    where = f"{name}: sessionflow"
    unknown = sorted(str(q) for q in flow if q not in SESSIONFLOW_BLOCKS)
    if unknown:
        raise ProfileError(
            f"{where}: unknown blocks {unknown}; known: {', '.join(SESSIONFLOW_BLOCKS)}"
        )
    picks = {
        str(q): tuple(
            _pick(p, f"{where} {q}", boards, kinds) for p in _list(flow, q, where, True)
        )
        for q in flow
    }
    return picks or None


def _hints(hints: tuple[str, ...], name: str) -> tuple[str, ...]:
    """Hint ids the engine has: the registry the validate package fills from
    validate/hints.py, imported here and not at the top, since the validate
    package imports this module."""
    from smd_engine.validate import HINTS

    _unique(list(hints), "hint", name)
    unknown = sorted(set(hints) - HINTS.keys())
    if unknown:
        raise ProfileError(
            f"{name}: unknown hints {unknown}; known: {', '.join(sorted(HINTS))}"
        )
    return hints


def _relations(items: Any, name: str) -> dict[str, dict[str, str]]:
    """Relation kinds in order: an engine relation by id, or `{id, label}`;
    a kind outside ENGINE_RELATIONS needs its label. Returns id to label ({}
    for an engine relation)."""
    if not isinstance(items, list):
        raise ProfileError(
            f"{name}: relations must be a list of strings and {{id, label}} mappings"
        )
    out: dict[str, dict[str, str]] = {}
    ids: list[str] = []
    for raw in items:
        if isinstance(raw, str):
            rid, label = raw, {}
        elif isinstance(raw, dict):
            _keys(raw, RELATION_KEYS, f"{name}: relation {raw.get('id')}")
            rid = str(raw["id"])
            label = _labels(raw.get("label"), f"{name}: relation {rid}")
        else:
            raise ProfileError(
                f"{name}: relations must be a list of strings and {{id, label}} "
                "mappings"
            )
        if label and rid in ENGINE_RELATIONS:
            raise ProfileError(
                f"{name}: relation '{rid}' is the engine's; it takes no label"
            )
        if not label and rid not in ENGINE_RELATIONS:
            raise ProfileError(
                f"{name}: relation '{rid}' is not the engine's and needs a label "
                "{ru, en}"
            )
        ids.append(rid)
        out[rid] = label
    _unique(ids, "relation", name)
    return out


def _hint_needs(hints: tuple[str, ...]) -> tuple[set[str], set[str]]:
    """The kinds and relation kinds the enabled hints name: HINT_KINDS, and
    what a hint of one profile's scheme registers (validate/context.py `hint`)."""
    from smd_engine.validate.context import hint_needs

    kinds = {HINT_KINDS[h] for h in hints if h in HINT_KINDS}
    relations: set[str] = set()
    for h in hints:
        k, r = hint_needs(h)
        kinds |= set(k)
        relations |= set(r)
    return kinds, relations


def _layout(boards: tuple[Board, ...], screen: Any, name: str) -> None:
    """The shape a screen can draw; boards drawn apart; rows the layout can grow."""
    if screen not in SCREENS:
        raise ProfileError(f"{name}: screen must be one of {', '.join(SCREENS)}")
    if screen == "triangles":
        _triangles(boards, name)
    left, top, right, bottom = MARGIN
    for a, b in combinations(boards, 2):
        if overlap(outline(a.region), outline(b.region)):
            raise ProfileError(
                f"{name}: the boards {a.id} and {b.id} overlap as drawn: regions "
                f"side by side need {left + right:g} between them, one above the "
                f"other {top + bottom:g}"
            )
    for row in rows_of(boards):
        for a, b in combinations(row, 2):
            if not (a.region[1] < b.region[3] and b.region[1] < a.region[3]):
                raise ProfileError(
                    f"{name}: {a.id} and {b.id} share a row of the screen, but one "
                    "lies above the other; boards of a row overlap vertically"
                )


def _triangles(boards: tuple[Board, ...], name: str) -> None:
    """Three boards, the top two without halves, each drawn within its part of
    the triangles screen (screen.triangle_parts)."""
    if len(boards) != 3 or any(b.halves for b in boards[:2]):
        raise ProfileError(
            f"{name}: the triangles screen takes three boards: two without halves "
            "on top, then one below them"
        )
    left, top, right, bottom = MARGIN
    for b, part in zip(boards, triangle_parts()):
        if not inside(outline(b.region), part):
            x0, y0, x1, y1 = part
            raise ProfileError(
                f"{name}: on the triangles screen board {b.id} must lie within "
                f"x {x0:g}..{x1:g}, y {y0:g}..{y1:g} as drawn: region "
                f"{x0 + left:g} <= x0 < x1 <= {x1 - right:g}, "
                f"{y0 + top:g} <= y0 < y1 <= {y1 - bottom:g}"
            )


def _parse(data: dict[str, Any], name: str) -> Profile:
    try:
        _keys(data, TOP_KEYS, name)
        entries = _mappings(_list(data, "boards", name, True), f"{name}: boards")
        boards = tuple(
            _board(b, f"{name}: board {b.get('id')}")
            for b in entries
            if "per_record" not in b
        )
        templates = tuple(
            _template(b, f"{name}: template {b.get('id')}")
            for b in entries
            if "per_record" in b
        )
        if not boards:
            raise ProfileError(f"{name}: a profile takes at least one board")
        by_id = {b.id: b for b in boards}
        by_template = {t.id: t for t in templates}
        kinds = tuple(
            _kind(k, set(by_id) | set(by_template), f"{name}: kind {k.get('id')}")
            for k in _mappings(_list(data, "kinds", name, True), f"{name}: kinds")
        )
        ids = [b.id for b in boards] + [t.id for t in templates]
        _unique(ids, "board", name)
        reserved = sorted(set(ids) & set(RESERVED_BOARD_IDS))
        if reserved:
            raise ProfileError(
                f"{name}: board ids {reserved} are the layers of smd graph"
            )
        _unique([k.id for k in kinds], "kind", name)
        known = {k.id for k in kinds}
        for t in templates:
            _known(t.kinds, known, f"{name}: template {t.id}")
            _known(t.unfolds, known, f"{name}: template {t.id}: unfolds")
            homed = sorted(
                k.id for k in kinds if k.home == t.id and k.id not in t.kinds
            )
            if homed:
                raise ProfileError(
                    f"{name}: template {t.id}: kinds {homed} live on it but are "
                    "not among its kinds"
                )
        raw_groups = data.get("compare_groups") or {}
        if not isinstance(raw_groups, dict):
            raise ProfileError(f"{name}: compare_groups must be a mapping")
        groups = {
            str(g): _known(_strings(ks, f"{name}: compare group {g}"), known, name)
            for g, ks in raw_groups.items()
        }
        skip = _strings(data.get("compare_skip") or [], f"{name}: compare_skip")
        _known(skip, known, f"{name}: compare_skip")
        steps = _reading(_list(data, "reading", name), name, by_id, known, by_template)
        sessionflow = _sessionflow(data.get("sessionflow"), name, by_id, known)
        relation_map = _relations(data.get("relations") or [], name)
        relations = tuple(relation_map)
        hints = _hints(_strings(data.get("hints") or [], f"{name}: hints"), name)
        if data.get("id") != name:
            raise ProfileError(f"{name}: id must be the file name")
        screen = data.get("screen", "regions")
        _layout(boards, screen, name)
        if templates and screen == "triangles":
            raise ProfileError(f"{name}: the triangles screen takes no templates")
        hint_kinds, hint_relations = _hint_needs(hints)
        need = set(REQUIRED_KINDS) | hint_kinds
        if need - known:
            raise ProfileError(
                f"{name}: missing kinds the engine names: {sorted(need - known)}"
            )
        if hint_relations - set(relations):
            raise ProfileError(
                f"{name}: missing relation kinds the hints name: "
                f"{sorted(hint_relations - set(relations))}"
            )
    except (KeyError, TypeError) as exc:
        raise ProfileError(f"{name}: malformed profile ({exc})") from exc
    return Profile(
        name,
        _labels(data.get("title"), name),
        boards,
        kinds,
        relations,
        hints,
        groups,
        tuple(s for s in steps if s.board not in by_template),
        sessionflow,
        str(screen),
        skip,
        {r: label for r, label in relation_map.items() if label},
        templates,
        steps,
    )


@cache
def load_profile(profile_id: str = DEFAULT_PROFILE) -> Profile:
    """The profile with this id, read once."""
    known = profile_ids()
    if profile_id not in known:
        raise ProfileError(f"unknown profile '{profile_id}'; known: {', '.join(known)}")
    path = profiles_dir() / f"{profile_id}.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ProfileError(f"{profile_id}: not valid YAML ({exc})") from exc
    if not isinstance(data, dict):
        raise ProfileError(f"{profile_id}: top level must be a mapping")
    return _parse(data, profile_id)


def default_profile() -> Profile:
    return load_profile(DEFAULT_PROFILE)


def profile_id(data: dict[str, Any]) -> str:
    return str(data.get("profile", DEFAULT_PROFILE))


def profile_of(data: dict[str, Any]) -> Profile:
    """The profile a board set follows, with the boards the record makes of
    the profile's templates (`boards` in the record). A record board that is
    malformed, names an unknown template or takes a taken or reserved id is
    left out; the validator reports it (validate/__init__.py
    `_record_board_findings`)."""
    base = load_profile(profile_id(data))
    declared = data.get("boards") if base.templates else None
    if not isinstance(declared, list):
        return base
    taken = {b.id for b in base.boards} | {t.id for t in base.templates}
    made: list[tuple[str, str, str]] = []
    for raw in declared:
        if not isinstance(raw, dict):
            continue
        bid, tid, label = raw.get("id"), raw.get("template"), raw.get("label")
        if (
            isinstance(bid, str)
            and isinstance(tid, str)
            and isinstance(label, str)
            and RECORD_BOARD_ID.fullmatch(bid)
            and base.template(tid) is not None
            and bid not in taken
            and bid not in RESERVED_BOARD_IDS
        ):
            taken.add(bid)
            made.append((bid, tid, label))
    return _with_record_boards(base, tuple(made)) if made else base


@cache
def _with_record_boards(
    base: Profile, made: tuple[tuple[str, str, str], ...]
) -> Profile:
    """The profile with record boards `made` (id, template, label): each takes
    its template's colour and `object`, a region below the fixed boards
    (screen.record_regions) and the label "<template>: <label>"; a reading
    step of a template is repeated for each of its boards, in the record's
    order, with the id "<step>-<board>"."""
    columns = max(len(row) for row in rows_of(base.boards))
    regions = record_regions([b.region for b in base.boards], len(made), columns)
    boards: list[Board] = []
    for (bid, tid, label), region in zip(made, regions):
        t = base.template(tid)
        assert t is not None
        boards.append(
            Board(
                bid,
                {lang: f"{text}: {label}" for lang, text in t.label.items()},
                (),
                region,
                t.colour,
                (region[0] + region[2]) / 2,
                t.object,
                tid,
            )
        )
    reading: list[Step] = []
    for step in base.steps:
        if base.template(step.board) is None:
            reading.append(step)
            continue
        pick = step.pick if isinstance(step.pick, dict) else {}
        reading += [
            Step(f"{step.id}-{b.id}", b.id, {**pick, "board": b.id}, step.id)
            for b in boards
            if b.template == step.board
        ]
    return replace(
        base,
        boards=base.boards + tuple(boards),
        reading=tuple(reading),
        _boards={},
        _kinds={},
    )
