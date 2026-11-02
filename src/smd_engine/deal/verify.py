"""`smd deal verify`: an audit of a verdict ledger that any party, or a third
party, can run, so that the holder's operator cannot slip in a hand-written or
replayed entry unnoticed.

What is checked (see `docs/deal-mode.md`, "Verifying the ledger"):

- the hash chain, the order of the entries and the head;
- every consent entry: its signed text hashes to `evidence`, the signature is the
  member's (key from the pack, namespace `smd-deal`), the text names this deal,
  topic, run, member and buyer, this pack's core sha256 and key list, and says what
  the entry says;
- every verdict entry: the consent entries it counted are earlier, current, valid,
  for the same topic, run and buyer, with the commitments it used, from the seller
  (and the buyer for a second run); the run is the next counted one and within
  the cap; the answers files it recorded match those given, with their signatures
  and commitments; with the holder's sealed files the outcome is recomputed; with
  a diff its head and verdicts match.

Entries from before 0.7.2 (unsigned or unbound consents, verdicts that name no
consents or answers) cannot be checked in full and are reported `unbound`. After
the first entry that has the 0.7.2 fields the software always writes them, so a
later entry without them is a `FAIL`: it cannot be told from a hand-written one."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from smd_engine.deal.consent import binding_code, parse_consent
from smd_engine.deal.ledger import GENESIS, RUN_BASE, RUN_MAX, entry_sha, ledger_head
from smd_engine.deal.signing import signatures_on, verify_signature
from smd_engine.deal.verdict import topic_items
from smd_engine.deal.verify_extra import (
    SIDES,
    AnswersFiles,
    SealedFolder,
    Topic,
    check_answers,
    check_diff,
    latest_answers,
    load_answers_files,
)
from smd_engine.deal.verify_report import FAIL, OK, UNBOUND, Report
from smd_engine.records import RecordError
from smd_engine.task.bounds import committer
from smd_engine.task.model import schema_issues, sha256_bytes

BIND_CODES = {"pack": "consent_bind_pack", "keys": "consent_bind_keys"}


def _topic(pack: dict[str, Any], name: str) -> Topic | None:
    try:
        items = topic_items(pack, name)
    except RecordError:
        return None
    return Topic(items, {s: committer(pack, items[s]) for s in SIDES})


def _chain(rep: Report, entries: list[dict[str, Any]]) -> None:
    prev, intact = GENESIS, True
    for n, e in enumerate(entries, start=1):
        for bad, code in (
            (e["seq"] != n, "chain_numbered"),
            (e["prev_sha256"] != prev, "chain_prev"),
            (e["sha256"] != entry_sha(e), "chain_edited"),
        ):
            if bad:
                rep.add(code, FAIL, n, got=e["seq"])
                intact = False
        prev = e["sha256"]
    if intact:
        rep.add("chain_ok", OK, n=len(entries))
    head = ledger_head({"entries": entries})
    if head:
        rep.add("head", OK, head=head)
    else:
        rep.add("head_none", OK)


def _signed_data(pack: dict[str, Any], e: dict[str, Any]) -> dict[str, Any] | None:
    signed = e.get("signed")
    if not isinstance(signed, str):
        return None
    try:
        return parse_consent(signed, "entry")
    except RecordError, yaml.YAMLError:
        return None


def _modern_from(pack: dict[str, Any], entries: list[dict[str, Any]]) -> int | None:
    """The number of the first entry that has the 0.7.2 fields (a consent bound to
    the pack, a verdict that records answers or consents); None when no entry does
    or the pack has no sealed floor."""
    if not signatures_on(pack):
        return None
    for e in entries:
        if e["type"] == "consent":
            data = _signed_data(pack, e)
            if data is not None and binding_code(data, pack) != "missing":
                return int(e["seq"])
        elif "answers" in e or "consents" in e:
            return int(e["seq"])
    return None


class Walk:
    """The entries of a ledger, checked in order."""

    def __init__(
        self,
        rep: Report,
        pack: dict[str, Any],
        pack_sha: str,
        entries: list[dict[str, Any]],
        files: AnswersFiles | None,
        sealed: SealedFolder | None,
    ) -> None:
        self.rep, self.pack, self.pack_sha = rep, pack, pack_sha
        self.entries, self.files, self.sealed = entries, files, sealed
        self.modern = _modern_from(pack, entries)
        self.latest = latest_answers(entries)
        self.status: dict[int, str] = {}  # consent entry number -> ok|unbound|fail
        self.counted: dict[str, int] = {}  # topic -> counted runs so far

    def after_modern(self, seq: int) -> bool:
        return self.modern is not None and seq > self.modern

    def run(self) -> None:
        for e in self.entries:
            topic = _topic(self.pack, e["topic"])
            if topic is None:
                self.rep.add("topic_unknown", FAIL, e["seq"], topic=e["topic"])
            elif e["type"] == "consent":
                self.status[e["seq"]] = self.consent(e, topic)
            else:
                self.verdict(e, topic)

    # consent entries

    def consent(self, e: dict[str, Any], topic: Topic) -> str:
        rep, pack, seq = self.rep, self.pack, e["seq"]
        who = {"by": e["by"], "run": e["run"], "topic": e["topic"]}
        seller, buyer = topic.members["floor"], topic.members["ceiling"]
        if (
            e["by"] not in (seller, buyer)
            or e["buyer"] != buyer
            or e["run"] > RUN_MAX
            or (e["run"] <= RUN_BASE and e["by"] != seller)
        ):
            rep.add("consent_party", FAIL, seq, **who)
            return FAIL
        signed, signature = e.get("signed"), e.get("signature")
        data = _signed_data(pack, e)
        old = data is None or binding_code(data, pack) == "missing"
        if old and not (isinstance(signed, str) and isinstance(signature, str)):
            return self._old_consent(e, who)
        if not (isinstance(signed, str) and isinstance(signature, str)):
            rep.add("consent_text", FAIL, seq, **who)
            return FAIL
        raw = signed.encode("utf-8")
        if sha256_bytes(raw) != e["evidence"]:
            rep.add("consent_sha", FAIL, seq, **who)
            return FAIL
        try:
            verify_signature(pack, e["by"], raw, signature, "entry")
        except RecordError:
            rep.add("consent_sig", FAIL, seq, **who)
            return FAIL
        if data is None:
            rep.add("consent_text", FAIL, seq, **who)
            return FAIL
        wrong = self._wrong_fields(data, e)
        if wrong:
            rep.add("consent_names", FAIL, seq, fields=", ".join(wrong), **who)
            return FAIL
        if data.get("commitments") != e["commitments"]:
            rep.add("consent_commit", FAIL, seq, **who)
            return FAIL
        code = binding_code(data, pack)
        if code == "missing":
            return self._old_consent(e, who)
        if code:
            rep.add(BIND_CODES[code], FAIL, seq, **who)
            return FAIL
        rep.add("consent_ok", OK, seq, **who)
        return OK

    def _old_consent(self, e: dict[str, Any], who: dict[str, Any]) -> str:
        if self.after_modern(e["seq"]):
            self.rep.add("consent_downgrade", FAIL, e["seq"], **who)
            return FAIL
        self.rep.add("consent_unbound", UNBOUND, e["seq"], **who)
        return UNBOUND

    def _wrong_fields(self, data: dict[str, Any], e: dict[str, Any]) -> list[str]:
        want = {
            "deal": self.pack["deal"]["id"],
            "topic": e["topic"],
            "run": e["run"],
            "member": e["by"],
            "buyer": e["buyer"],
        }
        wrong = [k for k, v in want.items() if data.get(k) != v]
        ref = data.get("pack")
        if not isinstance(ref, dict) or ref.get("id") != self.pack["id"]:
            wrong.append("pack")
        return wrong

    # verdict entries

    def verdict(self, e: dict[str, Any], topic: Topic) -> None:
        rep, seq = self.rep, e["seq"]
        counted = e["verdict"] in ("met", "not_met")
        right = (
            e["floor_member"] == topic.members["floor"]
            and e["ceiling_member"] == topic.members["ceiling"]
            and e["method"] == self.pack["holder"]["method"]
        )
        if not right:
            rep.add("verdict_who", FAIL, seq, topic=e["topic"])
        if counted:
            self._run(e)
            self._consents(e, topic)
        if "answers" in e:
            parties = {topic.members["floor"], topic.members["ceiling"]}
            members = {m["id"] for m in self.pack["members"]}
            if counted and not (parties <= set(e["answers"]) <= members):
                # a counted run read both parties' answers: an entry without one
                # of them, or naming no member of the pack, the engine does not write
                rep.add("verdict_answers_parties", FAIL, seq, run=e["run"])
            if self.files is not None:
                check_answers(rep, self.files, e, topic, self.latest)
        elif signatures_on(self.pack) and e.get("reason") != "cap_reached":
            if self.after_modern(seq):
                rep.add("verdict_downgrade_answers", FAIL, seq)
            else:
                rep.add("answers_old", UNBOUND, seq)
        if counted and self.sealed is not None:
            self.sealed.recompute(rep, self.pack, self.pack_sha, e, topic)

    def _run(self, e: dict[str, Any]) -> None:
        seq, topic = e["seq"], e["topic"]
        expected = self.counted.get(topic, 0) + 1
        self.counted[topic] = expected
        if e["run"] != expected:
            self.rep.add("verdict_run", FAIL, seq, run=e["run"], expected=expected)
        elif e["run"] > RUN_MAX:
            self.rep.add("verdict_cap", FAIL, seq, run=e["run"], max=RUN_MAX)
        else:
            self.rep.add("verdict_run_ok", OK, seq, run=e["run"], max=RUN_MAX)

    def _consents(self, e: dict[str, Any], topic: Topic) -> None:
        rep, seq = self.rep, e["seq"]
        refs = e.get("consents")
        if refs is None:
            if self.after_modern(seq) and signatures_on(self.pack):
                rep.add("verdict_downgrade_consents", FAIL, seq)
                return
            self._old_consents(e, topic)
            return
        problems = self._consent_problems(e, refs, topic)
        for code, detail in problems:
            rep.add(code, FAIL, seq, **detail)
        if not problems:
            rep.add("verdict_consents_ok", OK, seq, run=e["run"], n=len(refs))

    def _earlier_consents(self, e: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """member -> his latest consent entry for the run before entry `e`."""
        return {
            c["by"]: c
            for c in self.entries
            if c["type"] == "consent"
            and c["seq"] < e["seq"]
            and c["topic"] == e["topic"]
            and c["run"] == e["run"]
        }

    def _needed(self, e: dict[str, Any], topic: Topic) -> set[str | None]:
        return {topic.members["floor"]} | (
            {topic.members["ceiling"]} if e["run"] > RUN_BASE else set()
        )

    def _old_consents(self, e: dict[str, Any], topic: Topic) -> None:
        """A verdict that names no consents (before 0.7.2): the consent entries it
        needed must still be earlier in the chain, with its commitments."""
        rep, seq = self.rep, e["seq"]
        given = self._earlier_consents(e)
        missing = sorted(str(m) for m in self._needed(e, topic) if m not in given)
        if missing:
            rep.add(
                "verdict_consent_none", FAIL, seq, run=e["run"], who=", ".join(missing)
            )
        elif any(c["commitments"] != e.get("commitments") for c in given.values()):
            rep.add("verdict_consent_commit", FAIL, seq, run=e["run"])
        else:
            rep.add("verdict_consents_old", UNBOUND, seq, run=e["run"])

    def _consent_problems(
        self, e: dict[str, Any], refs: list[str], topic: Topic
    ) -> list[tuple[str, dict[str, Any]]]:
        by_sha = {c["sha256"]: c for c in self.entries if c["type"] == "consent"}
        out: list[tuple[str, dict[str, Any]]] = []
        found: list[dict[str, Any]] = []
        for ref in refs:
            c = by_sha.get(ref)
            if c is None or c["seq"] >= e["seq"]:
                out.append(("verdict_consent_missing", {"ref": ref[:12]}))
            else:
                found.append(c)
        latest = self._earlier_consents(e)
        for c in found:
            detail = {"ref": c["seq"], "by": c["by"]}
            if self.status.get(c["seq"]) != OK:
                out.append(("verdict_consent_invalid", detail))
            elif (c["topic"], c["run"], c["buyer"]) != (
                e["topic"],
                e["run"],
                e["ceiling_member"],
            ):
                out.append(("verdict_consent_other", detail))
            elif c["commitments"] != e.get("commitments"):
                out.append(("verdict_consent_commit", {"run": e["run"]}))
            elif latest.get(c["by"]) is not c:
                out.append(("verdict_consent_stale", detail))
        have = {c["by"] for c in found}
        needed = self._needed(e, topic)
        if have != needed:  # also when the verdict names none: `consents: []`
            out.append(("verdict_consent_parties", {"run": e["run"]}))
        return out


def verify_ledger(
    pack: dict[str, Any],
    pack_sha: str,
    ledger: dict[str, Any],
    answers: list[Path],
    sealed: Path | None,
    diff: dict[str, Any] | None,
) -> Report:
    """The report of all checks. `ledger` is the mapping read from the file, not
    yet accepted: a broken chain is a finding here, not a refusal."""
    rep = Report(pack["deal"]["id"], pack["id"], pack_sha, pack["lang"])
    if schema_issues(ledger, "task_verdicts", "ledger"):
        rep.add("ledger_shape", FAIL)
        return rep
    if ledger["deal"] != pack["deal"]["id"] or ledger["pack"]["id"] != pack["id"]:
        rep.add("ledger_for", FAIL)
        return rep
    entries = ledger["entries"]
    rep.ledger_head = ledger_head(ledger)
    _chain(rep, entries)
    files = load_answers_files(rep, pack, pack_sha, answers) if answers else None
    if files is None:
        rep.add("answers_not_given", "skip")
    folder = SealedFolder(sealed) if sealed else None
    if folder is None:
        rep.add("sealed_not_given", "skip")
    Walk(rep, pack, pack_sha, entries, files, folder).run()
    if diff is None:
        rep.add("diff_not_given", "skip")
    else:
        check_diff(rep, pack_sha, ledger, diff)
    return rep
