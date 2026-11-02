"""Per-position views of a deal diff. The diff holds every answer of every
member; a view is what one position is sent:

- no point that is not for the position (`audience`);
- no fact dispute over a claim of the buyer's side, unless the viewer is on the
  buyer's side;
- on a value point (nature value, or a range with no nature) the class is shown
  as `open` or `settled` only, and the answers of the other side are removed;
- a broker is on his principal's side, so he sees what the principal sees for the
  other side's answers, within his own audience.

A view is a `task_diff` record with a `view` block (position, sha256 of the whole
diff.yaml). It renders and is replied to like a diff; the reply names the view's
sha256 beside the diff's. Nothing in a view is added to the diff: it is a
subset, and what the script settled is not recomputed here."""

from __future__ import annotations

from typing import Any

from smd_engine.records import RecordError
from smd_engine.task.deal_render import point_open
from smd_engine.task.pairs import pair_summary
from smd_engine.task.positions import in_audience, member_positions

SIDES = {
    "seller": "sell",
    "broker_sell": "sell",
    "buyer": "buy",
    "broker_buy": "buy",
}
# what a value point keeps: the question, never a class, route or other answers
VALUE_KEEP = (
    "id",
    "kind",
    "section",
    "question",
    "item_kind",
    "nature",
    "unit",
    "refs",
    "audience",
)


def side_of(pack: dict[str, Any], position: str) -> str:
    """ "sell", "buy", or the position's own id. A broker is on the side of the
    position his principal holds; with no principal, on the side of his kind."""
    kinds = {p["id"]: p["kind"] for p in pack["positions"]}
    where = member_positions(pack)
    principals = {
        where[m["principal"]]
        for m in pack["members"]
        if m.get("position") == position and m.get("principal") in where
    }
    if len(principals) == 1:
        position = next(iter(principals))
    return SIDES.get(kinds.get(position, ""), position)


def is_value_point(p: dict[str, Any]) -> bool:
    return (
        p.get("nature") == "value"
        or p.get("subtype") == "value"
        or (p.get("item_kind") == "range" and "nature" not in p)
    )


def _buyer_fact_dispute(pack: dict[str, Any], p: dict[str, Any]) -> bool:
    claim = p.get("claim")
    if not claim or p["class"] != "conflict":
        return False
    return side_of(pack, claim["asserted_by"]) == "buy"


def _status(p: dict[str, Any]) -> dict[str, str]:
    return {"class": "open" if point_open(p) or p["route"] == "blocking" else "settled"}


def _value_point(p: dict[str, Any], mine: set[str]) -> dict[str, Any]:
    out = {k: p[k] for k in VALUE_KEEP if k in p}
    out.update(_status(p))
    out["answers"] = {m: a for m, a in p["answers"].items() if m in mine}
    return out


def _labels(labels: dict[str, Any], shown: set[str]) -> dict[str, Any]:
    """The labels block without the numbers and options of a point left out."""
    out = dict(labels)
    for key in ("numbers", "options"):
        if key in out:
            out[key] = {k: v for k, v in out[key].items() if k in shown}
    return out


def view_of(
    pack: dict[str, Any], diff: dict[str, Any], diff_sha: str, position: str
) -> dict[str, Any]:
    if position not in {p["id"] for p in pack["positions"]}:
        raise RecordError(f"{position} is not a position of the pack")
    where = member_positions(pack)
    side = side_of(pack, position)
    mine = {m for m in diff["members"] if side_of(pack, where[m]) == side}
    points: list[dict[str, Any]] = []
    for p in diff["points"]:
        if not in_audience(p, position):
            continue
        if side != "buy" and _buyer_fact_dispute(pack, p):
            continue
        points.append(_value_point(p, mine) if is_value_point(p) else p)
    shown = {p["id"] for p in points}
    value_ids = {p["id"] for p in diff["points"] if is_value_point(p)}
    by_pair = []
    for pair in diff.get("by_pair", []):
        entries = {
            pid: _status(e) if pid in value_ids else e
            for pid, e in pair["points"].items()
            if pid in shown
        }
        head = {k: v for k, v in pair.items() if k not in ("summary", "points")}
        by_pair.append(
            {**head, "summary": pair_summary(entries, point_open), "points": entries}
        )
    by_class: dict[str, int] = {}
    for p in points:
        by_class[p["class"]] = by_class.get(p["class"], 0) + 1
    start = {k: diff[k] for k in ("record", "schema_version")}
    out = {
        **start,
        "view": {"position": position, "diff": diff_sha},
        **{k: v for k, v in diff.items() if k not in start},
    }
    out["transcripts"] = {m: t for m, t in diff["transcripts"].items() if m in mine}
    if "labels" in out:
        out["labels"] = _labels(out["labels"], shown)
    if by_pair:
        out["by_pair"] = by_pair
    out["summary"] = {
        "points": len(points),
        "open": sum(1 for p in points if point_open(p)),
        "by_class": by_class,
    }
    out["points"] = points
    return out
