"""Deal mode, sealed bounds: pack checks of bound items and the holder, `smd deal
seal`, the commitment-only answers, the diff point that holds no answer, the
price wording on the pages, the refusal of sealed files as inputs and the model
consent, on the invented example in cases/example/deal/."""

from __future__ import annotations

import stat
import subprocess
from pathlib import Path
from typing import Any

import pytest

from deal_helpers import (
    CEILING,
    FLOOR,
    by_id,
    copy_deal,
    edit_pack,
    errors,
    run_diff,
    seal,
    set_answer,
)
from smd_engine.cli import main
from smd_engine.task.check import check_answers, check_pack, check_replies
from smd_engine.task.model import load_task, sha256_file


@pytest.fixture()
def work(tmp_path: Path) -> Path:
    return copy_deal(tmp_path / "deal")


def pack_of(work: Path) -> dict[str, Any]:
    return load_task(work / "pack.yaml")


def test_a_ceiling_before_the_last_stage_is_an_error(work: Path) -> None:
    pack = pack_of(work)
    assert errors(check_pack(pack, "p")) == []
    ceiling = next(i for i in pack["items"] if i["id"] == "price-ceiling")
    ceiling["bound"]["stage"] = "nda"
    found = errors(check_pack(pack, "p"))
    assert any("committed at the last stage (full-map), not at nda" in m for m in found)
    ceiling["bound"].pop("stage")
    assert any("names its stage" in m for m in errors(check_pack(pack, "p")))
    ceiling["bound"]["stage"] = "full-map"
    floor = next(i for i in pack["items"] if i["id"] == "price-floor")
    floor["bound"]["stage"] = "nda"
    assert any(
        "a floor is committed at day 0" in m for m in errors(check_pack(pack, "p"))
    )


def test_a_bound_item_needs_a_holder_a_deal_and_its_own_party(work: Path) -> None:
    pack = pack_of(work)
    del pack["holder"], pack["deal"]
    found = errors(check_pack(pack, "p"))
    assert "bound items need a holder" in found and "bound items need deal.id" in found
    pack = pack_of(work)
    next(i for i in pack["items"] if i["id"] == "price-floor")["audience"] = ["buyer"]
    assert any(
        "a floor is the seller's, not position buyer" in m
        for m in errors(check_pack(pack, "p"))
    )
    pack = pack_of(work)
    pack["members"].append({"id": "kai", "name": "Kai", "position": "seller"})
    assert any("needs exactly one" in m for m in errors(check_pack(pack, "p")))


def test_the_operator_is_never_a_broker_and_a_party_is_a_warning(work: Path) -> None:
    pack = pack_of(work)
    pack["holder"]["operator"] = "gleb"
    assert any("a broker never runs it" in m for m in errors(check_pack(pack, "p")))
    pack["holder"]["operator"] = "boris"
    issues = check_pack(pack, "p")
    assert errors(issues) == []
    assert any(
        i.level == "warning" and "party to the deal" in i.message for i in issues
    )
    pack["holder"]["operator"] = "nobody"
    assert any("not a member" in m for m in errors(check_pack(pack, "p")))


def test_seal_writes_a_private_file_and_prints_only_the_commitment(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path, commit = seal(work, tmp_path, "price-floor", FLOOR)
    shown = capsys.readouterr()
    salt = load_task(path, "task_sealed")["salt"]
    assert commit in shown.out
    for text in (shown.out, shown.err):
        assert FLOOR not in text and salt not in text
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    sealed = load_task(path, "task_sealed")
    assert (sealed["member"], sealed["side"], sealed["unit"]) == (
        "vera",
        "floor",
        "EUR",
    )
    assert (
        sealed["pack"]["sha256"]
        == load_task(work / "answers_vera.yaml")["pack"]["sha256"]
    )
    # one commitment stands per item and member
    again = [
        "deal",
        "seal",
        str(work / "pack.yaml"),
        "price-floor",
        "-o",
        str(path.parent),
    ]
    assert main(again + ["--value", "1"]) == 2
    assert "exists" in capsys.readouterr().err
    other = [
        "deal",
        "seal",
        str(work / "pack.yaml"),
        "price-floor",
        "-o",
        str(tmp_path / "o"),
    ]
    assert main(other + ["--value", "1", "--member", "boris"]) == 2


def test_an_answer_to_a_bound_item_is_the_commitment_and_nothing_else(
    work: Path, tmp_path: Path
) -> None:
    pack, sha = pack_of(work), load_task(work / "answers_vera.yaml")["pack"]["sha256"]
    path, commit = seal(work, tmp_path, "price-floor", FLOOR)
    set_answer(work, "vera", "price-floor", {"value": commit})
    ans = load_task(work / "answers_vera.yaml")
    assert errors(check_answers(pack, sha, ans, "a", work)) == []
    set_answer(work, "vera", "price-floor", {"value": float(FLOOR)})
    ans = load_task(work / "answers_vera.yaml")
    found = errors(check_answers(pack, sha, ans, "a", work))
    assert any("never the number itself" in m for m in found)
    assert not any(FLOOR in m for m in found)
    set_answer(work, "vera", "price-floor", {"value": commit, "reason": "my floor"})
    ans = load_task(work / "answers_vera.yaml")
    assert any(
        "holds the commitment only" in m
        for m in errors(check_answers(pack, sha, ans, "a", work))
    )


def test_the_diff_point_holds_who_committed_and_no_answer_or_number(
    work: Path, tmp_path: Path
) -> None:
    _, floor = seal(work, tmp_path, "price-floor", FLOOR)
    _, ceiling = seal(work, tmp_path, "price-ceiling", CEILING)
    set_answer(work, "vera", "price-floor", {"value": floor})
    out = tmp_path / "out"
    point = by_id(run_diff(work, out))["price-floor"]
    assert (point["class"], point["route"], point["verdict"]) == (
        "sealed",
        "price_meeting",
        "not_tested",
    )
    assert point["answers"] == {} and point["committed_by"] == ["vera"]
    ceiling_point = by_id(load_task(out / "diff.yaml"))["price-ceiling"]
    assert ceiling_point["silent"] == ["boris"] and ceiling_point["committed_by"] == []
    assert point["sealed"] == {"topic": "price", "side": "floor", "unit": "EUR"}
    assert all(
        pid not in ("price-floor", "price-ceiling")
        for pair in load_task(out / "diff.yaml")["by_pair"]
        for pid in pair["points"]
    )
    # neither the numbers, the salts nor the commitments are in any output
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
    assert (
        main(
            [
                "deal",
                "views",
                str(work / "pack.yaml"),
                str(out / "diff.yaml"),
                "-o",
                str(out / "views"),
            ]
        )
        == 0
    )
    secrets = [FLOOR, CEILING, floor, ceiling]
    secrets += [
        load_task(p, "task_sealed")["salt"]
        for p in (tmp_path / "safe").glob("sealed_*.yaml")
    ]
    for file in [p for p in out.rglob("*") if p.is_file()]:
        text = file.read_text(encoding="utf-8")
        assert not [s for s in secrets if s in text], file.name


def test_the_pages_say_price_is_for_the_meeting_in_russian(
    work: Path, tmp_path: Path
) -> None:
    edit_pack(work, lambda p: p.update(lang="ru"))
    out = tmp_path / "out"
    run_diff(work, out)
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
    phrase = "цена: не проверено — торг на личной встрече"
    for name in ("diff.md", "diff.html", "agenda.md"):
        assert phrase in (out / name).read_text(encoding="utf-8"), name


def test_the_bound_item_has_no_box_on_the_page_and_the_ceiling_is_not_in_the_core(
    work: Path, tmp_path: Path
) -> None:
    out = tmp_path / "pages"
    assert (
        main(
            [
                "task",
                "render",
                str(work / "pack.yaml"),
                "-o",
                str(out),
                "--position",
                "seller",
            ]
        )
        == 0
    )
    html = (out / "pack.seller.html").read_text(encoding="utf-8")
    assert "smd deal seal" in html and 'data-s="v:price-floor"' not in html
    assert "price-ceiling" not in html
    assert main(["task", "render", str(work / "pack.yaml"), "-o", str(out)]) == 0
    assert "price-floor" not in (out / "pack.md").read_text(encoding="utf-8")


def test_a_sealed_file_is_refused_as_an_input_of_the_diff(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path, _ = seal(work, tmp_path, "price-floor", FLOOR)
    capsys.readouterr()
    args = [
        "task",
        "diff",
        str(work / "pack.yaml"),
        str(path),
        "-o",
        str(tmp_path / "o"),
    ]
    assert main(args) == 2
    err = capsys.readouterr().err
    assert "a sealed file is not an input" in err and FLOOR not in err
    assert main(["task", "check", str(work / "pack.yaml"), str(path)]) == 2


def test_the_diff_says_whether_a_model_may_read_the_answers(
    work: Path, tmp_path: Path
) -> None:
    diff = run_diff(work, tmp_path / "out")
    assert diff["model_pass_allowed"] is False
    assert "Model pass: not allowed" in (tmp_path / "out" / "diff.md").read_text(
        encoding="utf-8"
    )
    edit_pack(work, lambda p: p["deal"].update(model_consent=True))
    assert run_diff(work, tmp_path / "again")["model_pass_allowed"] is True


def test_a_sealed_point_takes_keep_or_discuss_only(work: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    run_diff(work, out)
    diff = load_task(out / "diff.yaml")
    sha = sha256_file(out / "diff.yaml")

    def reply(choice: str) -> dict[str, Any]:
        entry = {
            "choice": choice,
            **({"accept_member": "boris"} if choice == "accept" else {}),
        }
        return {
            "record": "task_replies",
            "schema_version": "0.1",
            "diff": sha,
            "member": "vera",
            "date": "2026-11-04",
            "replies": {"price-floor": entry},
        }

    members = diff["members"]
    assert errors(check_replies(members, reply("keep"), "r", diff, sha)) == []
    assert errors(check_replies(members, reply("discuss"), "r", diff, sha)) == []
    assert any(
        "keep or discuss only" in m
        for m in errors(check_replies(members, reply("accept"), "r", diff, sha))
    )
    html = (out / "diff.html").read_text(encoding="utf-8")
    assert 'name="rc:price-floor" data-s="rc:price-floor" value="accept"' not in html


def test_a_sealed_file_in_a_git_work_tree_is_a_warning_until_it_is_ignored(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    subprocess.run(["git", "init", "-q", str(work)], check=True)
    seal_args = [
        "deal",
        "seal",
        str(work / "pack.yaml"),
        "price-floor",
        "-o",
        str(work),
    ]
    assert main(seal_args + ["--value", FLOOR]) == 0
    assert "not ignored" in capsys.readouterr().err
    check = ["task", "check", str(work / "pack.yaml"), str(work / "answers_boris.yaml")]
    assert main(check) == 0
    assert "keep it outside every repository" in capsys.readouterr().out
    (work / ".gitignore").write_text("sealed_*.yaml\n", encoding="utf-8")
    assert main(check) == 0
    assert "keep it outside" not in capsys.readouterr().out


def test_bound_items_need_the_sealed_floor_switched_on(work: Path) -> None:
    pack = pack_of(work)
    assert pack["deal"]["sealed_floor"] is True and errors(check_pack(pack, "p")) == []
    pack["deal"]["sealed_floor"] = False
    found = errors(check_pack(pack, "p"))
    assert any("bound items need deal.sealed_floor: true" in m for m in found)
    del pack["deal"]["sealed_floor"]  # off by default
    assert any("sealed_floor" in m for m in errors(check_pack(pack, "p")))
    # with no bound items the pack is valid with the floor off
    pack["items"] = [i for i in pack["items"] if i["kind"] != "bound"]
    assert errors(check_pack(pack, "p")) == []
