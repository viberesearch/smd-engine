"""Deal mode, added points: the id of an added point reveals no count, and the
pack form lets its author share the point with all positions."""

from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from deal_helpers import copy_deal, run_diff
from smd_engine.cli import main
from smd_engine.render.text import esc
from smd_engine.task.labels import LABELS

EXAMPLE_TASK = Path(__file__).resolve().parents[1] / "cases" / "example" / "task"


@pytest.fixture()
def work(tmp_path: Path) -> Path:
    return copy_deal(tmp_path / "deal")


def add_points(folder: Path, member: str, *entries: dict[str, Any]) -> None:
    path = folder / f"answers_{member}.yaml"
    ans = yaml.safe_load(path.read_text(encoding="utf-8"))
    ans["added"] = list(entries)
    path.write_text(yaml.safe_dump(ans, sort_keys=False), encoding="utf-8")


def added_ids(diff: dict[str, Any]) -> dict[str, str]:
    return {p["text"]: p["id"] for p in diff["points"] if p["kind"] == "added"}


def test_added_ids_in_a_deal_pack_come_from_the_text_not_from_a_count(
    work: Path, tmp_path: Path
) -> None:
    add_points(work, "boris", {"text": "Private."}, {"text": "Open.", "share": True})
    ids = added_ids(run_diff(work, tmp_path / "a"))
    tag = hashlib.sha256(b"Open.").hexdigest()[:8]
    assert ids["Open."] == f"add-boris-{tag}"
    assert not any(re.fullmatch(r"add-boris-\d+", i) for i in ids.values())
    # the same points in another order and with another private one before them
    add_points(
        work,
        "boris",
        {"text": "Other."},
        {"text": "Open.", "share": True},
        {"text": "Private."},
    )
    again = added_ids(run_diff(work, tmp_path / "b"))
    assert again["Open."] == ids["Open."] and again["Private."] == ids["Private."]


def test_a_repeated_added_text_gets_a_suffix_in_a_deal_pack(
    work: Path, tmp_path: Path
) -> None:
    add_points(
        work,
        "boris",
        {"text": "Twice.", "share": True},
        {"text": "Twice.", "share": True},
    )
    diff = run_diff(work, tmp_path / "out")
    got = [p["id"] for p in diff["points"] if p["kind"] == "added"]
    tag = hashlib.sha256(b"Twice.").hexdigest()[:8]
    assert got == [f"add-boris-{tag}", f"add-boris-{tag}-2"]


def test_added_ids_in_a_group_pack_keep_the_count(tmp_path: Path) -> None:
    folder = tmp_path / "task"
    shutil.copytree(EXAMPLE_TASK, folder)
    path = folder / "answers_ana.yaml"
    ans = yaml.safe_load(path.read_text(encoding="utf-8"))
    ans["added"] = [{"text": "First."}, {"text": "Second."}]
    path.write_text(yaml.safe_dump(ans, sort_keys=False), encoding="utf-8")
    names = [str(folder / f"answers_{m}.yaml") for m in ("ana", "ben", "cy")]
    out = tmp_path / "out"
    assert (
        main(["task", "diff", str(folder / "pack.yaml"), *names, "-o", str(out)]) == 0
    )
    diff = yaml.safe_load((out / "diff.yaml").read_text(encoding="utf-8"))
    assert sorted(added_ids(diff).values())[:2] == ["add-ana-1", "add-ana-2"]


def render(pack: Path, out: Path, *extra: str) -> None:
    assert main(["task", "render", str(pack), "-o", str(out), *extra]) == 0


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_deal_pack_form_offers_to_share_an_added_point(
    work: Path, tmp_path: Path, lang: str
) -> None:
    path = work / "pack.yaml"
    pack = yaml.safe_load(path.read_text(encoding="utf-8"))
    pack["lang"] = lang
    path.write_text(yaml.safe_dump(pack, sort_keys=False, allow_unicode=True), "utf-8")
    out = tmp_path / "out"
    render(path, out)
    render(path, out, "--position", "buyer")
    lab = LABELS[lang]
    for name in ("pack.html", "pack.buyer.html"):
        html = (out / name).read_text(encoding="utf-8")
        assert lab["share_all"] in html and esc(lab["added_hint_deal"]) in html
        # the box is unchecked unless the saved row says so; checked, it is exported
        assert "share.checked = !!vals.share" in html
        assert "', share: true'" in html
    assert (
        lab["share_all"]
        == {"en": "share with all positions", "ru": "показать всем позициям"}[lang]
    )


def test_group_pack_form_has_no_share_box(tmp_path: Path) -> None:
    render(EXAMPLE_TASK / "pack.yaml", tmp_path)
    html = (tmp_path / "pack.html").read_text(encoding="utf-8")
    assert "share_all" not in html and "share: true" not in html


def test_the_suffix_of_a_shared_added_id_does_not_count_private_points(
    work: Path, tmp_path: Path
) -> None:
    add_points(
        work,
        "boris",
        {"text": "Same."},
        {"text": "Same.", "share": True},
        {"text": "Same."},
    )
    points = [
        p for p in run_diff(work, tmp_path / "a")["points"] if p["kind"] == "added"
    ]
    tag = hashlib.sha256(b"Same.").hexdigest()[:8]
    shared = [p["id"] for p in points if "audience" not in p]
    assert shared == [f"add-boris-{tag}"]  # no "-2": two private copies are not counted
    private = [p["id"] for p in points if "audience" in p]
    assert len(set(private)) == 2 and shared[0] not in private


def test_a_group_pack_with_a_range_item_has_no_share_box(tmp_path: Path) -> None:
    group = tmp_path / "group"
    shutil.copytree(EXAMPLE_TASK, group)
    path = group / "pack.yaml"
    pack = yaml.safe_load(path.read_text(encoding="utf-8"))
    pack["items"].append(
        {
            "id": "weeks",
            "section": "Plan",
            "question": "How long?",
            "kind": "range",
            "unit": "weeks",
        }
    )
    path.write_text(yaml.safe_dump(pack, sort_keys=False), encoding="utf-8")
    render(path, tmp_path / "out")
    html = (tmp_path / "out" / "pack.html").read_text(encoding="utf-8")
    assert "it.kind === 'range'" in html  # the range script is on the page
    assert "share_all" not in html and "share: true" not in html
    assert "data-r': 'share'" not in html
