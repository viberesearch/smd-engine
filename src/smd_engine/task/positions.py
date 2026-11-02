"""Deal mode: positions, the shared core of a pack and the annex of each position.

A pack with `positions` is a deal pack. An item or an ontology term with an
`audience` (position ids) belongs to the annex of those positions; one without
it is part of the shared core. Everyone sees the core; a position sees its own
annex only. The core has one sha256 and each annex has its own, so a party can
check the text it was sent without ever holding the other side's annex.
A pack without `positions` is a group pack and none of this applies to it.
"""

from __future__ import annotations

import copy
import hashlib
from typing import Any

from smd_engine.records import RecordError, dump_record


def is_deal(pack: dict[str, Any]) -> bool:
    return bool(pack.get("positions"))


def in_audience(entry: dict[str, Any], position: str | None) -> bool:
    """Whether a pack entry (item or term) is for the position; an entry with no
    audience is the shared core and is for everyone."""
    audience = entry.get("audience")
    return audience is None or position in audience


def member_positions(pack: dict[str, Any]) -> dict[str, str]:
    return {m["id"]: m["position"] for m in pack["members"] if m.get("position")}


def audience_members(pack: dict[str, Any], entry: dict[str, Any]) -> list[str]:
    """The members an entry is for, in the pack's order."""
    where = member_positions(pack)
    return [
        m["id"]
        for m in pack["members"]
        if entry.get("audience") is None or where.get(m["id"]) in entry["audience"]
    ]


def core_view(pack: dict[str, Any]) -> dict[str, Any]:
    """The pack without any entry that has an audience."""
    out = copy.deepcopy(pack)
    out["items"] = [i for i in out["items"] if "audience" not in i]
    out["ontology"]["terms"] = [
        t for t in out["ontology"]["terms"] if "audience" not in t
    ]
    return out


def annex_of(pack: dict[str, Any], position: str) -> dict[str, Any]:
    """What only the position (and others named with it) sees: its terms and items."""
    return {
        "position": position,
        "terms": [
            t
            for t in pack["ontology"]["terms"]
            if "audience" in t and position in t["audience"]
        ],
        "items": [
            i for i in pack["items"] if "audience" in i and position in i["audience"]
        ],
    }


def has_annex(pack: dict[str, Any], position: str) -> bool:
    annex = annex_of(pack, position)
    return bool(annex["terms"] or annex["items"])


def position_view(pack: dict[str, Any], position: str) -> dict[str, Any]:
    """The pack as one position receives it: the core and its own annex, in the
    pack's order. Taking `core_view` of it gives the core of the whole pack."""
    if position not in {p["id"] for p in pack.get("positions", [])}:
        raise RecordError(f"{position} is not a position of the pack")
    out = copy.deepcopy(pack)
    out["items"] = [i for i in out["items"] if in_audience(i, position)]
    out["ontology"]["terms"] = [
        t for t in out["ontology"]["terms"] if in_audience(t, position)
    ]
    return out


SIDES = {
    "seller": "sell",
    "broker_sell": "sell",
    "buyer": "buy",
    "broker_buy": "buy",
}


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


def _sha(data: dict[str, Any]) -> str:
    return hashlib.sha256(dump_record(data).encode("utf-8")).hexdigest()


def core_sha(pack: dict[str, Any]) -> str:
    return _sha(core_view(pack))


def annex_sha(pack: dict[str, Any], position: str) -> str:
    return _sha(annex_of(pack, position))


def stamp_sha(pack: dict[str, Any], file_sha: str) -> str:
    """The sha256 answers, the diff and the pages carry for the pack: the sha of
    the pack file in a group pack, that of the shared core in a deal pack."""
    return core_sha(pack) if is_deal(pack) else file_sha


def pack_view(
    pack: dict[str, Any], position: str | None
) -> tuple[dict[str, Any], str, dict[str, str] | None]:
    """(pack to render, file name suffix, annex stamp) for `render`. A group pack is
    rendered whole; a deal pack as its core, or with `position` as that
    position's view."""
    if not is_deal(pack):
        if position is not None:
            raise RecordError("--position is for a deal pack (one with positions)")
        return pack, "", None
    if position is None:
        return core_view(pack), "", None
    view = position_view(pack, position)
    stamp = (
        {"position": position, "sha256": annex_sha(pack, position)}
        if has_annex(pack, position)
        else None
    )
    return view, f".{position}", stamp


def stamps_text(pack: dict[str, Any]) -> list[str]:
    """Lines for `smd task check`: the core sha256 and the annex sha256 of each
    position that has an annex. Empty for a group pack."""
    if not is_deal(pack):
        return []
    lines = [f"core sha256: {core_sha(pack)}"]
    lines += [
        f"annex sha256 {p['id']}: {annex_sha(pack, p['id'])}"
        for p in pack["positions"]
        if has_annex(pack, p["id"])
    ]
    return lines
