"""Reading a profile file into a `Profile`: every key checked, with the reason
in the error (the format is in docs/profiles.md; loading is in `profile.py`)."""

from __future__ import annotations

from math import inf
from itertools import combinations
from typing import Any


from smd_engine.profile_model import (
    Board,
    BOARD_DENSE,
    BOARD_FLAGS,
    BOARD_KEYS,
    COLOUR,
    ENGINE_RELATIONS,
    FRAME_PICKS,
    FRAME_STATES,
    HALVES,
    HINT_KINDS,
    Kind,
    KIND_FLAGS,
    KIND_KEYS,
    OF_WHOLE_HINTS,
    PICK_KEYS,
    Profile,
    ProfileError,
    READING_STEPS,
    RELATION_KEYS,
    REQUIRED_KINDS,
    RESERVED_BOARD_IDS,
    rows_of,
    SCREENS,
    SESSIONFLOW_BLOCKS,
    SHAPES,
    Step,
    STEP_KEYS,
    Template,
    TEMPLATE_FLAGS,
    TEMPLATE_KEYS,
    TOP_KEYS,
    VSM_HINTS,
)
from smd_engine.screen import (
    BOARD_TOP,
    MARGIN,
    WIDTH,
    inside,
    outline,
    overlap,
    triangle_parts,
)


def _labels(raw: Any, where: str, key: str = "label") -> dict[str, str]:
    """A {ru, en} label: both languages, text, neither empty (gate Г7д Б). A
    value left blank in the YAML (`ru:`) reads as None and is empty too."""
    if not isinstance(raw, dict) or not {"ru", "en"} <= raw.keys():
        raise ProfileError(f"{where}: {key} needs ru and en")
    scalars = [
        lang
        for lang in ("ru", "en")
        if raw[lang] is not None and not isinstance(raw[lang], str)
    ]
    if scalars:
        raise ProfileError(f"{where}: {key} {' and '.join(scalars)} must be text")
    empty = [
        lang for lang in ("ru", "en") if raw[lang] is None or not str(raw[lang]).strip()
    ]
    if empty:
        raise ProfileError(f"{where}: {key} {' and '.join(empty)} must not be empty")
    return {"ru": str(raw["ru"]), "en": str(raw["en"])}


def _keys(raw: dict[str, Any], allowed: set[str], where: str) -> None:
    unknown = sorted(str(k) for k in raw.keys() - allowed)
    if unknown:
        raise ProfileError(f"{where}: unknown keys {unknown}")


def _id(raw: dict[str, Any], where: str) -> str:
    value = raw.get("id")
    if not isinstance(value, str) or not value:
        raise ProfileError(f"{where}: id is missing or not a string")
    return value


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
        raise ProfileError(f"{where}: a colour is written #rrggbb, lowercase")
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
        _id(raw, where),
        _labels(raw.get("label"), where),
        ordered,
        (x0, y0, x1, y1),
        (colour[0], colour[1]),
        float(split),
        flags["object"],
        short=_labels(raw["short"], where, "short") if "short" in raw else {},
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
        raise ProfileError(
            f"{where}: colour takes 2 colours, each #rrggbb in lowercase"
        )
    kinds = _strings(raw.get("kinds"), f"{where}: kinds")
    if not kinds:
        raise ProfileError(f"{where}: a template takes at least one kind")
    return Template(
        _id(raw, where),
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
        _id(raw, where),
        _labels(raw.get("label"), where),
        _labels(raw.get("label_one"), where, "label_one"),
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
            rid = _id(raw, f"{name}: relation {raw.get('id')}")
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
        raw_groups = data.get("compare_groups", {})
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
        dense = data.get("board_dense", BOARD_DENSE)
        if not isinstance(dense, int) or isinstance(dense, bool) or dense < 1:
            raise ProfileError(f"{name}: board_dense must be a whole number > 0")
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
        need_vsm = sorted(set(hints) & set(VSM_HINTS))
        if need_vsm and not any(k.vsm for k in kinds):
            raise ProfileError(
                f"{name}: the hints {need_vsm} read vsm_system and need a kind "
                "flagged vsm"
            )
        need_whole = sorted(set(hints) & set(OF_WHOLE_HINTS))
        if need_whole and not any(k.of_whole for k in kinds):
            raise ProfileError(
                f"{name}: the hints {need_whole} read of_whole and need a kind "
                "flagged of_whole"
            )
    except (KeyError, TypeError) as exc:
        raise ProfileError(f"{name}: malformed profile ({exc})") from exc
    return Profile(
        name,
        _labels(data.get("title"), name, "title"),
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
        dense,
    )
