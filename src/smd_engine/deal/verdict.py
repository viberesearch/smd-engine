"""`smd deal verdict`: the holder compares the seller's sealed floor with the
buyer's sealed ceiling of one topic and logs the result in the ledger.

The result is a flag, `met`, `not_met` or `not_tested`, and never a stop: the
route of the point is the in-person price meeting. `not_tested` is the result
when a number is missing, a commitment fails, the units differ, or the run cap
is reached. The sealed numbers are opened here and nowhere else, after the cap
is checked, and are held in memory for the one comparison. Nothing written or
raised here repeats a number, a salt, or the gap between the two."""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Any, Callable, Mapping

from smd_engine.deal.consent import (
    consent_commitments,
    consented_commitments,
    latest_consents,
    parse_consent,
    read_consent,
)
from smd_engine.deal.ledger import (
    RUN_BASE,
    RUN_MAX,
    append_entry,
    entry_sha,
    tested_runs,
)
from smd_engine.deal.overlap import Comparator, comparator_for
from smd_engine.deal.sealed import commitment_of
from smd_engine.deal.signing import NAMESPACE, signatures_on, verify_signature
from smd_engine.records import RecordError, dump_record, parse_text
from smd_engine.task.bounds import committer, topics
from smd_engine.task.model import read_bytes, sha256_bytes

SIDES = ("floor", "ceiling")
# reads a sealed file when called; None when it is not a valid sealed file
Opener = Callable[[], dict[str, Any] | None]


def topic_items(pack: dict[str, Any], topic: str) -> dict[str, dict[str, Any]]:
    """{"floor": item, "ceiling": item} of a topic; both have to exist."""
    if not pack.get("holder") or not pack.get("deal"):
        raise RecordError("the pack has no holder and deal block")
    found = topics(pack).get(topic)
    if found is None or set(found) != set(SIDES):
        raise RecordError(f"topic {topic} needs a floor item and a ceiling item")
    return found


def _commitment(
    answers: dict[str, dict[str, Any]], member: str | None, item_id: str
) -> str | None:
    value = answers.get(member or "", {}).get("answers", {}).get(item_id, {})
    return value.get("value") if isinstance(value.get("value"), str) else None


def _problem(
    pack: dict[str, Any],
    pack_sha: str,
    side: str,
    item: dict[str, Any],
    member: str | None,
    commit: str | None,
    opener: Opener | None,
) -> str | None:
    """The reason the side cannot be opened, or None when it can."""
    if commit is None or opener is None:
        return f"no_{side}"
    sealed = opener()
    if sealed is None:
        return "bad_commitment"
    mine = (
        sealed["deal"] == pack["deal"]["id"]
        and sealed["pack"]["id"] == pack["id"]
        and sealed["pack"]["sha256"] == pack_sha
        and sealed["member"] == member
        and sealed["item"] == item["id"]
        and sealed["side"] == side
    )
    if not mine:
        return "bad_commitment"
    if sealed["unit"] != item["bound"]["unit"]:
        return "unit_mismatch"
    return None if commitment_of(sealed) == commit else "bad_commitment"


def _first_problem(
    pack: dict[str, Any],
    pack_sha: str,
    items: dict[str, dict[str, Any]],
    members: dict[str, str | None],
    commits: dict[str, str | None],
    read: Mapping[str, Opener],
) -> str | None:
    for side in SIDES:
        reason = _problem(
            pack,
            pack_sha,
            side,
            items[side],
            members[side],
            commits[side],
            read.get(side),
        )
        if reason:
            return reason
    return None


def _consent_problem(
    ledger: dict[str, Any],
    topic: str,
    run: int,
    members: dict[str, str | None],
    commits: dict[str, str | None],
) -> str | None:
    """Why a run lacks its consent, or None. Every run against the sealed floor
    needs the seller's consent, naming the buyer; a further run needs the buyer's
    too. Each party's latest consent names the two commitments he agreed to be
    tested; if either has changed since, the run is `commitment_changed`."""
    given = consented_commitments(ledger, topic, run)
    needed = {members["floor"]} | ({members["ceiling"]} if run > RUN_BASE else set())
    if set(given) != needed:
        return "consent_missing"
    if any(c != commits for c in given.values()):
        return "commitment_changed"
    return None


def run_verdict(
    pack: dict[str, Any],
    pack_sha: str,
    topic: str,
    answers: dict[str, dict[str, Any]],
    openers: dict[str, Opener],
    ledger: dict[str, Any],
    date: str,
    comparator: Comparator | None = None,
) -> dict[str, Any]:
    """Run the comparison of a topic and append its entry to the ledger.
    `answers` are the answers records by member; `openers` read the sealed file
    of a side ("floor", "ceiling") when called, and only after the cap and the
    consents are checked. A side with no opener was not given; one whose opener
    returns None is not a valid sealed file."""
    items = topic_items(pack, topic)
    members = {s: committer(pack, items[s]) for s in SIDES}
    comparator = comparator or comparator_for(pack["holder"]["method"])
    read = {side: cache(opener) for side, opener in openers.items()}  # read once
    entry: dict[str, Any] = {
        "type": "verdict",
        "date": date,
        "topic": topic,
        "floor_member": members["floor"],
        "ceiling_member": members["ceiling"],
        "method": comparator.method,
    }
    done = tested_runs(ledger, topic)
    run = done + 1
    commits = {s: _commitment(answers, members[s], items[s]["id"]) for s in SIDES}
    reason: str | None = None
    if run > RUN_MAX:
        reason = "cap_reached"
    else:
        if (
            None not in commits.values()
        ):  # a missing number is `no_floor` or `no_ceiling`
            reason = _consent_problem(ledger, topic, run, members, commits)
        reason = reason or _first_problem(pack, pack_sha, items, members, commits, read)
    if reason is not None:
        entry.update({"verdict": "not_tested", "reason": reason})
    else:
        floor, ceiling = read["floor"](), read["ceiling"]()
        assert floor is not None and ceiling is not None
        met = comparator.compare(float(floor["value"]), float(ceiling["value"]))
        entry.update(
            {
                "run": run,
                "verdict": "met" if met else "not_met",
                "commitments": {s: commits[s] for s in SIDES},
            }
        )
    return append_entry(ledger, entry)


def add_consent(
    pack: dict[str, Any],
    topic: str,
    ledger: dict[str, Any],
    member: str,
    evidence: Path,
    date: str,
    signature: str | None = None,
) -> dict[str, Any]:
    """Log one party's consent to the next run of a topic. `evidence` is the
    consent file (see `deal/consent.py`); the entry keeps its sha256 and the
    commitments it names. The seller consents to every run, naming the buyer; for a
    further run the buyer consents too, each with a file of his own. With a sealed
    floor `signature` (the armored SSH signature of the file) is required and
    verified, and the entry keeps the file's text and the signature."""
    items = topic_items(pack, topic)
    seller, buyer = (committer(pack, items[s]) for s in SIDES)
    if member not in (seller, buyer):
        raise RecordError(f"{member} is not a party to topic {topic}")
    run = tested_runs(ledger, topic) + 1
    if run <= RUN_BASE and member != seller:
        raise RecordError(
            f"the first run of topic {topic} needs the seller's consent only"
        )
    if run > RUN_MAX:
        raise RecordError(f"topic {topic} is at its maximum of {RUN_MAX} runs")
    signed = ""
    if signatures_on(pack):
        raw = read_bytes(evidence)
        try:
            signed = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise RecordError(f"{evidence}: not UTF-8 text") from None
        data = parse_consent(signed, str(evidence))
        commitments = consent_commitments(
            data, str(evidence), pack, topic, run, member, str(buyer)
        )
        if signature is None:
            raise RecordError(
                f"{evidence}: no signature; {member} signs the file with his key "
                f"(ssh-keygen -Y sign -f <private key> -n {NAMESPACE} {evidence})"
            )
        verify_signature(pack, member, raw, signature, str(evidence))
    else:
        raw = read_bytes(evidence)
        commitments = read_consent(evidence, pack, topic, run, member, str(buyer))
    # a new consent, naming other commitments, replaces the earlier one; so does a
    # signed one that names the same, when the earlier is a consent of a ledger
    # from before signatures (0.7.0), which a sealed-floor verdict refuses
    last = latest_consents(ledger, topic, run).get(member)
    if last and last["commitments"] == commitments and (not signed or "signed" in last):
        raise RecordError(f"{member} has consented to run {run} already")
    entry = {
        "type": "consent",
        "date": date,
        "topic": topic,
        "run": run,
        "by": member,
        "buyer": buyer,
        "evidence": sha256_bytes(raw),
        "commitments": commitments,
    }
    if signed:
        entry.update({"signed": signed, "signature": signature})
        again = parse_text(dump_record({"entry": entry}))["entry"]
        if entry_sha(again) != entry_sha(entry):
            raise RecordError(
                f"{evidence}: the text does not survive being kept in the ledger "
                "(it has a control character such as U+0085); write the consent "
                "in plain text and sign it again"
            )
    return append_entry(ledger, entry)
