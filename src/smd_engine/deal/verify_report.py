"""The report of `smd deal verify`: a list of checks, each `ok`, `fail`, `unbound`
(an entry from before the 0.7.2 bindings, which cannot be checked further) or
`skip` (a check that was not asked for or whose input was not given). The text of
a check is a label of the pack's language; the JSON form keeps the code and the
details, never a sealed number, a salt or a gap."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from smd_engine.task.deal_labels import VERIFY_LABELS

OK, FAIL, UNBOUND, SKIP = "ok", "fail", "unbound", "skip"
STATUSES = (OK, FAIL, UNBOUND, SKIP)


@dataclass
class Check:
    code: str
    status: str
    entry: int | None = None
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class Report:
    deal: str
    pack: str
    pack_sha256: str
    lang: str
    ledger_head: str | None = None
    checks: list[Check] = field(default_factory=list)

    def add(
        self, code: str, status: str, entry: int | None = None, **detail: Any
    ) -> None:
        self.checks.append(Check(code, status, entry, detail))

    def count(self, status: str) -> int:
        return sum(1 for c in self.checks if c.status == status)

    @property
    def ok(self) -> bool:
        return self.count(FAIL) == 0

    @property
    def complete(self) -> bool:
        """No check failed and none was left `unbound`: every entry was checked in
        full (`skip` is a check not asked for, and is not counted here)."""
        return self.ok and self.count(UNBOUND) == 0

    @property
    def result(self) -> str:
        return "fail" if not self.ok else "passed" if self.complete else "unbound"

    def text_of(self, check: Check) -> str:
        lab = VERIFY_LABELS[self.lang]
        detail = {"seq": check.entry, **check.detail}
        return str(lab["checks"][check.code]).format(**detail)

    def lines(self) -> list[str]:
        lab = VERIFY_LABELS[self.lang]
        out = [f"[{lab['status'][c.status]}] {self.text_of(c)}" for c in self.checks]
        counts = {s: self.count(s) for s in STATUSES}
        out.append(lab["summary"].format(**counts, result=lab["result"][self.result]))
        return out

    def as_json(self) -> str:
        data = {
            "deal": self.deal,
            "pack": self.pack,
            "pack_sha256": self.pack_sha256,
            "ledger_head": self.ledger_head,
            "ok": self.ok,
            "complete": self.complete,
            "counts": {s: self.count(s) for s in STATUSES},
            "checks": [
                {
                    "check": c.code,
                    "status": c.status,
                    "entry": c.entry,
                    "detail": c.detail,
                    "text": self.text_of(c),
                }
                for c in self.checks
            ],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
