"""Deal mode, what an agenda shows to whom. The agenda built from the whole diff
holds every annex point (a point with an `audience`) with its question; it goes
to nobody as it is. Two agendas are made from it:

- the common agenda (`smd task agenda`), for every reader of the call. An annex
  point never shows its question, text, refs, options, claim, red line or
  answers, nor its item id: if it is on the call it appears as "annex point 1"
  with the neutral `call_title` its pack author wrote, if any. A settled annex
  point is left out. A sealed price point (a `bound` item) is the exception to
  the last rule: its verdict is the shared state of the price, so it stays where
  it was, with its class, verdict and who committed, but no question and no id.
  A fact dispute over a claim of the buyer's side is left out, as in the sell
  side's view, and so is a value point's class, route and replies (it shows
  `open` or `settled`, as in a view). Annex points are not listed under a pair,
  which would name their audience. `why` never says a red line was rejected. The
  labels block keeps the core points only, numbered over them as the core pack
  numbers its items.
- the agenda of one position (`smd deal views --replies`), cut by the rules of
  the position's diff view: no point outside its audience, no buyer-side fact
  dispute for the sell side, no answers of a value point, labels and
  `call_by_pair` cut to what it shows. A value point shows `open` or `settled`
  and the replies of the position's own side only. A point of its own annex
  keeps its question.

A group agenda (a diff without positions) is returned as it is."""

from __future__ import annotations

from typing import Any

from smd_engine.deal.views import (
    filter_labels,
    is_value_point,
    side_members,
    value_status,
    view_of,
)
from smd_engine.task.pairs import call_by_pair

# what a neutral entry keeps of an annex point; a sealed point keeps its price state
NEUTRAL_KEEP = ("kind", "call_title", "why", "answers_withheld", "how", "replies")
SEALED_KEEP = (
    "class",
    "class_by",
    "route",
    "sealed",
    "committed_by",
    "changed_since_run",
    "verdict",
    "ledger_head",
)


# what a value point of the agenda loses: its class, route and subtype say how
# the ranges lie to each other
VALUE_DROP = ("class", "class_by", "route", "subtype", "how")


def _neutral(entry: dict[str, Any], handle: str) -> dict[str, Any]:
    keep = NEUTRAL_KEEP + (SEALED_KEEP if "sealed" in entry else ())
    out = {
        "id": handle,
        "annex": True,
        **{k: entry[k] for k in keep if k in entry},
    }
    if "why" in out:
        # no reason: a rejected red line is not said to be one, and the members
        # who chose discuss or did not reply would name the point's audience
        out["why"] = {}
    return out


def _value_entry(
    entry: dict[str, Any], status: str, mine: set[str] | None
) -> dict[str, Any]:
    """The entry of a value point as a view shows the point: `open` or `settled`,
    and the replies of `mine` only (none when `mine` is None)."""
    out = {k: v for k, v in entry.items() if k not in VALUE_DROP}
    out["class"] = status
    if "why" in out:  # blocking would say how the answers lie, as a route would
        out["why"] = {k: v for k, v in out["why"].items() if k != "blocking"}
    if "replies" in out:
        out["replies"] = {m: r for m, r in out["replies"].items() if m in (mine or ())}
        if not out["replies"]:
            del out["replies"]
    return out


def common_agenda(diff: dict[str, Any], agenda: dict[str, Any]) -> dict[str, Any]:
    if not diff.get("positions"):
        return agenda
    annex = {p["id"] for p in diff["points"] if p.get("audience") is not None}
    hidden = {  # a buyer-side fact dispute: not for the sell side, who reads this
        p["id"]
        for p in diff["points"]
        if p.get("buyer_claim") and p["class"] == "conflict"
    }
    value = {p["id"]: value_status(p) for p in diff["points"] if is_value_point(p)}
    handles: dict[str, str] = {}

    def neutral(entry: dict[str, Any]) -> dict[str, Any]:
        handles[entry["id"]] = f"annex-{len(handles) + 1}"
        return _neutral(entry, handles[entry["id"]])

    def shown(entry: dict[str, Any]) -> dict[str, Any]:
        if entry["id"] in annex:
            return neutral(entry)
        if entry["id"] in value:
            return _value_entry(entry, value[entry["id"]], None)
        return entry

    call = [shown(e) for e in agenda["call"] if e["id"] not in hidden]
    settled = [
        shown(e)
        for e in agenda["settled"]
        if e["id"] not in hidden and (e["id"] not in annex or "sealed" in e)
    ]
    out = {
        **agenda,
        "counts": {
            "points": len(call) + len(settled),
            "call": len(call),
            "settled": len(settled),
        },
        "call": call,
        "settled": settled,
    }
    if "call_by_pair" in agenda:
        out["call_by_pair"] = [
            {
                **pair,
                "points": [
                    i for i in pair["points"] if i not in annex and i not in hidden
                ],
            }
            for pair in agenda["call_by_pair"]
        ]
    if "labels" in agenda:
        core = {p["id"] for p in diff["points"]} - annex
        out["labels"] = filter_labels(agenda["labels"], core - hidden, core)
    return out


def position_agenda(
    pack: dict[str, Any],
    diff: dict[str, Any],
    diff_sha: str,
    agenda: dict[str, Any],
    position: str,
) -> dict[str, Any]:
    """The agenda one position is sent, from the full agenda and the position's
    view of the diff (`views.view_of`, which decides what the position may see)."""
    view = view_of(pack, diff, diff_sha, position)
    shown = {p["id"] for p in view["points"]}
    mine = side_members(pack, diff, position)
    value = {p["id"]: value_status(p) for p in diff["points"] if is_value_point(p)}

    def cut(entry: dict[str, Any]) -> dict[str, Any]:
        if entry["id"] in value:
            return _value_entry(entry, value[entry["id"]], mine)
        return entry

    call = [cut(e) for e in agenda["call"] if e["id"] in shown]
    settled = [cut(e) for e in agenda["settled"] if e["id"] in shown]
    start = {k: agenda[k] for k in ("record", "schema_version")}
    out = {
        **start,
        "view": view["view"],
        **{k: v for k, v in agenda.items() if k not in start},
    }
    out["counts"] = {
        "points": len(call) + len(settled),
        "call": len(call),
        "settled": len(settled),
    }
    out["call"] = call
    out["settled"] = settled
    if "call_by_pair" in agenda:
        out["call_by_pair"] = call_by_pair(view, call)
    if "labels" in agenda:
        out["labels"] = view["labels"]
    return out
