"""The method profile as the engine holds it: the constants of the format and the
classes `Board`, `Template`, `Kind`, `Step` and `Profile` (see `profile.py`)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


from smd_engine.render.frames_text import STEPS

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
COLOUR = re.compile(r"#[0-9a-f]{6}")
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
    "board_dense",
    "compare_groups",
    "compare_skip",
    "reading",
    "sessionflow",
}
# `short` is optional: the board's name where room is short (the legend's
# transitions, the graph's planes, the frames' element details); the label
# stands in when it is absent (gate Г8б В).
BOARD_KEYS = {"id", "label", "short", "halves", "region", "colour", "split"}
BOARD_FLAGS = ("object",)
# A board template (`per_record: true`): no region or halves; the kinds its
# boards take; each record declares its own boards of it (`boards` in a record).
TEMPLATE_KEYS = {"id", "label", "colour", "kinds", "unfolds", "per_record"}
TEMPLATE_FLAGS = ("object", "needs_position")
# `label` is plural, for counters, legends and groups; `label_one` singular,
# where one element's kind is named (the digest line, the tables, the panels).
KIND_KEYS = {"id", "label", "label_one", "home", "shape"}
KIND_FLAGS = (
    "needs_position",
    "container",
    "role",
    "scheme",
    "skeleton",
    "light_off",
    "stance",
    "factual",
    "vsm",
    "of_whole",
)
# Hints that read `vsm_system` (validate/management.py): without a kind
# flagged `vsm` they can never fire.
VSM_HINTS = ("single-node-metasystem", "absorbed-into-system-1", "no-model-of-whole")
# Hints that read `of_whole` (validate/management.py): without a kind flagged
# `of_whole`, `model-of-whole-one-filler` could never fire and
# `no-model-of-whole` would fire on every place that fills system 4.
OF_WHOLE_HINTS = ("no-model-of-whole", "model-of-whole-one-filler")
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
# Elements on one board past which the hint board-dense advises folding or
# splitting it; a profile sets its own in `board_dense` (docs/checks.md).
BOARD_DENSE = 15
# The kinds `seen_from` may name (gate Г3 Б): a position, or a reflexive
# position where the profile has that kind; never a place for others.
SEEN_FROM_KINDS = ("position", "reflexive_position")
# The kinds `reflected_from` may name (gate Г5а Б): the same, so that the
# reflexive exit of a cycle may be recorded on a reflexive position.
REFLECTED_FROM_KINDS = SEEN_FROM_KINDS
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
    short: dict[str, str] = field(default_factory=dict)  # empty: the label stands in


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
    label: dict[str, str]  # plural: «позиции»
    label_one: dict[str, str]  # singular: «позиция»
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
    vsm: bool = False  # takes the field `vsm_system`: Beer's systems 1-5
    of_whole: bool = (
        False  # takes the fields of_whole and written: a model of the whole
    )


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
    board_dense: int = BOARD_DENSE
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

    def board_short(self, board_id: str, lang: str) -> str:
        """The board's short name, where room is short; its label without one."""
        board = self.board(board_id)
        return (board.short or board.label)[lang]

    def kind_label(self, kind_id: str, lang: str) -> str:
        return self.kind(kind_id).label[lang]

    def kind_label_one(self, kind_id: str, lang: str) -> str:
        """The singular label of a kind, for one element of it."""
        return self.kind(kind_id).label_one[lang]


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
