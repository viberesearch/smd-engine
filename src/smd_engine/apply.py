"""Apply a board patch: a decision recorded as additions, field changes,
removals and state changes, giving the next sub-version of the same cycle."""

from __future__ import annotations

import copy
from typing import Any

# Board lists a patch may add to, in the order of the board schema.
ADDABLE = (
    "boards",
    "elements",
    "relations",
    "transitions",
    "qualifications",
    "theses",
    "hypotheses",
    "ontology",
    "signoffs",
)
# Board lists whose items have an id that `set` and `remove` may name; a
# record board (`boards`) is removed with the elements on it.
WITH_ID = ("boards", "elements", "qualifications", "theses", "hypotheses", "ontology")
# Item fields that name other items: lists dropped when they become empty...
OPTIONAL_LISTS = (
    "in",
    "feeds",
    "about",
    "targets",
    "raises",
    "qualifications",
    "arises_from",
    "covers",
)
# ...lists the schema requires to be non-empty, left empty for the validator to
# report, so that a removal never deletes a decision silently...
REQUIRED_LISTS = ("valid_for",)
# ...and single ids, deleted.
SCALARS = (
    "seen_from",
    "performed_by",
    "cooperation",
    "test",
    "assigned_by",
    "unfolds",
)


# A `set` entry for a relation names it by these, and by `match_label` when
# the three fit several relations; the other keys are the fields it sets.
RELATION_KEY = ("from", "to", "kind")
RELATION_FIELDS = ("carries", "label", "voice", "cites")


class PatchError(ValueError):
    """The patch does not fit the board: a wrong board or an unknown id."""


def apply_patch(board: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """The board with the patch applied; board is not changed.

    Applies add, set, board_notes, remove, sources, state and title in that
    order, then sets state.version and appends the patch id to `applied`.
    `set` and `remove` address a transition by its number `n` as it is after
    `add`, before this patch renumbers; `set` also addresses a relation by its
    `from`, `to` and `kind`. Raises PatchError for a patch made for
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
    if add.get("boards") and "boards" not in new:
        new = _with_boards(new)
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
        on = _on_boards(new, ids)
        dropped = _remove(new, ids | {e for es in on.values() for e in es}, numbers)
        for key, why in removed.items():
            if isinstance(key, int):
                lines.append(f"{patch['id']}: removed transition {key}: {why}")
            else:
                head = f"{patch['id']}: removed {key}: {why}"
                with_it = [f"with {', '.join(on[key])}"] if on.get(key) else []
                lines.append(
                    "; ".join(
                        [head]
                        + with_it
                        + dropped.get(key, [])
                        + [d for e in on.get(key, []) for d in dropped.get(e, [])]
                    )
                )
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


def _with_boards(board: dict[str, Any]) -> dict[str, Any]:
    """The board with an empty `boards`, placed before the elements as in the schema."""
    out: dict[str, Any] = {}
    for key, value in board.items():
        if key == "elements":
            out["boards"] = []
        out[key] = value
    out.setdefault("boards", [])
    return out


def _on_boards(board: dict[str, Any], ids: set[str]) -> dict[str, list[str]]:
    """The elements on each removed record board, by board id."""
    removed = {b.get("id") for b in board.get("boards", []) if b.get("id") in ids}
    out: dict[str, list[str]] = {}
    for el in board.get("elements", []):
        if el.get("board") in removed and el.get("id") not in ids:
            out.setdefault(el["board"], []).append(str(el["id"]))
    return out


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


def _relation(board: dict[str, Any], change: dict[str, Any]) -> dict[str, Any]:
    """The one relation a `set` entry names by `from`, `to` and `kind` (and
    `match_label`, the label it has now, when given); PatchError naming the
    candidates when none or several fit."""
    key = tuple(change[k] for k in RELATION_KEY)
    wanted = f"{key[0]} -> {key[1]} ({key[2]})"
    hits = [
        r
        for r in board.get("relations", [])
        if tuple(r[k] for k in RELATION_KEY) == key
    ]
    if "match_label" in change:
        hits = [r for r in hits if r.get("label") == change["match_label"]]
        wanted += f" with label '{change['match_label']}'"
    if len(hits) == 1:
        found: dict[str, Any] = hits[0]
        return found
    if not hits:
        raise PatchError(f"set: no relation {wanted}")
    named = "; ".join(f"'{r['label']}'" if r.get("label") else "no label" for r in hits)
    raise PatchError(
        f"set: {len(hits)} relations {wanted} fit: {named}; "
        "name one by `match_label`, its current label"
    )


def _set_relation(board: dict[str, Any], change: dict[str, Any]) -> None:
    """Set `carries`, `label`, `voice` or `cites` of the relation the entry
    names; a field already there is replaced in place, a new one is added at
    the end in the order carries, label, voice, cites; null deletes a field."""
    extra = set(change) - set(RELATION_KEY) - set(RELATION_FIELDS) - {"match_label"}
    if extra:
        raise PatchError(
            f"set: a relation entry takes {', '.join(RELATION_FIELDS)}, not "
            + ", ".join(sorted(extra))
        )
    rel = _relation(board, change)
    for field in RELATION_FIELDS:
        if field not in change:
            continue
        if change[field] is None:
            rel.pop(field, None)
        else:
            rel[field] = copy.deepcopy(change[field])


def _set(board: dict[str, Any], change: dict[str, Any]) -> None:
    """Merge the change into its item, the record of an id, the transition
    numbered `n` or the relation named by `from`, `to` and `kind`: a mapping
    merges into a mapping one level deep, key by key; null deletes a field or a
    key; lists and scalars replace."""
    if "id" in change and all(k in change for k in RELATION_KEY):
        raise PatchError(
            f"set: an entry names an id ('{change['id']}') or a relation by "
            "from, to and kind, not both"
        )
    if "id" not in change and "n" not in change:
        if all(k in change for k in RELATION_KEY):
            _set_relation(board, change)
            return
        raise PatchError("set: an entry names an id, a transition n, or a relation")
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
    # Entries of an ontology's continuum that name the item by id.
    for key in ("lives_in", "tempos"):
        if isinstance(item.get(key), list):
            item[key] = [
                x
                for x in item[key]
                if not (isinstance(x, dict) and _gone(x.get("id"), gone))
            ]
            if not item[key]:
                del item[key]
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
