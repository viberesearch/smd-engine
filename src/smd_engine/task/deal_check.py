"""Checks of the deal fields of a pack and of its answers. Each function returns
(level, message) pairs; `check.py` wraps them as issues. A pack with none of the
deal fields gets no message from here."""

from __future__ import annotations

from typing import Any

from smd_engine.validate.redlines import _line_findings

from smd_engine.task.asking import asking_findings
from smd_engine.task.bounds import bound_answer_findings, bound_findings
from smd_engine.task.positions import (
    annex_sha,
    has_annex,
    in_audience,
    is_deal,
    member_positions,
)

Found = list[tuple[str, str]]
BROKERS = ("broker_sell", "broker_buy")


def _dups(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        if v in seen and v not in out:
            out.append(v)
        seen.add(v)
    return out


def _positions(pack: dict[str, Any]) -> Found:
    out: Found = []
    positions = pack.get("positions", [])
    for d in _dups([p["id"] for p in positions]):
        out.append(("error", f"position id {d} is used twice"))
    kinds = {p["id"]: p["kind"] for p in positions}
    members = {m["id"] for m in pack["members"]}
    for m in pack["members"]:
        who = f"member {m['id']}"
        if not positions:
            for key in ("position", "principal"):
                if key in m:
                    out.append(("error", f"{who}: {key} needs the pack's positions"))
            continue
        if m.get("position") not in kinds:
            out.append(
                (
                    "error",
                    f"{who}: position {m.get('position')!r} is not one of the positions",
                )
            )
        principal = m.get("principal")
        if principal is not None:
            if principal not in members or principal == m["id"]:
                out.append(
                    ("error", f"{who}: principal {principal} is not another member")
                )
            if kinds.get(m.get("position")) not in BROKERS:
                out.append(("error", f"{who}: only a broker has a principal"))
        elif kinds.get(m.get("position")) in BROKERS:
            out.append(
                ("warning", f"{who}: a broker names the member he acts for (principal)")
            )
    return out


def _audiences(pack: dict[str, Any]) -> Found:
    out: Found = []
    known = {p["id"] for p in pack.get("positions", [])}
    entries = [(f"item {i['id']}", i) for i in pack["items"]] + [
        (f"term {t['term']!r}", t) for t in pack["ontology"]["terms"]
    ]
    for name, entry in entries:
        for pos in entry.get("audience", []):
            if pos not in known:
                out.append(
                    ("error", f"{name}: audience {pos} is not a position of the pack")
                )
    annex = {i["id"] for i in pack["items"] if "audience" in i}
    for item in pack["items"]:
        if "audience" in item:
            continue
        for ref in [
            *item.get("refs", []),
            *([item["fit_of"]] if "fit_of" in item else []),
        ]:
            if ref in annex:
                out.append(
                    (
                        "error",
                        f"item {item['id']}: core item names {ref}, which is in an annex",
                    )
                )
    return out


def _claims(pack: dict[str, Any]) -> Found:
    out: Found = []
    sources = {s["id"]: s for s in pack["sources"]}
    asserting = (
        {p["id"] for p in pack["positions"]}
        if pack.get("positions")
        else {m["id"] for m in pack["members"]}
    )
    for item in pack["items"]:
        claim = item.get("claim")
        if claim is None:
            continue
        who = f"item {item['id']}"
        if claim["source"] not in sources:
            out.append(
                (
                    "error",
                    f"{who}: claim source {claim['source']} is not a source of the pack",
                )
            )
        elif claim["level"] == "checked" and "sha256" not in sources[claim["source"]]:
            out.append(
                ("warning", f"{who}: a checked claim names a source with no sha256")
            )
        if claim["asserted_by"] not in asserting:
            out.append(
                (
                    "error",
                    f"{who}: claim asserted_by {claim['asserted_by']} is not a known position",
                )
            )
        if item.get("nature", "fact") != "fact":
            out.append(
                ("error", f"{who}: a fact item has nature fact, not {item['nature']}")
            )
    return out


def _lines(pack: dict[str, Any]) -> Found:
    out: Found = []
    for item in pack["items"]:
        if "line" in item:
            # the same rules as a red line on a board (validate/redlines.py)
            el = {"line": item["line"], "red_line": True, "kind": "standard"}
            out += [
                ("error", f"item {item['id']}: {m}")
                for m in _line_findings(el, pack["date"])
            ]
    return out


def _fits(pack: dict[str, Any]) -> Found:
    out: Found = []
    ids = {i["id"] for i in pack["items"]}
    for item in pack["items"]:
        target = item.get("fit_of")
        if target is not None and (target not in ids or target == item["id"]):
            out.append(
                (
                    "error",
                    f"item {item['id']}: fit_of {target} is not another item of the pack",
                )
            )
    return out


def _pairs(pack: dict[str, Any]) -> Found:
    out: Found = []
    pairs = pack.get("pairs", [])
    if pairs and not pack.get("positions"):
        return [("error", "pairs need the pack's positions")]
    members = {m["id"] for m in pack["members"]}
    for d in _dups([p["id"] for p in pairs]):
        out.append(("error", f"pair id {d} is used twice"))
    seen: set[frozenset[str]] = set()
    for p in pairs:
        who = f"pair {p['id']}"
        ends = frozenset(p["members"])
        if len(ends) != 2:
            out.append(("error", f"{who}: the two members are the same member"))
        for m in p["members"]:
            if m not in members:
                out.append(("error", f"{who}: {m} is not a member of the pack"))
        if ends in seen:
            out.append(("error", f"{who}: the same two members as another pair"))
        seen.add(ends)
    return out


def _item_stages(pack: dict[str, Any]) -> Found:
    stages = (pack.get("deal") or {}).get("stages") or []
    return [
        (
            "error",
            f"item {i['id']}: stage {i['stage']} is not one of deal.stages",
        )
        for i in pack["items"]
        if "stage" in i and i["stage"] not in stages
    ]


def deal_pack_findings(pack: dict[str, Any]) -> Found:
    return (
        _positions(pack)
        + asking_findings(pack)
        + _item_stages(pack)
        + _audiences(pack)
        + _claims(pack)
        + _lines(pack)
        + _fits(pack)
        + _pairs(pack)
        + bound_findings(pack)
    )


def source_id_findings(pack: dict[str, Any], ans: dict[str, Any]) -> Found:
    """Errors for `source_ids` that name no source of the pack."""
    known = {s["id"] for s in pack["sources"]}
    return [
        ("error", f"answers.{item_id}: source id {sid} is not a source of the pack")
        for item_id, a in ans["answers"].items()
        for sid in a.get("source_ids", [])
        if sid not in known
    ]


def deal_answers_findings(pack: dict[str, Any], ans: dict[str, Any]) -> Found:
    """The source ids, the annex stamp and the audience of one answers file."""
    out = source_id_findings(pack, ans) + bound_answer_findings(pack, ans)
    stamp = ans["pack"].get("annex")
    if not is_deal(pack):
        if stamp:
            out.append(("error", "annex: the pack has no positions"))
        return out
    position = member_positions(pack).get(ans["member"])
    if position is None:
        return out  # not a member of the pack: reported by check_answers
    if stamp:
        if stamp["position"] != position:
            out.append(
                (
                    "error",
                    f"annex position {stamp['position']} is not the member's ({position})",
                )
            )
        elif not has_annex(pack, position) or stamp["sha256"] != annex_sha(
            pack, position
        ):
            out.append(
                (
                    "error",
                    "annex sha256 differs from the annex: the answers are for another text",
                )
            )
    elif has_annex(pack, position):
        out.append(
            ("warning", f"no annex stamp, though position {position} has an annex")
        )
    items = {i["id"]: i for i in pack["items"]}
    for item_id in ans["answers"]:
        if item_id in items and not in_audience(items[item_id], position):
            out.append(("error", f"answers: {item_id} is not for position {position}"))
    return out
