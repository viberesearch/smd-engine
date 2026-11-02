"""Deal mode, item kind range: the script classes of the spans, the checks of
unit and order, and the pages, on the invented example in cases/example/deal/."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from deal_helpers import (
    MEMBERS,
    by_id,
    copy_deal,
    errors,
    item,
    run_diff,
    set_answer,
)
from smd_engine.cli import main
from smd_engine.task.check import check_answers, check_pack
from smd_engine.task.deal_web import deal_script
from smd_engine.task.model import load_task, schema_issues, sha256_file
from smd_engine.task.positions import core_sha

GROUP = Path(__file__).resolve().parents[1] / "cases" / "example" / "task"


@pytest.fixture()
def work(tmp_path: Path) -> Path:
    return copy_deal(tmp_path / "deal")


def span(lo: float, hi: float, unit: str = "weeks") -> dict[str, Any]:
    return {"value": {"min": lo, "max": hi, "unit": unit}}


def handover(work: Path, tmp_path: Path) -> dict[str, Any]:
    return by_id(run_diff(work, tmp_path / "out"))["handover"]


def test_spans_that_share_a_stretch_are_compatible_and_accepted_unless_objected(
    work: Path, tmp_path: Path
) -> None:
    point = handover(work, tmp_path)  # 4-8, 6-12 and 4-8 weeks
    assert (point["class"], point["class_by"], point["route"]) == (
        "compatible",
        "script",
        "accept_unless_objected",
    )
    assert point["sets"]["common"] == {"min": 6, "max": 8, "unit": "weeks"}
    out = tmp_path / "out"
    assert main(["task", "render", str(out / "diff.yaml"), "-o", str(out)]) == 0
    md = (out / "diff.md").read_text(encoding="utf-8")
    assert "common: 6 to 8 weeks" in md and "**compatible**" in md
    assert "4 to 8 weeks" in md and "6 to 12 weeks (as of 2026-11-03)" in md


def test_identical_spans_agree_and_nested_spans_refine(
    work: Path, tmp_path: Path
) -> None:
    for m in MEMBERS:
        set_answer(work, m, "handover", span(4, 8))
    assert handover(work, tmp_path)["class"] == "agreement"
    set_answer(work, "boris", "handover", span(5, 6))
    set_answer(work, "gleb", "handover", span(4, 7))
    point = handover(work, tmp_path / "again")
    assert (point["class"], point["route"]) == ("refinement", "accept_unless_objected")
    assert point["sets"]["common"] == {"min": 5, "max": 6, "unit": "weeks"}


def test_spans_with_no_common_stretch_are_a_value_conflict_for_the_call(
    work: Path, tmp_path: Path
) -> None:
    set_answer(work, "boris", "handover", span(10, 14))
    point = handover(work, tmp_path)
    assert (point["class"], point["subtype"], point["route"]) == (
        "conflict",
        "value",
        "call",
    )
    assert "sets" not in point


def test_a_range_needs_the_unit_of_the_item_and_min_not_above_max(work: Path) -> None:
    pack = load_task(work / "pack.yaml")
    sha = core_sha(pack)
    ans = load_task(work / "answers_boris.yaml")
    for bad, text in (
        (span(6, 12, "days"), "unit of a range here is 'weeks'"),
        (span(12, 6), "min of a range is above its max"),
        ({"value": 7}, "a range item takes"),
    ):
        ans["answers"]["handover"] = bad
        found = errors(check_answers(pack, sha, ans, "a", work))
        assert any(text in m for m in found), (bad, found)
    ans["answers"]["handover"] = {
        "value": {"min": 1, "max": 2, "unit": "weeks", "x": 1}
    }
    assert schema_issues(ans, "task_answers", "a")


def test_a_diff_refuses_answers_in_another_unit(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    set_answer(work, "boris", "handover", span(6, 12, "days"))
    names = [str(work / f"answers_{m}.yaml") for m in MEMBERS]
    args = ["task", "diff", str(work / "pack.yaml"), *names, "-o", str(tmp_path)]
    assert main(args) != 0
    assert "unit of a range" in capsys.readouterr().err
    assert not (tmp_path / "diff.yaml").exists()


def test_the_schema_ties_unit_to_range_items(work: Path) -> None:
    pack = load_task(work / "pack.yaml")
    del item(pack, "handover")["unit"]
    item(pack, "read-clients")["unit"] = "weeks"
    assert len([i for i in check_pack(pack, "p") if i.level == "error"]) >= 2


def test_the_pack_pages_ask_for_from_to_and_the_unit(
    work: Path, tmp_path: Path
) -> None:
    out = tmp_path / "pages"
    assert main(["task", "render", str(work / "pack.yaml"), "-o", str(out)]) == 0
    md = (out / "pack.md").read_text(encoding="utf-8")
    assert "Unit: weeks" in md and "a range: from, to" in md
    html = (out / "pack.html").read_text(encoding="utf-8")
    assert 'data-s="v:handover:min"' in html and 'data-s="v:handover:max"' in html
    assert "it.kind === 'range'" in html and "q(it.unit)" in html
    assert "it.kind === 'range'" not in deal_script()


def test_a_group_pack_may_have_a_range_item(tmp_path: Path) -> None:
    """A pack with no positions takes the kind too, and its page gets the script."""
    group = tmp_path / "group"
    shutil.copytree(GROUP, group)
    pack_path = group / "pack.yaml"
    pack = yaml.safe_load(pack_path.read_text(encoding="utf-8"))
    pack["items"].append(
        {
            "id": "pilot-weeks",
            "section": "Plan",
            "question": "How many weeks should the pilot run?",
            "kind": "range",
            "unit": "weeks",
        }
    )
    pack_path.write_text(yaml.safe_dump(pack, sort_keys=False), encoding="utf-8")
    sha = sha256_file(pack_path)
    spans = {"ana": (4, 8), "ben": (6, 10), "cy": (5, 9)}
    names = []
    for m, (lo, hi) in spans.items():
        path = group / f"answers_{m}.yaml"
        ans = yaml.safe_load(path.read_text(encoding="utf-8"))
        ans["pack"]["sha256"] = sha
        ans["answers"]["pilot-weeks"] = span(lo, hi)
        path.write_text(yaml.safe_dump(ans, sort_keys=False), encoding="utf-8")
        names.append(str(path))
    out = tmp_path / "out"
    assert main(["task", "diff", str(pack_path), *names, "-o", str(out)]) == 0
    point = by_id(load_task(out / "diff.yaml"))["pilot-weeks"]
    assert point["class"] == "compatible"
    assert main(["task", "render", str(pack_path), "-o", str(out)]) == 0
    assert 'data-s="v:pilot-weeks:min"' in (out / "pack.html").read_text(
        encoding="utf-8"
    )
