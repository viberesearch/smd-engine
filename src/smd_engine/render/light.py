"""A lighter screen for presenting a dense record.

The screen keeps the structure: the kinds the profile does not mark
`light_off` (in the program's profile: entry, positions, places, goals, gaps,
frames with their functions, concepts, models, cooperations, situations,
boundaries of normality, series of linked events, visionaries) and the К layer.
The `light_off` kinds (facts, signals and notes), moves still awaiting a
decision, `refers` links, link labels and the list of open items leave the
screen; they stay in the record, in the HTML tables and in the frame texts. A
flow keeps the word for what it carries (`carries`), which becomes its only text.

`fold` goes further for an overview: each board keeps its skeleton (the kinds
the profile marks `skeleton`: entry, positions, frames with their functions,
situations; and the ends of transitions) and the rest of each region becomes
one counter that says what is folded, an element of the kind `note` (a kind
every profile defines).
"""

from __future__ import annotations

import copy
from typing import Any

from smd_engine.profile import profile_of
from smd_engine.render.layout import region_of
from smd_engine.render.text import LABELS

HIDDEN_RELATIONS = {"refers"}
COUNTER_KIND = "note"  # profile.REQUIRED_KINDS


def visible(el: dict[str, Any], hidden: set[str]) -> bool:
    """Whether the lighter screen shows an element; `hidden` are the kinds it
    leaves off."""
    if el["kind"] in hidden:
        return False
    return bool(el.get("move", {}).get("status") != "candidate")


def lighten(data: dict[str, Any]) -> dict[str, Any]:
    """A copy of the record with only what the lighter screen shows."""
    out = copy.deepcopy(data)
    hidden = profile_of(data).kinds_where("light_off")
    keep = {e["id"] for e in out["elements"] if visible(e, hidden)}
    out["elements"] = [
        {**e, "in": [p for p in e["in"] if p in keep]} if "in" in e else e
        for e in out["elements"]
        if e["id"] in keep
    ]
    out["relations"] = [
        {k: v for k, v in r.items() if k != "label"}
        for r in out.get("relations", [])
        if r["kind"] not in HIDDEN_RELATIONS and r["from"] in keep and r["to"] in keep
    ]
    out["transitions"] = [
        t for t in out.get("transitions", []) if t["from"] in keep and t["to"] in keep
    ]
    if out.get("state"):
        out["state"] = {
            k: v for k, v in out["state"].items() if k in ("version", "next_move")
        }
    for q in out.get("qualifications", []):
        if "targets" in q:
            q["targets"] = [t for t in q["targets"] if t in keep]
            if not q["targets"]:
                del q["targets"]
    return out


def fold(
    data: dict[str, Any], lang: str = "ru", keep: set[str] | None = None
) -> tuple[dict[str, Any], dict[str, str]]:
    """A copy of the record with the skeleton, the ends of transitions and
    `keep`; each region's other elements fold into one counter that names them
    by kind. A K whose targets all fold moves its badge to the counter. Returns
    the copy and a map from each folded element to its counter."""
    lab = LABELS[lang]
    profile = profile_of(data)
    skeleton = profile.kinds_where("skeleton")
    ends = {t[k] for t in data.get("transitions", []) for k in ("from", "to")}
    stay = {
        e["id"]
        for e in data["elements"]
        if e["kind"] in skeleton or e["id"] in ends | (keep or set())
    }
    out = copy.deepcopy(data)
    folded: dict[str, list[dict[str, Any]]] = {}
    for e in out["elements"]:
        if e["id"] not in stay:
            folded.setdefault(region_of(e), []).append(e)
    to_counter: dict[str, str] = {}
    counters = []
    for region, items in folded.items():
        cid = f"more-{region.replace('.', '-')}"
        by_kind: dict[str, int] = {}
        for e in items:
            by_kind[e["kind"]] = by_kind.get(e["kind"], 0) + 1
            to_counter[e["id"]] = cid
        parts = ", ".join(
            f"{profile.kind_label(k, lang)} {n}" for k, n in by_kind.items()
        )
        board, _, half = region.partition(".")
        counter = {
            "id": cid,
            "board": board,
            "kind": COUNTER_KIND,
            "label": f"+{len(items)} {lab['more']}: {parts}",
            "folded": [e["label"] for e in items],  # for the viewer's panel
        }
        counters.append({**counter, "half": half} if half else counter)
    out["elements"] = [
        {**e, "in": [p for p in e["in"] if p in stay]} if "in" in e else e
        for e in out["elements"]
        if e["id"] in stay
    ] + counters
    out["relations"] = [
        r for r in out.get("relations", []) if r["from"] in stay and r["to"] in stay
    ]
    for q in out.get("qualifications", []):
        targets = q.get("targets", [])
        if targets and not set(targets) & stay:
            q["targets"] = [to_counter[targets[0]]]
        elif targets:
            q["targets"] = [t for t in targets if t in stay]
    return out, to_counter
