from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from smd_engine.cli import main
from smd_engine.leverage import leverage_order, natural_key, reach
from smd_engine.records import dump_record
from smd_engine.status import render_status

C2 = Path(__file__).resolve().parents[1] / "cases/example/bakeries-c2.board.yaml"


def hypothesis(id_: str, **fields: Any) -> dict[str, Any]:
    return {"id": id_, "status": "untested", "assumes": id_, **fields}


def test_status_sections_of_a_small_record(board2: dict[str, Any]) -> None:
    text = render_status(board2, "en")
    assert text.startswith("# Bakeries, screen after session 2")
    for expected in (
        "- **State:** cycle 2 (version 0.2), draft; revises bakeries-c1; accepted 2; open 2",
        "- **What failed:** session 1 left the plant without a payer",
        "## Open and partly answered K (1)",
        "## Hypotheses in testing (1)",
        "## Waiting for a human sign-off",
        "- AI variants of theses 1: T3",
        "## Transitions (2)",
        "## Counts: elements 15",
        "- by board: ",
        "- by kind: ",
    ):
        assert expected in text, expected
    # H1 is confirmed and H2 testing: no untested section
    assert "Untested" not in text and len(text.splitlines()) < 30


def test_status_cuts_long_lists_with_and_n_more(board2: dict[str, Any]) -> None:
    data = copy.deepcopy(board2)
    data["qualifications"] = [
        {
            "id": f"K{n}",
            "targets": ["f-new"],
            "text": f"remark {n}",
            "by": "x",
            "status": "partly" if n % 2 else "open",
            "raised_in": 1,
        }
        for n in range(1, 13)
    ]
    data["hypotheses"] = [hypothesis(f"H{n}", targets=["f-new"]) for n in range(1, 10)]
    text = render_status(data, "en")
    assert "## Open and partly answered K (12)" in text
    assert text.count("- and 4 more") == 2  # 12 K with 8 shown, 9 H with 5 shown
    assert "## Untested hypotheses by reach (a proposal; the group chooses) (9)" in text
    assert text.count("(reach ") == 5
    # open before partly: K2 (open) is shown before K1 (partly)
    assert text.index("- K2 (open)") < text.index("- K1 (partly)")


def test_status_in_russian_uses_the_label_tables(board2: dict[str, Any]) -> None:
    text = render_status(board2, "ru")
    assert "## Открытые и частично закрытые K (1)" in text
    assert "- K1 (открыто):" in text
    assert "## Ждут подписи человека" in text
    assert "## Переходы (2)" in text and "Счёт" in text


def test_cli_status_prints_or_writes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["status", str(C2), "--lang", "en"]) == 0
    printed = capsys.readouterr().out
    out = tmp_path / "out" / "status.md"
    assert main(["status", str(C2), "--lang", "en", "-o", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == printed


def test_leverage_counts_what_a_refutation_reaches() -> None:
    record: dict[str, Any] = {
        "relations": [
            {"from": "a", "to": "b", "kind": "flow"},
            {"from": "c", "to": "a", "kind": "flow"},
            {"from": "a", "to": "b", "kind": "refers"},  # same neighbour: once
            {"from": "a", "to": "d", "kind": "refers"},
            {"from": "x", "to": "y", "kind": "flow"},  # not near a target
        ],
        "theses": [
            {"id": "T1", "feeds": ["a"]},
            {"id": "T2", "about": ["a"], "feeds": ["z"]},
            {"id": "T3", "feeds": ["z"]},
        ],
        "ontology": [{"id": "O1", "test": "H1"}, {"id": "O2", "test": "H9"}],
    }
    found = reach(record, hypothesis("H1", targets=["a"], qualifications=["K1", "K2"]))
    assert found["targets"] == {"a"} and found["K"] == {"K1", "K2"}
    assert found["O"] == {"O1"} and found["T"] == {"T1", "T2"}
    assert found["near"] == {"b", "c", "d"}


def test_leverage_order_by_score_then_id_and_only_untested() -> None:
    record: dict[str, Any] = {
        "relations": [{"from": "a", "to": "b", "kind": "flow"}],
        "hypotheses": [
            hypothesis("H10", targets=["q"]),  # score 1
            hypothesis("H2", targets=["q"]),  # score 1: ties by id, 2 before 10
            hypothesis("H3", targets=["a"]),  # score 2: itself and b
            hypothesis("H4", targets=["a"], qualifications=["K1"]),  # score 3
            hypothesis("H5", targets=["a", "q"], status="testing"),  # not listed
        ],
    }
    order = leverage_order(record)
    assert [(x.id, x.score) for x in order] == [
        ("H4", 3),
        ("H3", 2),
        ("H2", 1),
        ("H10", 1),
    ]
    assert leverage_order(record) == order  # the same record, the same order
    assert sorted(["H10", "H2", "H1"], key=natural_key) == ["H1", "H2", "H10"]


def test_index_shows_the_reach_of_untested_hypotheses(
    board2: dict[str, Any], tmp_path: Path
) -> None:
    board2["hypotheses"].append(hypothesis("H3", targets=["f-new"]))
    path = tmp_path / "x.board.yaml"
    path.write_text(dump_record(board2), encoding="utf-8")
    out = tmp_path / "index.html"
    assert main(["index", str(path), "--lang", "en", "-o", str(out)]) == 0
    html = out.read_text(encoding="utf-8")
    assert "<th>reach (proposal)</th>" in html
    assert '<span title="targets 1, K 0, O 0, T' in html
