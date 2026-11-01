from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from smd_engine.cli import main
from smd_engine.records import RecordError, load_record
from smd_engine.story.check import check_story
from smd_engine.story.model import LEVELS, Boards
from smd_engine.validate import Finding, validate_record

from story_helpers import BOARD, CASE, case_boards, case_story


def run(story: dict[str, Any], boards: Boards | None = None) -> list[Finding]:
    return check_story(story, boards or case_boards())


def rules(found: list[Finding], level: str = "error") -> list[str]:
    """The rule of each finding of a level (`G3 sentence 2` -> `G3`)."""
    return [f.ref.split()[0] for f in found if f.level == level]


def only(
    text: str, ids: list[str] | None = None, level: str = "stated", **extra: Any
) -> dict[str, Any]:
    """The owner story with one sentence, the facts about p-founder (61 years)
    and goal-handover (3 years) at hand."""
    story = copy.deepcopy(case_story("owner"))
    story["sentences"] = [
        {
            "text": text,
            "ids": ids if ids is not None else ["p-founder", "goal-handover"],
            "level": level,
        }
    ]
    story.update(extra)
    return story


def test_the_sample_stories_pass_without_findings() -> None:
    for name in ("owner", "buyer", "bank", "successor-premortem"):
        assert run(case_story(name)) == []


def test_g1_a_sentence_needs_an_existing_id() -> None:
    found = run(only("Вам 61 год.", []))
    assert rules(found) == ["G1"] and "no id" in found[0].message
    found = run(only("Вам 61 год.", ["no-such-id", "p-founder"]))
    assert rules(found) == ["G1"] and "unknown id 'no-such-id'" in found[0].message


def test_g2_the_level_is_never_above_the_weakest_id() -> None:
    boards = case_boards()
    assert [boards.level(i) for i in ("H4", "H1", "H2", "K1", "O1", "p-founder")] == [
        "checked",
        "hypothesis",
        "hypothesis",
        "hypothesis",
        "hypothesis",
        "stated",
    ]
    assert boards.level("sig-august") == "checked"
    assert boards.level("fact-revenue") == "unverified"
    found = run(only("Вам 61 год.", ["p-founder", "H1"], "stated"))
    assert rules(found) == ["G2"] and "'H1' is only hypothesis" in found[0].message
    assert rules(run(only("Вам 61 год.", ["p-founder", "H1"], "hypothesis"))) == []
    story = only("Выручка 2025 года 0,95 млн евро.", ["fact-revenue"], "stated")
    story["allow"].append("fact-revenue")
    assert rules(run(story)) == ["G2"]


def test_g2_levels_of_theses_closed_k_and_refuted_hypotheses() -> None:
    boards = case_boards()
    boards.items["T1"] = ("thesis", {"id": "T1", "status": "voiced"})
    boards.items["T2"] = ("thesis", {"id": "T2", "status": "assumption"})
    boards.items["T3"] = ("thesis", {"id": "T3", "status": "ai_variant"})
    boards.items["T4"] = ("thesis", {"id": "T4", "status": "refined"})
    boards.items["K9"] = ("qualification", {"id": "K9", "status": "closed"})
    boards.items["H9"] = ("hypothesis", {"id": "H9", "status": "refuted"})
    boards.items["H8"] = ("hypothesis", {"id": "H8", "status": "testing"})
    got = {i: boards.level(i) for i in ("T1", "T2", "T3", "T4", "K9", "H9", "H8")}
    assert got == {
        "T1": "stated",
        "T2": "hypothesis",
        "T3": "hypothesis",
        "T4": "stated",
        "K9": "stated",
        "H9": "checked",
        "H8": "hypothesis",
    }
    assert LEVELS == ("hypothesis", "unverified", "stated", "checked")


def test_g2_hints_modal_words_and_facts_worded_without_any() -> None:
    found = run(only("Возможно, вам 61 год.", ["p-founder"], "stated"))
    hints = [f for f in found if f.level == "hint"]
    assert [f.ref.split()[0] for f in hints] == ["G2"]
    assert "возможно" in hints[0].message.lower()
    found = run(only("Вам 61 год.", ["p-founder", "H1"], "hypothesis"))
    assert any("no modal word" in f.message for f in found if f.level == "hint")
    assert rules(run(only("Вам 61 год.", ["p-founder"], "stated")), "hint") == []


def test_g3_a_number_must_be_in_an_id() -> None:
    found = run(only("Вам 62 года."))
    assert rules(found) == ["G3"] and "number 62" in found[0].message
    assert rules(run(only("Вам 61 год."))) == []


@pytest.mark.parametrize(
    "text,ok",
    [
        ("Вам 61 год.", True),
        ("Дело за 3 года.", True),
        ("Дело за три года.", True),
        ("Дело за трёх лет.", True),
        ("Дело за четыре года.", False),
        ("Выручка выросла вдвое.", False),
        ("Половина смен идёт без записи.", False),
        ("Прошло полтора года.", False),
        ("Записей было дважды по пять.", False),
        ("Вам шестьдесят один год.", True),  # 60 and 1 are summed to 61
        ("Вам шестьдесят год.", False),
        ("Дело за двадцать пять лет.", False),  # 25, not 20 and 5: none on the ids
    ],
)
def test_g3_number_words_are_numbers(text: str, ok: bool) -> None:
    assert (rules(run(only(text))) == []) == ok


def test_g3_the_form_constant_is_allowed_only_in_its_form() -> None:
    story = copy.deepcopy(case_story("successor-premortem"))
    story["sentences"] = [
        {"text": "Прошло три года.", "ids": ["H5", "fn-train"], "level": "hypothesis"}
    ]
    assert rules(run(story)) == []
    for form in ("scqa", "scenarios"):
        story["form"] = form
        assert rules(run(story)) == ["G3"]
    story["form"] = "scenarios"
    story["sentences"][0]["text"] = "Есть два сценария."
    assert rules(run(story)) == []


def test_g3_reads_the_days_a_red_line_was_breached() -> None:
    boards = case_boards()
    assert 14 in boards.numbers("rl-dialin")
    assert {(2026, 8, 3), (2026, 8, 17)} <= boards.date_facts("rl-dialin")
    assert 92 in boards.numbers("rl-cover")
    assert 14 not in boards.numbers("fn-train")


def test_g3_dates_in_ids_are_not_loose_numbers() -> None:
    boards = case_boards()
    # the month and day of 2026-06-30 and 2026-09-30 are not numbers of the id
    assert not {6, 9, 30} & boards.numbers("rl-cover")
    assert (2026, 6, 30) in boards.date_facts("rl-cover")


def _bank_with(old: str, new: str) -> dict[str, Any]:
    story = copy.deepcopy(case_story("bank"))
    for sentence in story["sentences"]:
        sentence["text"] = sentence["text"].replace(old, new)
    return story


def test_g3_a_month_or_day_of_a_cited_date_does_not_pass_as_a_figure() -> None:
    assert rules(run(case_story("bank"))) == []
    # 9 is the month of 2026-09-30, 3 the month of 2026-03-31
    found = run(_bank_with("1,1 в июне", "9 в июне"))
    assert rules(found) == ["G3"] and "number 9" in found[0].message
    found = run(_bank_with("длиннее восстановления", "втрое длиннее восстановления"))
    assert rules(found) == ["G3"] and "number 3" in found[0].message


def test_g3_a_date_in_a_sentence_matches_a_whole_date_of_an_id() -> None:
    assert rules(run(_bank_with("30 июня", "30 июня 2026 года"))) == []
    assert rules(run(_bank_with("30 июня", "2026-06-30"))) == []
    assert rules(run(_bank_with("30 июня", "30.06.2026"))) == []
    found = run(_bank_with("30 июня", "29 июня"))
    assert rules(found) == ["G3"] and "date ?-06-29" in found[0].message
    found = run(_bank_with("30 июня", "30 июня 2025 года"))
    assert rules(found) == ["G3"] and "date 2025-06-30" in found[0].message
    # a day and a month the ids do not hold together, though each is a month
    # and a day of some date of theirs
    assert rules(run(_bank_with("30 июня", "30 марта"))) == ["G3"]


def test_g4_ids_must_be_in_the_allow_list() -> None:
    story = only("Вам 61 год.", ["p-founder", "fact-revenue"], "unverified")
    found = run(story)
    assert rules(found) == ["G4"] and "'fact-revenue'" in found[0].message
    story["allow"].append("fact-revenue")
    assert rules(run(story)) == []


def test_g5_an_opposition_touching_the_path_stays_in_the_conflict() -> None:
    story = copy.deepcopy(case_story("buyer"))
    story["path"] = [
        "place-buyer",
        "fn-journal",
        "sig-august",
        "nb-qual",
        "fn-train",
        "place-successor",
        "coop-transfer",
    ]
    story["conflict"] = ["nb-qual"]
    found = run(story)
    assert rules(found) == ["G5"] and "sig-august" in found[0].message
    story["conflict"] = ["sig-august", "nb-qual"]
    assert rules(run(story)) == []


def _founder_label(label: str) -> Boards:
    boards = case_boards()
    boards.items["p-founder"][1]["label"] = label
    return boards


def test_g3_summed_number_words_against_the_ids() -> None:
    story = only("Прошло двадцать пять лет.", ["p-founder", "goal-handover"])
    assert rules(run(story)) == ["G3"]
    assert rules(run(story, _founder_label("основатель, стаж 25 лет"))) == []
    # 20 and 5 on the id are not 25
    found = run(story, _founder_label("основатель, 20 лет и 5 месяцев"))
    assert rules(found) == ["G3"] and "number 25" in found[0].message


def test_g6_comparatives_without_a_number_are_hints() -> None:
    found = run(only("Это лучше всех.", ["p-founder"]))
    assert rules(found, "hint") == ["G6"] and "лучше" in found[0].message
    assert rules(run(only("Это лучше на 61 %.", ["p-founder"])), "hint") == []
    found = run(only("Это самый крупный покупатель.", ["p-founder"]))
    assert rules(found, "hint") == ["G6"]
    found = run(only("This is the best option.", ["p-founder"]))
    assert rules(found, "hint") == ["G6"]
    # «уже» is the adverb "already" unless «чем» follows
    assert rules(run(only("Покупатель уже видел журнал.", ["p-founder"])), "hint") == []
    found = run(only("Это уже чем у других.", ["p-founder"]))
    assert rules(found, "hint") == ["G6"] and "уже" in found[0].message
    comma = run(only("Это уже, чем у других.", ["p-founder"]))
    assert rules(comma, "hint") == ["G6"]


def test_g7_voice_and_stamp() -> None:
    story = copy.deepcopy(case_story("owner"))
    story["voice"] = "participant"
    assert rules(run(story)) == ["G7"]
    story = copy.deepcopy(case_story("owner"))
    story["voice"] = "ИИ"
    assert run(story) == []
    story["boards"][0]["version"] = "2.0"
    found = run(story)
    assert rules(found) == ["G7"] and "regenerate" in found[0].message
    story = copy.deepcopy(case_story("owner"))
    story["boards"][0]["sha256"] = "0" * 64
    assert "sha256" in run(story)[0].message


def test_g7_a_changed_board_file_fails_the_stamp(tmp_path: Path) -> None:
    from smd_engine.story.model import load_boards

    changed = tmp_path / "copy.board.yaml"
    changed.write_text(
        BOARD.read_text(encoding="utf-8") + "\n# edit\n", encoding="utf-8"
    )
    boards = load_boards([changed])
    found = run(case_story("owner"), boards)
    assert rules(found) == ["G7"] and "sha256" in found[0].message


def test_structure_path_links_conflict_and_resolution() -> None:
    story = copy.deepcopy(case_story("bank"))
    story["path"][1] = "fn-shot"  # place-bank - fn-shot: no link
    found = run(story)
    assert "S2" in rules(found) and "place-bank - fn-shot" in found[0].ref
    story = copy.deepcopy(case_story("bank"))
    story["conflict"] = ["sig-august"]  # not on the path, not opposed to it
    assert rules(run(story)) == ["S3", "S4"]
    story = copy.deepcopy(case_story("bank"))
    story["resolution"] = []
    assert rules(run(story), "warning") == ["S3"]
    story = copy.deepcopy(case_story("bank"))
    story["open"] = ["fn-books"]
    assert rules(run(story)) == ["S1"]
    story = copy.deepcopy(case_story("bank"))
    story["path"][0] = "no-such-element"
    assert "S1" in rules(run(story))


def test_s4_the_path_is_4_to_9_items_with_a_conflict_before_the_resolution() -> None:
    story = copy.deepcopy(case_story("bank"))
    story["path"] = ["place-bank", "fn-books"]
    story["conflict"], story["resolution"] = ["place-bank"], ["fn-books"]
    found = run(story)
    assert rules(found) == ["S4"] and "2 items" in found[0].message
    story = copy.deepcopy(case_story("bank"))
    story["path"] = [
        "place-bank",
        "coop-transfer",
        "place-buyer",
        "fn-tranche",
        "rl-cover",
    ]
    found = run(story)  # the resolution is before the conflict
    assert rules(found) == ["S4"] and "comes before" in found[0].message
    story = copy.deepcopy(case_story("bank"))
    assert rules(run(story)) == []


def test_a_weak_link_on_the_path_is_a_warning() -> None:
    story = copy.deepcopy(case_story("owner"))
    story["path"] = ["fact-staff", "s-small"]  # joined by a refers
    assert rules(run(story), "warning") == ["S2"]


# --- the schema ---


def test_schema_accepts_the_samples_and_refuses_a_broken_story() -> None:
    for name in ("owner", "buyer", "bank", "successor-premortem"):
        assert validate_record(case_story(name)) == []
    story = copy.deepcopy(case_story("owner"))
    del story["allow"]
    story["form"] = "essay"
    story["sentences"][0]["level"] = "sure"
    story["boards"][0]["sha256"] = "abc"
    story["extra"] = 1
    messages = " ".join(f.message for f in validate_record(story))
    assert "allow" in messages and "essay" in messages and "sure" in messages
    assert "abc" in messages and "extra" in messages
    assert [f.level for f in check_story(story, case_boards())] == ["error"] * len(
        validate_record(story)
    )


def test_schema_version_and_empty_story_are_refused() -> None:
    story = copy.deepcopy(case_story("owner"))
    story["schema_version"] = "0.2"
    assert "schema 0.2" in validate_record(story)[0].message
    story = copy.deepcopy(case_story("owner"))
    story["sentences"] = []
    story["conflict"] = []
    assert len(validate_record(story)) == 2


def test_validate_command_reads_story_files(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate", str(CASE)]) == 0
    out = capsys.readouterr().out
    assert "owner.story.yaml" in out and "0 error(s)" in out


# --- the command ---


def test_cli_check_exit_codes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    owner = str(CASE / "owner.story.yaml")
    assert main(["story", "check", owner, "--boards", str(BOARD)]) == 0
    assert "0 error(s), 0 warning(s), 0 hint(s)" in capsys.readouterr().out
    broken = copy.deepcopy(case_story("owner"))
    broken["sentences"][0]["text"] = "Вам 62 года."
    path = tmp_path / "broken.story.yaml"
    path.write_text(yaml.safe_dump(broken, allow_unicode=True), encoding="utf-8")
    assert main(["story", "check", str(path), "--boards", str(BOARD)]) == 1
    assert "error: G3 sentence 1" in capsys.readouterr().out
    assert (
        main(["story", "check", str(path), "--boards", str(tmp_path / "none.yaml")])
        == 2
    )
    with pytest.raises(RecordError):
        load_record(tmp_path / "none.story.yaml")
    assert main(["story", "check", str(BOARD), "--boards", str(BOARD)]) == 2
