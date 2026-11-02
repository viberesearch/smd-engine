"""The consent file of a run (record `task_consent`): the file a party writes
and keeps, and whose sha256 `smd deal consent` logs in the ledger. The seller
consents to every run against his sealed floor, naming the buyer; for a second
run the buyer consents too.

    record: task_consent
    deal: <deal id>
    pack: {id: <pack id>}
    topic: <topic>
    run: 1
    member: <the party>
    buyer: <the buyer, the member who commits the ceiling>
    commitments: {floor: <sha256>, ceiling: <sha256>}

The file ties the consent to one deal, topic, run, buyer and party, and names the two
commitments, those in the answers files, that the run will compare. It cannot
stand for the other party or be reused for another run, and a commitment changed
afterwards, by either party, is not covered: the run is `commitment_changed`
until both parties consent again.
The engine has no signatures: it cannot tell who wrote the file. What it keeps is
its sha256, which the party checks against his own copy; the ledger entry is not
the holder's word, because the holder cannot produce a file the party recognises."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from smd_engine.records import RecordError
from smd_engine.task.bounds import SHA
from smd_engine.task.model import load_task


def read_consent(
    path: Path, pack: dict[str, Any], topic: str, run: int, member: str, buyer: str
) -> dict[str, str]:
    """The commitments ({"floor", "ceiling"}) a consent file names, once the
    file is for this deal, topic, run, member and buyer."""
    data = load_task(path, "task_consent")
    pack_id = data.get("pack")
    expected = {
        "deal": pack["deal"]["id"],
        "topic": topic,
        "run": run,
        "member": member,
        "buyer": buyer,
    }
    wrong = [k for k, v in expected.items() if data.get(k) != v]
    if not isinstance(pack_id, dict) or pack_id.get("id") != pack["id"]:
        wrong.append("pack")
    commits: Any = data.get("commitments")
    if not (
        isinstance(commits, dict)
        and set(commits) == {"floor", "ceiling"}
        and all(isinstance(c, str) and SHA.fullmatch(c) for c in commits.values())
    ):
        wrong.append("commitments")
    if wrong:
        raise RecordError(
            f"{path}: not a consent of {member} to run {run} of topic {topic} "
            f"against buyer {buyer} in this deal ({', '.join(wrong)})"
        )
    return {side: str(commits[side]) for side in ("floor", "ceiling")}


def consented_commitments(
    ledger: dict[str, Any], topic: str, run: int
) -> dict[str, dict[str, str]]:
    """member -> the commitments he consented to for the run; his latest consent
    counts."""
    return {
        e["by"]: e["commitments"]
        for e in ledger["entries"]
        if e["type"] == "consent" and e["topic"] == topic and e["run"] == run
    }
