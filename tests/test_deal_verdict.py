"""Deal mode, the verdict: `smd deal verdict` behind the Comparator protocol, the
hash-chained ledger, the run cap with both parties' consent, and the verdict on
the pages, on the invented example in cases/example/deal/."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from deal_helpers import (
    CEILING,
    FLOOR,
    MEMBERS,
    by_id,
    copy_deal,
    edit_pack,
    seal,
    set_answer,
)
from smd_engine.cli import main
from smd_engine.deal import ledger as led
from smd_engine.deal.overlap import Comparator, LocalComparator, comparator_for
from smd_engine.deal.sealed import commitment_of
from smd_engine.deal.verdict import run_verdict
from smd_engine.records import RecordError
from smd_engine.task.model import load_task, sha256_file


@pytest.fixture()
def work(tmp_path: Path) -> Path:
    return copy_deal(tmp_path / "deal")


def committed(
    work: Path, tmp_path: Path, floor: str | None = FLOOR, ceiling: str | None = CEILING
) -> dict[str, Path]:
    """Seal the given numbers and write the commitments into the answers files."""
    files: dict[str, Path] = {}
    for side, item, member, value in (
        ("floor", "price-floor", "vera", floor),
        ("ceiling", "price-ceiling", "boris", ceiling),
    ):
        if value is not None:
            files[side], commit = seal(work, tmp_path, item, value)
            set_answer(work, member, item, {"value": commit})
    return files


def verdict(
    work: Path, files: dict[str, Path], ledger: Path, *extra: str, first: bool = True
) -> int:
    """Run `smd deal verdict`. While no run has been made, the seller consents to
    run 1 first (naming the buyer and the commitments now in the answers) unless
    `first` is false: every run against the sealed floor needs his consent."""
    if first and not [
        e for e in raw_entries(ledger) if e.get("run") and e["type"] == "verdict"
    ]:
        seller_consent(work, ledger)
    args = [
        "deal",
        "verdict",
        str(work / "pack.yaml"),
        "price",
        "--ledger",
        str(ledger),
    ]
    args += ["--answers", *(str(work / f"answers_{m}.yaml") for m in MEMBERS)]
    if not ledger.exists():
        args.append("--new")
    for side, path in files.items():
        args += [f"--{side}", str(path)]
    return main([*args, "--date", "2026-11-10", *extra])


def diff_with_ledger(work: Path, ledger: Path, out: Path) -> int:
    answers = [str(work / f"answers_{m}.yaml") for m in MEMBERS]
    return main(
        ["task", "diff", str(work / "pack.yaml"), *answers]
        + ["-o", str(out), "--ledger", str(ledger)]
    )


def entries(ledger: Path) -> list[dict[str, Any]]:
    return load_task(ledger, "task_verdicts")["entries"]


def verdicts(ledger: Path) -> list[dict[str, Any]]:
    return [e for e in entries(ledger) if e["type"] == "verdict"]


def raw_entries(ledger: Path) -> list[dict[str, Any]]:
    return load_task(ledger)["entries"] if ledger.exists() else []


def seller_consent(work: Path, ledger: Path) -> None:
    """The seller's consent to run 1 for the commitments now in the answers files,
    unless the ledger holds it already; it starts the ledger when there is none."""
    tmp = ledger.parent / "consents"
    tmp.mkdir(exist_ok=True)
    note = consent_file(work, tmp, "vera", run=1)
    commits = load_task(note)["commitments"]
    mine = [
        e
        for e in raw_entries(ledger)
        if e["type"] == "consent" and e["run"] == 1 and e["by"] == "vera"
    ]
    if mine and mine[-1]["commitments"] == commits:
        return
    args = [
        "deal",
        "consent",
        str(work / "pack.yaml"),
        "price",
        "--ledger",
        str(ledger),
    ]
    args += ["--member", "vera", "--evidence", str(note), "--date", "2026-11-09"]
    assert main(args + ([] if ledger.exists() else ["--new"])) == 0


def consent_file(work: Path, tmp_path: Path, member: str, **change: Any) -> Path:
    """The task_consent file of a party to run 2 (`run=1` for the seller's consent
    to the first), naming the buyer and the two commitments now in the answers
    files; `change` overrides a field."""
    commits = {
        side: load_task(work / f"answers_{who}.yaml")["answers"]
        .get(item, {})
        .get("value", "0" * 64)
        for side, who, item in (
            ("floor", "vera", "price-floor"),
            ("ceiling", "boris", "price-ceiling"),
        )
    }
    data: dict[str, Any] = {
        "record": "task_consent",
        "deal": "bakery-2026",
        "pack": {"id": "bakery-sale"},
        "topic": "price",
        "run": 2,
        "member": member,
        "buyer": "boris",
        "commitments": commits,
        **change,
    }
    note = tmp_path / f"consent_{member}.yaml"
    note.write_text(yaml.safe_dump(data), encoding="utf-8")
    return note


def consent(work: Path, tmp_path: Path, ledger: Path, member: str, run: int = 2) -> int:
    note = consent_file(work, tmp_path, member, run=run)
    return main(
        ["deal", "consent", str(work / "pack.yaml"), "price", "--ledger", str(ledger)]
        + ["--member", member, "--evidence", str(note), "--date", "2026-11-11"]
    )


def test_a_floor_within_the_ceiling_is_met_and_the_ledger_holds_no_number(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = committed(work, tmp_path)
    ledger = tmp_path / "verdicts.yaml"
    assert verdict(work, files, ledger) == 0
    shown = capsys.readouterr()
    assert "price: terms met - bargain at the in-person meeting" in shown.out
    (entry,) = verdicts(ledger)
    assert (entry["verdict"], entry["run"], entry["method"]) == ("met", 1, "local-v1")
    assert (entry["floor_member"], entry["ceiling_member"]) == ("vera", "boris")
    secrets = [FLOOR, CEILING] + [
        load_task(p, "task_sealed")["salt"] for p in files.values()
    ]
    for text in (ledger.read_text(encoding="utf-8"), shown.out, shown.err):
        assert not [s for s in secrets if s in text]


def test_a_floor_above_the_ceiling_is_not_met_and_still_no_stop(
    work: Path, tmp_path: Path
) -> None:
    files = committed(work, tmp_path, floor="600000", ceiling="512750")
    ledger = tmp_path / "verdicts.yaml"
    assert verdict(work, files, ledger) == 0
    assert verdicts(ledger)[0]["verdict"] == "not_met"
    out = tmp_path / "out"
    assert diff_with_ledger(work, ledger, out) == 0
    point = by_id(load_task(out / "diff.yaml"))["price-floor"]
    assert (point["verdict"], point["route"]) == ("not_met", "price_meeting")


def test_a_missing_ceiling_is_not_tested_and_does_not_use_a_run(
    work: Path, tmp_path: Path
) -> None:
    files = committed(work, tmp_path, ceiling=None)
    ledger = tmp_path / "verdicts.yaml"
    assert verdict(work, files, ledger) == 0
    (entry,) = verdicts(ledger)
    assert (entry["verdict"], entry["reason"]) == ("not_tested", "no_ceiling")
    assert "run" not in entry
    # the buyer seals later, at the last stage: the first run is still free
    later = committed(work, tmp_path / "later", floor=None)
    assert verdict(work, {"floor": files["floor"], **later}, ledger) == 0
    assert [e["verdict"] for e in verdicts(ledger)] == ["not_tested", "met"]


def test_a_commitment_that_fails_or_another_unit_is_not_tested(
    work: Path, tmp_path: Path
) -> None:
    files = committed(work, tmp_path)
    ledger = tmp_path / "verdicts.yaml"
    # a number changed after the commitment: the sealed file no longer matches
    other = yaml.safe_load(files["ceiling"].read_text(encoding="utf-8"))
    other["value"] = 999999
    forged = tmp_path / "forged.yaml"
    forged.write_text(yaml.safe_dump(other), encoding="utf-8")
    assert verdict(work, {**files, "ceiling": forged}, ledger) == 0
    # the buyer's file given as the seller's
    assert verdict(work, {**files, "floor": files["ceiling"]}, ledger) == 0
    # a unit other than the item's
    other["value"], other["unit"] = 1, "USD"
    forged.write_text(yaml.safe_dump(other), encoding="utf-8")
    assert verdict(work, {**files, "ceiling": forged}, ledger) == 0
    assert [(e["verdict"], e["reason"]) for e in verdicts(ledger)] == [
        ("not_tested", "bad_commitment"),
        ("not_tested", "bad_commitment"),
        ("not_tested", "unit_mismatch"),
    ]
    assert (
        led.tested_runs(led.load_ledger(ledger, load_task(work / "pack.yaml")), "price")
        == 0
    )


def test_a_second_run_needs_both_parties_consent_and_no_run_beyond_two(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = committed(work, tmp_path)
    ledger = tmp_path / "verdicts.yaml"
    assert verdict(work, files, ledger) == 0
    assert verdict(work, files, ledger) == 0  # no consent at all
    assert consent(work, tmp_path, ledger, "vera") == 0
    assert verdict(work, files, ledger) == 0  # the seller's consent alone is not enough
    assert consent(work, tmp_path, ledger, "boris") == 0
    assert verdict(work, files, ledger) == 0
    got = [(e["type"], e.get("verdict"), e.get("reason")) for e in entries(ledger)]
    assert got == [
        ("consent", None, None),  # the seller's, to run 1
        ("verdict", "met", None),
        ("verdict", "not_tested", "consent_missing"),
        ("consent", None, None),
        ("verdict", "not_tested", "consent_missing"),
        ("consent", None, None),
        ("verdict", "met", None),
    ]
    assert [e["run"] for e in entries(ledger) if e.get("verdict") == "met"] == [1, 2]
    # the hard maximum: a third run is refused, with or without consent
    assert verdict(work, files, ledger) == 0
    assert entries(ledger)[-1]["reason"] == "cap_reached"
    capsys.readouterr()
    assert consent(work, tmp_path, ledger, "vera") == 2
    assert "maximum of 2 runs" in capsys.readouterr().err


def test_consent_comes_from_a_party_and_only_after_a_first_run(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = committed(work, tmp_path, ceiling=None)
    ledger = tmp_path / "verdicts.yaml"
    assert verdict(work, files, ledger) == 0  # not tested: no run is used
    capsys.readouterr()
    assert consent(work, tmp_path, ledger, "boris", run=1) == 2
    assert "needs the seller's consent only" in capsys.readouterr().err
    later = committed(work, tmp_path / "later", floor=None)
    assert verdict(work, {"floor": files["floor"], **later}, ledger) == 0
    capsys.readouterr()
    assert consent(work, tmp_path, ledger, "gleb") == 2  # the broker is no party
    assert "not a party" in capsys.readouterr().err
    assert consent(work, tmp_path, ledger, "vera") == 0
    assert consent(work, tmp_path, ledger, "vera") == 2
    assert "consented to run 2 already" in capsys.readouterr().err


def test_the_sealed_files_are_not_opened_once_the_cap_is_reached(
    work: Path, tmp_path: Path
) -> None:
    files = committed(work, tmp_path)
    ledger = tmp_path / "verdicts.yaml"
    for member in ("vera", "boris"):
        assert verdict(work, files, ledger) == 0
        consent(work, tmp_path, ledger, member)
    assert verdict(work, files, ledger) == 0
    gone = {side: tmp_path / "gone" for side in files}
    assert verdict(work, gone, ledger) == 0
    assert entries(ledger)[-1]["reason"] == "cap_reached"


def test_an_edited_or_cut_ledger_is_detected(work: Path, tmp_path: Path) -> None:
    files = committed(work, tmp_path)
    ledger = tmp_path / "verdicts.yaml"
    assert verdict(work, files, ledger) == 0
    assert verdict(work, files, ledger) == 0
    out = tmp_path / "out"
    assert diff_with_ledger(work, ledger, out) == 0
    whole = by_id(load_task(out / "diff.yaml"))
    assert whole["price-floor"]["verdict"] == "met"
    head = whole["price-floor"]["ledger_head"]
    assert (
        head
        == whole["price-ceiling"]["ledger_head"]
        == led.load_ledger(ledger, load_task(work / "pack.yaml"))["entries"][-1][
            "sha256"
        ]
    )
    # cut the last entry: the chain is still whole, but the head is not the diff's
    cut = load_task(ledger)
    cut["entries"].pop()
    ledger.write_text(yaml.safe_dump(cut), encoding="utf-8")
    assert diff_with_ledger(work, ledger, out) == 2  # diff.yaml differs: refused
    # edit an entry: the chain breaks
    edited = load_task(ledger)
    edited["entries"][1]["verdict"] = "not_met"
    ledger.write_text(yaml.safe_dump(edited), encoding="utf-8")
    with pytest.raises(RecordError, match="chain is broken: entry 2 was edited"):
        led.load_ledger(ledger, load_task(work / "pack.yaml"))
    assert verdict(work, files, ledger) == 2


def test_the_comparator_can_be_replaced_without_changing_the_formats(
    work: Path, tmp_path: Path
) -> None:
    assert isinstance(comparator_for("local-v1"), LocalComparator)
    with pytest.raises(RecordError, match="not known"):
        comparator_for("mpc-v9")

    class Never:
        method = "never-v0"

        def compare(self, floor: float, ceiling: float) -> bool:
            return False

    plug: Comparator = Never()
    files = committed(work, tmp_path)
    pack = load_task(work / "pack.yaml")
    sha = load_task(work / "answers_vera.yaml")["pack"]["sha256"]
    answers = {m: load_task(work / f"answers_{m}.yaml") for m in ("vera", "boris")}
    sealed = {s: load_task(p, "task_sealed") for s, p in files.items()}
    openers = {s: (lambda r=r: r) for s, r in sealed.items()}
    ledger = {
        "record": "task_verdicts",
        "schema_version": "0.1",
        "deal": "bakery-2026",
        "pack": {"id": "bakery-sale"},
        "entries": [],
    }
    commitments = {s: commitment_of(r) for s, r in sealed.items()}
    led.append_entry(
        ledger,
        {
            "type": "consent",
            "date": "2026-11-09",
            "topic": "price",
            "run": 1,
            "by": "vera",
            "buyer": "boris",
            "evidence": "0" * 64,
            "commitments": commitments,
        },
    )
    entry = run_verdict(
        pack, sha, "price", answers, openers, ledger, "2026-11-10", plug
    )
    assert (entry["verdict"], entry["method"]) == ("not_met", "never-v0")
    assert commitment_of(sealed["floor"]) == entry["commitments"]["floor"]


def test_the_verdict_reads_in_russian_on_the_pages(work: Path, tmp_path: Path) -> None:
    edit_pack(work, lambda p: p.update(lang="ru"))
    files = committed(work, tmp_path)
    ledger = tmp_path / "verdicts.yaml"
    assert verdict(work, files, ledger) == 0
    out = tmp_path / "out"
    assert diff_with_ledger(work, ledger, out) == 0
    assert (
        main(
            [
                "task",
                "agenda",
                str(out / "diff.yaml"),
                "--members",
                "vera,boris,gleb",
                "-o",
                str(out / "agenda.md"),
            ]
        )
        == 0
    )
    phrase = "цена: условия сошлись — торг на личной встрече"
    for name in ("diff.md", "diff.html", "agenda.md"):
        assert phrase in (out / name).read_text(encoding="utf-8"), name
    # the seller's view has his floor point and the verdict, not the buyer's point
    assert (
        main(
            [
                "deal",
                "views",
                str(work / "pack.yaml"),
                str(out / "diff.yaml"),
                "-o",
                str(out / "v"),
            ]
        )
        == 0
    )
    seller = by_id(load_task(out / "v" / "diff.seller.yaml"))
    assert seller["price-floor"]["verdict"] == "met" and "price-ceiling" not in seller


def test_a_ledger_that_does_not_exist_is_not_started_without_new(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = committed(work, tmp_path)
    ledger = tmp_path / "verdicts.yaml"
    assert verdict(work, files, ledger) == 0
    # a mistyped path would start a ledger with a run count of zero: refused
    other = tmp_path / "other.yaml"
    capsys.readouterr()
    args = ["deal", "verdict", str(work / "pack.yaml"), "price", "--ledger", str(other)]
    args += ["--answers", *(str(work / f"answers_{m}.yaml") for m in MEMBERS)]
    assert main(args) == 2
    assert "no ledger there" in capsys.readouterr().err and not other.exists()
    # and --new does not take over a ledger that is there
    assert main([*args[:-4], "--ledger", str(ledger), *args[-4:], "--new"]) == 2
    assert "drop --new" in capsys.readouterr().err
    assert len(entries(ledger)) == 2  # the seller's consent and the verdict


def test_a_consent_file_must_be_the_partys_for_this_run_and_commitments(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = committed(work, tmp_path, floor="600000", ceiling="512750")
    ledger = tmp_path / "verdicts.yaml"
    assert verdict(work, files, ledger) == 0
    base = [
        "deal",
        "consent",
        str(work / "pack.yaml"),
        "price",
        "--ledger",
        str(ledger),
    ]

    def attempt(member: str, evidence: Path) -> int:
        return main([*base, "--member", member, "--evidence", str(evidence)])

    capsys.readouterr()
    assert attempt("vera", work / "pack.yaml") == 2  # any file will not do
    vera, boris = (consent_file(work, tmp_path, m) for m in ("vera", "boris"))
    assert attempt("boris", vera) == 2  # one party's file is not the other's
    assert attempt("vera", consent_file(work, tmp_path, "vera", run=3)) == 2
    assert attempt("vera", consent_file(work, tmp_path, "vera", topic="rent")) == 2
    assert "not a consent of boris to run 2" in capsys.readouterr().err
    assert len(entries(ledger)) == 2
    vera = consent_file(work, tmp_path, "vera")  # the bad ones wrote over the file
    assert attempt("vera", vera) == 0 and attempt("boris", boris) == 0
    (entry,) = [e for e in entries(ledger) if e.get("by") == "vera" and e["run"] == 2]
    assert entry["evidence"] == sha256_file(vera)
    assert set(entry["commitments"]) == {"floor", "ceiling"}


def test_a_commitment_changed_after_the_consent_gives_no_second_run(
    work: Path, tmp_path: Path
) -> None:
    files = committed(work, tmp_path, floor="600000", ceiling="512750")
    ledger = tmp_path / "verdicts.yaml"
    assert verdict(work, files, ledger) == 0
    for member in ("vera", "boris"):
        assert consent(work, tmp_path, ledger, member) == 0
    # the seller seals a lower floor after both consented: not what they agreed to
    lower, commit = seal(work, tmp_path / "again", "price-floor", "500000")
    set_answer(work, "vera", "price-floor", {"value": commit})
    assert verdict(work, {**files, "floor": lower}, ledger) == 0
    assert entries(ledger)[-1]["reason"] == "commitment_changed"
    assert (
        led.tested_runs(led.load_ledger(ledger, load_task(work / "pack.yaml")), "price")
        == 1
    )
    # the buyer sees the new commitment and consents again, naming it
    assert consent(work, tmp_path, ledger, "vera") == 0
    assert consent(work, tmp_path, ledger, "boris") == 0
    assert verdict(work, {**files, "floor": lower}, ledger) == 0
    assert (entries(ledger)[-1]["verdict"], entries(ledger)[-1]["run"]) == ("met", 2)


def test_the_diff_flags_a_commitment_changed_since_the_last_run(
    work: Path, tmp_path: Path
) -> None:
    files = committed(work, tmp_path)
    ledger = tmp_path / "verdicts.yaml"
    assert verdict(work, files, ledger) == 0
    out = tmp_path / "out"
    assert diff_with_ledger(work, ledger, out) == 0
    assert "changed_since_run" not in by_id(load_task(out / "diff.yaml"))["price-floor"]
    _, commit = seal(work, tmp_path / "again", "price-floor", "100000")
    set_answer(work, "vera", "price-floor", {"value": commit})
    out = tmp_path / "out2"  # the answers changed, so this is another diff
    assert diff_with_ledger(work, ledger, out) == 0
    pts = by_id(load_task(out / "diff.yaml"))
    for pid in ("price-floor", "price-ceiling"):  # the topic's flag, not one point's
        assert (pts[pid]["verdict"], pts[pid]["changed_since_run"]) == (
            "not_tested",
            ["vera"],
        )
    assert "Commitment changed since the last run" in (out / "diff.md").read_text(
        encoding="utf-8"
    )


def test_the_diff_after_the_verdict_replaces_the_diff_before_it(
    work: Path, tmp_path: Path
) -> None:
    files = committed(work, tmp_path)
    ledger = tmp_path / "verdicts.yaml"
    out = tmp_path / "out"
    answers = [str(work / f"answers_{m}.yaml") for m in MEMBERS]
    assert (
        main(["task", "diff", str(work / "pack.yaml"), *answers, "-o", str(out)]) == 0
    )
    assert verdict(work, files, ledger) == 0
    assert diff_with_ledger(work, ledger, out) == 0  # the documented cycle
    assert by_id(load_task(out / "diff.yaml"))["price-floor"]["verdict"] == "met"
    # a diff that carries a verdict is not replaced by one that does not
    assert (
        main(["task", "diff", str(work / "pack.yaml"), *answers, "-o", str(out)]) == 2
    )
    # nor is a file with something else written into it, a model note for one
    target = out / "diff.yaml"
    target.write_text(target.read_text(encoding="utf-8") + "# note\n", encoding="utf-8")
    assert verdict(work, files, ledger) == 0
    assert diff_with_ledger(work, ledger, out) == 2


def test_every_run_against_the_floor_needs_the_sellers_consent_naming_the_buyer(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = committed(work, tmp_path)
    ledger = tmp_path / "verdicts.yaml"
    # no consent: nothing is compared, no run is used, and the ledger says why
    assert verdict(work, files, ledger, first=False) == 0
    (entry,) = verdicts(ledger)
    assert (entry["verdict"], entry["reason"]) == ("not_tested", "consent_missing")
    # the buyer cannot give the seller's consent, nor can a file name another buyer
    capsys.readouterr()
    assert consent(work, tmp_path, ledger, "boris", run=1) == 2
    assert "seller's consent only" in capsys.readouterr().err
    other = consent_file(work, tmp_path, "vera", run=1, buyer="gleb")
    args = [
        "deal",
        "consent",
        str(work / "pack.yaml"),
        "price",
        "--ledger",
        str(ledger),
    ]
    assert main([*args, "--member", "vera", "--evidence", str(other)]) == 2
    assert "against buyer boris" in capsys.readouterr().err
    # the seller's consent, with the buyer named, allows the run; the cap stays
    assert consent(work, tmp_path, ledger, "vera", run=1) == 0
    consented = [e for e in entries(ledger) if e["type"] == "consent"]
    assert [(e["by"], e["buyer"], e["run"]) for e in consented] == [
        ("vera", "boris", 1)
    ]
    assert verdict(work, files, ledger, first=False) == 0
    assert verdicts(ledger)[-1]["verdict"] == "met"
    assert verdict(work, files, ledger, first=False) == 0
    assert verdicts(ledger)[-1]["reason"] == "consent_missing"  # run 2 needs both
