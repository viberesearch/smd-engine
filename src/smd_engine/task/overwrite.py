"""When `smd task diff` may replace a diff.yaml that differs from the new one.

A differing file may hold a model pass (classes written into it), so it is not
replaced without `--force`. One difference is expected: the deal cycle runs the
diff before the verdict and again after it, and the second diff differs from the
first in the verdict fields of the sealed points only. That replacement is
allowed when the new ledger extends the one the old diff was made from, which
keeps the check for a ledger cut short or swapped."""

from __future__ import annotations

from typing import Any

import yaml

from smd_engine.deal.ledger import has_entry
from smd_engine.records import dump_record

LEDGER_FIELDS = ("verdict", "ledger_head", "changed_since_run")


def _without_ledger_fields(diff: dict[str, Any]) -> str:
    points = [
        (
            {k: v for k, v in p.items() if k not in LEDGER_FIELDS}
            if p.get("item_kind") == "bound"
            else p
        )
        for p in diff["points"]
    ]
    return dump_record({**diff, "points": points})


def replaceable(
    old_text: str, new: dict[str, Any], ledger: dict[str, Any] | None
) -> bool:
    """True when the old diff.yaml differs from `new` only in the ledger fields of
    the sealed points, and the ledger it was made from is a part of `ledger`."""
    try:
        old = yaml.safe_load(old_text)
        if dump_record(old) != old_text:  # a comment or an edit by hand
            return False
        heads = {p["ledger_head"] for p in old["points"] if p.get("ledger_head")}
        same = _without_ledger_fields(old) == _without_ledger_fields(new)
    except yaml.YAMLError, KeyError, TypeError, AttributeError:
        return False
    return same and all(ledger is not None and has_entry(ledger, h) for h in heads)
