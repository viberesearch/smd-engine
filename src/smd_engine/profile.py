"""Method profiles: the boards, kinds, relations and hints a record follows.

A profile is a YAML file in `profiles/` (packaged in the wheel under
`assets/profiles`). A board set names its profile in `profile`;
`program-three-boards` when absent. The format is in docs/profiles.md.
"""

from __future__ import annotations

from dataclasses import replace
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from smd_engine.screen import record_regions
from smd_engine.profile_model import (
    DEFAULT_PROFILE,
    HALVES,
    SHAPES,
    SCREENS,
    COLOUR,
    RECORD_BOARD_ID,
    RESERVED_BOARD_IDS,
    FRAME_PICKS,
    PICK_KEYS,
    FRAME_STATES,
    TOP_KEYS,
    BOARD_KEYS,
    BOARD_FLAGS,
    TEMPLATE_KEYS,
    TEMPLATE_FLAGS,
    KIND_KEYS,
    KIND_FLAGS,
    VSM_HINTS,
    OF_WHOLE_HINTS,
    STEP_KEYS,
    RELATION_KEYS,
    ENGINE_RELATIONS,
    REQUIRED_KINDS,
    HINT_KINDS,
    BOARD_DENSE,
    SEEN_FROM_KINDS,
    REFLECTED_FROM_KINDS,
    SESSIONFLOW_BLOCKS,
    READING_STEPS,
    Pick,
    Region,
    ProfileError,
    Board,
    Template,
    Kind,
    Step,
    Profile,
    rows_of,
    matches,
)
from smd_engine.profile_parse import _parse

# the names of the profile model stay importable from here
__all__ = [
    "DEFAULT_PROFILE",
    "HALVES",
    "SHAPES",
    "SCREENS",
    "COLOUR",
    "RECORD_BOARD_ID",
    "RESERVED_BOARD_IDS",
    "FRAME_PICKS",
    "PICK_KEYS",
    "FRAME_STATES",
    "TOP_KEYS",
    "BOARD_KEYS",
    "BOARD_FLAGS",
    "TEMPLATE_KEYS",
    "TEMPLATE_FLAGS",
    "KIND_KEYS",
    "KIND_FLAGS",
    "VSM_HINTS",
    "OF_WHOLE_HINTS",
    "STEP_KEYS",
    "RELATION_KEYS",
    "ENGINE_RELATIONS",
    "REQUIRED_KINDS",
    "HINT_KINDS",
    "BOARD_DENSE",
    "SEEN_FROM_KINDS",
    "REFLECTED_FROM_KINDS",
    "SESSIONFLOW_BLOCKS",
    "READING_STEPS",
    "Pick",
    "Region",
    "ProfileError",
    "Board",
    "Template",
    "Kind",
    "Step",
    "Profile",
    "rows_of",
    "matches",
    "profiles_dir",
    "profile_ids",
    "load_profile",
    "default_profile",
    "profile_id",
    "profile_of",
]


def profiles_dir() -> Path:
    """Profile files: packaged in the wheel, or the repository in a dev checkout."""
    packaged = Path(str(resources.files("smd_engine"))) / "assets" / "profiles"
    if packaged.is_dir():
        return packaged
    return Path(__file__).resolve().parents[2] / "profiles"


def profile_ids() -> list[str]:
    return sorted(p.stem for p in profiles_dir().glob("*.yaml"))


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
    (screen.record_regions), the label "<template>: <label>" and its own
    label as the short name; a reading
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
                {lang: label for lang in t.label},
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
