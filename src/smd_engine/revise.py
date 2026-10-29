"""Open the next cycle of a board set and apply the human's decisions to it."""

from __future__ import annotations

import copy
import datetime as dt
import re
from typing import Any

from smd_engine.validate import AI_VOICES

# Fields that describe the previous cycle only; the next cycle writes its own.
CYCLE_ONLY = ("checked_by", "notes", "transitions", "reflected_from", "applied")


def next_id(record_id: str) -> str:
    """bakeries-c2 -> bakeries-c3: increment the trailing number."""
    m = re.fullmatch(r"(.*?)(\d+)", record_id)
    if not m:
        raise ValueError(f"cannot derive the next id from {record_id!r}; give --id")
    return f"{m.group(1)}{int(m.group(2)) + 1}"


def _bump(version: str) -> str:
    m = re.fullmatch(r"(\d+)\.(\d+)", version)
    return f"{m.group(1)}.{int(m.group(2)) + 1}" if m else version


def revise(
    prev: dict[str, Any],
    new_id: str | None = None,
    date: str | None = None,
    decisions: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Return the next cycle on top of prev, and what the human must still do.

    `decisions` may hold `signoffs` (same form as in a record), `reflected_from`
    and `difficulty`. Each sign-off is applied to its target: close_k closes
    the K and drops it from state.open, accept_move and reject_move set the
    move's status, accept_thesis marks the thesis refined, partly_k and
    reopen_k set the K partly answered or open again and keep it in
    state.open. accept_result is
    recorded but not applied, because the result, artefacts and resolved_in
    come from the field.
    """
    decisions = decisions or {}
    cycle = prev["cycle"] + 1
    date = date or dt.date.today().isoformat()
    new = {k: copy.deepcopy(v) for k, v in prev.items() if k not in CYCLE_ONLY}
    new.update(
        id=new_id or next_id(prev["id"]),
        date=date,
        cycle=cycle,
        revises=prev["id"],
        status="draft",
    )
    if decisions.get("reflected_from"):
        new["reflected_from"] = decisions["reflected_from"]

    # Earlier decisions stand; a new draft carries no verification.
    signoffs = [s for s in new.get("signoffs", []) if s["function"] != "verify_record"]
    ks = {q["id"]: q for q in new.get("qualifications", [])}
    theses = {t["id"]: t for t in new.get("theses", [])}
    moved = {e["id"]: e for e in new.get("elements", []) if "move" in e}
    moved.update({t["id"]: t for t in theses.values() if "move" in t})
    hyps = {h["id"] for h in new.get("hypotheses", [])}

    state = new.get("state", {})
    open_items = list(state.get("open", []))
    accepted: list[str] = []
    todo: list[str] = []
    for raw in decisions.get("signoffs", []):
        s = {**raw, "cycle": cycle}
        s.setdefault("date", date)
        fn, target = s["function"], s.get("target")
        if (s.get("by") or "").strip().lower() in AI_VOICES:
            raise ValueError(f"{fn} {target}: a sign-off is a human point, not AI")
        if fn == "close_k":
            if target not in ks:
                raise ValueError(f"close_k: '{target}' is not a qualification")
            ks[target].update(status="closed", closed_in=cycle)
            open_items = [o for o in open_items if o != target]
        elif fn in ("partly_k", "reopen_k"):
            if target not in ks:
                raise ValueError(f"{fn}: '{target}' is not a qualification")
            ks[target]["status"] = "partly" if fn == "partly_k" else "open"
            ks[target].pop("closed_in", None)
            if target not in open_items:
                open_items.append(target)
        elif fn in ("accept_move", "reject_move"):
            if target not in moved:
                raise ValueError(f"{fn}: '{target}' carries no move")
            status = "accepted" if fn == "accept_move" else "rejected"
            moved[target]["move"]["status"] = status
        elif fn == "accept_thesis":
            if target not in theses:
                raise ValueError(f"accept_thesis: '{target}' is not a thesis")
            theses[target]["status"] = "refined"
        elif fn == "accept_result":
            if target not in hyps:
                raise ValueError(f"accept_result: '{target}' is not a hypothesis")
            todo.append(
                f"{target}: set status, result, artefacts and resolved_in: {cycle}"
            )
        else:
            raise ValueError(f"{fn}: a new draft cannot be verified; sign it later")
        signoffs.append(s)
        accepted.append(f"{fn} {target}")
    if signoffs:
        new["signoffs"] = signoffs

    new_state: dict[str, Any] = {"version": _bump(str(state.get("version", "0.1")))}
    if decisions.get("difficulty"):
        new_state["difficulty"] = decisions["difficulty"]
    new_state["accepted"] = accepted
    new_state["open"] = open_items
    new["state"] = new_state

    todo.append("edit title and notes for this cycle")
    if "reflected_from" not in new:
        todo.append("set reflected_from: the position this cycle was made from")
    if "difficulty" not in new_state:
        todo.append("set state.difficulty: what failed in the previous cycle")
    todo.append(
        "set state.next_move; add transitions if the cycle moved between boards"
    )
    return new, todo
