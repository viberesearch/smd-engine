"""Apply a board patch: a decision recorded as additions, field changes,
removals and state changes, giving the next sub-version of the same cycle."""

from __future__ import annotations

import copy
from typing import Any

# Board lists a patch may add to, in the order of the board schema.
ADDABLE = (
    "elements",
    "relations",
    "transitions",
    "qualifications",
    "theses",
    "hypotheses",
    "ontology",
    "signoffs",
)
# Board lists whose items have an id that `set` and `remove` may name.
WITH_ID = ("elements", "qualifications", "theses", "hypotheses", "ontology")
# Item fields that name other items: lists dropped when they become empty...
OPTIONAL_LISTS = ("in", "feeds", "about", "targets", "raises", "qualifications")
# ...lists the schema requires to be non-empty, left empty for the validator to
# report, so that a removal never deletes a decision silently...
REQUIRED_LISTS = ("valid_for",)
# ...and single ids, deleted.
SCALARS = ("seen_from", "performed_by", "cooperation", "test")


class PatchError(ValueError):
    """The patch does not fit the board: a wrong board or an unknown id."""


def apply_patch(board: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """The board with the patch applied; board is not changed.

    Applies add, set, board_notes, remove, sources, state and title in that
    order, then sets state.version and appends the patch id to `applied`.
    `set` and `remove` address a transition by its number `n` as it is after
    `add`, before this patch renumbers. Raises PatchError for a patch made for
    another board or naming an unknown id or transition number, and ValueError
    for a patch that was already applied.
    """
    if patch["applies_to"] != board["id"]:
        raise PatchError(
            f"patch {patch['id']} applies to {patch['applies_to']}, not {board['id']}"
        )
    if patch["id"] in board.get("applied", []):
        raise ValueError(f"patch {patch['id']} is already applied to {board['id']}")
    new = copy.deepcopy(board)
    add = patch.get("add", {})
    for field in ADDABLE:
        if add.get(field):
            new.setdefault(field, []).extend(copy.deepcopy(add[field]))
    for change in patch.get("set", []):
        _set(new, change)
    # Lines appended to the board's notes, joined to it by "\n": the board_notes
    # text, then one line per removal.
    lines = []
    if patch.get("board_notes", "").strip():
        lines.append(patch["board_notes"].rstrip())
    # An item id (str) or a transition number (int) -> reason, in patch order.
    removed = {
        r["id"] if "id" in r else r["n"]: r["reason"] for r in patch.get("remove", [])
    }
    for key in removed:
        if isinstance(key, int):
            if _transition(new, key) is None:
                raise PatchError(f"remove: unknown transition {key}")
        elif _find(new, key) is None:
            raise PatchError(f"remove: unknown id '{key}'")
    if removed:
        ids = {k for k in removed if isinstance(k, str)}
        numbers = {k for k in removed if isinstance(k, int)}
        dropped = _remove(new, ids, numbers)
        for key, why in removed.items():
            if isinstance(key, int):
                lines.append(f"{patch['id']}: removed transition {key}: {why}")
            else:
                head = f"{patch['id']}: removed {key}: {why}"
                lines.append("; ".join([head] + dropped.get(key, [])))
    if lines:
        new["notes"] = "\n".join(([new["notes"]] if new.get("notes") else []) + lines)
    for sid in add.get("sources", []):
        if sid not in new.setdefault("sources", []):
            new["sources"].append(sid)
    _state(new, patch.get("state", {}))
    if "title" in patch:
        new["title"] = patch["title"]
    new.setdefault("state", {})["version"] = str(patch["version"])
    if "applied" not in new:
        new = _with_applied(new)
    new["applied"].append(patch["id"])
    return new


def _with_applied(board: dict[str, Any]) -> dict[str, Any]:
    """The board with an empty `applied`, placed before the elements as in the schema."""
    out: dict[str, Any] = {}
    for key, value in board.items():
        if key == "elements":
            out["applied"] = []
        out[key] = value
    out.setdefault("applied", [])
    return out


def _find(board: dict[str, Any], item_id: str) -> dict[str, Any] | None:
    for field in WITH_ID:
        for item in board.get(field, []):
            if item.get("id") == item_id:
                found: dict[str, Any] = item
                return found
    return None


def _transition(board: dict[str, Any], n: int) -> dict[str, Any] | None:
    for item in board.get("transitions", []):
        if item.get("n") == n:
            found: dict[str, Any] = item
            return found
    return None


def _set(board: dict[str, Any], change: dict[str, Any]) -> None:
    """Merge the change into its item, the record of an id or the transition
    numbered `n`: a mapping merges into a mapping one level deep, key by key;
    null deletes a field or a key; lists and scalars replace."""
    if "id" in change:
        item = _find(board, change["id"])
        if item is None:
            raise PatchError(f"set: unknown id '{change['id']}'")
    else:
        item = _transition(board, change["n"])
        if item is None:
            raise PatchError(f"set: unknown transition {change['n']}")
    for key, value in change.items():
        if key in ("id", "n"):
            continue
        if value is None:
            item.pop(key, None)
        elif isinstance(value, dict) and isinstance(item.get(key), dict):
            for sub, sub_value in value.items():
                if sub_value is None:
                    item[key].pop(sub, None)
                else:
                    item[key][sub] = copy.deepcopy(sub_value)
        else:
            item[key] = copy.deepcopy(value)


def _gone(value: Any, gone: set[str]) -> bool:
    """Whether a field value names a removed item; a value of a wrong shape
    does not, and is left for the schema check after application."""
    return isinstance(value, str) and value in gone


def _names(link: dict[str, Any], gone: set[str]) -> bool:
    return _gone(link.get("from"), gone) or _gone(link.get("to"), gone)


def _n(transition: dict[str, Any]) -> int:
    n = transition.get("n")
    return n if isinstance(n, int) else 0


def _remove(
    board: dict[str, Any], gone: set[str], numbers: set[int]
) -> dict[str, list[str]]:
    """Drop the items, the transitions numbered `numbers` and every link that
    names the items; return, per removed id, the sign-offs dropped with it."""
    for field in WITH_ID:
        if field in board:
            board[field] = [x for x in board[field] if not _gone(x.get("id"), gone)]
    if "relations" in board:
        board["relations"] = [r for r in board["relations"] if not _names(r, gone)]
    if "transitions" in board:
        kept = [
            t
            for t in sorted(board["transitions"], key=_n)
            if not _names(t, gone) and _n(t) not in numbers
        ]
        # Transitions run 1..n; the ones after a dropped transition move up.
        for n, tr in enumerate(kept, 1):
            tr["n"] = n
        board["transitions"] = kept
    for field in WITH_ID:
        for item in board.get(field, []):
            _unlink(item, gone)
    if _gone(board.get("reflected_from"), gone):
        del board["reflected_from"]
    dropped: dict[str, list[str]] = {}
    kept_signoffs = []
    for s in board.get("signoffs", []):
        target = s.get("target")
        if not _gone(target, gone):
            kept_signoffs.append(s)
            continue
        who = ", ".join(str(s[k]) for k in ("by", "date") if s.get(k))
        dropped.setdefault(target, []).append(
            f"dropped sign-off {s.get('function')} {target}"
            + (f" ({who})" if who else "")
        )
    if "signoffs" in board:
        board["signoffs"] = kept_signoffs
    state = board.get("state", {})
    if isinstance(state.get("open"), list):
        state["open"] = [o for o in state["open"] if not _gone(o, gone)]
    return dropped


def _unlink(item: dict[str, Any], gone: set[str]) -> None:
    for key in OPTIONAL_LISTS + REQUIRED_LISTS:
        if isinstance(item.get(key), list):
            item[key] = [x for x in item[key] if not _gone(x, gone)]
            if not item[key] and key in OPTIONAL_LISTS:
                del item[key]
    for key in SCALARS:
        if _gone(item.get(key), gone):
            del item[key]
    if isinstance(item.get("subjects"), list):
        item["subjects"] = [
            s
            for s in item["subjects"]
            if not (isinstance(s, dict) and _gone(s.get("position"), gone))
        ]
        if not item["subjects"]:
            del item["subjects"]
    move = item.get("move")
    if isinstance(move, dict) and isinstance(move.get("from"), list):
        # An empty `from` stays for the validator to report.
        move["from"] = [x for x in move["from"] if not _gone(x, gone)]


def _state(board: dict[str, Any], change: dict[str, Any]) -> None:
    if not change:
        return
    state = board.setdefault("state", {})
    for key in ("accepted", "open"):
        if change.get(key):
            state[key] = state.get(key, []) + list(change[key])
    if change.get("remove_open") and "open" in state:
        state["open"] = [o for o in state["open"] if o not in change["remove_open"]]
    for key in ("next_move", "difficulty"):
        if key in change:
            state[key] = change[key]
