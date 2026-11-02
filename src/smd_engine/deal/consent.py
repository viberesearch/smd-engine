"""The consent file of a run (record `task_consent`): the file a party writes
and keeps, and whose sha256 `smd deal consent` logs in the ledger. The seller
consents to every run against his sealed floor, naming the buyer; for a second
run the buyer consents too.

    record: task_consent
    deal: <deal id>
    pack: {id: <pack id>, sha256: <core sha256 of the pack>}   # sha256: sealed floor
    keys: <sha256 of the pack's key list>                        # sealed floor
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

Signatures (packs with `deal.sealed_floor`, see `signing.py`): the party signs the
file with his SSH key, namespace `smd-deal`, and `smd deal consent` verifies it
against the key the pack lists for him. The ledger entry keeps the exact text of
the file (`signed`, whose sha256 is `evidence`) and the armored signature
(`signature`), so anyone with the ledger can verify the consent again without the
party's file, and `smd deal verdict` does so before it counts one. The holder's
operator cannot write a consent for a party: he has no key. In a pack without a
sealed floor nothing is signed; the entry keeps only the sha256, which the party
checks against his own copy.

Binding (0.7.2, sealed floor only): the signed file also names `pack.sha256`, the
core sha256 of the pack the party was sent, and `keys`, the sha256 of that pack's
key list (`signing.key_list_sha`). `smd deal consent` and `smd deal verdict` refuse a
consent whose two values differ from the pack they hold, so a consent cannot be
carried over to a fork of the pack with other text or other keys. A 0.7.1 consent,
which names neither, is refused as a new consent and by a verdict; it stays in an
old ledger, readable, and the party writes it again with both values."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from smd_engine.deal.signing import key_list_sha, signatures_on, verify_signature
from smd_engine.records import RecordError, parse_text
from smd_engine.task.bounds import SHA
from smd_engine.task.model import load_task, sha256_bytes
from smd_engine.task.positions import core_sha


def parse_consent(text: str, where: str) -> dict[str, Any]:
    """The mapping in the text of a consent file."""
    try:
        data = parse_text(text)
    except yaml.YAMLError as exc:
        raise RecordError(f"{where}: not valid YAML ({exc})") from exc
    if not isinstance(data, dict) or data.get("record") != "task_consent":
        raise RecordError(f"{where}: expected record task_consent")
    return data


def read_consent(
    path: Path, pack: dict[str, Any], topic: str, run: int, member: str, buyer: str
) -> dict[str, str]:
    """The commitments ({"floor", "ceiling"}) a consent file names, once the
    file is for this deal, topic, run, member and buyer."""
    data = load_task(path, "task_consent")
    return consent_commitments(data, str(path), pack, topic, run, member, buyer)


def binding_code(data: dict[str, Any], pack: dict[str, Any]) -> str:
    """How a consent file is bound to this pack text and key list: `""` when it is,
    `missing` when it names `pack.sha256` or `keys` no (a 0.7.1 consent), `pack` or
    `keys` when that value differs from the pack's. Only a pack with a sealed floor
    binds; others are not asked."""
    if not signatures_on(pack):
        return ""
    ref = data.get("pack")
    sha = ref.get("sha256") if isinstance(ref, dict) else None
    keys = data.get("keys")
    if sha is None or keys is None:
        return "missing"
    if sha != core_sha(pack):
        return "pack"
    return "keys" if keys != key_list_sha(pack) else ""


BINDING_MESSAGES = {
    "missing": (
        "does not name pack.sha256 and keys (a consent from before 0.7.2); "
        "the party writes it again with both and signs it again"
    ),
    "pack": (
        "pack.sha256 is not the core sha256 of this pack (a consent for "
        "another text of the pack)"
    ),
    "keys": "keys is not the sha256 of this pack's key list (another set of keys)",
}


def binding_problem(data: dict[str, Any], pack: dict[str, Any]) -> str:
    """Why a consent file is not bound to this pack text and key list, or an empty
    string."""
    return BINDING_MESSAGES.get(binding_code(data, pack), "")


def is_bound(pack: dict[str, Any], entry: dict[str, Any]) -> bool:
    """Whether a consent entry keeps a signed text bound to this pack."""
    try:
        data = parse_consent(str(entry.get("signed", "")), "entry")
    except RecordError:
        return False
    return not binding_problem(data, pack)


def consent_commitments(
    data: dict[str, Any],
    path: str,
    pack: dict[str, Any],
    topic: str,
    run: int,
    member: str,
    buyer: str,
) -> dict[str, str]:
    """The same for the mapping of a consent file; `path` names it in errors."""
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
    if problem := binding_problem(data, pack):
        raise RecordError(f"{path}: {problem}")
    return {side: str(commits[side]) for side in ("floor", "ceiling")}


def latest_consents(
    ledger: dict[str, Any], topic: str, run: int
) -> dict[str, dict[str, Any]]:
    """member -> his consent entry for the run; his latest consent counts."""
    return {
        e["by"]: e
        for e in ledger["entries"]
        if e["type"] == "consent" and e["topic"] == topic and e["run"] == run
    }


def consented_commitments(
    ledger: dict[str, Any], topic: str, run: int
) -> dict[str, dict[str, str]]:
    """member -> the commitments he consented to for the run."""
    return {m: e["commitments"] for m, e in latest_consents(ledger, topic, run).items()}


def verify_consents(
    pack: dict[str, Any], ledger: dict[str, Any], topic: str, run: int
) -> None:
    """Refuse (RecordError) unless every consent that counts for the run carries
    its text and a valid signature of the member, and the entry says what the
    signed text says."""
    for member, e in latest_consents(ledger, topic, run).items():
        what = (
            f"the consent of {member} to run {run} of topic {topic} (entry {e['seq']})"
        )
        signed, signature = e.get("signed"), e.get("signature")
        if not (isinstance(signed, str) and isinstance(signature, str)):
            raise RecordError(
                f"{what} is not signed; {member} consents again with a signed file"
            )
        raw = signed.encode("utf-8")
        if sha256_bytes(raw) != e["evidence"]:
            raise RecordError(f"{what}: the signed text is not the one logged")
        verify_signature(pack, member, raw, signature, what)
        data = parse_consent(signed, what)
        named = consent_commitments(data, what, pack, topic, run, member, e["buyer"])
        if named != e["commitments"]:
            raise RecordError(f"{what}: the commitments differ from the signed text")
