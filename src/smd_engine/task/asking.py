"""Deal mode, the asking price: the seller's price, shared in the pack as
`deal.asking_price: {value, unit, stage?}`. The seller chooses the stage of
`deal.stages` at which the pack pages open it; by default that is the stage after
`nda`, else the second stage, else the only one. The diff and the agenda are made
after the answers and always show it. A pack without positions, or with no seller,
has none and gets nothing from here."""

from __future__ import annotations

from typing import Any

from smd_engine.task.deal_labels import DEAL_LABELS
from smd_engine.task.positions import is_deal

NDA = "nda"
Found = list[tuple[str, str]]


def has_seller(pack: dict[str, Any]) -> bool:
    return any(p["kind"] == "seller" for p in pack.get("positions", []))


def default_stage(stages: list[str]) -> str:
    """The stage after `nda`; the second stage when there is no `nda`; the only
    stage when there is one."""
    after = stages.index(NDA) + 1 if NDA in stages else 1
    return stages[min(after, len(stages) - 1)]


def asking_price(pack: dict[str, Any]) -> dict[str, Any] | None:
    """{"value", "unit", "stage"?} with the stage resolved, or None. A pack with no
    `deal.stages` has no stage, so its pages show the price from the start."""
    given = (pack.get("deal") or {}).get("asking_price")
    if not given:
        return None
    stages = pack["deal"].get("stages")
    out = {"value": given["value"], "unit": given["unit"]}
    stage = given.get("stage") or (default_stage(stages) if stages else None)
    if stage:
        out["stage"] = stage
    return out


def is_open_at(ask: dict[str, Any], pack: dict[str, Any], stage: str | None) -> bool:
    """Whether a page for `stage` shows the price: the stage is the price's or a
    later one. A price with no stage is always open; with no stage given, a price
    that has one is not shown."""
    if "stage" not in ask:
        return True
    stages = pack["deal"]["stages"]
    if stage not in stages:
        return False
    return bool(stages.index(stage) >= stages.index(ask["stage"]))


def price_text(ask: dict[str, Any]) -> str:
    """ "120 000 EUR": the number in groups of three, then the unit."""
    value = ask["value"]
    shown = f"{value:,}" if isinstance(value, int) else f"{value:,.2f}".rstrip("0")
    return f"{shown.replace(',', ' ').rstrip('.')} {ask['unit']}"


def page_line(pack: dict[str, Any], stage: str | None) -> str:
    """The line of a pack page: the price, or the stage at which it opens."""
    ask = asking_price(pack)
    if ask is None:
        return ""
    lab = DEAL_LABELS[pack["lang"]]
    if is_open_at(ask, pack, stage):
        return f"{lab['asking_price']}: {price_text(ask)}"
    return str(lab["asking_opens"]).format(s=ask["stage"])


def diff_line(record: dict[str, Any]) -> str:
    """The line of a diff or an agenda that carries `asking_price`, or an empty
    string. It is shown to every reader: both are made after the answers."""
    ask = record.get("asking_price")
    if not ask:
        return ""
    return f"{DEAL_LABELS[record['lang']]['asking_price']}: {price_text(ask)}"


def asking_findings(pack: dict[str, Any]) -> Found:
    """A deal pack with a seller states the asking price; its stage is a stage of
    the deal. A pack with no seller may state one all the same."""
    deal = pack.get("deal") or {}
    given = deal.get("asking_price")
    if given is None:
        if is_deal(pack) and has_seller(pack):
            return [
                (
                    "error",
                    "a deal pack with a seller states the asking price: "
                    "deal.asking_price {value, unit, stage}",
                )
            ]
        return []
    stage = given.get("stage")
    stages = deal.get("stages")
    if stage is not None and not stages:
        return [("error", "deal.asking_price: a stage needs deal.stages")]
    if stage is not None and stage not in (stages or []):
        return [("error", f"deal.asking_price: stage {stage} is not in deal.stages")]
    return []
