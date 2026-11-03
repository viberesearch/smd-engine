"""The inputs `smd deal verify` takes besides the ledger: the answers files, the
folder of the holder's sealed files, and a diff. The sealed numbers are read only
to recompute a comparison, in memory, and never reach a message or the report."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from smd_engine.deal.overlap import comparator_for
from smd_engine.deal.sealed import commitment_of, read_sealed
from smd_engine.deal.signing import key_holders, signatures_on, verify_file
from smd_engine.deal.verify_report import FAIL, OK, SKIP, Report
from smd_engine.records import RecordError
from smd_engine.task.bounds import committer
from smd_engine.task.model import load_task, sha256_file

SIDES = ("floor", "ceiling")


@dataclass
class AnswersFile:
    sha: str
    answers: dict[str, Any]


@dataclass
class Topic:
    """The two bound items of a topic and the members who commit them."""

    items: dict[str, dict[str, Any]]
    members: dict[str, str | None]

    def side_of(self, member: str) -> str | None:
        return next((s for s in SIDES if self.members[s] == member), None)


AnswersFiles = dict[str, list[AnswersFile]]


def load_answers_files(
    rep: Report, pack: dict[str, Any], pack_sha: str, paths: list[Path]
) -> AnswersFiles:
    """Read the answers files given, check that each is for this text of the pack
    and (with a sealed floor) that a member with a key signed it."""
    out: AnswersFiles = {}
    for path in paths:
        try:
            ans = load_task(path, "task_answers")
            sha = sha256_file(path)
        except RecordError:
            rep.add("answers_file_bad", FAIL, file=path.name)
            continue
        member = str(ans.get("member"))
        ref = ans.get("pack")
        out.setdefault(member, []).append(AnswersFile(sha, ans.get("answers") or {}))
        if not isinstance(ref, dict) or ref.get("sha256") != pack_sha:
            rep.add("answers_file_pack", FAIL, file=path.name, member=member)
        elif signatures_on(pack) and member in key_holders(pack):
            try:
                verify_file(pack, member, path, None)
            except RecordError:
                rep.add("answers_file_sig", FAIL, file=path.name, member=member)
            else:
                rep.add("answers_file", OK, file=path.name, member=member)
        else:
            rep.add("answers_file_nosig", OK, file=path.name, member=member)
    return out


def latest_answers(entries: list[dict[str, Any]]) -> dict[str, int]:
    """member -> number of the last verdict entry that records his answers file."""
    out: dict[str, int] = {}
    for e in entries:
        if e["type"] == "verdict":
            for member in e.get("answers") or {}:
                out[member] = e["seq"]
    return out


def check_answers(
    rep: Report,
    files: AnswersFiles,
    e: dict[str, Any],
    topic: Topic,
    latest: dict[str, int],
) -> None:
    """The answers files a verdict entry recorded against those given: the sha256
    of each, and the commitment in it against the one the run compared."""
    for member, sha in e["answers"].items():
        mine = files.get(member, [])
        hit = next((f for f in mine if f.sha == sha), None)
        if hit is None:
            if mine and latest.get(member) == e["seq"]:
                rep.add("answers_mismatch", FAIL, e["seq"], member=member)
            else:
                rep.add("answers_nofile", SKIP, e["seq"], member=member)
            continue
        side = topic.side_of(member)
        used = (e.get("commitments") or {}).get(side or "")
        if side and used is not None:
            item = topic.items[side]["id"]
            given = (hit.answers.get(item) or {}).get("value")
            if given != used:
                rep.add("answers_commit", FAIL, e["seq"], member=member)
                continue
        rep.add("answers_ok", OK, e["seq"], member=member)


class SealedFolder:
    """The holder's sealed files in a folder (and its subfolders), found by the
    commitment each one gives, with their signatures beside them."""

    def __init__(self, folder: Path) -> None:
        if not folder.is_dir():
            raise RecordError(f"{folder}: not a folder")
        self.found: dict[str, tuple[Path, dict[str, Any]]] = {}
        for path in sorted(folder.rglob("sealed_*.yaml")):
            sealed = read_sealed(path)
            if sealed is not None:
                self.found[commitment_of(sealed)] = (path, sealed)

    def recompute(
        self,
        rep: Report,
        pack: dict[str, Any],
        pack_sha: str,
        e: dict[str, Any],
        topic: Topic,
    ) -> None:
        """Recompute the outcome of a counted verdict from the two sealed files:
        their signatures, what they are for, and the comparison. A file that is
        not in the folder leaves the run not recomputed."""
        seq = e["seq"]
        commits = e.get("commitments") or {}
        got = {s: self.found.get(commits.get(s, "")) for s in SIDES}
        absent = [s for s in SIDES if got[s] is None]
        if absent:
            rep.add("sealed_missing", SKIP, seq, sides=", ".join(absent))
            return
        numbers: dict[str, float] = {}
        failed = False
        for side in SIDES:
            found = got[side]
            assert found is not None
            path, sealed = found
            item, member = topic.items[side], topic.members[side]
            here = (
                sealed["deal"] == pack["deal"]["id"]
                and sealed["pack"]["id"] == pack["id"]
                and sealed["pack"]["sha256"] == pack_sha
                and sealed["member"] == member
                and sealed["item"] == item["id"]
                and sealed["side"] == side
                and sealed["unit"] == item["bound"]["unit"]
            )
            if not here:
                rep.add("sealed_bad", FAIL, seq, side=side)
                failed = True
                continue
            if signatures_on(pack):
                try:
                    verify_file(pack, str(member), path, None)
                except RecordError:
                    rep.add("sealed_sig", FAIL, seq, side=side, member=member)
                    failed = True
                    continue
            numbers[side] = float(sealed["value"])
        if failed:
            return
        try:
            comparator = comparator_for(e["method"])
        except RecordError:
            rep.add("sealed_method", FAIL, seq, method=e["method"])
            return
        met = comparator.compare(numbers["floor"], numbers["ceiling"])
        recomputed = "met" if met else "not_met"
        if recomputed != e["verdict"]:
            rep.add(
                "sealed_flip", FAIL, seq, logged=e["verdict"], recomputed=recomputed
            )
        else:
            rep.add("sealed_ok", OK, seq, verdict=recomputed)
