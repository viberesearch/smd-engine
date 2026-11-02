"""Deal mode, positions and audience: the shared core, one annex per position,
the stamps of the answers, `render --position`, alpha and the agenda on the
invented example in cases/example/deal/.

REGENERATE. The answers carry the sha256 of the pack's core and of the member's
annex. After a change to cases/example/deal/pack.yaml run
`restamp(Path("cases/example/deal"))` from tests/deal_helpers.py."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from deal_helpers import DEAL, copy_deal, edit_pack, restamp, run_diff
from smd_engine.cli import main
from smd_engine.records import RecordError
from smd_engine.task.agenda import expected_repliers
from smd_engine.task.asking import asking_price, default_stage
from smd_engine.task.check import check_answers, check_pack
from smd_engine.task.deal_web import deal_script
from smd_engine.task.model import load_task, sha256_file
from smd_engine.task.positions import (
    annex_sha,
    core_sha,
    core_view,
    pack_view,
    position_view,
    stamp_sha,
)

PACK = DEAL / "pack.yaml"
ANSWERS = [DEAL / f"answers_{m}.yaml" for m in ("vera", "boris", "gleb")]


def errors(issues: list[Any]) -> list[str]:
    return [i.message for i in issues if i.level == "error"]


@pytest.fixture()
def work(tmp_path: Path) -> Path:
    return copy_deal(tmp_path / "deal")


def run_diff(folder: Path, out: Path) -> dict[str, Any]:
    names = [str(folder / f"answers_{m}.yaml") for m in ("vera", "boris", "gleb")]
    assert (
        main(["task", "diff", str(folder / "pack.yaml"), *names, "-o", str(out)]) == 0
    )
    return load_task(out / "diff.yaml")


def test_the_example_deal_pack_and_answers_check_clean(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["task", "check", str(PACK), *map(str, ANSWERS)]) == 0
    assert "0 error(s), 0 warning(s)" in capsys.readouterr().out


def test_a_position_view_keeps_the_core_and_only_its_own_annex() -> None:
    pack = load_task(PACK)
    buyer = position_view(pack, "buyer")
    ids = [i["id"] for i in buyer["items"]]
    assert "first-year" in ids
    assert "sale-reason" not in ids and "broker-note" not in ids
    assert [t["term"] for t in buyer["ontology"]["terms"]] == [
        "client base",
        "key person",
    ]
    for position in ("seller", "buyer", "broker"):
        assert core_view(position_view(pack, position)) == core_view(pack)
    with pytest.raises(RecordError):
        position_view(pack, "verifier")


def test_the_core_sha_ignores_annexes_and_each_annex_has_its_own_sha(
    work: Path,
) -> None:
    before = load_task(work / "pack.yaml")
    core, seller, buyer = (
        core_sha(before),
        annex_sha(before, "seller"),
        annex_sha(before, "buyer"),
    )
    after = edit_pack(
        work,
        lambda p: next(i for i in p["items"] if i["id"] == "sale-reason").update(
            question="Why does the owner sell, in one line?"
        ),
    )
    assert core_sha(after) == core
    assert annex_sha(after, "buyer") == buyer
    assert annex_sha(after, "seller") != seller
    assert len({seller, buyer, annex_sha(before, "broker")}) == 3


def test_a_deal_pack_is_stamped_with_its_core_a_group_pack_with_its_file() -> None:
    pack = load_task(PACK)
    assert stamp_sha(pack, sha256_file(PACK)) == core_sha(pack) != sha256_file(PACK)
    group = load_task(DEAL.parent / "task" / "pack.yaml")
    assert stamp_sha(group, "f" * 64) == "f" * 64


def test_answers_must_carry_the_core_sha_and_their_own_annex_sha(work: Path) -> None:
    pack = load_task(work / "pack.yaml")
    sha = core_sha(pack)
    ans = load_task(work / "answers_vera.yaml")
    assert errors(check_answers(pack, sha, ans, "a", work)) == []
    assert any(
        "differs" in m for m in errors(check_answers(pack, "0" * 64, ans, "a", work))
    )
    ans["pack"]["annex"]["sha256"] = annex_sha(pack, "buyer")
    assert any(
        "annex sha256" in m for m in errors(check_answers(pack, sha, ans, "a", work))
    )
    ans["pack"]["annex"] = {"position": "buyer", "sha256": annex_sha(pack, "buyer")}
    assert any(
        "not the member's" in m
        for m in errors(check_answers(pack, sha, ans, "a", work))
    )
    del ans["pack"]["annex"]
    found = check_answers(pack, sha, ans, "a", work)
    assert any("no annex stamp" in i.message for i in found if i.level == "warning")


def test_an_answer_to_an_item_of_another_annex_is_an_error(work: Path) -> None:
    pack = load_task(work / "pack.yaml")
    ans = load_task(work / "answers_boris.yaml")
    ans["answers"]["sale-reason"] = {"value": "I look at the seller's answers"}
    found = errors(check_answers(pack, core_sha(pack), ans, "a", work))
    assert any("sale-reason is not for position buyer" in m for m in found)


def test_pack_check_catches_position_and_audience_errors(work: Path) -> None:
    def broken(p: dict[str, Any]) -> None:
        p["members"][1]["position"] = "nobody"
        p["members"][0]["principal"] = "boris"
        p["items"][2]["audience"] = ["seller", "ghost"]
        p["items"][0]["refs"] = ["first-year"]

    pack = load_task(work / "pack.yaml")
    broken(pack)
    found = errors(check_pack(pack, "p"))
    assert any("position 'nobody'" in m for m in found)
    assert any("only a broker has a principal" in m for m in found)
    assert any("audience ghost" in m for m in found)
    assert any("core item names first-year" in m for m in found)


def test_audience_and_position_need_the_positions_of_the_pack(work: Path) -> None:
    pack = load_task(work / "pack.yaml")
    del pack["positions"]
    found = errors(check_pack(pack, "p"))
    assert any("needs the pack's positions" in m for m in found)
    assert any("audience seller is not a position" in m for m in found)


def test_render_position_writes_the_core_and_that_annex_only(
    work: Path, tmp_path: Path
) -> None:
    out = tmp_path / "out"
    assert main(["task", "render", str(work / "pack.yaml"), "-o", str(out)]) == 0
    assert (
        main(
            [
                "task",
                "render",
                str(work / "pack.yaml"),
                "-o",
                str(out),
                "--position",
                "buyer",
            ]
        )
        == 0
    )
    core = (out / "pack.md").read_text(encoding="utf-8")
    buyer = (out / "pack.buyer.md").read_text(encoding="utf-8")
    assert "the owner sell now" not in core and "the owner sell now" not in buyer
    assert (
        "change in the first year" in buyer and "change in the first year" not in core
    )
    assert "weak points" not in buyer and "family plan" not in buyer
    assert "Gleb (Sell-side broker)" in buyer
    html = (out / "pack.buyer.html").read_text(encoding="utf-8")
    pack = load_task(work / "pack.yaml")
    assert annex_sha(pack, "buyer") in html and core_sha(pack) in html
    assert '"annex"' in html
    assert '"annex"' not in (out / "pack.html").read_text(encoding="utf-8")


def test_render_position_is_refused_for_a_group_pack_and_an_unknown_position(
    work: Path, tmp_path: Path
) -> None:
    group = DEAL.parent / "task" / "pack.yaml"
    with pytest.raises(RecordError):
        pack_view(load_task(group), "buyer")
    args = ["task", "render", str(work / "pack.yaml"), "-o", str(tmp_path / "o")]
    assert main([*args, "--position", "ghost"]) != 0
    assert not (tmp_path / "o").exists()


def test_the_deal_script_is_the_group_script_plus_the_annex_stamp() -> None:
    from smd_engine.task.web import asset_text

    assert "annex" not in asset_text("task.js")
    assert deal_script().count("P.annex") == 3


def test_diff_marks_audience_points_and_counts_silence_inside_the_audience(
    work: Path, tmp_path: Path
) -> None:
    diff = run_diff(work, tmp_path / "out")
    by_id = {p["id"]: p for p in diff["points"]}
    assert by_id["first-year"]["audience"] == ["buyer"]
    assert "silent" not in by_id["first-year"]
    assert "audience" not in by_id["read-clients"]
    assert by_id["read-clients"]["class"] == "conflict"
    assert diff["positions"] == {"vera": "seller", "boris": "buyer", "gleb": "broker"}
    assert diff["pack"]["sha256"] == core_sha(load_task(work / "pack.yaml"))


def test_alpha_is_computed_on_the_shared_core_only(work: Path, tmp_path: Path) -> None:
    base = run_diff(work, tmp_path / "a")["alpha"]
    assert base["basis"] == {"scope": "core", "items": 2, "of": 4}

    def add(p: dict[str, Any]) -> None:
        p["items"].append(
            {
                "id": "mood",
                "section": "Own position",
                "question": "How do you feel?",
                "kind": "choice",
                "audience": ["seller", "buyer"],
                "options": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
            }
        )

    edit_pack(work, add)
    for m, v in (("vera", "a"), ("boris", "b")):
        path = work / f"answers_{m}.yaml"
        path.write_text(
            path.read_text() + f"  mood: {{value: {v}}}\n", encoding="utf-8"
        )
    alpha = run_diff(work, tmp_path / "b")["alpha"]
    assert alpha["basis"] == {"scope": "core", "items": 2, "of": 5}
    assert alpha["choice_items"] == base["choice_items"]


def test_an_item_for_one_position_needs_no_reply_from_the_others(
    work: Path, tmp_path: Path
) -> None:
    run_diff(work, tmp_path / "out")
    agenda = tmp_path / "agenda.md"
    code = main(
        [
            "task",
            "agenda",
            str(tmp_path / "out" / "diff.yaml"),
            "--members",
            "vera,boris,gleb",
            "-o",
            str(agenda),
        ]
    )
    assert code == 0
    data = load_task(tmp_path / "agenda.yaml")
    call = {p["id"] for p in data["call"]}
    assert "read-clients" in call
    assert "first-year" not in call and "sale-reason" not in call


def test_a_deal_pack_with_a_seller_needs_its_asking_price_in_a_stage_of_the_deal(
    work: Path,
) -> None:
    pack = load_task(work / "pack.yaml")
    assert errors(check_pack(pack, "p")) == []
    ask = pack["deal"]["asking_price"]
    assert asking_price(pack) == {"value": 95000, "unit": "EUR", "stage": "full-map"}
    ask["stage"] = "closing"
    assert any(
        "stage closing is not in deal.stages" in m
        for m in errors(check_pack(pack, "p"))
    )
    del pack["deal"]["asking_price"]
    assert any("states the asking price" in m for m in errors(check_pack(pack, "p")))
    # a pack with no seller is not asked; a pack with no positions is a group pack
    pack["positions"] = [p for p in pack["positions"] if p["kind"] != "seller"]
    pack["members"] = [m for m in pack["members"] if m["id"] != "vera"]
    assert not any("asking price" in m for m in errors(check_pack(pack, "p")))


def test_the_default_stage_of_the_asking_price_is_the_one_after_nda() -> None:
    assert default_stage(["intro", "nda", "map", "close"]) == "map"
    assert default_stage(["nda", "map"]) == "map"
    assert default_stage(["nda"]) == "nda"
    assert default_stage(["intro", "map", "close"]) == "map"


def test_the_pages_open_the_asking_price_from_its_stage_on(
    work: Path, tmp_path: Path
) -> None:
    def page(*extra: str, name: str = "pack.md") -> str:
        out = tmp_path / "pages"
        pack = str(work / "pack.yaml")
        assert main(["task", "render", pack, "-o", str(out), *extra]) == 0
        return (out / name).read_text(encoding="utf-8")

    assert "Asking price: opens at stage full-map" in page()
    assert "Asking price: opens at stage full-map" in page("--stage", "nda")
    assert "Asking price: 95 000 EUR" in page("--stage", "full-map")
    assert "Asking price: 95 000 EUR" in page(
        "--stage", "full-map", "--position", "buyer", name="pack.buyer.html"
    )
    edit_pack(work, lambda p: p.update(lang="ru"))
    assert "Запрашиваемая цена: 95 000 EUR" in page("--stage", "full-map")
    assert "Запрашиваемая цена: открывается на этапе full-map" in page("--stage", "nda")
    assert (
        main(
            [
                "task",
                "render",
                str(work / "pack.yaml"),
                "-o",
                str(tmp_path),
                "--stage",
                "x",
            ]
        )
        == 2
    )


def test_the_diff_and_the_agenda_show_the_asking_price(
    work: Path, tmp_path: Path
) -> None:
    diff = run_diff(work, tmp_path / "out")
    assert diff["asking_price"] == {"value": 95000, "unit": "EUR", "stage": "full-map"}
    assert "Asking price: 95 000 EUR" in (tmp_path / "out" / "diff.md").read_text()
    assert "95 000 EUR" in (tmp_path / "out" / "diff.html").read_text()
    agenda = tmp_path / "agenda.md"
    members = "vera,boris,gleb"
    args = ["task", "agenda", str(tmp_path / "out" / "diff.yaml")]
    assert main([*args, "--members", members, "-o", str(agenda)]) == 0
    assert "Asking price: 95 000 EUR" in agenda.read_text(encoding="utf-8")
    assert load_task(agenda.with_suffix(".yaml"))["asking_price"]["unit"] == "EUR"


def test_an_item_names_a_stage_of_the_deal(work: Path) -> None:
    pack = load_task(work / "pack.yaml")
    talk = next(i for i in pack["items"] if i["id"] == "price-talk")
    assert talk["stage"] == "full-map"
    talk["stage"] = "closing"
    assert any("price-talk: stage closing" in m for m in errors(check_pack(pack, "p")))


def add_points(folder: Path, member: str, *entries: dict[str, Any]) -> None:
    path = folder / f"answers_{member}.yaml"
    ans = yaml.safe_load(path.read_text(encoding="utf-8"))
    ans["added"] = list(entries)
    path.write_text(yaml.safe_dump(ans, sort_keys=False), encoding="utf-8")


def test_an_added_point_is_for_the_authors_position_unless_shared(
    work: Path, tmp_path: Path
) -> None:
    add_points(work, "boris", {"text": "Private."}, {"text": "Open.", "share": True})
    out = tmp_path / "out"
    diff = run_diff(work, out)
    added = {p["id"]: p for p in diff["points"] if p["kind"] == "added"}
    assert added["add-boris-1"]["audience"] == ["buyer"]
    assert "audience" not in added["add-boris-2"]
    assert "silent" not in added["add-boris-1"]  # nobody else is in its audience
    assert (
        main(["deal", "views", str(PACK), str(out / "diff.yaml"), "-o", str(out)]) == 0
    )
    for position, private in (("seller", False), ("buyer", True), ("broker", False)):
        ids = {p["id"] for p in load_task(out / f"diff.{position}.yaml")["points"]}
        assert ("add-boris-1" in ids) is private and "add-boris-2" in ids
    # only the author is in the audience, so nobody else owes a reply to it
    where = diff["positions"]
    members = diff["members"]
    assert expected_repliers(added["add-boris-1"], members, where) == []
    assert expected_repliers(added["add-boris-2"], members, where) == ["vera", "gleb"]


def test_share_on_an_added_point_is_ignored_and_warned_in_a_group_pack(
    tmp_path: Path,
) -> None:
    folder = tmp_path / "task"
    shutil.copytree(Path(__file__).resolve().parents[1] / "cases/example/task", folder)
    add_points(folder, "ana", {"text": "A group point.", "share": False})
    pack = load_task(folder / "pack.yaml")
    ans = load_task(folder / "answers_ana.yaml")
    issues = check_answers(
        pack, sha256_file(folder / "pack.yaml"), ans, "answers_ana.yaml", folder
    )
    assert any("share is for a deal pack" in i.message for i in issues)
    assert errors(issues) == []
    out = tmp_path / "out"
    names = [str(folder / f"answers_{m}.yaml") for m in ("ana", "ben", "cy")]
    assert (
        main(["task", "diff", str(folder / "pack.yaml"), *names, "-o", str(out)]) == 0
    )
    added = [p for p in load_task(out / "diff.yaml")["points"] if p["kind"] == "added"]
    assert added and all("audience" not in p for p in added)
