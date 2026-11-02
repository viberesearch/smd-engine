"""Deal mode, items: fact items with evidence, nature and fit_of, red-line items
and the blocking route, on the invented example in cases/example/deal/."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from deal_helpers import (
    MEMBERS,
    by_id,
    copy_deal,
    edit_pack,
    errors,
    item,
    restamp,
    run_diff,
    set_answer,
)
from smd_engine.cli import main
from smd_engine.task.check import check_answers, check_pack, check_replies
from smd_engine.task.deal_web import deal_script
from smd_engine.task.model import load_task, schema_issues, sha256_file
from smd_engine.task.positions import core_sha


@pytest.fixture()
def work(tmp_path: Path) -> Path:
    return copy_deal(tmp_path / "deal")


def test_a_fact_conflict_is_a_fact_conflict_routed_to_a_check(
    work: Path, tmp_path: Path
) -> None:
    pts = by_id(run_diff(work, tmp_path / "out"))
    margin = pts["margin"]
    assert (margin["class"], margin["subtype"], margin["route"]) == (
        "conflict",
        "fact",
        "check",
    )
    assert margin["claim"]["source"] == "s2" and margin["nature"] == "fact"
    assert margin["answers"]["vera"]["source_ids"] == ["s2"]
    assert pts["lease-term"]["class"] == "agreement"


def test_the_diff_pages_show_the_claim_and_the_sources_by_name(
    work: Path, tmp_path: Path
) -> None:
    run_diff(work, tmp_path / "out")
    md = (tmp_path / "out" / "diff.md").read_text(encoding="utf-8")
    assert "Claim: The gross margin" in md and "accounts of the last year" in md
    assert "does_not_hold" not in md and "cannot say" in md
    html = (tmp_path / "out" / "diff.html").read_text(encoding="utf-8")
    assert "accounts of the last year" in html


def test_a_fact_claim_must_name_a_known_source_and_position(work: Path) -> None:
    pack = load_task(work / "pack.yaml")
    claim = item(pack, "margin")["claim"]
    claim["source"], claim["asserted_by"] = "s9", "ghost"
    found = errors(check_pack(pack, "p"))
    assert any("claim source s9" in m for m in found)
    assert any("asserted_by ghost" in m for m in found)


def test_a_checked_claim_needs_a_source_with_a_sha256(work: Path) -> None:
    pack = load_task(work / "pack.yaml")
    del pack["sources"][2]["sha256"]
    found = [i for i in check_pack(pack, "p") if i.level == "warning"]
    assert any("checked claim" in i.message for i in found)


def test_fact_and_line_items_take_their_own_answers_and_known_source_ids(
    work: Path,
) -> None:
    pack = load_task(work / "pack.yaml")
    sha = core_sha(pack)
    ans = load_task(work / "answers_boris.yaml")
    ans["answers"]["margin"]["value"] = "maybe"
    ans["answers"]["rl-staff"]["value"] = "holds"
    ans["answers"]["lease-term"]["source_ids"] = ["s7"]
    found = errors(check_answers(pack, sha, ans, "a", work))
    assert any("answers.margin: a fact item takes one of" in m for m in found)
    assert any("answers.rl-staff: a line item takes one of" in m for m in found)
    assert any("source id s7" in m for m in found)


def test_the_schema_ties_claim_and_line_to_their_kinds(work: Path) -> None:
    pack = load_task(work / "pack.yaml")
    item(pack, "margin").pop("claim")
    item(pack, "read-clients")["claim"] = item(pack, "lease-term")["claim"]
    item(pack, "rl-staff")["options"] = [{"id": "a", "label": "A"}]
    found = [i.message for i in schema_issues(pack, "task_pack", "p")]
    assert len(found) >= 3


def test_a_fit_point_waits_for_its_reading_while_the_reading_conflicts(
    work: Path, tmp_path: Path
) -> None:
    pts = by_id(run_diff(work, tmp_path / "out"))
    fit = pts["fit-clients"]
    assert (fit["class"], fit["after_reading"], fit["route"]) == (
        "conflict",
        "read-clients",
        "call",
    )
    assert "after_reading" not in pts["read-clients"]
    md = (tmp_path / "out" / "diff.md").read_text(encoding="utf-8")
    assert "Only after the reading of: Item 1" in md


def test_a_fit_point_that_agrees_still_waits_while_its_reading_conflicts(
    work: Path, tmp_path: Path
) -> None:
    for m in MEMBERS:
        set_answer(work, m, "fit-clients", {"value": "fits"})
    pts = by_id(run_diff(work, tmp_path / "out"))
    assert pts["read-clients"]["class"] == "conflict"
    fit = pts["fit-clients"]
    assert (fit["class"], fit["after_reading"], fit["route"]) == (
        "agreement",
        "read-clients",
        "call",
    )


def test_a_fit_point_is_not_held_back_when_the_reading_agrees(
    work: Path, tmp_path: Path
) -> None:
    for m in MEMBERS:
        set_answer(work, m, "read-clients", {"value": "regulars"})
    pts = by_id(run_diff(work, tmp_path / "out"))
    assert pts["read-clients"]["class"] == "agreement"
    assert "after_reading" not in pts["fit-clients"]


def test_fit_of_must_name_another_item(work: Path) -> None:
    def point_at_itself(p: dict[str, Any]) -> None:
        item(p, "fit-clients")["fit_of"] = "fit-clients"

    pack = load_task(work / "pack.yaml")
    point_at_itself(pack)
    assert any("fit_of fit-clients" in m for m in errors(check_pack(pack, "p")))
    item(pack, "fit-clients")["fit_of"] = "nothing"
    assert any("fit_of nothing" in m for m in errors(check_pack(pack, "p")))


def test_alpha_leaves_out_value_and_position_items(work: Path, tmp_path: Path) -> None:
    with_nature = run_diff(work, tmp_path / "a")["alpha"]
    edit_pack(work, lambda p: item(p, "fit-clients").pop("nature"))
    without = run_diff(work, tmp_path / "b")["alpha"]
    assert with_nature["basis"] == {"scope": "core", "items": 2, "of": 4}
    assert without["basis"] == {"scope": "core", "items": 3, "of": 4}
    assert without["choice_items"]["units"] > with_nature["choice_items"]["units"]


def test_a_rejected_red_line_is_blocking(work: Path, tmp_path: Path) -> None:
    line = by_id(run_diff(work, tmp_path / "out"))["rl-staff"]
    assert (line["class"], line["route"]) == ("line_rejected", "blocking")
    assert line["line"]["min"] == 80
    md = (tmp_path / "out" / "diff.md").read_text(encoding="utf-8")
    assert "Red line: share of the baking staff kept at least 80 %" in md


def test_a_single_rejection_blocks_and_all_accepting_agree(
    work: Path, tmp_path: Path
) -> None:
    set_answer(work, "boris", "rl-staff", {"value": "accept"})
    assert by_id(run_diff(work, tmp_path / "a"))["rl-staff"]["class"] == "agreement"
    for m in ("vera", "gleb"):
        path = work / f"answers_{m}.yaml"
        ans = yaml.safe_load(path.read_text(encoding="utf-8"))
        del ans["answers"]["rl-staff"]
        path.write_text(yaml.safe_dump(ans, sort_keys=False), encoding="utf-8")
    set_answer(work, "boris", "rl-staff", {"value": "reject"})
    only = by_id(run_diff(work, tmp_path / "b"))["rl-staff"]
    assert (only["class"], only["route"]) == ("line_rejected", "blocking")


def test_a_red_line_is_checked_like_a_board_red_line(work: Path) -> None:
    pack = load_task(work / "pack.yaml")
    line = item(pack, "rl-staff")["line"]
    line["max"] = 50
    line["until"] = "2026-11-01"
    found = errors(check_pack(pack, "p"))
    assert any("min 80 is not below max 50" in m for m in found)
    assert any("until 2026-11-01 is not after since" in m for m in found)


def write_replies(
    folder: Path, diff: Path, member: str, replies: dict[str, Any]
) -> Path:
    path = folder / f"replies_{member}.yaml"
    data = {
        "record": "task_replies",
        "schema_version": "0.1",
        "diff": sha256_file(diff),
        "member": member,
        "date": "2026-11-04",
        "replies": replies,
    }
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def test_a_rejected_line_is_always_on_the_call_and_a_reply_cannot_accept_it(
    work: Path, tmp_path: Path
) -> None:
    out = tmp_path / "out"
    run_diff(work, out)
    diff = out / "diff.yaml"
    keep = {"rl-staff": {"choice": "keep"}}
    files = [write_replies(work, diff, m, keep) for m in MEMBERS]
    agenda = tmp_path / "agenda.md"
    args = [
        "task",
        "agenda",
        str(diff),
        *map(str, files),
        "--members",
        ",".join(MEMBERS),
    ]
    assert main([*args, "-o", str(agenda)]) == 0
    call = {p["id"]: p for p in load_task(tmp_path / "agenda.yaml")["call"]}
    assert call["rl-staff"]["why"] == {"blocking": True}
    assert "a rejected red line always goes to the call" in agenda.read_text(
        encoding="utf-8"
    )
    bad = load_task(
        write_replies(
            work,
            diff,
            "vera",
            {"rl-staff": {"choice": "accept", "accept_member": "gleb"}},
        )
    )
    found = errors(
        check_replies(list(MEMBERS), bad, "r", load_task(diff), sha256_file(diff))
    )
    assert any("a rejected red line cannot be accepted" in m for m in found)


def test_a_group_pack_may_use_fact_items_with_a_member_as_the_asserter(
    work: Path,
) -> None:
    def group(p: dict[str, Any]) -> None:
        del p["positions"], p["pairs"]
        for m in p["members"]:
            m.pop("position"), m.pop("principal", None)
        p["items"] = [i for i in p["items"] if "audience" not in i]
        p["ontology"]["terms"] = [
            t for t in p["ontology"]["terms"] if "audience" not in t
        ]
        item(p, "margin")["claim"]["asserted_by"] = "vera"
        item(p, "lease-term")["claim"]["asserted_by"] = "ghost"

    pack = load_task(work / "pack.yaml")
    group(pack)
    found = errors(check_pack(pack, "p"))
    assert found == ["item lease-term: claim asserted_by ghost is not a known position"]


def test_the_pack_pages_show_the_deal_items_and_the_export_carries_source_ids(
    work: Path, tmp_path: Path
) -> None:
    out = tmp_path / "out"
    assert main(["task", "render", str(work / "pack.yaml"), "-o", str(out)]) == 0
    md = (out / "pack.md").read_text(encoding="utf-8")
    assert (
        "- Made by: Seller" in md
        and "- Source: accounts of the last year (2026-10-20)" in md
    )
    assert (
        "- Level: checked" in md
        and "| s2 | s2 | accounts of the last year | 4b1c9d6a0e7f |" in md
    )
    html = (out / "pack.html").read_text(encoding="utf-8")
    assert 'data-s="si:margin"' in html and "source_ids" in html
    assert '"kind": "fact"' not in html
    assert deal_script().count("source_ids") == 1


def test_the_russian_pages_have_the_deal_words(work: Path, tmp_path: Path) -> None:
    edit_pack(work, lambda p: p.update(lang="ru"))
    out = tmp_path / "out"
    assert main(["task", "render", str(work / "pack.yaml"), "-o", str(out)]) == 0
    md = (out / "pack.md").read_text(encoding="utf-8")
    assert "Красная линия:" in md
    assert "Кто утверждает" in md and "Позиции" in md
    restamp(work)
    diff = run_diff(work, tmp_path / "d")
    assert diff["lang"] == "ru"
    ru = (tmp_path / "d" / "diff.md").read_text(encoding="utf-8")
    assert "красная линия не принята" in ru and "блокирует: всегда на созвон" in ru
