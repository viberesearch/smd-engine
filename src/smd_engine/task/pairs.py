"""Deal mode, pairs: the answers of two members compared on their own. A deal
pack may list `pairs` (a seller and a buyer, a broker and a buyer). The diff
then has `by_pair`: for each pair the class and route of each point that both
members were asked, worked out from their two answers only. The classes of the
whole diff are unchanged. A pack without `pairs` gets nothing from here."""

from __future__ import annotations

from collections import Counter
from typing import Any, Callable

from smd_engine.task.deal_items import apply_after_reading
from smd_engine.task.positions import member_positions

KEEP = ("class", "class_by", "subtype", "route", "after_reading", "raised_by")


def pair_summary(
    entries: dict[str, dict[str, Any]], is_open: Callable[[dict[str, Any]], bool]
) -> dict[str, Any]:
    return {
        "points": len(entries),
        "open": sum(1 for e in entries.values() if is_open(e)),
        "by_class": dict(Counter(e["class"] for e in entries.values())),
    }


def build_by_pair(
    pack: dict[str, Any],
    points: list[dict[str, Any]],
    point_fn: Callable[..., dict[str, Any]],
    is_open: Callable[[dict[str, Any]], bool],
) -> list[dict[str, Any]]:
    """The `by_pair` block of a diff. `points` are the diff's points; `point_fn`
    is the one that classes a point from answers (diff._point), run here on the
    two answers of a pair. A point with an audience is compared only when both
    members are in it; an added point belongs to one member and is left out, and so is a
    sealed point (it holds no answers)."""
    where = member_positions(pack)
    out: list[dict[str, Any]] = []
    for pair in pack.get("pairs", []):
        ends = pair["members"]
        rows = []
        for p in points:
            audience = p.get("audience")
            if (
                p["kind"] == "added"
                or p.get("item_kind") == "bound"
                or (
                    audience is not None
                    and any(where.get(m) not in audience for m in ends)
                )
            ):
                continue
            answers = {m: p["answers"][m] for m in ends if m in p["answers"]}
            extra = {"fit_of": p["fit_of"]} if "fit_of" in p else {}
            rows.append(
                point_fn(p["id"], p["kind"], extra, answers, ends, p.get("item_kind"))
            )
        apply_after_reading(rows)
        entries = {r["id"]: {k: r[k] for k in KEEP if k in r} for r in rows}
        out.append(
            {
                "id": pair["id"],
                **({"label": pair["label"]} if pair.get("label") else {}),
                "members": ends,
                "summary": pair_summary(entries, is_open),
                "points": entries,
            }
        )
    return out


def call_by_pair(
    diff: dict[str, Any], call: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """The `call_by_pair` block of an agenda: for each pair, the ids of the points
    on the call that the pair was asked and that it put there, because one of the
    two marked discuss or did not reply, or because they rejected a red line. A
    point on the call that no pair put there stays in `call` only."""
    out: list[dict[str, Any]] = []
    for pair in diff["by_pair"]:
        ends = set(pair["members"])
        ids = []
        for entry in call:
            mine = pair["points"].get(entry["id"])
            why = entry["why"]
            if mine is not None and (
                ends & set(why.get("discuss", []))
                or ends & set(why.get("no_reply", []))
                or (why.get("blocking") and mine["class"] == "line_rejected")
            ):
                ids.append(entry["id"])
        out.append(
            {
                "id": pair["id"],
                **({"label": pair["label"]} if pair.get("label") else {}),
                "members": pair["members"],
                "points": ids,
            }
        )
    return out
