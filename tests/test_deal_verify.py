"""Deal mode, `smd deal verify`: the audit of a verdict ledger. A clean ledger
passes; a hand-written entry, a forged or replayed consent, a verdict with no
consent, a flipped outcome and a diff that does not match the ledger fail; entries
from before 0.7.2 are reported `unbound` and make the exit 1 unless
`--allow-unbound`. Keys are made at run time."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

import pytest
import yaml

from deal_helpers import MEMBERS, key_of, make_key, needs_ssh, sign_answers, sign_file
from smd_engine.cli import main
from smd_engine.deal import ledger as led
from smd_engine.task.deal_labels import VERIFY_LABELS
from smd_engine.task.model import load_task
from test_deal_signed import hand_consent, rechain
from test_deal_verdict import (  # noqa: F401  (the fixture and the helpers)
    CEILING,
    FLOOR,
    committed,
    consent,
    consent_file,
    diff_with_ledger,
    raw_entries,
    verdict,
    work,
)

pytestmark = needs_ssh


@pytest.fixture()
def run(
    capsys: pytest.CaptureFixture[str],
) -> Callable[..., tuple[int, str]]:
    def go(
        work: Path, ledger: Path, *extra: str, plain: bool = False
    ) -> tuple[int, str]:
        capsys.readouterr()
        args = ["deal", "verify", str(work / "pack.yaml"), "--ledger", str(ledger)]
        if not plain:
            args += ["--answers", *(str(work / f"answers_{m}.yaml") for m in MEMBERS)]
        code = main([*args, *extra])
        shown = capsys.readouterr()
        return code, shown.out + shown.err

    return go


def made(work: Path, tmp_path: Path) -> tuple[dict[str, Path], Path]:
    """Commit the example numbers and log the seller's consent and a run."""
    files = committed(work, tmp_path)
    ledger = tmp_path / "verdicts.yaml"
    assert verdict(work, files, ledger) == 0
    return files, ledger


def edit(ledger: Path, change: Callable[[list[dict[str, Any]]], None]) -> None:
    """Change the entries of a ledger file and rewrite its hashes, as the holder
    could."""
    data = load_task(ledger)
    change(data["entries"])
    led.save_ledger(ledger, data)
    rechain(ledger)


def codes(out: str, status: str) -> list[str]:
    """The `check` codes of the given status in a --json report."""
    return [c["check"] for c in json.loads(out)["checks"] if c["status"] == status]


def test_a_clean_ledger_passes_with_answers_sealed_files_and_diff(
    work: Path, tmp_path: Path, run: Callable[..., tuple[int, str]]
) -> None:
    files, ledger = made(work, tmp_path)
    assert diff_with_ledger(work, ledger, tmp_path / "out") == 0
    extra = [
        "--sealed",
        str(tmp_path / "safe"),
        "--diff",
        str(tmp_path / "out/diff.yaml"),
    ]
    code, out = run(work, ledger, *extra)
    assert code == 0, out
    assert "[FAIL]" not in out and "[unbound" not in out
    assert "hash chain intact: 2 entries in order" in out
    assert "recomputed from the sealed files: met" in out
    assert f"ledger head {led.ledger_head(load_task(ledger))}" in out
    assert out.rstrip().endswith("(15 ok, 0 FAIL, 0 unbound, 0 skipped)")
    code, out = run(work, ledger, *extra, "--json")
    report = json.loads(out)
    assert code == 0 and report["ok"] is True and report["counts"]["fail"] == 0
    assert report["ledger_head"] == led.ledger_head(load_task(ledger))
    assert not codes(out, "fail") and not codes(out, "unbound")


def test_a_second_run_with_both_consents_passes_and_a_missing_buyer_consent_fails(
    work: Path, tmp_path: Path, run: Callable[..., tuple[int, str]]
) -> None:
    files, ledger = made(work, tmp_path)
    assert consent(work, tmp_path, ledger, "vera") == 0
    assert consent(work, tmp_path, ledger, "boris") == 0
    assert verdict(work, files, ledger) == 0
    code, out = run(work, ledger, "--sealed", str(tmp_path / "safe"))
    assert code == 0, out
    assert "entry 5: run 2, within the cap of 2" in out
    assert "[FAIL]" not in out and "[unbound" not in out

    def drop_buyer(entries: list[dict[str, Any]]) -> None:
        entries[4]["consents"] = entries[4]["consents"][:1]

    edit(ledger, drop_buyer)
    code, out = run(work, ledger, "--json")
    assert code == 1
    assert "verdict_consent_parties" in codes(out, "fail")


def test_without_sealed_the_recompute_is_skipped_and_said_so(
    work: Path, tmp_path: Path, run: Callable[..., tuple[int, str]]
) -> None:
    _, ledger = made(work, tmp_path)
    code, out = run(work, ledger, "--json")
    assert code == 0
    assert "sealed_not_given" in codes(out, "skip")
    assert "diff_not_given" in codes(out, "skip")
    code, out = run(work, ledger, plain=True)
    assert "--sealed not given: the verdicts are not recomputed" in out
    assert "answers files not given" in out


def test_a_hand_written_verdict_entry_even_rechained_fails(
    work: Path, tmp_path: Path, run: Callable[..., tuple[int, str]]
) -> None:
    _, ledger = made(work, tmp_path)
    first = raw_entries(ledger)[-1]

    def forge(entries: list[dict[str, Any]]) -> None:
        entry = {k: v for k, v in first.items() if k not in ("answers", "consents")}
        entries.append({**entry, "seq": 3, "run": 2, "date": "2026-11-12"})

    edit(ledger, forge)
    assert main(["task", "check", str(work / "pack.yaml")]) == 0  # the pack is fine
    code, out = run(work, ledger, "--json")
    assert code == 1
    fails = codes(out, "fail")
    assert (
        "verdict_downgrade_consents" in fails and "verdict_downgrade_answers" in fails
    )


def test_a_consent_with_a_forged_signature_fails(
    work: Path, tmp_path: Path, run: Callable[..., tuple[int, str]]
) -> None:
    _, ledger = made(work, tmp_path)
    note = tmp_path / "consents" / "consent_vera.yaml"
    make_key(tmp_path / "forger")
    forged = sign_file(tmp_path / "forger", note)
    text = forged.read_text(encoding="utf-8")

    def swap(entries: list[dict[str, Any]]) -> None:
        entries[0]["signature"] = text

    edit(ledger, swap)
    code, out = run(work, ledger, "--json")
    assert code == 1
    assert "consent_sig" in codes(out, "fail")


def test_a_consent_replayed_from_another_run_or_topic_fails(
    work: Path, tmp_path: Path, run: Callable[..., tuple[int, str]]
) -> None:
    committed(work, tmp_path)
    for name in ("c1", "c2"):
        (tmp_path / name).mkdir()
    other_run = consent_file(work, tmp_path / "c1", "vera", run=2)  # signed for run 2
    other_topic = consent_file(work, tmp_path / "c2", "vera", run=1, topic="rent")
    for n, note in enumerate((other_run, other_topic)):
        path = tmp_path / f"v{n}.yaml"
        hand_consent(
            work,
            path,
            note,
            signed=note.read_text(encoding="utf-8"),
            signature=Path(f"{note}.sig").read_text(encoding="utf-8"),
        )
        code, out = run(work, path, "--json")
        assert code == 1, out
        assert "consent_names" in codes(out, "fail")


def test_a_verdict_naming_a_missing_consent_fails(
    work: Path, tmp_path: Path, run: Callable[..., tuple[int, str]]
) -> None:
    _, ledger = made(work, tmp_path)

    def point_elsewhere(entries: list[dict[str, Any]]) -> None:
        entries[1]["consents"] = ["f" * 64]

    edit(ledger, point_elsewhere)
    code, out = run(work, ledger, "--json")
    assert code == 1
    assert "verdict_consent_missing" in codes(out, "fail")


def test_the_run_cap_of_two_counted_runs_is_checked(
    work: Path, tmp_path: Path, run: Callable[..., tuple[int, str]]
) -> None:
    _, ledger = made(work, tmp_path)
    first = raw_entries(ledger)[-1]

    def more(entries: list[dict[str, Any]]) -> None:
        for n in (2, 3):
            entries.append({**first, "seq": n + 1, "run": n})

    edit(ledger, more)
    code, out = run(work, ledger, "--json")
    assert code == 1
    assert "verdict_cap" in codes(out, "fail")


def test_entries_from_before_0_7_2_are_unbound_and_do_not_fail(
    work: Path, tmp_path: Path, run: Callable[..., tuple[int, str]]
) -> None:
    committed(work, tmp_path)
    sign_answers(work)
    (tmp_path / "c").mkdir()
    note = consent_file(work, tmp_path / "c", "vera", run=1)
    old = load_task(note)  # a 0.7.1 consent: no pack sha256, no keys
    old["pack"] = {"id": old["pack"]["id"]}
    del old["keys"]
    note.write_text(yaml.safe_dump(old), encoding="utf-8")
    sign_file(key_of(work, "vera"), note)
    ledger = tmp_path / "verdicts.yaml"
    hand_consent(
        work,
        ledger,
        note,
        signed=note.read_text(encoding="utf-8"),
        signature=Path(f"{note}.sig").read_text(encoding="utf-8"),
    )
    data = load_task(ledger)
    data["entries"][0]["date"] = "2026-11-09"
    led.append_entry(
        data,
        {
            "type": "verdict",
            "date": "2026-11-10",
            "topic": "price",
            "floor_member": "vera",
            "ceiling_member": "boris",
            "method": "local-v1",
            "run": 1,
            "verdict": "met",
            "commitments": old["commitments"],
        },
    )
    led.save_ledger(ledger, data)
    rechain(ledger)
    code, out = run(work, ledger, "--sealed", str(tmp_path / "safe"))
    assert code == 1, out  # fail closed: unbound entries are not proven
    assert "[unbound (old entry)]" in out and "[FAIL]" not in out
    assert run(work, ledger, "--allow-unbound")[0] == 0
    unbound = codes(run(work, ledger, "--json")[1], "unbound")
    assert {"consent_unbound", "verdict_consents_old", "answers_old"} <= set(unbound)


def test_sealed_recompute_catches_a_flipped_outcome_and_prints_no_number(
    work: Path, tmp_path: Path, run: Callable[..., tuple[int, str]]
) -> None:
    files, ledger = made(work, tmp_path)

    def flip(entries: list[dict[str, Any]]) -> None:
        entries[1]["verdict"] = "not_met"

    edit(ledger, flip)
    assert run(work, ledger)[0] == 0  # without the sealed files nothing shows it
    secrets = [FLOOR, CEILING] + [
        load_task(p, "task_sealed")["salt"] for p in files.values()
    ]
    for extra in ((), ("--json",)):
        code, out = run(work, ledger, "--sealed", str(tmp_path / "safe"), *extra)
        assert code == 1
        assert not [s for s in secrets if s in out]
    assert (
        "logged not_met, recomputed met"
        in run(work, ledger, "--sealed", str(tmp_path / "safe"))[1]
    )


def test_a_diff_that_does_not_match_the_ledger_fails(
    work: Path, tmp_path: Path, run: Callable[..., tuple[int, str]]
) -> None:
    _, ledger = made(work, tmp_path)
    assert diff_with_ledger(work, ledger, tmp_path / "out") == 0
    path = tmp_path / "out" / "diff.yaml"
    for n, (field, value, code_name) in enumerate(
        (("verdict", "not_met", "diff_verdict"), ("ledger_head", "f" * 64, "diff_head"))
    ):
        diff = load_task(path)
        for p in diff["points"]:
            if "sealed" in p:
                p[field] = value
        bad = tmp_path / f"diff{n}.yaml"
        bad.write_text(yaml.safe_dump(diff, sort_keys=False), encoding="utf-8")
        code, out = run(work, ledger, "--diff", str(bad), "--json")
        assert code == 1
        assert code_name in codes(out, "fail")


def test_every_check_code_has_an_english_and_a_russian_label() -> None:
    source = Path(__file__).resolve().parents[1] / "src" / "smd_engine" / "deal"
    used: set[str] = set()
    for path in source.glob("verify*.py"):
        used |= set(re.findall(r'\.add\(\s*"(\w+)"', path.read_text(encoding="utf-8")))
    en, ru = (VERIFY_LABELS[lang]["checks"] for lang in ("en", "ru"))
    assert used <= set(en) and set(en) == set(ru)
    fields = re.compile(r"{(\w+)}")
    assert all(set(fields.findall(en[c])) == set(fields.findall(ru[c])) for c in en)
    assert set(VERIFY_LABELS["en"]["status"]) == set(VERIFY_LABELS["ru"]["status"])
