from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from smd_engine.cli import main
from smd_engine.eval import evaluate, format_result, match_theses, parse_cite
from smd_engine.records import load_record

GOLDEN = Path(__file__).resolve().parents[1] / "cases" / "example" / "golden"
EXPECTED = GOLDEN / "bakeries-c2-expected.board.yaml"


@pytest.fixture
def expected() -> dict[str, Any]:
    return load_record(EXPECTED)


def test_eval_counts_and_thresholds(expected: dict[str, Any]) -> None:
    n = len([e for e in expected["elements"] if e["kind"] != "entry"])
    same = evaluate(expected, expected, min_agreement=n, max_only_expected=0)
    assert same.counts["agreement"] == n and same.failures == []
    worse = copy.deepcopy(expected)
    worse["elements"] = [e for e in worse["elements"] if e["id"] != "fn-logistics"]
    got = evaluate(worse, expected, min_agreement=n, max_only_expected=0)
    assert got.counts["only_b"] == 1 and got.counts["agreement"] == n - 1
    assert len(got.failures) == 2


def test_theses_match_by_source_address(expected: dict[str, Any]) -> None:
    run = copy.deepcopy(expected)
    by_id = {t["id"]: t for t in run["theses"]}
    by_id["T3"]["cites"] = ["s3#t=00:08:35"]  # 25 s later: the same utterance
    by_id["T4"]["cites"] = ["s3#t=00:12:30"]  # 60 s later: another one
    by_id["T5"]["cites"] = ["s4#t=00:14:20"]  # same time, another source
    matched, only_run, only_expected = match_theses(run, expected)
    ids = {m.expected: m.run for m in matched}
    assert ids["T3"] == "T3" and "T4" not in ids and "T5" not in ids
    assert {t for t, _ in only_run} == {"T4", "T5"}
    assert {t for t, _ in only_expected} == {"T4", "T5"}
    assert parse_cite("fp#r=2&t=00:00:10").params == (("r", "2"),)
    assert parse_cite("gs#p=9").seconds is None


def test_cli_eval(capsys: pytest.CaptureFixture[str]) -> None:
    path = str(EXPECTED)
    assert main(["eval", path, path]) == 0
    out = capsys.readouterr().out
    assert out.startswith("agreement 13 · refinement 0 · conflict 0")
    assert "theses matched by cites (9)" in out
    assert main(["eval", path, path, "--min-agreement", "999"]) == 1
    assert "FAIL: agreement 13 is below the minimum 999" in capsys.readouterr().out


def test_output_has_run_blocks_and_compares_k_and_h(expected: dict[str, Any]) -> None:
    run = copy.deepcopy(expected)
    run["run"] = {"procedure": "theses-to-board", "model": "m1"}
    run["qualifications"] = run["qualifications"][:1]
    run["hypotheses"][1]["assumes"] = "Nothing alike at all, wholly other words."
    result = evaluate(run, expected)
    assert result.qualifications is not None and result.hypotheses is not None
    assert result.qualifications.matched == [("K1", "K1")]
    assert result.qualifications.only_expected == ["K2"]
    assert result.hypotheses.matched == [("H1", "H1")]
    assert result.hypotheses.only_run == ["H2"]
    assert result.hypotheses.only_expected == ["H2"]
    out = format_result(result)
    assert "run: procedure=theses-to-board, model=m1" in out
    assert "expected: procedure=theses-to-board, version=0.3.3" in out
    assert "qualifications only in the expected record (1):\n  K2" in out
    assert "hypotheses matched by wording (1):\n  H1 = H1" in out


def test_output_prints_the_v2_run_stamp(expected: dict[str, Any]) -> None:
    run = copy.deepcopy(expected)
    sha = "a" * 64
    run["run"] = {
        "procedure": "theses-to-board",
        "pack_sha256": sha,
        "inputs": {"s3": sha},
        "temperature": 0.2,
        "sample": 2,
    }
    out = format_result(evaluate(run, expected))
    assert (
        f"run: procedure=theses-to-board, pack_sha256={sha}, inputs={{s3: {sha}}}, "
        "temperature=0.2, sample=2"
    ) in out
