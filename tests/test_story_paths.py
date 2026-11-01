from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from smd_engine.cli import main
from smd_engine.story.gaps import gap_report, suggest
from smd_engine.story.model import Boards
from smd_engine.story.paths import (
    MAX_LEN,
    MIN_LEN,
    conflict_objects,
    enumerate_candidates,
    skeleton,
    walk_text,
)

from story_helpers import BOARD, STORIES, case_boards, case_story, mini


def test_candidates_are_simple_typed_walks_through_a_conflict_to_a_resolution() -> None:
    boards = case_boards()
    found, truncated = enumerate_candidates(boards, "p-founder")
    assert found and not truncated
    conflict = conflict_objects(boards)
    for c in found:
        assert MIN_LEN <= len(c.path) <= MAX_LEN
        assert len(set(c.path)) == len(c.path)
        assert c.path[0] == "p-founder"
        assert c.weak == 0 and all(not s.link.weak for s in c.steps)
        assert set(c.path[:-1]) & conflict
        assert c.resolution == c.path[-1]
        assert all(
            s.a == p and s.b == q for s, p, q in zip(c.steps, c.path, c.path[1:])
        )


def test_conflict_objects_cover_the_four_kinds() -> None:
    conflict = conflict_objects(case_boards())
    assert {"sig-august", "nb-qual"} <= conflict  # an opposes pair
    assert {"rl-dialin", "rl-cover"} <= conflict  # red lines in breach
    assert {"gl-handover", "ev-trial", "ev-sign", "ev-intro"} <= conflict  # a series


def test_order_is_lexicographic_and_stable() -> None:
    found, _ = enumerate_candidates(case_boards(), "place-bank")
    assert [c.key for c in found] == sorted(c.key for c in found)
    again, _ = enumerate_candidates(case_boards(), "place-bank")
    assert [c.path for c in again] == [c.path for c in found]
    # share, best rank, items, components, backward links, ids
    assert all(c.key[2] == len(c.path) for c in found)
    assert all(c.key[-1] == tuple(c.path) for c in found)


def test_a_shorter_walk_comes_before_a_longer_one_that_meets_more_hypotheses() -> None:
    found, _ = enumerate_candidates(case_boards(), "place-bank")
    longest = max(found, key=lambda c: (len(c.path), len(c.open)))
    assert len(longest.path) == MAX_LEN
    assert len(longest.open) >= len(found[0].open)
    assert max(len(c.path) for c in found[:5]) < MAX_LEN
    assert found.index(longest) > 5


def test_a_walk_that_meets_a_resolution_object_first_is_refused(
    tmp_path: Path,
) -> None:
    coop2 = {"id": "coop2", "board": "oo", "kind": "cooperation", "label": "c2"}
    chain = [
        {"from": "p1", "to": "coop1", "kind": "flow", "carries": "information"},
        {"from": "coop1", "to": "fn1", "kind": "flow", "carries": "information"},
        {"from": "fn1", "to": "nb1", "kind": "uses"},
        {"from": "coop2", "to": "nb1", "kind": "uses"},
    ]
    boards = mini(tmp_path, chain, [coop2])
    # p1 - coop1 - fn1 - nb1 - coop2 reaches the resolution coop1 before the conflict
    assert enumerate_candidates(boards, "p1")[0] == []
    # the same shape with a function in place of coop1 is a walk
    chain[0:2] = [
        {"from": "p1", "to": "fn2", "kind": "flow", "carries": "information"},
        {"from": "fn2", "to": "fn1", "kind": "flow", "carries": "product"},
    ]
    found, _ = enumerate_candidates(mini(tmp_path, chain, [coop2]), "p1")
    assert [c.path for c in found] == [["p1", "fn2", "fn1", "nb1", "coop2"]]


@pytest.mark.parametrize("name", STORIES)
def test_the_stories_of_the_case_follow_listed_walks(name: str) -> None:
    boards = case_boards()
    story = case_story(name)
    # the walks `smd story paths` shows by default (--limit 5)
    found, _ = enumerate_candidates(boards, story["protagonist"], limit=5)
    match = [c for c in found if c.path == story["path"]]
    assert match, "the story's path is not among the top 5 walks of the boards"
    cand = match[0]
    assert set(story["conflict"]) == set(cand.conflict)
    assert story["resolution"] == [cand.resolution] or set(story["resolution"]) <= set(
        cand.path
    )
    assert set(story["open"]) <= set(cand.open)


def test_leverage_order_puts_the_walk_with_the_stronger_hypothesis_first() -> None:
    boards = case_boards()
    found, _ = enumerate_candidates(boards, "p-founder")
    ranks = [(c.key[0], c.key[1]) for c in found]
    assert ranks == sorted(ranks)


def test_refers_is_walked_only_on_request_and_marked(tmp_path: Path) -> None:
    boards = mini(
        tmp_path,
        [
            {"from": "p1", "to": "fn1", "kind": "flow", "carries": "money"},
            {"from": "fn1", "to": "fn2", "kind": "flow", "carries": "product"},
            {"from": "fn2", "to": "nb1", "kind": "uses"},
            {"from": "nb1", "to": "coop1", "kind": "refers"},
        ],
    )
    assert enumerate_candidates(boards, "p1")[0] == []
    found, _ = enumerate_candidates(boards, "p1", allow_refers=True)
    assert len(found) == 1 and found[0].weak == 1
    assert "~refers~" in walk_text(found[0])
    assert found[0].typed_share < 1


def test_typed_share_orders_before_anything_else(tmp_path: Path) -> None:
    boards = mini(
        tmp_path,
        [
            {"from": "p1", "to": "fn1", "kind": "flow", "carries": "money"},
            {"from": "fn1", "to": "fn2", "kind": "flow", "carries": "product"},
            {"from": "fn2", "to": "nb1", "kind": "uses"},
            {"from": "coop1", "to": "nb1", "kind": "uses"},
            {"from": "fn1", "to": "nb1", "kind": "refers"},
        ],
    )
    found, _ = enumerate_candidates(boards, "p1", allow_refers=True)
    shares = [c.typed_share for c in found]
    assert len(found) == 2 and shares == sorted(shares, reverse=True)
    assert found[0].weak == 0 and found[1].weak == 1
    assert enumerate_candidates(boards, "p1")[0][0].path == found[0].path


def test_skeleton_is_a_story_file_without_sentences() -> None:
    boards = case_boards()
    cand = enumerate_candidates(boards, "place-bank", limit=1)[0][0]
    sk = skeleton(boards, cand, "place-bank", "place-bank", "scqa")
    assert sk["record"] == "story" and sk["sentences"] == [] and sk["voice"] == "ai"
    assert sk["boards"] == boards.stamps
    assert set(cand.path) <= set(sk["allow"])


def test_gaps_report_a_weak_walk_and_a_missing_link(tmp_path: Path) -> None:
    weak = mini(
        tmp_path,
        [
            {"from": "p1", "to": "fn1", "kind": "flow", "carries": "money"},
            {"from": "fn1", "to": "fn2", "kind": "flow", "carries": "product"},
            {"from": "fn2", "to": "nb1", "kind": "uses"},
            {"from": "nb1", "to": "coop1", "kind": "refers"},
        ],
    )
    rep = gap_report(weak, "p1", "p1")
    assert rep.status == "gap" and rep.weak == 1
    assert [(m.a, m.b, m.now) for m in rep.missing] == [("nb1", "coop1", "refers")]
    assert rep.missing[0].kind == "flow" and rep.missing[0].carries == "information"


def test_gaps_join_two_parts_of_the_graph(tmp_path: Path) -> None:
    apart = mini(
        tmp_path,
        [
            {"from": "p1", "to": "fn1", "kind": "flow", "carries": "money"},
            {"from": "fn1", "to": "fn2", "kind": "flow", "carries": "product"},
            {"from": "fn2", "to": "nb1", "kind": "uses"},
        ],
    )
    rep = gap_report(apart, "p1", "p1")
    assert rep.status == "gap"
    assert rep.component == 4 and rep.conflict == ["nb1"] and rep.resolution == []
    assert [(m.a, m.b, m.now) for m in rep.missing] == [("nb1", "coop1", "none")]
    assert rep.route == ["p1", "fn1", "fn2", "nb1", "coop1"]


def test_gap_costs_are_compared_lexicographically_without_weights() -> None:
    from smd_engine.story.gaps import (
        STEP_BOARD,
        STEP_MENTION,
        STEP_OTHER,
        STEP_REFERS,
        STEP_TYPED,
        ZERO,
        _plus,
    )

    steps = [STEP_OTHER, STEP_BOARD, STEP_MENTION, STEP_REFERS, STEP_TYPED]
    assert steps == sorted(steps, reverse=True)
    # no number of weaker steps adds up to one stronger step
    many = ZERO
    for _ in range(50):
        many = _plus(many, STEP_REFERS)
    assert many < STEP_MENTION < STEP_BOARD < STEP_OTHER
    three_refers = _plus(_plus(STEP_REFERS, STEP_REFERS), STEP_REFERS)
    assert three_refers < STEP_MENTION


def test_gaps_for_a_pair_with_a_typed_walk() -> None:
    rep = gap_report(case_boards(), "place-bank", "place-bank")
    assert rep.status == "path" and rep.typed and not rep.missing


def test_suggested_kinds_follow_the_ends() -> None:
    boards = case_boards()
    assert suggest(boards, "sig-august", "nb-qual")[2] == "opposes"
    assert suggest(boards, "nb-qual", "sig-august")[:3] == (
        "sig-august",
        "nb-qual",
        "opposes",
    )
    assert suggest(boards, "fn-dialin", "fn-shot")[2:] == ("flow", "product")
    assert suggest(boards, "p-founder", "fn-dialin")[2:] == ("flow", "money")
    assert suggest(boards, "fn-journal", "coop-transfer")[2:] == ("flow", "information")


def test_boards_with_a_repeated_id_are_refused(tmp_path: Path) -> None:
    from smd_engine.records import RecordError
    from smd_engine.story.model import load_boards

    mini(tmp_path)
    with pytest.raises(RecordError, match="is in board sets"):
        load_boards([tmp_path / "mini.board.yaml", _copy(tmp_path)])


def _copy(tmp_path: Path) -> Path:
    other = tmp_path / "other.board.yaml"
    other.write_text(
        (tmp_path / "mini.board.yaml").read_text().replace("id: mini", "id: mini2"),
        encoding="utf-8",
    )
    return other


def test_cli_paths_text_yaml_and_errors(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        main(["story", "paths", str(BOARD), "--audience", "place-bank", "--limit", "2"])
        == 0
    )
    out = capsys.readouterr().out
    assert "2 walk(s) of 4-9 items" in out and "walk: place-bank" in out
    assert (
        main(
            [
                "story",
                "paths",
                str(BOARD),
                "--audience",
                "place-bank",
                "--limit",
                "2",
                "--yaml",
            ]
        )
        == 0
    )
    docs = list(yaml.safe_load_all(capsys.readouterr().out))
    assert (
        len(docs) == 2 and docs[0]["record"] == "story" and docs[0]["sentences"] == []
    )
    assert main(["story", "paths", str(BOARD), "--audience", "nope"]) == 2
    assert (
        main(
            [
                "story",
                "paths",
                str(BOARD),
                "--audience",
                "a",
                "--audience",
                "b",
                "--protagonist",
                "p-lead",
            ]
        )
        == 2
    )


def test_cli_gaps(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(["story", "paths", str(BOARD), "--gaps", "--audience", "place-bank"]) == 0
    )
    assert "a typed walk exists" in capsys.readouterr().out


def test_kinds_of_ends_are_elements_of_the_boards() -> None:
    boards: Boards = case_boards()
    for name in STORIES:
        story = case_story(name)
        assert story["audience"] in boards.elements
        assert story["protagonist"] in boards.elements


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("fn-dialin", "rl-dialin", ("fn-dialin", "rl-dialin", "uses", None)),
        ("p-founder", "goal-handover", ("p-founder", "goal-handover", "uses", None)),
        ("goal-handover", "p-founder", ("p-founder", "goal-handover", "uses", None)),
        (
            "coop-transfer",
            "goal-handover",
            ("coop-transfer", "goal-handover", "produces", None),
        ),
        (
            "goal-handover",
            "coop-transfer",
            ("coop-transfer", "goal-handover", "produces", None),
        ),
        ("p-founder", "p-lead", ("p-founder", "p-lead", "shift", None)),
        ("fn-shot", "p-lead", ("fn-shot", "p-lead", "flow", "product")),
        ("fn-dialin", "fn-shot", ("fn-dialin", "fn-shot", "flow", "product")),
        (
            "coop-transfer",
            "place-bank",
            ("coop-transfer", "place-bank", "flow", "product"),
        ),
        ("rl-dialin", "fn-dialin", ("fn-dialin", "rl-dialin", "uses", None)),
        ("s-small", "fn-dialin", ("s-small", "fn-dialin", "flow", "information")),
        ("ev-trial", "ev-intro", ("ev-trial", "ev-intro", "belongs", None)),
    ],
)
def test_suggested_link_by_kinds_and_direction(
    a: str, b: str, expected: tuple[str, str, str, str | None]
) -> None:
    assert suggest(case_boards(), a, b) == expected
