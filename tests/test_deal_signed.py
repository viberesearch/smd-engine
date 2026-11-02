"""Deal mode, signatures: with `deal.sealed_floor` the consent files and the sealed
files are signed with the party's SSH key (`ssh-keygen -Y`, namespace smd-deal),
and the holder's operator cannot forge a consent. Keys are made at run time."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from deal_helpers import (
    FLOOR,
    copy_deal,
    edit_pack,
    errors,
    key_of,
    needs_ssh,
    sign_file,
)
from smd_engine.cli import main
from smd_engine.deal import ledger as led
from smd_engine.deal import signing
from smd_engine.records import RecordError
from smd_engine.task.check import check_pack
from smd_engine.task.model import load_task, sha256_bytes
from test_deal_verdict import (  # noqa: F401  (the fixture and the helpers)
    committed,
    consent_file,
    entries,
    raw_entries,
    seller_consent,
    verdict,
    verdicts,
    work,
)


def key_errors(folder: Path) -> list[str]:
    pack = load_task(folder / "pack.yaml")
    return [m for m in errors(check_pack(pack, "p")) if "ssh_key" in m]


def consent_cmd(work: Path, ledger: Path, member: str, note: Path, *extra: str) -> int:
    args = [
        "deal",
        "consent",
        str(work / "pack.yaml"),
        "price",
        "--ledger",
        str(ledger),
    ]
    args += ["--member", member, "--evidence", str(note), "--date", "2026-11-09"]
    return main([*args, *extra] + ([] if ledger.exists() else ["--new"]))


def rechain(ledger: Path) -> None:
    """Rewrite the hashes of a ledger file after a test edited its entries, as the
    holder could."""
    data = load_task(ledger)
    prev = led.GENESIS
    for e in data["entries"]:
        e["prev_sha256"] = prev
        e["sha256"] = prev = led.entry_sha(e)
    led.save_ledger(ledger, data)


def hand_consent(work: Path, ledger: Path, note: Path, **extra: Any) -> None:
    """A consent entry of vera to run 1 written by hand into a new ledger."""
    raw = note.read_bytes()
    pack = load_task(work / "pack.yaml")
    data = led.new_ledger(pack)
    entry = {
        "type": "consent",
        "date": "2026-11-09",
        "topic": "price",
        "run": 1,
        "by": "vera",
        "buyer": "boris",
        "evidence": sha256_bytes(raw),
        "commitments": load_task(note)["commitments"],
        **extra,
    }
    led.append_entry(data, entry)
    led.save_ledger(ledger, data)


def test_the_pack_check_needs_a_valid_key_for_each_party_with_a_sealed_floor(
    tmp_path: Path,
) -> None:
    folder = copy_deal(tmp_path / "deal")
    assert key_errors(folder) == []

    def drop(p: dict[str, Any]) -> None:
        del p["members"][0]["ssh_key"]
        p["members"][1]["ssh_key"] = "ssh-ed25519 not*base64"
        p["members"][2]["ssh_key"] = "not a key"  # a broker's key is checked too

    edit_pack(folder, drop)
    found = key_errors(folder)
    assert any("member vera: ssh_key is required" in m for m in found)
    assert any("member boris: ssh_key is not a valid OpenSSH" in m for m in found)
    assert any("member gleb: ssh_key must be an OpenSSH" in m for m in found)
    twin = copy_deal(tmp_path / "twin")
    edit_pack(
        twin, lambda p: p["members"][1].update(ssh_key=p["members"][0]["ssh_key"])
    )
    assert any("member boris: ssh_key is the key of" in m for m in key_errors(twin))
    # without the sealed floor nothing about keys is asked
    edit_pack(twin, lambda p: p["deal"].update(sealed_floor=False))
    assert key_errors(twin) == []


@needs_ssh
def test_seal_signs_with_a_key_or_prints_the_command(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = ["deal", "seal", str(work / "pack.yaml"), "price-floor", "--value", "431250"]
    assert main([*base, "-o", str(tmp_path / "a")]) == 0
    shown = capsys.readouterr().out
    sealed = next((tmp_path / "a").glob("sealed_*.yaml"))
    assert f"ssh-keygen -Y sign -f <private key> -n smd-deal {sealed}" in shown
    assert not Path(f"{sealed}.sig").exists()
    key = key_of(work, "vera")
    assert main([*base, "-o", str(tmp_path / "b"), "--key", str(key)]) == 0
    capsys.readouterr()
    sealed = next((tmp_path / "b").glob("sealed_*.yaml"))
    pack = load_task(work / "pack.yaml")
    signing.verify_file(pack, "vera", sealed, None)
    with pytest.raises(RecordError, match="signature is not boris"):
        signing.verify_file(pack, "boris", sealed, None)


@needs_ssh
def test_a_signed_consent_is_logged_with_its_text_and_checked_again_at_the_verdict(
    work: Path, tmp_path: Path
) -> None:
    files = committed(work, tmp_path)
    ledger = tmp_path / "verdicts.yaml"
    note = consent_file(work, tmp_path, "vera", run=1)
    note.write_bytes(note.read_bytes().replace(b"\n", b"\r\n").rstrip() + b"  \r\n")
    sign_file(key_of(work, "vera"), note)  # the party signs the file as it is
    assert consent_cmd(work, ledger, "vera", note) == 0
    (entry,) = raw_entries(ledger)
    assert entry["signed"].encode("utf-8") == note.read_bytes()
    assert entry["evidence"] == sha256_bytes(entry["signed"].encode("utf-8"))
    assert entry["signature"].startswith("-----BEGIN SSH SIGNATURE-----")
    assert verdict(work, files, ledger, first=False) == 0
    assert verdicts(ledger)[0]["verdict"] == "met"


@needs_ssh
def test_a_consent_not_signed_by_its_party_is_refused(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    committed(work, tmp_path)
    ledger = tmp_path / "verdicts.yaml"
    seller_consent(work, ledger)
    before = len(entries(ledger))
    note = consent_file(
        work,
        tmp_path,
        "vera",
        run=1,
        commitments={"floor": "1" * 64, "ceiling": "2" * 64},
    )
    capsys.readouterr()
    sign_file(key_of(work, "boris"), note)  # the buyer signs the seller's consent
    assert consent_cmd(work, ledger, "vera", note) == 2
    assert "is not vera's" in capsys.readouterr().err
    Path(f"{note}.sig").unlink()  # unsigned
    assert consent_cmd(work, ledger, "vera", note) == 2
    assert "no signature" in capsys.readouterr().err
    other = tmp_path / "elsewhere.sig"  # --signature points at a signature of its own
    sign_file(key_of(work, "vera"), note)
    shutil.move(f"{note}.sig", other)
    assert consent_cmd(work, ledger, "vera", note, "--signature", str(other)) == 0
    assert len(entries(ledger)) == before + 1


@needs_ssh
def test_an_unsigned_consent_of_an_older_ledger_is_replaced_by_a_signed_one(
    work: Path, tmp_path: Path
) -> None:
    files = committed(work, tmp_path)
    ledger = tmp_path / "verdicts.yaml"
    note = consent_file(work, tmp_path, "vera", run=1)
    hand_consent(work, ledger, note)  # the consent of a 0.7.0 ledger: no signature
    assert verdict(work, files, ledger, first=False) == 2
    sign_file(key_of(work, "vera"), note)
    assert consent_cmd(work, ledger, "vera", note) == 0  # the same commitments
    assert consent_cmd(work, ledger, "vera", note) == 2  # but only once
    assert verdict(work, files, ledger, first=False) == 0
    assert verdicts(ledger)[0]["verdict"] == "met"


@needs_ssh
def test_a_signed_consent_that_the_ledger_cannot_keep_is_refused(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    committed(work, tmp_path)
    ledger = tmp_path / "verdicts.yaml"
    note = consent_file(work, tmp_path, "vera", run=1)
    flow = json.dumps(load_task(note), ensure_ascii=False)  # one line of flow YAML
    note.write_text(flow[:-1] + ', "note": "caf\u0085e"}', encoding="utf-8")
    sign_file(key_of(work, "vera"), note)
    capsys.readouterr()
    assert consent_cmd(work, ledger, "vera", note) == 2
    assert "does not survive being kept in the ledger" in capsys.readouterr().err
    assert not ledger.exists()


@needs_ssh
def test_a_seal_that_cannot_sign_still_gives_the_commitment_and_the_command(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    safe = tmp_path / "safe"
    args = ["deal", "seal", str(work / "pack.yaml"), "price-floor", "-o", str(safe)]
    args += ["--value", FLOOR, "--key", str(tmp_path / "no-such-key")]
    assert main(args) == 2
    shown = capsys.readouterr()
    (sealed,) = safe.glob("sealed_vera_price-floor.yaml")
    assert "commitment: " in shown.out and f"-n smd-deal {sealed}" in shown.out
    assert "not signed" in shown.err and FLOOR not in shown.out


@needs_ssh
def test_the_verdict_refuses_a_forged_unsigned_or_tampered_consent(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = committed(work, tmp_path)
    note = consent_file(work, tmp_path, "vera", run=1)
    text = note.read_text(encoding="utf-8")

    def attempt(name: str, signer: str | None, **extra: Any) -> str:
        ledger = tmp_path / f"{name}.yaml"
        if signer:  # the signature the operator puts in the entry
            sign_file(key_of(work, signer), note)
            extra = {
                "signed": text,
                "signature": Path(f"{note}.sig").read_text(),
                **extra,
            }
        hand_consent(work, ledger, note, **extra)
        capsys.readouterr()
        assert verdict(work, files, ledger, first=False) == 2
        assert verdicts(ledger) == []  # nothing is logged
        return capsys.readouterr().err

    assert "is not vera's" in attempt("forged", "boris")
    assert "is not signed" in attempt(
        "unsigned", None
    )  # an entry from before signatures
    # the operator swaps in a text of his own and fixes the hashes of the entry
    other = text.replace("price", "rent", 1)
    sign_file(key_of(work, "vera"), note)
    ledger = tmp_path / "tampered.yaml"
    hand_consent(
        work, ledger, note, signed=other, signature=Path(f"{note}.sig").read_text()
    )
    data = load_task(ledger)
    data["entries"][0]["evidence"] = sha256_bytes(other.encode("utf-8"))
    ledger.write_text(yaml.safe_dump(data), encoding="utf-8")
    rechain(ledger)
    capsys.readouterr()
    assert verdict(work, files, ledger, first=False) == 2
    assert "is not vera's" in capsys.readouterr().err
    assert verdicts(ledger) == []


@needs_ssh
def test_the_verdict_refuses_a_sealed_file_that_is_unsigned_or_signed_by_the_wrong_party(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = committed(work, tmp_path)
    ledger = tmp_path / "verdicts.yaml"
    seller_consent(work, ledger)
    Path(f"{files['floor']}.sig").rename(tmp_path / "floor.sig")
    capsys.readouterr()
    assert verdict(work, files, ledger) == 2
    assert "not signed by vera" in capsys.readouterr().err
    sign_file(key_of(work, "boris"), files["floor"])  # signed by the buyer
    assert verdict(work, files, ledger) == 2
    assert "is not vera's" in capsys.readouterr().err
    # --floor-sig names a signature kept elsewhere
    assert verdict(work, files, ledger, "--floor-sig", str(tmp_path / "floor.sig")) == 0
    assert verdicts(ledger)[-1]["verdict"] == "met"
    assert [e["type"] for e in entries(ledger)] == ["consent", "verdict"]


def test_a_missing_ssh_keygen_is_a_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: None)
    pack = {"members": [{"id": "vera", "ssh_key": "ssh-ed25519 AAAA"}]}
    with pytest.raises(RecordError, match="ssh-keygen was not found"):
        signing.verify_signature(pack, "vera", b"x", "sig", "a file")
