"""Map acceptance: a member accepts or rejects a map (a board set) in three
layers, the vocabulary, each element and an independent check, and the record
(`task_acceptance`) is pinned to the board's id, version and the sha256 of its
file. The act is the member's; the engine writes no acceptance and no sign-off.
Any edit of the board file voids the acceptance. When the map changed, the
elements to ask again are the ones `compare` does not find unchanged."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from smd_engine.compare import compare
from smd_engine.profile import ProfileError
from smd_engine.records import RecordError, load_record
from smd_engine.task.model import (
    Issue,
    load_task,
    member_ids,
    schema_issues,
    sha256_file,
)

ACTS = ("accept", "reject", "not_read")


def load_board(path: Path) -> dict[str, Any]:
    board = load_record(path)
    if board["record"] != "board_set":
        raise RecordError(f"{path}: a map is a board set")
    return board


def board_version(board: dict[str, Any]) -> str:
    """The version a story stamps: state.version, else the cycle."""
    return str(board.get("state", {}).get("version", board["cycle"]))


def is_void(pack: dict[str, Any], acc: dict[str, Any]) -> bool:
    """Whether the board file changed since the member accepted it."""
    return bool(acc["board"]["sha256"] != pack["map"]["sha256"])


def reask(prior: dict[str, Any], board: dict[str, Any]) -> dict[str, list[str]]:
    """Element ids of the current board by what `compare` says of the prior one:
    `unchanged` (an agreement, the earlier act stands as the pair's answer),
    `changed` (reworded, moved, retyped or new: to be asked again) and
    `removed` (only in the prior board: nothing to ask). Matching is by wording,
    so a pair that is not an agreement is asked again rather than trusted."""
    got: dict[str, list[str]] = {"unchanged": [], "changed": [], "removed": []}
    for pair in compare(prior, board):
        if pair.kind == "agreement" and pair.b:
            got["unchanged"].append(pair.b)
        elif pair.b:
            got["changed"].append(pair.b)
        elif pair.a:
            got["removed"].append(pair.a)
    return {k: sorted(v) for k, v in got.items()}


def _ids(board: dict[str, Any]) -> set[str]:
    return {e["id"] for e in board["elements"]}


def _independent(pack: dict[str, Any], acc: dict[str, Any]) -> bool:
    who = acc["checked_by"].casefold()
    names = {m["id"].casefold() for m in pack["members"]}
    return who not in names | {m["name"].casefold() for m in pack["members"]}


def check_acceptance(
    pack: dict[str, Any],
    acc: dict[str, Any],
    where: str,
    board_path: Path | None = None,
    prior_path: Path | None = None,
) -> list[Issue]:
    """Errors stop the record being read; a void acceptance is a warning, a
    state and not a fault. `board_path` is the board file the pack's map names;
    `prior_path` the board file the acceptance was given on."""
    issues = schema_issues(acc, "task_acceptance", where)
    if issues:
        return issues
    out: list[Issue] = []

    def add(level: str, msg: str) -> None:
        out.append(Issue(level, where, msg))

    pinned = pack.get("map")
    if pinned is None:
        add("error", "the pack has no map: an acceptance needs the pack's `map`")
        return out
    if acc["member"] not in member_ids(pack):
        add("error", f"member {acc['member']} is not a member of the pack")
    void = is_void(pack, acc)
    if void:
        was = acc["board"]["id"]
        now = "" if was == pinned["id"] else f" ({was} is now {pinned['id']})"
        add(
            "warning",
            f"void: the map changed since this acceptance (sha256 differs from "
            f"the pack's map{now}); ask the vocabulary and the check again",
        )
    elif acc["board"]["version"] != pinned["version"]:
        add("warning", "board version differs from the map's, though sha256 is equal")
    if acc.get("checked_by") and not _independent(pack, acc):
        add(
            "warning",
            "checked_by is a member of the pack: the check is not independent",
        )
    if board_path is not None:
        out += _against_boards(pack, acc, where, void, board_path, prior_path)
    return out


def _against_boards(
    pack: dict[str, Any],
    acc: dict[str, Any],
    where: str,
    void: bool,
    board_path: Path,
    prior_path: Path | None,
) -> list[Issue]:
    out: list[Issue] = []

    def add(level: str, msg: str) -> None:
        out.append(Issue(level, where, msg))

    if sha256_file(board_path) != pack["map"]["sha256"]:
        add("error", f"{board_path} is not the pack's map (sha256 differs)")
        return out
    board = load_board(board_path)
    listed = set(acc["elements"])
    if not void:
        unknown = sorted(listed - _ids(board))
        if unknown:
            add("error", f"elements: {', '.join(unknown)} not on the board")
        missing = len(_ids(board) - listed)
        if missing:
            add("warning", f"{missing} element(s) of the board have no act: not_read")
        return out
    if prior_path is None:
        add(
            "warning",
            "to ask only the changed elements, give the earlier board as --prior",
        )
        return out
    if sha256_file(prior_path) != acc["board"]["sha256"]:
        add("error", f"{prior_path} is not the board this acceptance was given on")
        return out
    prior = load_board(prior_path)
    unknown = sorted(listed - _ids(prior))
    if unknown:
        add("error", f"elements: {', '.join(unknown)} not on the earlier board")
    try:
        got = reask(prior, board)
    except ProfileError as exc:
        add("error", f"cannot compare the boards: {exc}")
        return out
    add(
        "warning",
        f"ask again {len(got['changed'])} changed element(s): "
        f"{', '.join(got['changed']) or '-'}; {len(got['unchanged'])} unchanged "
        f"(the earlier act stands), {len(got['removed'])} removed",
    )
    return out


def summary_line(acc: dict[str, Any], void: bool) -> str:
    """One line for a printout: the layers of an acceptance and its state."""
    counts = {a: sum(1 for v in acc["elements"].values() if v == a) for a in ACTS}
    by = f" by {acc['checked_by']}" if acc.get("checked_by") else ""
    return (
        f"acceptance {acc['member']}{' (void)' if void else ''}: "
        f"vocabulary {acc['vocabulary']}; elements {counts['accept']} accept, "
        f"{counts['reject']} reject, {counts['not_read']} not read; "
        f"check {acc['check']}{by}"
    )


def check_files(
    pack: dict[str, Any],
    names: list[str],
    board: str | None,
    prior: str | None,
) -> list[tuple[str, list[Issue], str]]:
    """(file, issues, summary line) per acceptance file; the summary is empty
    when the file is not a valid acceptance."""
    got = []
    for name in names:
        acc = load_task(Path(name), "task_acceptance")
        issues = check_acceptance(
            pack,
            acc,
            name,
            Path(board) if board else None,
            Path(prior) if prior else None,
        )
        line = ""
        if "map" in pack and not schema_issues(acc, "task_acceptance", name):
            line = summary_line(acc, is_void(pack, acc))
        got.append((name, issues, line))
    return got
