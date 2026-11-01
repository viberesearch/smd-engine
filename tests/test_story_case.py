"""The invented Spectra Coffee case stays valid and its stories stay checked:
a change to the board that is not followed by new stories fails here (G7)."""

from __future__ import annotations

import collections
import re
from pathlib import Path

import pytest

from smd_engine.cli import main
from smd_engine.records import dump_record, load_record
from smd_engine.redline import breaches
from smd_engine.story.check import check_story
from smd_engine.story.render import render_story_md
from smd_engine.story.paths import conflict_objects
from smd_engine.validate import taxonomy_values, validate_record

from story_helpers import BOARD, CASE, STORIES, case_boards, case_story


def board() -> dict:
    return load_record(BOARD)


def test_the_board_validates_with_no_error_and_no_warning() -> None:
    manifest = load_record(CASE / "sources.yaml")
    ids = {s["id"] for s in manifest["sources"]}
    kinds = {s["id"]: s["kind"] for s in manifest["sources"]}
    tax = taxonomy_values(load_record(CASE / "taxonomies.yaml"))
    found = validate_record(board(), ids, None, tax, kinds)
    assert [f for f in found if f.level != "hint"] == []


@pytest.mark.parametrize("name", STORIES)
def test_each_story_passes_the_check_with_no_finding(name: str) -> None:
    assert check_story(case_story(name), case_boards()) == []


def test_the_command_checks_all_four_stories() -> None:
    for name in STORIES:
        story = str(CASE / f"{name}.story.yaml")
        assert main(["story", "check", story, "--boards", str(BOARD)]) == 0


def test_the_commands_read_the_sources_and_taxonomies_like_validate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sources, tax = str(CASE / "sources.yaml"), str(CASE / "taxonomies.yaml")
    flags = ["--sources", sources, "--taxonomies", tax]
    story = str(CASE / "owner.story.yaml")
    assert main(["story", "check", story, "--boards", str(BOARD), *flags]) == 0
    assert main(["story", "paths", str(BOARD), "--audience", "place-bank", *flags]) == 0
    # a manifest without a cited source: the board set is invalid
    manifest = load_record(CASE / "sources.yaml")
    manifest["sources"] = [s for s in manifest["sources"] if s["id"] != "s-log"]
    short = tmp_path / "sources.yaml"
    short.write_text(dump_record(manifest), encoding="utf-8")
    capsys.readouterr()
    bad = ["--sources", str(short)]
    assert main(["story", "check", story, "--boards", str(BOARD), *bad]) == 2
    assert "s-log" in capsys.readouterr().err
    assert main(["story", "paths", str(BOARD), "--audience", "place-bank", *bad]) == 2
    # a taxonomy file that is not one
    assert (
        main(["story", "paths", str(BOARD), "--audience", "x", "--taxonomies", sources])
        == 2
    )


def test_rendered_pages_show_in_their_header_that_the_example_is_invented(
    tmp_path: Path,
) -> None:
    out = tmp_path / "bundle"
    args = ["--sources", str(CASE / "sources.yaml"), "--taxonomies"]
    assert (
        main(
            [
                "publish",
                str(BOARD),
                "--out",
                str(out),
                *args,
                str(CASE / "taxonomies.yaml"),
            ]
        )
        == 0
    )
    pages = sorted(out.glob("*.html"))
    assert len(pages) >= 4
    for page in pages:
        html = page.read_text(encoding="utf-8")
        header = re.search(r"<h1>(.*?)</h1>", html)
        title = re.search(r"<title>(.*?)</title>", html)
        shown = (header or title).group(1) if (header or title) else ""
        assert "вымышленный пример" in shown.lower(), page.name


def test_render_writes_a_story_as_readable_markdown(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    story = case_story("bank")
    text = render_story_md(story, case_boards())
    assert text.startswith("# Вымышленный пример: история для банка")
    assert "- Для: банк, финансирующий покупателя (вымышленный) [place-bank]" in text
    assert "## Ситуация" in text and "## Осложнение" in text
    for sentence in story["sentences"]:
        assert f"{sentence['text']} [{', '.join(sentence['ids'])}]" in text
    assert "## Открытые вопросы" in text and "- [H3] Банк финансирует покупку" in text
    stamp = story["boards"][0]
    assert f"{stamp['id']}, {stamp['version']}, sha256 {stamp['sha256'][:12]}" in text
    assert "voice: ai" in text and "не подписан" in text
    # without the boards an open question is its id
    assert "- [H3]\n" in render_story_md(story)
    out = tmp_path / "bank.md"
    path = str(CASE / "bank.story.yaml")
    assert (
        main(["story", "render", path, "--md", "--boards", str(BOARD), "-o", str(out)])
        == 0
    )
    assert out.read_text(encoding="utf-8") == text
    assert main(["story", "render", path, "--md"]) == 0
    assert "[place-bank, place-buyer, s-small]" in capsys.readouterr().out
    assert main(["story", "render", str(BOARD), "--md"]) == 2
    en = render_story_md(story, case_boards(), "en")
    assert "## Situation" in en and "- For:" in en


def test_every_title_and_source_says_the_business_is_invented() -> None:
    assert "Вымышленный пример" in board()["title"]
    assert "ВЫМЫШЛЕННЫЙ ПРИМЕР" in board()["notes"]
    for name in STORIES:
        assert "Вымышленный пример" in case_story(name)["title"]
        assert "черновик ИИ" in case_story(name)["title"]
    for src in load_record(CASE / "sources.yaml")["sources"]:
        assert "вымышленн" in src["title"].lower() or "вымышленн" in src.get("note", "")
    for el in board()["elements"]:
        assert el["lineage"] == ["fictional"] and el["voice"] == "ai"


def test_all_six_tiers_are_tagged() -> None:
    tiers = collections.Counter(
        t for el in board()["elements"] for t in el.get("tags", {}).get("tier", [])
    )
    assert set(tiers) == {
        "intent",
        "model",
        "entity",
        "product",
        "process",
        "organisation",
    }


def test_red_lines_carry_a_corridor_or_yes_no_recovery_and_observations() -> None:
    lines = [e for e in board()["elements"] if e.get("red_line")]
    assert {e["id"] for e in lines} == {"rl-dialin", "rl-cover"}
    kinds = set()
    for el in lines:
        assert el["line"]["recovery_days"] and el["observed"]
        kinds.add("expect" if "expect" in el["line"] else "corridor")
        assert breaches(el, board()["date"])
    assert kinds == {"expect", "corridor"}


def test_the_board_has_flows_with_carries_opposes_and_a_series_of_events() -> None:
    rels = board()["relations"]
    flows = [r for r in rels if r["kind"] == "flow"]
    assert flows and all(r.get("carries") for r in flows)
    assert any(r["kind"] == "opposes" for r in rels)
    assert sum(r["kind"] == "belongs" for r in rels) >= 3
    assert {"nb-qual", "gl-handover"} <= conflict_objects(case_boards())
    typed = [h for h in board()["hypotheses"] if h.get("rule")]
    assert len(typed) >= 3
