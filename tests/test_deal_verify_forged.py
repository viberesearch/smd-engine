"""Deal mode, `smd deal verify`: entries a holder's operator could hand-write or
replay, and the checks that catch them, one test each (replaced or replayed
inputs, an empty list of consents, old entries that are not fully verified).
Keys are made at run time."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest
import yaml

from deal_helpers import edit_pack, key_of, needs_ssh, sign_file
from smd_engine.cli import main
from smd_engine.deal import ledger as led
from smd_engine.task.deal_labels import VERIFY_LABELS
from smd_engine.task.model import load_task
from test_deal_signed import rechain
from test_deal_verdict import (  # noqa: F401  (the fixture and the helpers)
    consent,
    raw_entries,
    verdict,
    work,
)
from test_deal_verify import codes, edit, made, run  # noqa: F401

pytestmark = needs_ssh

Run = Callable[..., tuple[int, str]]


def fails(out: str) -> list[str]:
    return codes(out, "fail")


def test_a_counted_verdict_with_an_empty_list_of_consents_fails(
    work: Path, tmp_path: Path, run: Run
) -> None:
    _, ledger = made(work, tmp_path)
    real = [e for e in raw_entries(ledger) if e["type"] == "verdict"][0]
    forged = tmp_path / "forged.yaml"
    data = led.new_ledger(load_task(work / "pack.yaml"))
    entry = {k: v for k, v in real.items() if k not in ("seq", "prev_sha256", "sha256")}
    led.append_entry(data, {**entry, "consents": []})  # no consent entry at all
    led.save_ledger(forged, data)
    code, out = run(work, forged, "--json")
    assert code == 1
    assert "verdict_consent_parties" in fails(out)
    assert "verdict_consents_ok" not in codes(out, "ok")


def test_a_second_run_with_an_empty_list_of_consents_fails(
    work: Path, tmp_path: Path, run: Run
) -> None:
    _, ledger = made(work, tmp_path)
    assert consent(work, tmp_path, ledger, "vera") == 0  # the buyer did not consent
    first = [e for e in raw_entries(ledger) if e["type"] == "verdict"][0]

    def second(entries: list[dict[str, Any]]) -> None:
        entries.append({**first, "seq": 4, "run": 2, "consents": []})

    edit(ledger, second)
    code, out = run(work, ledger, "--sealed", str(tmp_path / "safe"), "--json")
    assert code == 1
    assert "verdict_consent_parties" in fails(out)


def test_a_verdict_that_drops_a_party_s_answers_fails(
    work: Path, tmp_path: Path, run: Run
) -> None:
    _, ledger = made(work, tmp_path)

    def drop_buyer(entries: list[dict[str, Any]]) -> None:
        v = next(e for e in entries if e["type"] == "verdict")
        del v["answers"][v["ceiling_member"]]

    edit(ledger, drop_buyer)
    code, out = run(work, ledger, "--json")
    assert code == 1 and "verdict_answers_parties" in fails(out)


def old_style(entries: list[dict[str, Any]]) -> None:
    """The ledger as 0.7.1 wrote it: an unsigned-looking consent, a verdict that
    names no consents and no answers."""
    del entries[0]["signed"], entries[0]["signature"]
    del entries[1]["answers"], entries[1]["consents"]


def test_an_old_ledger_is_not_called_fully_verified(
    work: Path, tmp_path: Path, run: Run
) -> None:
    _, ledger = made(work, tmp_path)
    edit(ledger, old_style)
    code, out = run(work, ledger, "--allow-unbound")
    assert code == 0 and "[FAIL]" not in out and "[unbound" in out
    summary = out.rstrip().splitlines()[-1]
    assert "all checks passed" not in summary and "not fully verified" in summary
    assert json.loads(run(work, ledger, "--json")[1])["complete"] is False
    ok_code, ok_out = run(work, made(work, tmp_path / "again")[1], "--json")
    assert ok_code == 0 and json.loads(ok_out)["complete"] is True


def test_an_unbound_entry_fails_the_exit_unless_allowed(
    work: Path, tmp_path: Path, run: Run
) -> None:
    _, ledger = made(work, tmp_path)
    assert run(work, ledger)[0] == 0  # nothing unbound
    edit(ledger, old_style)
    code, out = run(work, ledger)
    assert code == 1 and "[FAIL]" not in out
    assert run(work, ledger, "--allow-unbound")[0] == 0


def test_the_summary_verdicts_are_labelled_in_both_languages() -> None:
    keys = {
        set(VERIFY_LABELS[lang]["result"]) == {"passed", "unbound", "fail"}
        for lang in ("en", "ru")
    }
    assert keys == {True}
    assert "не полностью" in VERIFY_LABELS["ru"]["result"]["unbound"]


# one test for each check on a replaced or replayed input


def test_a_replaced_answers_file_fails_even_when_signed_again(
    work: Path, tmp_path: Path, run: Run
) -> None:
    _, ledger = made(work, tmp_path)
    path = work / "answers_vera.yaml"
    ans = yaml.safe_load(path.read_text(encoding="utf-8"))
    ans["date"] = "2026-12-31"
    path.write_text(yaml.safe_dump(ans, sort_keys=False), encoding="utf-8")
    sign_file(key_of(work, "vera"), path)
    code, out = run(work, ledger, "--json")
    assert code == 1
    assert "answers_mismatch" in fails(out)


def test_a_superseded_consent_kept_in_the_verdict_fails_as_stale(
    work: Path, tmp_path: Path, run: Run
) -> None:
    _, ledger = made(work, tmp_path)

    def replay(entries: list[dict[str, Any]]) -> None:
        later = {**entries[0], "seq": 2, "date": "2026-11-09"}
        entries[1]["seq"] = 3
        entries.insert(1, later)  # the same consent again: the verdict names the first

    edit(ledger, replay)
    code, out = run(work, ledger, "--json")
    assert code == 1
    assert "verdict_consent_stale" in fails(out)


def test_a_commitment_that_the_consent_did_not_name_fails(
    work: Path, tmp_path: Path, run: Run
) -> None:
    _, ledger = made(work, tmp_path)

    def other(entries: list[dict[str, Any]]) -> None:
        entries[1]["commitments"]["floor"] = "0" * 64

    edit(ledger, other)
    code, out = run(work, ledger, "--json")
    assert code == 1
    assert "verdict_consent_commit" in fails(out)
    assert "answers_commit" in fails(out)  # nor is it the one in his answers file


def test_a_consent_entry_that_misstates_its_commitments_fails(
    work: Path, tmp_path: Path, run: Run
) -> None:
    _, ledger = made(work, tmp_path)

    def other(entries: list[dict[str, Any]]) -> None:
        entries[0]["commitments"]["floor"] = "0" * 64

    edit(ledger, other)
    code, out = run(work, ledger, "--json")
    assert code == 1
    assert "consent_commit" in fails(out)


def test_a_counted_verdict_with_the_wrong_run_number_fails(
    work: Path, tmp_path: Path, run: Run
) -> None:
    _, ledger = made(work, tmp_path)

    def renumber(entries: list[dict[str, Any]]) -> None:
        entries[1]["run"] = 2

    edit(ledger, renumber)
    code, out = run(work, ledger, "--json")
    assert code == 1
    assert "verdict_run" in fails(out)


def test_a_sealed_file_made_for_another_text_of_the_pack_fails(
    work: Path, tmp_path: Path, run: Run
) -> None:
    """The ledger was made on one text of the pack and is audited against another:
    the sealed files, found by their commitments, are stamped with the first."""
    _, ledger = made(work, tmp_path)
    edit_pack(work, lambda p: p["items"][0].update(question="A revised question?"))
    code, out = run(work, ledger, "--sealed", str(tmp_path / "safe"), "--json")
    assert code == 1
    assert "sealed_bad" in fails(out)
