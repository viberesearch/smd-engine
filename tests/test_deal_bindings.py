"""Deal mode, bindings of the sealed floor (0.7.2): a consent names the core sha256
and the key list of its pack, the answers files of the parties with a key are signed
and the verdict entry records them with the consents it counted. Keys are made at
run time."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from deal_helpers import (
    MEMBERS,
    consent_binding,
    copy_deal,
    edit_pack,
    key_of,
    make_key,
    needs_ssh,
    sign_answers,
    sign_file,
)
from smd_engine.cli import main
from smd_engine.deal import ledger as led
from smd_engine.records import RecordError
from smd_engine.task.model import load_task, sha256_file
from test_deal_signed import consent_cmd, hand_consent, rechain
from test_deal_verdict import (  # noqa: F401  (the fixture and the helpers)
    committed,
    consent,
    consent_file,
    entries,
    raw_entries,
    seller_consent,
    verdicts,
    work,
)

pytestmark = needs_ssh


def fork_binding(tmp_path: Path, change: Any) -> dict[str, Any]:
    """The binding a consent would carry for a fork of the pack (`change` edits the
    fork's pack)."""
    fork = copy_deal(tmp_path / "fork")
    edit_pack(fork, change)
    return consent_binding(fork)


def verdict_cmd(work: Path, files: dict[str, Path], ledger: Path) -> int:
    """`smd deal verdict` on the answers files as they are: nobody signs them here."""
    args = [
        "deal",
        "verdict",
        str(work / "pack.yaml"),
        "price",
        "--ledger",
        str(ledger),
    ]
    args += ["--answers", *(str(work / f"answers_{m}.yaml") for m in MEMBERS)]
    for side, path in files.items():
        args += [f"--{side}", str(path)]
    return main([*args, "--date", "2026-11-10"])


def keep(note: Path) -> dict[str, str]:
    """The signed text and the signature of a consent file, as a ledger entry keeps
    them."""
    return {
        "signed": note.read_text(encoding="utf-8"),
        "signature": Path(f"{note}.sig").read_text(encoding="utf-8"),
    }


def test_a_consent_for_a_forked_pack_or_other_keys_is_refused_at_consent_and_verdict(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = committed(work, tmp_path)
    sign_answers(work)
    forger = make_key(tmp_path / "forger")
    text = fork_binding(tmp_path, lambda p: p.update(title="Another text"))
    keyed = fork_binding(
        tmp_path / "k", lambda p: p["members"][1].update(ssh_key=forger)
    )
    cases = {
        "pack.sha256 is not the core sha256": text,  # a fork with other text
        "keys is not the sha256": {**consent_binding(work), "keys": keyed["keys"]},
    }
    for n, (message, binding) in enumerate(cases.items()):
        ledger = tmp_path / f"v{n}.yaml"
        note = consent_file(work, tmp_path, "vera", run=1, **binding)
        capsys.readouterr()
        assert consent_cmd(work, ledger, "vera", note) == 2  # refused at consent
        assert message in capsys.readouterr().err
        assert not ledger.exists()
        hand_consent(work, ledger, note, **keep(note))  # the operator logs it himself
        assert verdict_cmd(work, files, ledger) == 2  # refused at the verdict
        assert message in capsys.readouterr().err
        assert verdicts(ledger) == []


def test_a_consent_without_the_bindings_is_refused_as_new_and_kept_in_an_old_ledger(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = committed(work, tmp_path)
    sign_answers(work)
    note = consent_file(work, tmp_path, "vera", run=1)
    old = load_task(note)  # a 0.7.1 consent: the pack id alone, no keys
    old["pack"] = {"id": old["pack"]["id"]}
    del old["keys"]
    note.write_text(yaml.safe_dump(old), encoding="utf-8")
    sign_file(key_of(work, "vera"), note)
    ledger = tmp_path / "verdicts.yaml"
    assert consent_cmd(work, ledger, "vera", note) == 2
    assert "a consent from before 0.7.2" in capsys.readouterr().err
    assert not ledger.exists()
    hand_consent(work, ledger, note, **keep(note))  # it sits in an old ledger
    pack = load_task(work / "pack.yaml")
    assert len(led.load_ledger(ledger, pack)["entries"]) == 1  # which still loads
    assert verdict_cmd(work, files, ledger) == 2  # but no run is counted on it
    assert "from before 0.7.2" in capsys.readouterr().err
    note = consent_file(work, tmp_path, "vera", run=1)  # written again with both
    assert consent_cmd(work, ledger, "vera", note) == 0  # taken, though the same
    assert consent_cmd(work, ledger, "vera", note) == 2  # but once
    assert verdict_cmd(work, files, ledger) == 0
    assert verdicts(ledger)[0]["verdict"] == "met"


def test_the_verdict_refuses_unsigned_or_wrongly_signed_answers(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = committed(work, tmp_path)
    ledger = tmp_path / "verdicts.yaml"
    seller_consent(work, ledger)
    capsys.readouterr()
    assert verdict_cmd(work, files, ledger) == 2  # nobody signed
    assert "answers_vera.yaml: not signed by vera" in capsys.readouterr().err
    sign_answers(work)
    sign_file(key_of(work, "boris"), work / "answers_vera.yaml")  # the wrong party
    assert verdict_cmd(work, files, ledger) == 2
    assert "answers_vera.yaml: the signature is not vera's" in capsys.readouterr().err
    sign_answers(work)
    answers = work / "answers_boris.yaml"
    answers.write_text(  # edited after he signed
        answers.read_text(encoding="utf-8") + "# edited\n", encoding="utf-8"
    )
    assert verdict_cmd(work, files, ledger) == 2
    assert "answers_boris.yaml: the signature is not boris's" in capsys.readouterr().err
    assert verdicts(ledger) == [] and len(entries(ledger)) == 1  # nothing was logged
    sign_answers(work)  # the broker has no key: his file needs no signature
    assert verdict_cmd(work, files, ledger) == 0


def test_a_verdict_entry_records_the_answers_and_the_consents_it_used(
    work: Path, tmp_path: Path
) -> None:
    files = committed(work, tmp_path)
    sign_answers(work)
    ledger = tmp_path / "verdicts.yaml"
    seller_consent(work, ledger)
    assert verdict_cmd(work, files, ledger) == 0
    first = verdicts(ledger)[0]
    shas = {m: sha256_file(work / f"answers_{m}.yaml") for m in MEMBERS}
    assert first["answers"] == shas
    (vera,) = [e for e in entries(ledger) if e["type"] == "consent"]
    assert first["consents"] == [vera["sha256"]]
    note = consent_file(work, tmp_path, "boris")  # run 2 counts both consents
    assert (
        main(  # (the helper `consent` signs and logs the party's file)
            [
                "deal",
                "consent",
                str(work / "pack.yaml"),
                "price",
                "--ledger",
                str(ledger),
            ]
            + ["--member", "boris", "--evidence", str(note), "--date", "2026-11-11"]
        )
        == 0
    )
    assert consent(work, tmp_path, ledger, "vera") == 0
    assert verdict_cmd(work, files, ledger) == 0
    second = verdicts(ledger)[1]
    counted = [e["sha256"] for e in entries(ledger) if e["type"] == "consent"][-2:]
    assert second["consents"] == counted and len(counted) == 2
    # the chain covers the new fields: an edited list of consents breaks it
    data = load_task(ledger)
    data["entries"][-1]["consents"] = counted[:1]
    led.save_ledger(ledger, data)
    with pytest.raises(RecordError, match="entry .* was edited"):
        led.load_ledger(ledger, load_task(work / "pack.yaml"))
    rechain(ledger)  # rechained by hand, it loads: the signed inputs are named in it
    assert len(led.load_ledger(ledger, load_task(work / "pack.yaml"))["entries"]) > 3


def test_a_ledger_of_0_7_1_without_the_new_fields_still_loads_and_diffs(
    work: Path, tmp_path: Path
) -> None:
    committed(work, tmp_path)
    ledger = tmp_path / "verdicts.yaml"
    pack = load_task(work / "pack.yaml")
    data = led.new_ledger(pack)
    old = {
        "type": "verdict",
        "date": "2026-11-10",
        "topic": "price",
        "method": "local-v1",
    }
    old |= {"floor_member": "vera", "ceiling_member": "boris", "run": 1}
    old |= {"verdict": "met", "commitments": {"floor": "1" * 64, "ceiling": "2" * 64}}
    led.append_entry(data, old)  # no `answers`, no `consents`
    led.save_ledger(ledger, data)
    assert len(led.load_ledger(ledger, pack)["entries"]) == 1
    answers = [str(work / f"answers_{m}.yaml") for m in MEMBERS]
    out = tmp_path / "out"
    assert (
        main(
            ["task", "diff", str(work / "pack.yaml"), *answers, "-o", str(out)]
            + ["--ledger", str(ledger)]
        )
        == 0
    )


def test_an_older_signed_answers_file_swapped_back_is_not_counted(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = committed(work, tmp_path)
    sign_answers(work)
    ledger = tmp_path / "verdicts.yaml"
    seller_consent(work, ledger)
    assert verdict_cmd(work, files, ledger) == 0  # run 1 on the first commitment
    old = work / "answers_vera.yaml"
    shutil.copy(old, tmp_path / "older.yaml")
    shutil.copy(f"{old}.sig", tmp_path / "older.yaml.sig")
    new = old.read_text(encoding="utf-8").replace(
        load_task(old)["answers"]["price-floor"]["value"], "a" * 64
    )
    old.write_text(new, encoding="utf-8")  # vera commits another floor and signs it
    sign_answers(work)
    assert consent(work, tmp_path, ledger, "vera") == 0  # both consent to the new one
    assert consent(work, tmp_path, ledger, "boris") == 0
    shutil.copy(tmp_path / "older.yaml", old)  # the operator puts the older back,
    shutil.copy(tmp_path / "older.yaml.sig", f"{old}.sig")  # with its signature
    capsys.readouterr()
    assert verdict_cmd(work, files, ledger) == 0
    last = verdicts(ledger)[-1]
    assert (last["verdict"], last["reason"]) == ("not_tested", "commitment_changed")
    assert last["answers"]["vera"] == sha256_file(old)  # the file it read is on record


def test_task_diff_warns_of_unsigned_answers_and_does_not_refuse(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    answers = [str(work / f"answers_{m}.yaml") for m in MEMBERS]
    args = [
        "task",
        "diff",
        str(work / "pack.yaml"),
        *answers,
        "-o",
        str(tmp_path / "o"),
    ]
    assert main(args) == 0
    err = capsys.readouterr().err
    assert "warning: " in err and "answers_vera.yaml: not signed by vera" in err
    assert "answers_boris.yaml: not signed by boris" in err
    assert "answers_gleb" not in err  # the broker has no key
    sign_answers(work)
    assert main(args) == 0
    assert "not signed" not in capsys.readouterr().err
