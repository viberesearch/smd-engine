from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from smd_engine.agree import agree, alpha_nominal, format_result, reading
from smd_engine.cli import main
from smd_engine.records import load_record

GOLDEN = Path(__file__).resolve().parents[1] / "cases" / "example" / "golden"
EXPECTED = GOLDEN / "bakeries-c2-expected.board.yaml"
N = None


def test_alpha_krippendorff_2011_example() -> None:
    # Krippendorff (2011), "Computing Krippendorff's Alpha-Reliability": four
    # observers, twelve units, nominal values 1 to 5, gaps marked N; alpha = 0.743.
    rows = [
        [1, 2, 3, 3, 2, 1, 4, 1, 2, N, N, N],
        [1, 2, 3, 3, 2, 2, 4, 1, 2, 5, N, 3],
        [N, 3, 3, 3, 2, 3, 4, 2, 2, 5, 1, N],
        [1, 2, 3, 3, 2, 4, 4, 1, 2, 5, 1, N],
    ]
    got = alpha_nominal(list(zip(*rows)))
    # unit 10 holds (5, 5) and unit 11 holds (1, 1) in two raters, unit 12 holds
    # one value and is not pairable: 11 pairable units, 40 values
    assert (got.units, got.pairable_units, got.pairable_values) == (12, 11, 40)
    assert got.alpha is not None and round(got.alpha, 3) == 0.743


def test_alpha_by_hand_two_raters() -> None:
    # Units (a, a), (b, b), (a, b). Each unit has m = 2, so each ordered pair counts 1.
    # D_o = o_ab + o_ba = 2. n = 6, n_a = n_b = 3, D_e = (6*6 - 9 - 9) / 5 = 3.6.
    # alpha = 1 - 2 / 3.6 = 4/9.
    got = alpha_nominal([["a", "a"], ["b", "b"], ["a", "b"]])
    assert got.alpha == pytest.approx(4 / 9)


def test_alpha_by_hand_three_raters_with_a_gap() -> None:
    # Units (x, x, y), (y, y, y), (x, y, N). Pairable values: 3 + 3 + 2 = 8.
    # D_o = (9 - 5) / 2 + 0 + (4 - 2) / 1 = 2 + 2 = 4. n_x = 3, n_y = 5.
    # D_e = (64 - 9 - 25) / 7 = 30 / 7. alpha = 1 - 4 * 7 / 30 = 1 / 15.
    got = alpha_nominal([["x", "x", "y"], ["y", "y", "y"], ["x", "y", N]])
    assert got.alpha == pytest.approx(1 / 15)


def test_alpha_perfect_agreement_is_one() -> None:
    got = alpha_nominal([["a", "a", "a"], ["b", "b", "b"], ["c", "c", N]])
    assert got.alpha == 1.0


def test_alpha_ignores_units_with_fewer_than_two_values() -> None:
    with_lone = alpha_nominal([["a", "a"], ["b", "b"], ["a", "b"], ["c", N]])
    without = alpha_nominal([["a", "a"], ["b", "b"], ["a", "b"]])
    assert with_lone.alpha == without.alpha
    assert with_lone.units == 4 and with_lone.pairable_units == 3


def test_alpha_is_undefined_with_one_value_or_no_pairs() -> None:
    one = alpha_nominal([["a", "a"], ["a", "a", "a"]])
    assert one.alpha is None and "only one value" in one.why_not
    lone = alpha_nominal([["a", N], [N, "b"], [N, N]])
    assert lone.alpha is None and "no unit has two values" in lone.why_not


def test_reading_follows_the_conventional_cut_offs() -> None:
    assert reading(0.800) == "reliable" and reading(1.0) == "reliable"
    assert reading(0.799) == "tentative" and reading(0.667) == "tentative"
    assert reading(0.666) == "not reliable" and reading(-0.1) == "not reliable"
    assert reading(None) == "n/a"


def _runs() -> list[dict[str, Any]]:
    """Three runs on the golden record: A is the record itself.

    B moves T4's cite 20 s (still the same utterance), drops T9, adds T10 at
    s3#t=00:40:00, relabels T3 belt, and changes the `of` and the move of two
    elements. C relabels T5 belt, drops no thesis but T10, and gives T4 another
    move op.
    """
    a = load_record(EXPECTED)
    a["run"] = {"procedure": "theses-to-board", "sample": 1}
    a["theses"][3]["move"] = {"op": "glue", "from": ["f-new"], "status": "candidate"}
    b, c = copy.deepcopy(a), copy.deepcopy(a)
    b["run"]["sample"], c["run"]["sample"] = 2, 3
    by_b = {t["id"]: t for t in b["theses"]}
    by_c = {t["id"]: t for t in c["theses"]}
    by_b["T3"]["belt"] = "mk"
    by_b["T4"]["cites"] = ["s3#t=00:11:50"]
    b["theses"] = [t for t in b["theses"] if t["id"] != "T9"]
    b["theses"].append(
        {**by_b["T1"], "id": "T10", "cites": ["s3#t=00:40:00"], "belt": "m"}
    )
    by_c["T5"]["belt"] = "md"
    by_c["T4"]["move"]["op"] = "adjoin"
    for rec, of in ((b, "time"), (c, "position")):
        el = {e["id"]: e for e in rec["elements"]}
        el["gap-risk"]["of"] = of
    return [a, b, c]


def test_agree_end_to_end_on_three_runs() -> None:
    result = agree(_runs(), ["a", "b", "c"])
    fields = {f.name: f for f in result.fields}
    # belt, hand-worked: eight units have all three values (T1..T8), T9 has two (A and C).
    # Disagreeing units: T3 {md 2, mk 1} and T5 {mk 2, md 1}, each (9 - 5) / 2 = 2,
    # so D_o = 4. n = 26; n_md = 11, n_mk = 9, n_m = 6; D_e = (676 - 238) / 25 = 17.52.
    # alpha = 1 - 4 / 17.52. T10 has one value and is not pairable.
    belt = fields["belt"].alpha
    assert (belt.units, belt.pairable_units, belt.pairable_values) == (10, 9, 26)
    assert belt.alpha == pytest.approx(1 - 4 / 17.52)
    assert fields["kind"].alpha.alpha == 1.0 and fields["status"].alpha.alpha == 1.0
    # the move op is on T4 only: {glue 2, adjoin 1} is a lone unit, alpha 0
    assert fields["op"].alpha.alpha == pytest.approx(0.0)
    assert fields["op"].alpha.units == 1
    # `of` on a thesis: T7 only, and all three runs agree on a single value
    assert fields["of"].alpha.alpha is None
    # elements: gap-risk is the one with `of`: {position 2, time 1}
    assert fields["element.of"].alpha.alpha == pytest.approx(0.0)
    assert fields["element.kind"].alpha.alpha == 1.0  # 13 elements, 39 values
    cov = result.coverage
    assert (cov.addresses, cov.by_all, cov.by_some, cov.by_one) == (10, 8, 1, 1)
    assert cov.one_run_only == [("s3#t=00:40:00", "b")]
    assert result.warnings == [
        "no record has run.pack_sha256",
        "no record has run.inputs",
    ]


def test_agree_text_output() -> None:
    out = format_result(agree(_runs(), ["a", "b", "c"], ["belt", "of"]))
    assert "belt" in out and "0.772" in out and "tentative" in out
    assert "of: alpha is n/a, only one value occurs in all units" in out
    assert "found by all runs:  8 (80%)" in out
    assert "s3#t=00:40:00  (b)" in out
    assert "Reading: the least stable field is belt, alpha 0.772, tentative." in out
    assert "not a law" in out


def test_agree_warns_when_runs_differ() -> None:
    runs = _runs()
    sha = "a" * 64
    runs[0]["run"].update({"pack_sha256": sha, "inputs": {"s3": sha}})
    runs[1]["run"].update({"pack_sha256": "b" * 64, "inputs": {"s3": sha}})
    runs[2]["run"]["procedure"] = "other"
    out = agree(runs, ["a", "b", "c"]).warnings
    assert "run.procedure differs between the records" in out
    assert "run.pack_sha256 differs between the records" in out
    assert "run.pack_sha256 is missing in c" in out
    assert "run.inputs is missing in c" in out
    assert "run.inputs differs between the records" not in out


def test_cli_agree(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    paths = []
    for name, rec in zip("abc", _runs()):
        path = tmp_path / f"{name}.board.yaml"
        path.write_text(yaml.safe_dump(rec, allow_unicode=True), encoding="utf-8")
        paths.append(str(path))
    assert main(["agree", *paths]) == 0
    out = capsys.readouterr().out
    assert out.startswith("agreement of 3 runs: a.board.yaml, b.board.yaml")
    assert main(["agree", *paths, "--fields", "belt,voice", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert [f["field"] for f in data["fields"]] == ["belt", "voice"]
    assert data["fields"][0]["reading"] == "tentative"
    assert data["coverage"]["by_one"] == 1
    assert main(["agree", paths[0]]) == 2
    assert "two or more records" in capsys.readouterr().err
    assert main(["agree", *paths, "--fields", "belt,colour"]) == 2
    assert "unknown field colour" in capsys.readouterr().err


def test_agree_does_not_read_fields_with_few_units() -> None:
    out = format_result(agree(_runs(), ["a", "b", "c"], ["belt", "op"]))
    assert "Not read, fewer than 5 pairable units: op" in out
    assert "Reading: the least stable field is belt, alpha 0.772, tentative." in out
