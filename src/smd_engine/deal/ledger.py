"""The verdict ledger (`verdicts.yaml`, record `task_verdicts`): the holder's
append-only list of the comparisons run and of the consents to runs.

Each entry names the hash of the one before it (`prev_sha256`, 64 zeros for the
first) and carries its own `sha256`, so an edited entry breaks the chain. The
head, the last entry's sha256, is written into `diff.yaml`, so a ledger cut short
later no longer matches a diff made earlier. The ledger holds no sealed number
and no salt; the commitments in it are public already (they are in the answers).

Run cap (case owner, dz02#l=47): one run per seller-buyer pair per topic and
deal; a second only when both parties' consent is logged here, not the holder's
alone; two at most. Every run against a sealed floor also needs the seller's
consent, naming the buyer (ЦН1 А, dz02#l=55). A comparison that could not be made (`not_tested`) gives
nothing away and does not count."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from smd_engine.records import RecordError, dump_record
from smd_engine.task.model import load_task, schema_issues

GENESIS = "0" * 64
RUN_BASE = 1  # runs per pair and topic that need no consent
RUN_MAX = 2  # hard maximum, with both parties' consent for the second


def entry_sha(entry: dict[str, Any]) -> str:
    body = {k: v for k, v in entry.items() if k != "sha256"}
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def new_ledger(pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "record": "task_verdicts",
        "schema_version": "0.1",
        "deal": pack["deal"]["id"],
        "pack": {"id": pack["id"]},
        "entries": [],
    }


def chain_problems(ledger: dict[str, Any]) -> list[str]:
    out: list[str] = []
    prev = GENESIS
    for n, e in enumerate(ledger["entries"], start=1):
        if e["seq"] != n:
            out.append(f"entry {n} is numbered {e['seq']}")
        if e["prev_sha256"] != prev:
            out.append(f"entry {n} does not follow the entry before it")
        if e["sha256"] != entry_sha(e):
            out.append(f"entry {n} was edited")
        prev = e["sha256"]
    return out


def load_ledger(path: Path, pack: dict[str, Any]) -> dict[str, Any]:
    """The ledger in a file, refused when it is not valid, belongs to another
    deal or pack, or its chain is broken."""
    ledger = load_task(path, "task_verdicts")
    issues = schema_issues(ledger, "task_verdicts", str(path))
    if issues:
        raise RecordError(f"{path}: {issues[0].message}")
    if not pack.get("deal"):
        raise RecordError(f"{path}: the pack has no deal block")
    if ledger["deal"] != pack["deal"]["id"] or ledger["pack"]["id"] != pack["id"]:
        raise RecordError(f"{path}: the ledger is for another deal or pack")
    problems = chain_problems(ledger)
    if problems:
        raise RecordError(f"{path}: the ledger chain is broken: {problems[0]}")
    return ledger


def save_ledger(path: Path, ledger: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(dump_record(ledger), encoding="utf-8")
    os.replace(tmp, path)


def append_entry(ledger: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    """Number and chain `entry`, add it to the ledger, and return it."""
    entries = ledger["entries"]
    full = {
        "seq": len(entries) + 1,
        **entry,
        "prev_sha256": entries[-1]["sha256"] if entries else GENESIS,
    }
    full["sha256"] = entry_sha(full)
    entries.append(full)
    return full


def ledger_head(ledger: dict[str, Any] | None) -> str | None:
    if not ledger or not ledger["entries"]:
        return None
    return str(ledger["entries"][-1]["sha256"])


def _tested(ledger: dict[str, Any], topic: str) -> list[dict[str, Any]]:
    return [
        e
        for e in ledger["entries"]
        if e["type"] == "verdict"
        and e["topic"] == topic
        and e["verdict"] in ("met", "not_met")
    ]


def tested_runs(ledger: dict[str, Any], topic: str) -> int:
    return len(_tested(ledger, topic))


def topic_verdict(ledger: dict[str, Any] | None, topic: str) -> str:
    """The verdict of the latest run that was made, else `not_tested`."""
    done = _tested(ledger, topic) if ledger else []
    return str(done[-1]["verdict"]) if done else "not_tested"


def last_commitments(ledger: dict[str, Any] | None, topic: str) -> dict[str, str]:
    """The commitments ({"floor", "ceiling"}) the latest counted run used."""
    done = _tested(ledger, topic) if ledger else []
    return dict(done[-1]["commitments"]) if done else {}


def has_entry(ledger: dict[str, Any], sha: str) -> bool:
    return any(e["sha256"] == sha for e in ledger["entries"])
