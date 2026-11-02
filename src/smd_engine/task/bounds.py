"""Deal mode, sealed bounds: item kind `bound`. A bound is a one-sided limit on a
number (a price): the seller's floor, committed at day 0, or the buyer's ceiling,
optional and committed only at the last stage. The party commits to the number
with `smd deal seal`; the answers hold the commitment (a sha256), never the
number. The holder compares a floor with a ceiling of one topic and the result is
a flag, `met`, `not_met` or `not_tested`, that sends the point to the in-person
price meeting. A pack without a `bound` item gets nothing from here."""

from __future__ import annotations

import re
from typing import Any

from smd_engine.deal.ledger import last_commitments, ledger_head, topic_verdict
from smd_engine.task.asking import asking_price
from smd_engine.task.positions import audience_members, is_deal

Found = list[tuple[str, str]]
SHA = re.compile(r"[0-9a-f]{64}")
BROKERS = ("broker_sell", "broker_buy")
PARTY_KINDS = {"floor": "seller", "ceiling": "buyer"}
VERDICTS = ("met", "not_met", "not_tested")


def bound_items(pack: dict[str, Any]) -> list[dict[str, Any]]:
    return [i for i in pack["items"] if i["kind"] == "bound"]


def optional_bound(item: dict[str, Any]) -> bool:
    """A ceiling is the buyer's to give or not; a missing one is no gap."""
    return bool(item["kind"] == "bound" and item["bound"]["side"] == "ceiling")


def topics(pack: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    """topic -> {"floor": item, "ceiling": item} of the bound items."""
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for item in bound_items(pack):
        out.setdefault(item["bound"]["topic"], {})[item["bound"]["side"]] = item
    return out


def committer(pack: dict[str, Any], item: dict[str, Any]) -> str | None:
    """The member who commits a bound item: the one member of its audience."""
    who = audience_members(pack, item) if "audience" in item else []
    return who[0] if len(who) == 1 else None


def commitment_problem(value: Any) -> str:
    """Why an answer to a bound item is not a commitment, or an empty string.
    The message never repeats the value."""
    if isinstance(value, str) and SHA.fullmatch(value):
        return ""
    return (
        "a bound item takes the commitment printed by `smd deal seal` "
        "(64 hex digits), never the number itself"
    )


def _holder(pack: dict[str, Any]) -> Found:
    holder = pack.get("holder")
    if not holder or "operator" not in holder:
        return []
    op = holder["operator"]
    member = next((m for m in pack["members"] if m["id"] == op), None)
    if member is None:
        return [("error", f"holder: operator {op} is not a member")]
    kinds = {p["id"]: p["kind"] for p in pack.get("positions", [])}
    kind = kinds.get(member.get("position", ""), "")
    if kind in BROKERS:
        return [("error", f"holder: operator {op} is a broker; a broker never runs it")]
    if kind in ("seller", "buyer"):
        return [("warning", f"holder: operator {op} is a party to the deal")]
    return []


def _stage(item: dict[str, Any], stages: list[str] | None) -> Found:
    who = f"item {item['id']}"
    b = item["bound"]
    if b["side"] == "floor":
        if "stage" in b:
            return [("error", f"{who}: a floor is committed at day 0, it has no stage")]
        return []
    if "stage" not in b:
        return [("error", f"{who}: a ceiling names its stage, the last of deal.stages")]
    if not stages:
        return [("error", f"{who}: a ceiling needs deal.stages")]
    if b["stage"] not in stages:
        return [("error", f"{who}: stage {b['stage']} is not one of deal.stages")]
    if b["stage"] != stages[-1]:
        return [
            (
                "error",
                f"{who}: a ceiling is committed at the last stage ({stages[-1]}), "
                f"not at {b['stage']}",
            )
        ]
    return []


def _item(pack: dict[str, Any], item: dict[str, Any]) -> Found:
    who = f"item {item['id']}"
    b = item["bound"]
    out = _stage(item, (pack.get("deal") or {}).get("stages"))
    if "audience" not in item:
        return out + [("error", f"{who}: a bound item has an audience, its committer")]
    kinds = {p["id"]: p["kind"] for p in pack["positions"]}
    want = PARTY_KINDS[b["side"]]
    for pos in item["audience"]:
        if kinds.get(pos) != want:
            out.append(
                ("error", f"{who}: a {b['side']} is the {want}'s, not position {pos}")
            )
    n = len(audience_members(pack, item))
    if n != 1:
        out.append(
            (
                "error",
                f"{who}: its audience holds {n} members; a bound item needs exactly "
                "one (one pack per buyer)",
            )
        )
    return out


def bound_findings(pack: dict[str, Any]) -> Found:
    """Errors and warnings of the holder and of the bound items of a pack."""
    out = _holder(pack)
    items = bound_items(pack)
    if not items:
        return out
    if not is_deal(pack):
        return out + [("error", "bound items need the pack's positions")]
    if not pack.get("holder"):
        out.append(("error", "bound items need a holder"))
    if not pack.get("deal"):
        out.append(("error", "bound items need deal.id"))
    elif not pack["deal"].get("sealed_floor"):
        out.append(
            (
                "error",
                "bound items need deal.sealed_floor: true (the sealed floor is "
                "off by default)",
            )
        )
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    for item in items:
        out += _item(pack, item)
        b = item["bound"]
        key = (b["topic"], b["side"])
        if key in seen:
            out.append(
                (
                    "error",
                    f"item {item['id']}: topic {b['topic']} has a {b['side']} already",
                )
            )
        seen.setdefault(key, item)
    for topic, sides in topics(pack).items():
        if len(sides) == 2 and (
            sides["floor"]["bound"]["unit"] != sides["ceiling"]["bound"]["unit"]
        ):
            out.append(("error", f"topic {topic}: floor and ceiling differ in unit"))
    return out


def bound_answer_findings(pack: dict[str, Any], ans: dict[str, Any]) -> Found:
    """A bound item's answer holds the commitment only."""
    bound = {i["id"] for i in bound_items(pack)}
    return [
        (
            "error",
            f"answers.{item_id}: a sealed item holds the commitment only, "
            f"not {', '.join(k for k in a if k != 'value')}",
        )
        for item_id, a in ans["answers"].items()
        if item_id in bound and set(a) - {"value"}
    ]


def topic_state(
    pack: dict[str, Any],
    given: dict[str, dict[str, dict[str, Any]]],
    ledger: dict[str, Any] | None,
    topic: str,
) -> tuple[str, list[str]]:
    """(verdict, members whose commitment changed) of a topic. The verdict is the
    latest counted run's; when a party's commitment in the answers is not the one
    that run used, the run does not speak for the answers now and the verdict is
    `not_tested`."""
    verdict = topic_verdict(ledger, topic)
    used = last_commitments(ledger, topic)
    changed = []
    for side, item in topics(pack)[topic].items():
        member = committer(pack, item)
        now = given[item["id"]].get(member or "", {}).get("value")
        if member and side in used and now != used[side]:
            changed.append(member)
    return ("not_tested", changed) if changed else (verdict, changed)


def bound_point(
    pack: dict[str, Any],
    item: dict[str, Any],
    given: dict[str, dict[str, dict[str, Any]]],
    ledger: dict[str, Any] | None,
) -> dict[str, Any]:
    """The diff point of a bound item. It holds who committed, never an answer:
    the commitments stay in the answers files."""
    b = item["bound"]
    committed = list(given[item["id"]])
    verdict, changed = topic_state(pack, given, ledger, b["topic"])
    who = audience_members(pack, item)
    sealed = {"topic": b["topic"], "side": b["side"], "unit": b["unit"]}
    if "stage" in b:
        sealed["stage"] = b["stage"]
    point: dict[str, Any] = {
        "id": item["id"],
        "kind": "item",
        "section": item["section"],
        "question": item["question"],
        "item_kind": "bound",
        "sealed": sealed,
        "audience": item["audience"],
        **({"call_title": item["call_title"]} if "call_title" in item else {}),
        "answers": {},
        "committed_by": [m for m in who if m in committed],
    }
    silent = [m for m in who if m not in committed]
    if silent:
        point["silent"] = silent
    point.update({"class": "sealed", "class_by": "script", "route": "price_meeting"})
    point["verdict"] = verdict
    if changed:
        point["changed_since_run"] = changed
    if ledger_head(ledger):
        point["ledger_head"] = ledger_head(ledger)
    return point


def deal_fields(pack: dict[str, Any]) -> dict[str, Any]:
    """Top-level diff fields of the pack's `deal` block, none for a pack without
    one. `model_pass_allowed` is false unless the parties consented; the asking
    price, when the seller gave one, is shared with every reader of the diff."""
    deal = pack.get("deal")
    if not deal:
        return {}
    out: dict[str, Any] = {"model_pass_allowed": bool(deal.get("model_consent", False))}
    ask = asking_price(pack)
    if ask:
        out["asking_price"] = ask
    return out
