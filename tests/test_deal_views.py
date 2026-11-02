"""Deal mode, pairs and per-position views, on the invented example in
cases/example/deal/: `by_pair`, `call_by_pair`, `smd deal views` and the view sha
of a reply."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from deal_helpers import by_id, copy_deal, edit_pack, errors, run_diff, set_answer
from smd_engine.cli import main
from smd_engine.task.check import check_pack
from smd_engine.task.deal_web import deal_script
from smd_engine.task.model import load_task, sha256_file

TASK = Path(__file__).resolve().parents[1] / "cases" / "example" / "task"
FAR = {"min": 71, "max": 73, "unit": "weeks"}  # no common stretch with 4 to 8


@pytest.fixture()
def work(tmp_path: Path) -> Path:
    return copy_deal(tmp_path / "deal")


def views(work: Path, tmp_path: Path, *extra: str) -> Path:
    """Diff the example and write the views; the folder holds diff.yaml and them."""
    out = tmp_path / "out"
    run_diff(work, out)
    assert (
        main(
            [
                "deal",
                "views",
                str(work / "pack.yaml"),
                str(out / "diff.yaml"),
                "-o",
                str(out),
                *extra,
            ]
        )
        == 0
    )
    return out


def view(out: Path, position: str) -> dict[str, Any]:
    return load_task(out / f"diff.{position}.yaml")


def test_pairs_are_checked_against_the_members_and_the_positions(work: Path) -> None:
    pack = load_task(work / "pack.yaml")
    assert errors(check_pack(pack, "p")) == []
    pack["pairs"] = [
        {"id": "a", "members": ["vera", "ghost"]},
        {"id": "a", "members": ["vera", "vera"]},
        {"id": "b", "members": ["boris", "vera"]},
        {"id": "c", "members": ["vera", "boris"]},
    ]
    found = errors(check_pack(pack, "p"))
    assert any("pair id a is used twice" in m for m in found)
    assert any("ghost is not a member" in m for m in found)
    assert any("the same member" in m for m in found)
    assert any("pair c: the same two members as another pair" in m for m in found)
    del pack["positions"]
    for m in pack["members"]:
        m.pop("position"), m.pop("principal", None)
    assert any(
        "pairs need the pack's positions" in m for m in errors(check_pack(pack, "p"))
    )


def test_by_pair_classes_each_pair_on_its_own_answers(
    work: Path, tmp_path: Path
) -> None:
    set_answer(work, "vera", "key-person", {"value": "baker"})
    set_answer(work, "boris", "key-person", {"value": "baker"})
    set_answer(work, "gleb", "key-person", {"value": "owner"})
    out = tmp_path / "out"
    diff = run_diff(work, out)
    pairs = {p["id"]: p for p in diff["by_pair"]}
    assert by_id(diff)["key-person"]["class"] == "conflict"
    assert pairs["seller-buyer"]["points"]["key-person"]["class"] == "agreement"
    assert pairs["broker-buyer"]["points"]["key-person"]["class"] == "conflict"
    # a point is compared only when both members were asked: no annex point here
    assert "first-year" not in pairs["seller-buyer"]["points"]
    assert "broker-note" not in pairs["broker-buyer"]["points"]
    assert pairs["seller-buyer"]["summary"]["points"] == 12
    assert "By pair" in (out / "diff.md").read_text(encoding="utf-8")
    # a group pack has no pairs and gets no block
    group = tmp_path / "group"
    names = [str(p) for p in sorted(TASK.glob("answers_*.yaml"))]
    assert (
        main(["task", "diff", str(TASK / "pack.yaml"), *names, "-o", str(group)]) == 0
    )
    assert "by_pair" not in load_task(group / "diff.yaml")


def test_the_agenda_lists_the_call_points_by_pair(work: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    diff = run_diff(work, out)
    sha = sha256_file(out / "diff.yaml")

    def replies(member: str, **choices: str) -> str:
        path = tmp_path / f"replies_{member}.yaml"
        path.write_text(
            yaml.safe_dump(
                {
                    "record": "task_replies",
                    "schema_version": "0.1",
                    "diff": sha,
                    "member": member,
                    "date": "2026-11-04",
                    "replies": {pid: {"choice": c} for pid, c in choices.items()},
                }
            ),
            encoding="utf-8",
        )
        return str(path)

    # every open point is replied to by keep, except two that vera or boris discuss
    open_ids = [p["id"] for p in diff["points"] if p["route"] in ("call", "mark_each")]
    keep = {
        pid: "keep"
        for pid in open_ids
        if pid not in ("first-year", "broker-note", "sale-reason")
    }
    files = [
        replies("vera", **{**keep, "read-clients": "discuss"}),
        replies("boris", **{**keep, "key-person": "discuss"}),
        replies("gleb", **keep),
    ]
    agenda_md = tmp_path / "agenda.md"
    assert (
        main(
            [
                "task",
                "agenda",
                str(out / "diff.yaml"),
                *files,
                "--members",
                "vera,boris,gleb",
                "-o",
                str(agenda_md),
            ]
        )
        == 0
    )
    agenda = load_task(tmp_path / "agenda.yaml")
    by_pair = {p["id"]: p["points"] for p in agenda["call_by_pair"]}
    assert "read-clients" in by_pair["seller-buyer"]
    assert "read-clients" not in by_pair["broker-buyer"]  # only vera discussed it
    assert (
        "key-person" in by_pair["seller-buyer"]
        and "key-person" in by_pair["broker-buyer"]
    )
    assert "rl-staff" in by_pair["seller-buyer"]  # boris rejects the red line
    assert "Gleb" in agenda_md.read_text(encoding="utf-8")


def test_a_view_has_only_the_points_for_its_position(
    work: Path, tmp_path: Path
) -> None:
    out = views(work, tmp_path)
    ids = {
        pos: {p["id"] for p in view(out, pos)["points"]}
        for pos in ("seller", "buyer", "broker")
    }
    assert "sale-reason" in ids["seller"] and "first-year" not in ids["seller"]
    assert "first-year" in ids["buyer"] and "sale-reason" not in ids["buyer"]
    assert "broker-note" in ids["broker"] and "sale-reason" not in ids["broker"]
    seller = view(out, "seller")
    assert seller["summary"]["points"] == len(seller["points"]) == 14
    assert (
        "numbers" in seller["labels"]
        and "first-year" not in seller["labels"]["numbers"]
    )
    for ext in ("md", "html"):
        text = (out / f"diff.seller.{ext}").read_text(encoding="utf-8")
        assert "first-year" not in text and "What would you change" not in text
    # the view is a subset: a point it keeps is the diff's point
    whole = by_id(load_task(out / "diff.yaml"))
    assert by_id(seller)["margin"] == whole["margin"]


def test_a_value_point_shows_open_or_settled_and_the_own_side_only(
    work: Path, tmp_path: Path
) -> None:
    out = views(work, tmp_path)  # 4-8 and 6-12 weeks share a stretch: settled
    assert by_id(view(out, "seller"))["handover"]["class"] == "settled"
    set_answer(work, "boris", "handover", {"value": FAR, "reason": "no way"})
    out = views(work, tmp_path / "second")
    whole = by_id(load_task(out / "diff.yaml"))["handover"]
    assert (whole["class"], whole["subtype"]) == ("conflict", "value")
    for pos in ("seller", "broker"):
        point = by_id(view(out, pos))["handover"]
        assert point["class"] == "open"
        assert set(point["answers"]) == {"vera", "gleb"}
        assert not {"route", "subtype", "sets", "class_by", "silent"} & set(point)
    assert set(by_id(view(out, "buyer"))["handover"]["answers"]) == {"boris"}
    # the other side's figures and reason are in no file of the other side
    for pos in ("seller", "broker"):
        for ext in ("yaml", "md", "html"):
            text = (out / f"diff.{pos}.{ext}").read_text(encoding="utf-8")
            assert not re.search(r"\b7[13]\b", text) and "no way" not in text
    seller_pair = {p["id"]: p for p in view(out, "seller")["by_pair"]}["seller-buyer"]
    assert seller_pair["points"]["handover"] == {"class": "open"}


def test_a_buyer_claim_in_dispute_is_hidden_from_the_sellers_side(
    work: Path, tmp_path: Path
) -> None:
    edit_pack(
        work,
        lambda p: next(i for i in p["items"] if i["id"] == "margin")["claim"].update(
            asserted_by="buyer"
        ),
    )
    out = views(work, tmp_path)
    assert "margin" in by_id(view(out, "buyer"))
    for pos in ("seller", "broker"):
        assert "margin" not in by_id(view(out, pos))
        assert "margin" not in view(out, pos)["by_pair"][0]["points"]
        assert "margin" not in (out / f"diff.{pos}.md").read_text(encoding="utf-8")
    # a dispute over the seller's claim stays in every view
    plain = views(copy_deal(tmp_path / "plain"), tmp_path / "plain_run")
    assert by_id(view(plain, "buyer"))["margin"]["class"] == "conflict"
    assert by_id(view(plain, "seller"))["margin"]["class"] == "conflict"


def test_a_reply_names_the_view_it_was_given(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = views(work, tmp_path)
    seller = view(out, "seller")
    assert seller["view"] == {
        "position": "seller",
        "diff": sha256_file(out / "diff.yaml"),
    }
    reply = {
        "record": "task_replies",
        "schema_version": "0.1",
        "diff": seller["view"]["diff"],
        "view": sha256_file(out / "diff.seller.yaml"),
        "member": "vera",
        "date": "2026-11-04",
        "replies": {"read-clients": {"choice": "keep"}},
    }
    path = tmp_path / "replies_vera.yaml"
    path.write_text(yaml.safe_dump(reply), encoding="utf-8")
    args = ["task", "check", str(work / "pack.yaml"), "--replies", str(path), "--diff"]
    assert main([*args, str(out / "diff.seller.yaml")]) == 0
    reply["view"] = "0" * 64
    path.write_text(yaml.safe_dump(reply), encoding="utf-8")
    assert main([*args, str(out / "diff.seller.yaml")]) == 1
    assert "another view" in capsys.readouterr().out
    # the page of a view puts the view sha in the replies it exports; a whole diff's does not
    page = (out / "diff.seller.html").read_text(encoding="utf-8")
    assert (
        "'view: ' + q(cfg.view)" in page
        and sha256_file(out / "diff.seller.yaml") in page
    )
    assert "'view: '" not in (out / "diff.html").read_text(encoding="utf-8")
    assert "'view: '" not in deal_script()
    # an agenda is built from the whole diff only
    members = ["--members", "vera,boris,gleb"]
    assert main(["task", "agenda", str(out / "diff.seller.yaml"), *members]) == 2
    assert "whole diff.yaml" in capsys.readouterr().err


def test_views_refuse_a_group_pack_a_foreign_diff_and_an_unknown_position(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "out"
    run_diff(work, out)
    diff, pack = str(out / "diff.yaml"), str(work / "pack.yaml")

    def refused(*args: str) -> str:
        capsys.readouterr()
        assert main(["deal", "views", *args, "-o", str(out)]) == 2
        return capsys.readouterr().err

    assert "deal pack" in refused(str(TASK / "pack.yaml"), diff)
    assert "not a position" in refused(pack, diff, "--position", "ghost")
    edit_pack(work, lambda p: p.update(title="Another title of the same pack"))
    assert "another text of the pack" in refused(pack, diff)


def test_the_agenda_shows_no_answers_of_a_value_point_or_an_annex_point(
    work: Path, tmp_path: Path
) -> None:
    set_answer(work, "boris", "handover", {"value": FAR, "reason": "Far too long."})
    out = tmp_path / "out"
    run_diff(work, out)
    reply = tmp_path / "replies_vera.yaml"
    reply.write_text(
        yaml.safe_dump(
            {
                "record": "task_replies",
                "schema_version": "0.1",
                "diff": sha256_file(out / "diff.yaml"),
                "member": "vera",
                "date": "2026-11-04",
                "replies": {"sale-reason": {"choice": "discuss"}},
            }
        ),
        encoding="utf-8",
    )
    agenda_md = out / "agenda.md"
    assert (
        main(
            ["task", "agenda", str(out / "diff.yaml"), str(reply)]
            + ["--members", "vera,boris,gleb", "-o", str(agenda_md)]
        )
        == 0
    )
    call = by_id({"points": load_task(out / "agenda.yaml")["call"]})
    for pid in ("handover", "sale-reason"):
        assert call[pid]["answers_withheld"] is True and "answers" not in call[pid]
    assert "answers" in call["read-clients"]  # the shared core keeps its table
    for text in (agenda_md, out / "agenda.yaml"):
        shown = text.read_text(encoding="utf-8")
        assert "Health" not in shown and "Far too long" not in shown


def test_a_view_leaks_no_annex_item_through_points_labels_or_pages(
    work: Path, tmp_path: Path
) -> None:
    """The whole diff.yaml names every annex item in its points and its labels
    block; a position's view names none that is not for it."""
    out = views(work, tmp_path)
    pack = load_task(work / "pack.yaml")
    whole = load_task(out / "diff.yaml")
    assert "first-year" in whole["labels"]["numbers"]  # the holder's file has it
    for position in ("seller", "buyer", "broker"):
        hidden = [
            i
            for i in pack["items"]
            if "audience" in i and position not in i["audience"]
        ]
        assert hidden
        shown = view(out, position)
        for block in ("numbers", "options"):
            assert not [i["id"] for i in hidden if i["id"] in shown["labels"][block]]
        for ext in ("yaml", "md", "html"):
            text = (out / f"diff.{position}.{ext}").read_text(encoding="utf-8")
            for i in hidden:
                assert i["id"] not in text and i["question"] not in text


def test_task_diff_warns_that_a_deal_diff_with_annex_points_is_the_holders_only(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run_diff(work, tmp_path / "out")
    warning = "full diff: holder only; send parties their views from smd deal views"
    assert warning in capsys.readouterr().err
    # a group pack has no annex: no warning
    names = [str(p) for p in sorted(TASK.glob("answers_*.yaml"))]
    assert (
        main(
            ["task", "diff", str(TASK / "pack.yaml"), *names, "-o", str(tmp_path / "g")]
        )
        == 0
    )
    assert warning not in capsys.readouterr().err
