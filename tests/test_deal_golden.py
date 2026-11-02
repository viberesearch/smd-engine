"""Group packs behave exactly as before deal mode: the renders of the invented
example in cases/example/task/ are pinned by sha256. A change to them must be
deliberate; restamp with `shasum -a 256` on the files named in GOLDEN, written
by the commands in the test."""

from __future__ import annotations

import hashlib
from pathlib import Path

from smd_engine.cli import main

TASK = Path(__file__).resolve().parents[1] / "cases" / "example" / "task"

GOLDEN = {
    "pack.md": "987e5324ca5672208c48774a9bf7d12ebd89d842acaf0f88182206e90714728b",
    "pack.html": "0d1ccfe5af3404aff5db31f24db15d19b2f380ea6ac90631033d0c1f83f2fa36",
    "diff.yaml": "7a519d4438ad4399347dfe1884d2a7e02c3486fc5bbd149b7c2d0c770a478c37",
    "diff.md": "c76a0cd8763c1915fb484ac7a9d21bf3dffefe47d089a0f34438d222d2235c2d",
    "diff.html": "0f3fb204b0014ab6daa330a7afc964ea9b57a888449442b852039c21e454f2f7",
    "agenda.md": "9698e1638c6def5656d8dfb9991e2384e7078e68449aade6d20be53f8175779e",
    "agenda.yaml": "6814ebe42f2d360d982111fdf8ff98b99f56af8ba33b90eb339a70c97c1af37b",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_example_task_renders_match_the_golden_shas(tmp_path: Path) -> None:
    answers = [str(TASK / f"answers_{m}.yaml") for m in ("ana", "ben", "cy")]
    replies = [str(TASK / f"replies_{m}.yaml") for m in ("ana", "ben")]
    assert main(["task", "render", str(TASK / "pack.yaml"), "-o", str(tmp_path)]) == 0
    assert (
        main(["task", "diff", str(TASK / "pack.yaml"), *answers, "-o", str(tmp_path)])
        == 0
    )
    args = ["task", "agenda", str(tmp_path / "diff.yaml"), *replies]
    assert (
        main([*args, "--members", "ana,ben,cy", "-o", str(tmp_path / "agenda.md")]) == 0
    )
    assert {name: sha(tmp_path / name) for name in GOLDEN} == GOLDEN
