"""`smd deal verify --diff` against the ledger: a point shown `not_tested` over a
counted run is accepted only when the commitment really changed since the run,
and every bound item must be in the diff, so a holder cannot hide a logged
verdict from the parties' diff."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Callable

import yaml

from deal_helpers import needs_ssh, seal, set_answer, sign_answers
from smd_engine.task.model import load_task
from test_deal_verdict import diff_with_ledger, work  # noqa: F401  (the fixture)
from test_deal_verify import codes, made, run  # noqa: F401  (the fixture)

pytestmark = needs_ssh

PRICE = ("price-floor", "price-ceiling")
Run = Callable[..., tuple[int, str]]


def forged(
    tmp_path: Path, src: Path, change: Callable[[dict[str, Any]], None], n: int = 0
) -> Path:
    """A copy of the diff at `src` changed by the holder."""
    diff = load_task(src)
    change(diff)
    out = tmp_path / f"forged{n}.yaml"
    out.write_text(yaml.safe_dump(diff, sort_keys=False), encoding="utf-8")
    return out


def answers(work: Path, *more: Path) -> list[str]:
    """`--answers` with the parties' current files and `more` (one flag: a second
    `--answers` would replace the first list)."""
    now = [work / f"answers_{m}.yaml" for m in ("vera", "boris", "gleb")]
    return ["--answers", *(str(p) for p in (*now, *more))]


def hide(diff: dict[str, Any], who: list[str]) -> None:
    for p in diff["points"]:
        if p["id"] in PRICE:
            p["verdict"], p["changed_since_run"] = "not_tested", who


def test_a_logged_verdict_hidden_as_changed_since_run_fails(
    work: Path, tmp_path: Path, run: Run  # noqa: F811
) -> None:
    _, ledger = made(work, tmp_path)
    assert diff_with_ledger(work, ledger, tmp_path / "out") == 0
    bad = forged(tmp_path, tmp_path / "out/diff.yaml", lambda d: hide(d, ["vera"]))
    for plain in (False, True):  # the diff names the file the run recorded
        code, out = run(work, ledger, "--diff", str(bad), "--json", plain=plain)
        assert code == 1 and "diff_changed_same" in codes(out, "fail")
    broker = forged(
        tmp_path, tmp_path / "out/diff.yaml", lambda d: hide(d, ["gleb"]), 1
    )
    code, out = run(work, ledger, "--diff", str(broker), "--json")
    assert code == 1 and "diff_changed_who" in codes(out, "fail")


def test_a_new_answers_file_with_the_same_commitment_does_not_hide_the_verdict(
    work: Path, tmp_path: Path, run: Run  # noqa: F811
) -> None:
    _, ledger = made(work, tmp_path)
    shutil.copy(work / "answers_vera.yaml", tmp_path / "answers_vera_run.yaml")
    shutil.copy(work / "answers_vera.yaml.sig", tmp_path / "answers_vera_run.yaml.sig")
    set_answer(work, "vera", "sale-reason", {"value": "Health."})
    sign_answers(work)
    assert diff_with_ledger(work, ledger, tmp_path / "out") == 0
    bad = forged(tmp_path, tmp_path / "out/diff.yaml", lambda d: hide(d, ["vera"]))
    old = answers(work, tmp_path / "answers_vera_run.yaml")
    code, out = run(work, ledger, "--diff", str(bad), *old, "--json", plain=True)
    assert code == 1 and "diff_changed_same" in codes(out, "fail")
    code, out = run(work, ledger, "--diff", str(bad), "--json", plain=True)
    assert code == 0 and "diff_changed_nofile" in codes(out, "skip")


def test_a_real_change_since_the_run_passes(
    work: Path, tmp_path: Path, run: Run  # noqa: F811
) -> None:
    _, ledger = made(work, tmp_path)
    shutil.copy(work / "answers_vera.yaml", tmp_path / "answers_vera_run.yaml")
    shutil.copy(work / "answers_vera.yaml.sig", tmp_path / "answers_vera_run.yaml.sig")
    _, commit = seal(work, tmp_path / "again", "price-floor", "100000")
    set_answer(work, "vera", "price-floor", {"value": commit})
    sign_answers(work)
    assert diff_with_ledger(work, ledger, tmp_path / "out") == 0
    diff = str(tmp_path / "out/diff.yaml")
    old = answers(work, tmp_path / "answers_vera_run.yaml")
    code, out = run(work, ledger, "--diff", diff, *old, "--json", plain=True)
    assert code == 0, out
    assert codes(out, "ok").count("diff_changed_ok") == 2


def test_a_sealed_point_left_out_stripped_or_with_mixed_heads_fails(
    work: Path, tmp_path: Path, run: Run  # noqa: F811
) -> None:
    _, ledger = made(work, tmp_path)
    assert diff_with_ledger(work, ledger, tmp_path / "out") == 0
    src = tmp_path / "out/diff.yaml"

    def drop(d: dict[str, Any]) -> None:
        d["points"] = [p for p in d["points"] if p["id"] != "price-floor"]

    def strip(d: dict[str, Any]) -> None:
        for p in d["points"]:
            if p["id"] == "price-floor":
                del p["sealed"]

    def mix(d: dict[str, Any]) -> None:
        for p in d["points"]:
            if p["id"] == "price-floor":
                del p["ledger_head"]
                p["verdict"] = "not_tested"

    for n, (change, code_name) in enumerate(
        ((drop, "diff_missing"), (strip, "diff_point_shape"), (mix, "diff_head_mixed"))
    ):
        code, out = run(
            work, ledger, "--diff", str(forged(tmp_path, src, change, n)), "--json"
        )
        assert code == 1 and code_name in codes(out, "fail"), (code_name, out)


def test_a_made_up_answers_file_an_old_or_no_head_or_a_false_view_fails(
    work: Path, tmp_path: Path, run: Run  # noqa: F811
) -> None:
    _, ledger = made(work, tmp_path)
    assert diff_with_ledger(work, ledger, tmp_path / "out") == 0
    src = tmp_path / "out/diff.yaml"
    first = load_task(ledger)["entries"][0]["sha256"]  # the consent, before the run

    def fake_file(d: dict[str, Any]) -> None:
        hide(d, ["vera"])
        for f in d["answers_files"]:
            if f["member"] == "vera":
                f["sha256"] = "e" * 64

    def old_head(d: dict[str, Any]) -> None:
        for p in d["points"]:
            if p["id"] in PRICE:
                p["verdict"], p["ledger_head"] = "not_tested", first

    def no_head(d: dict[str, Any]) -> None:
        for p in d["points"]:
            if p["id"] in PRICE:
                p["verdict"] = "not_tested"
                del p["ledger_head"]

    def ghost_view(d: dict[str, Any]) -> None:
        d["view"] = {"position": "ghost", "diff": "0" * 64}
        d["points"] = [p for p in d["points"] if p["id"] not in PRICE]

    for n, (change, code_name) in enumerate(
        (
            (fake_file, "diff_changed_file"),
            (old_head, "diff_stale"),
            (no_head, "diff_stale"),
            (ghost_view, "diff_view_bad"),
        )
    ):
        bad = str(forged(tmp_path, src, change, n))
        code, out = run(work, ledger, "--diff", bad, "--json")
        assert code == 1 and code_name in codes(out, "fail"), (code_name, out)
