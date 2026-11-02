"""Task packs: schemas, check, render, diff, agenda, on the invented example in
cases/example/task/.

REGENERATE. The answers carry the sha256 of pack.yaml and the replies that of the
diff.yaml the three answers give. After a change to pack.yaml or to the diff
format, restamp them: `shasum -a 256 cases/example/task/pack.yaml` into the
`pack.sha256` line of each answers file (and the transcript's sha into
answers_ben.yaml), then `uv run smd task diff` into a scratch folder and its
`shasum -a 256 diff.yaml` into the `diff:` line of each replies file."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import pytest
import yaml

from smd_engine.cli import main
from smd_engine.records import RecordError
from smd_engine.task.agenda import build_agenda
from smd_engine.task.check import check_answers, check_pack, check_replies
from smd_engine.task.diff import build_diff, classify_structured, load_answers
from smd_engine.task.labels import LABELS
from smd_engine.task.refs import ref_groups
from smd_engine.task.svg import (
    LINE,
    NARROW,
    PAD_X,
    WIDE,
    ontology_figure,
    ontology_svg,
    text_width,
)
from smd_engine.task.model import (
    load_task,
    member_ids,
    schema_issues,
    sha256_file,
)

TASK = Path(__file__).resolve().parents[1] / "cases" / "example" / "task"
PACK = TASK / "pack.yaml"
ANSWERS = [TASK / f"answers_{m}.yaml" for m in ("ana", "ben", "cy")]
REPLIES = [TASK / f"replies_{m}.yaml" for m in ("ana", "ben")]


def levels(issues: list[Any], level: str = "error") -> list[str]:
    return [i.message for i in issues if i.level == level]


@pytest.fixture()
def work(tmp_path: Path) -> Path:
    """A copy of the example, to change."""
    dest = tmp_path / "task"
    shutil.copytree(TASK, dest)
    return dest


@pytest.fixture()
def diff_dir(tmp_path: Path) -> Path:
    out = tmp_path / "out"
    code = main(["task", "diff", str(PACK), *map(str, ANSWERS), "-o", str(out)])
    assert code == 0
    return out


def points(diff: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {p["id"]: p for p in diff["points"]}


def test_example_files_validate_against_their_schemas() -> None:
    assert schema_issues(load_task(PACK), "task_pack", "pack") == []
    for path in ANSWERS:
        assert schema_issues(load_task(path), "task_answers", path.name) == []
    for path in REPLIES:
        assert schema_issues(load_task(path), "task_replies", path.name) == []
    pack = load_task(PACK)
    assert {i["kind"] for i in pack["items"]} == {
        "choice",
        "multi",
        "text",
        "number",
        "ids",
        "steps",
    }
    assert len(pack["items"]) == 6


def test_check_passes_on_the_example(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["task", "check", str(PACK), *map(str, ANSWERS)])
    assert code == 0
    assert "0 error(s), 0 warning(s)" in capsys.readouterr().out


def test_check_catches_a_wrong_pack_sha_and_an_unknown_option(work: Path) -> None:
    pack = load_task(work / "pack.yaml")
    sha = sha256_file(work / "pack.yaml")
    ans = load_task(work / "answers_ana.yaml")
    ans["pack"]["sha256"] = "0" * 64
    found = levels(check_answers(pack, sha, ans, "a", work))
    assert any("pack sha256 differs" in m for m in found)
    ans = load_task(work / "answers_ana.yaml")
    ans["answers"]["first-function"]["value"] = "nonsense"
    ans["answers"]["no-such-item"] = {"value": "x"}
    ans["member"] = "zed"
    found = levels(check_answers(pack, sha, ans, "a", work))
    assert any("'nonsense' is not an option" in m for m in found)
    assert any("no-such-item is not an item" in m for m in found)
    assert any("member zed is not a member" in m for m in found)


def test_check_catches_pack_errors_and_replies_errors(work: Path) -> None:
    pack = load_task(work / "pack.yaml")
    pack["items"][0]["refs"] = ["nowhere"]
    pack["items"][1]["id"] = pack["items"][0]["id"]
    found = levels(check_pack(pack, "p"))
    assert any("ref nowhere" in m for m in found)
    assert any("used twice" in m for m in found)
    rep = load_task(work / "replies_ana.yaml")
    rep["replies"]["ghost"] = {"choice": "keep"}
    rep["replies"]["tc-pilot"] = {"choice": "accept", "accept_member": "ana"}
    rep["diff"] = "1" * 64
    diff = {
        "members": ["ana", "ben"],
        "points": [{"id": "tc-pilot", "answers": {"ana": {}}}],
    }
    found = levels(check_replies(["ana", "ben"], rep, "r", diff, "2" * 64))
    assert any("another diff" in m for m in found)
    assert any("ghost is not a point" in m for m in found)
    assert any("own answer" in m for m in found)
    bad = {"choice": "accept"}  # accept without accept_member breaks the schema
    rep["replies"]["tc-pilot"] = bad
    assert schema_issues(rep, "task_replies", "r")


def test_check_verifies_transcript_sha(work: Path) -> None:
    pack = load_task(work / "pack.yaml")
    sha = sha256_file(work / "pack.yaml")
    ans = load_task(work / "answers_ben.yaml")
    assert levels(check_answers(pack, sha, ans, "a", work)) == []
    (work / "transcript_ben.txt").write_text("changed", encoding="utf-8")
    assert any(
        "sha256 differs" in m for m in levels(check_answers(pack, sha, ans, "a", work))
    )
    (work / "transcript_ben.txt").unlink()
    found = levels(check_answers(pack, sha, ans, "a", work), "warning")
    assert any("file not found" in m for m in found)


def test_render_writes_md_with_mermaid_and_html_with_inline_svg(tmp_path: Path) -> None:
    assert main(["task", "render", str(PACK), "-o", str(tmp_path)]) == 0
    md = (tmp_path / "pack.md").read_text(encoding="utf-8")
    assert md.count("```mermaid") == 2  # the cycle and the relations
    assert "-->|answers for|" in md and "| Term | Definition | Source |" in md
    page = (tmp_path / "pack.html").read_text(encoding="utf-8")
    assert "<svg" in page and "marker-end" in page
    assert 'id="export"' in page and "answers_" in page and "localStorage" in page
    assert "http" not in page  # no network reference of any kind
    assert "<script src" not in page and "<link" not in page
    assert sha256_file(PACK) in page


def test_render_uses_the_language_of_the_pack(work: Path, tmp_path: Path) -> None:
    text = (
        (work / "pack.yaml").read_text(encoding="utf-8").replace("lang: en", "lang: ru")
    )
    (work / "pack.yaml").write_text(text, encoding="utf-8")
    assert main(["task", "render", str(work / "pack.yaml"), "-o", str(tmp_path)]) == 0
    assert "Проверка терминов" in (tmp_path / "pack.md").read_text(encoding="utf-8")
    assert "Файл ответов" in (tmp_path / "pack.html").read_text(encoding="utf-8")


def test_diff_classes_on_the_example(diff_dir: Path) -> None:
    diff = yaml.safe_load((diff_dir / "diff.yaml").read_text(encoding="utf-8"))
    got = points(diff)
    assert (got["first-function"]["class"], got["first-function"]["class_by"]) == (
        "conflict",
        "script",
    )
    assert (
        got["first-function"]["route"] == "call"
        and got["first-function"]["subtype"] is None
    )
    assert got["shared-risks"]["class"] == "refinement"
    assert got["shared-risks"]["route"] == "accept_unless_objected"
    assert (
        got["pilot-bakeries"]["class"] == "agreement"
        and got["pilot-bakeries"]["route"] == "accept"
    )
    assert (
        got["check-first"]["class"] == "only_one"
        and got["check-first"]["raised_by"] == "ben"
    )
    assert (
        got["add-cy-1"]["class"] == "only_one"
        and got["add-cy-1"]["route"] == "mark_each"
    )
    assert (
        got["next-steps"]["class"] == "conflict"
        and got["next-steps"]["subtype"] == "step"
    )
    for pid in ("payer-view", "tc-plant", "tc-pilot", "tc-payer"):
        assert (got[pid]["class"], got[pid]["class_by"]) == ("to_read", "model")
    assert diff["summary"]["points"] == 10
    assert (diff_dir / "diff.md").read_text(encoding="utf-8").count("```mermaid") == 1
    assert "<details" in (diff_dir / "diff.html").read_text(encoding="utf-8")


def test_diff_has_alpha_and_lists_the_transcript(diff_dir: Path) -> None:
    diff = yaml.safe_load((diff_dir / "diff.yaml").read_text(encoding="utf-8"))
    assert diff["alpha"]["choice_items"]["alpha"] == pytest.approx(0.0)
    assert set(diff["alpha"]["sections"]) == {"Scope"}
    assert diff["alpha"]["choice_items"]["reading"].endswith("few units")
    [entry] = diff["transcripts"]["ben"]
    assert entry["status"] == "ok" and entry["sha256"] == sha256_file(
        TASK / "transcript_ben.txt"
    )
    assert {f["member"]: f["drafted_by"] for f in diff["answers_files"]}[
        "ben"
    ] == "model_edited"


def test_diff_is_the_same_every_time_and_does_not_overwrite_edits(
    diff_dir: Path, tmp_path: Path
) -> None:
    again = tmp_path / "again"
    main(["task", "diff", str(PACK), *map(str, ANSWERS), "-o", str(again)])
    assert (again / "diff.yaml").read_bytes() == (diff_dir / "diff.yaml").read_bytes()
    target = diff_dir / "diff.yaml"
    target.write_text(
        target.read_text(encoding="utf-8") + "# model note\n", encoding="utf-8"
    )
    args = ["task", "diff", str(PACK), *map(str, ANSWERS), "-o", str(diff_dir)]
    assert main(args) == 2  # refused: the file keeps its edit
    assert target.read_text(encoding="utf-8").endswith("# model note\n")
    assert main([*args, "--force"]) == 0


def test_diff_refuses_answers_for_another_pack_text(work: Path, tmp_path: Path) -> None:
    pack = load_task(work / "pack.yaml")
    sha = sha256_file(work / "pack.yaml")
    text = (work / "answers_cy.yaml").read_text(encoding="utf-8").replace(sha, "a" * 64)
    (work / "answers_cy.yaml").write_text(text, encoding="utf-8")
    paths = [work / f"answers_{m}.yaml" for m in ("ana", "cy")]
    with pytest.raises(RecordError, match="pack sha256 differs"):
        load_answers(pack, sha, paths)
    with pytest.raises(RecordError, match="already answered"):
        load_answers(pack, sha, [work / "answers_ana.yaml", work / "answers_ana.yaml"])


def test_classify_structured_sets() -> None:
    assert classify_structured("multi", {"a": ["x"], "b": ["X "]})[0] == "agreement"
    assert (
        classify_structured(
            "multi", {"a": ["x"], "b": ["x", "y"], "c": ["x", "y", "z"]}
        )[0]
        == "refinement"
    )
    assert (
        classify_structured("ids", {"a": ["x", "y"], "b": ["x", "z"]})[0] == "conflict"
    )
    assert classify_structured("steps", {"a": ["s1", "s2"], "b": ["s1"]})[:2] == (
        "conflict",
        "step",
    )
    assert (
        classify_structured("steps", {"a": ["s1", "s2"], "b": ["s2", "s1"]})[0]
        == "agreement"
    )
    assert classify_structured("number", {"a": 3, "b": 3.0})[0] == "agreement"
    assert classify_structured("number", {"a": 3, "b": 4})[0] == "conflict"


def agenda_for(diff_dir: Path, members: list[str], names: list[str]) -> dict[str, Any]:
    diff_path = diff_dir / "diff.yaml"
    diff = load_task(diff_path)
    replies = [load_task(TASK / f"replies_{n}.yaml") for n in names]
    return build_agenda(diff, sha256_file(diff_path), replies, members)


def test_example_replies_carry_the_sha_of_the_example_diff(diff_dir: Path) -> None:
    sha = sha256_file(diff_dir / "diff.yaml")
    for path in REPLIES:
        assert load_task(path)["diff"] == sha, "restamp the replies (see REGENERATE)"
    code = main(
        [
            "task",
            "check",
            str(PACK),
            "--replies",
            *map(str, REPLIES),
            "--diff",
            str(diff_dir / "diff.yaml"),
        ]
    )
    assert code == 0


def test_agenda_counts_a_missing_reply_as_discuss(diff_dir: Path) -> None:
    agenda = agenda_for(diff_dir, ["ana", "ben", "cy"], ["ana", "ben"])
    assert agenda["not_replied"] == ["cy"]
    call = {p["id"]: p for p in agenda["call"]}
    assert call["tc-pilot"]["why"] == {"no_reply": ["cy"]}  # both others kept it
    assert call["first-function"]["why"] == {"discuss": ["ben"], "no_reply": ["cy"]}
    assert "add-cy-1" not in call  # cy raised it and need not reply
    assert {p["id"] for p in agenda["settled"]} == {
        "shared-risks",
        "pilot-bakeries",
        "add-cy-1",
    }


def test_agenda_with_all_replies_lists_only_discuss_points(
    diff_dir: Path, tmp_path: Path
) -> None:
    agenda = agenda_for(diff_dir, ["ana", "ben"], ["ana", "ben"])
    assert [p["id"] for p in agenda["call"]] == [
        "tc-plant",
        "first-function",
        "payer-view",
    ]
    settled = {p["id"]: p for p in agenda["settled"]}
    assert settled["next-steps"]["how"] == "replies"
    assert settled["next-steps"]["replies"] == {"ana": "keep", "ben": "accept ana"}
    assert settled["pilot-bakeries"]["how"] == "accept"
    out = tmp_path / "agenda.md"
    code = main(
        [
            "task",
            "agenda",
            str(diff_dir / "diff.yaml"),
            *map(str, REPLIES),
            "--members",
            "ana,ben",
            "-o",
            str(out),
        ]
    )
    assert code == 0 and out.with_suffix(".yaml").exists()
    assert "Points for the call" in out.read_text(encoding="utf-8")


def test_agenda_refuses_replies_for_another_diff(diff_dir: Path) -> None:
    diff = load_task(diff_dir / "diff.yaml")
    rep = load_task(TASK / "replies_ana.yaml")
    rep["diff"] = "0" * 64
    with pytest.raises(RecordError, match="diff sha256 differs"):
        build_agenda(diff, sha256_file(diff_dir / "diff.yaml"), [rep], ["ana", "ben"])


def test_build_diff_keeps_members_in_the_pack_order() -> None:
    pack = load_task(PACK)
    loaded = load_answers(pack, sha256_file(PACK), list(reversed(ANSWERS)))
    diff = build_diff(pack, sha256_file(PACK), loaded)
    assert diff["answered_by"] == member_ids(pack)


def svg_boxes(svg: str) -> list[tuple[dict[str, float], list[str]]]:
    """(rect geometry, text lines) of every box of an ontology SVG."""
    root = ElementTree.fromstring(svg)
    out = []
    for g in root.iter("g"):
        rect = g.find("rect")
        assert rect is not None
        geo = {k: float(rect.attrib[k]) for k in ("x", "y", "width", "height")}
        lines = ["".join(t.itertext()) for t in g.iter("tspan")]
        out.append((geo, lines))
    return out


def many_hypotheses() -> dict[str, Any]:
    long = "Собственник сегмента хотя бы раз называл красные линии величинами "
    elements = [{"id": f"q{i}", "label": f"В{i}. Вопрос {long}"} for i in range(3)]
    relations = []
    for n in range(14):
        elements.append({"id": f"g{n}", "label": f"Г{n}. {long * 2}длинноеслово"})
        relations.append({"from": f"g{n}", "to": f"q{n % 3}", "kind": "отвечает на"})
    return {"elements": elements, "relations": relations}


def test_ontology_svg_wraps_labels_inside_boxes_without_overlap() -> None:
    cases = [
        (many_hypotheses(), "ru"),  # many to one: grouped by target
        (load_task(PACK)["ontology"], "en"),  # rows by tier
    ]
    for onto, lang in cases:
        for width in (WIDE, NARROW):
            boxes = svg_boxes(ontology_svg(onto, lang, max_w=width))
            assert len(boxes) == len(onto["elements"])
            for geo, lines in boxes:
                assert all(
                    text_width(line) <= geo["width"] - 2 * PAD_X for line in lines
                ), "a line is wider than its box"
                assert LINE * len(lines) <= geo["height"], "a box is too low"
            words = {w for _, lines in boxes for line in lines for w in line.split()}
            assert {e["label"].split()[0] for e in onto["elements"]} <= words
            for i, (a, _) in enumerate(boxes):
                for b, _ in boxes[i + 1 :]:
                    apart = (
                        a["x"] + a["width"] <= b["x"]
                        or b["x"] + b["width"] <= a["x"]
                        or a["y"] + a["height"] <= b["y"]
                        or b["y"] + b["height"] <= a["y"]
                    )
                    assert apart, "two boxes overlap"


def test_ontology_figure_has_a_narrow_drawing_for_a_phone() -> None:
    fig = ontology_figure(many_hypotheses(), "ru")
    assert fig.count("<svg") == 2 and "onto-narrow" in fig
    assert fig.count('id="onto-w-arrow"') == 1  # the two drawings share no ids


def test_ids_item_is_a_checklist_of_labels_that_exports_ids(tmp_path: Path) -> None:
    assert main(["task", "render", str(PACK), "-o", str(tmp_path)]) == 0
    page = (tmp_path / "pack.html").read_text(encoding="utf-8")
    key = 'data-s="v:check-first"'
    assert f'<input type="text" {key}' not in page
    assert (
        f'<input type="checkbox" {key} value="fn-dough"> <span>dough production</span>'
        in page
    )
    assert 'class="ckf"' in page and 'class="ckn"' in page  # filter box and count
    assert "<legend>quality standard</legend>" in page  # grouped by relation target
    assert '"kind": "ids"' in page  # the script reads the ticked ids as a list
    md = (tmp_path / "pack.md").read_text(encoding="utf-8")
    assert "- [ ] dough production" in md and "**quality standard**" in md


def test_ref_groups_follow_the_relations() -> None:
    onto = load_task(PACK)["ontology"]
    groups = ref_groups(onto, ["fn-dough", "place-mills", "fn-logistics"])
    assert groups == [
        ("dough production", [("place-mills", "regional mills")]),
        ("quality standard", [("fn-dough", "dough production")]),
        (None, [("fn-logistics", "night logistics")]),
    ]


def test_the_russian_facilitator_label_is_vedushchiy() -> None:
    assert LABELS["ru"]["facilitator"] == "Ведущий"
    assert LABELS["en"]["facilitator"] == "Facilitator"


def test_diff_pages_show_labels_not_item_ids(diff_dir: Path) -> None:
    page = (diff_dir / "diff.html").read_text(encoding="utf-8")
    assert "<b>Item 1</b> Which function should the shared plant take first?" in page
    assert "Dough production" in page and "Night logistics" in page
    assert "Refers to: dough production; night logistics; quality standard" in page
    assert ">Ana<" in page and ">ana<" not in page
    assert "<b>first-function</b>" not in page
    md = (diff_dir / "diff.md").read_text(encoding="utf-8")
    assert "#### Item 1: Which function" in md and "| Ben | Dough production |" in md
    assert "#### first-function" not in md
    out = diff_dir / "agenda.md"
    args = ["task", "agenda", str(diff_dir / "diff.yaml"), *map(str, REPLIES)]
    assert main([*args, "--members", "ana,ben,cy", "-o", str(out)]) == 0
    agenda = out.read_text(encoding="utf-8")
    assert "### 4. Item 1: Which function" in agenda
    assert "Ana: accept Ben" in agenda and "Dough production" in agenda
    assert "accept ben" not in agenda and "first-function:" not in agenda


def test_a_diff_without_labels_is_shown_as_written(
    diff_dir: Path, tmp_path: Path
) -> None:
    diff = load_task(diff_dir / "diff.yaml")
    del diff["labels"]
    target = tmp_path / "diff.yaml"
    target.write_text(yaml.safe_dump(diff, allow_unicode=True), encoding="utf-8")
    assert main(["task", "render", str(target), "-o", str(tmp_path)]) == 0
    assert "| ben | dough |" in (tmp_path / "diff.md").read_text(encoding="utf-8")
