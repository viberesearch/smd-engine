"""Helpers of the deal tests: the invented example and the restamp of its answers."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

import yaml

from smd_engine.cli import main
from smd_engine.deal.sealed import commitment_of
from smd_engine.task.model import load_task
from smd_engine.task.positions import annex_sha, core_sha, has_annex

DEAL = Path(__file__).resolve().parents[1] / "cases" / "example" / "deal"
MEMBERS = ("vera", "boris", "gleb")
SHA_LINE = re.compile(r'^(  sha256: )"[0-9a-f]{64}"$', re.M)
ANNEX_LINE = re.compile(r'^(  annex: \{position: \w+, sha256: )"[0-9a-f]{64}"\}$', re.M)


def restamp(folder: Path) -> None:
    """Write the core sha256 and the annex sha256 of folder/pack.yaml into every
    answers_<member>.yaml of the folder. Run it after a change to the pack:
    `restamp(Path("cases/example/deal"))`."""
    pack = load_task(folder / "pack.yaml")
    where = {m["id"]: m["position"] for m in pack["members"]}
    for path in folder.glob("answers_*.yaml"):
        text = path.read_text(encoding="utf-8")
        member = yaml.safe_load(text)["member"]
        position = where[member]
        text = SHA_LINE.sub(lambda m: f'{m[1]}"{core_sha(pack)}"', text, count=1)
        if has_annex(pack, position):
            text = ANNEX_LINE.sub(
                lambda m: f'{m[1]}"{annex_sha(pack, position)}"}}', text, count=1
            )
        path.write_text(text, encoding="utf-8")


def copy_deal(dest: Path) -> Path:
    shutil.copytree(DEAL, dest)
    return dest


def edit_pack(folder: Path, change) -> dict:  # type: ignore[no-untyped-def]
    """Load folder/pack.yaml, apply `change(pack)`, write it back and restamp."""
    path = folder / "pack.yaml"
    pack = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(pack)
    path.write_text(
        yaml.safe_dump(pack, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    restamp(folder)
    return pack


def run_diff(folder: Path, out: Path) -> dict[str, Any]:
    names = [str(folder / f"answers_{m}.yaml") for m in MEMBERS]
    assert (
        main(["task", "diff", str(folder / "pack.yaml"), *names, "-o", str(out)]) == 0
    )
    return load_task(out / "diff.yaml")


def by_id(diff: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {p["id"]: p for p in diff["points"]}


def item(pack: dict[str, Any], item_id: str) -> dict[str, Any]:
    return next(i for i in pack["items"] if i["id"] == item_id)


def errors(issues: list[Any]) -> list[str]:
    return [i.message for i in issues if i.level == "error"]


def set_answer(folder: Path, member: str, item_id: str, entry: dict[str, Any]) -> None:
    path = folder / f"answers_{member}.yaml"
    ans = yaml.safe_load(path.read_text(encoding="utf-8"))
    ans["answers"][item_id] = entry
    path.write_text(yaml.safe_dump(ans, sort_keys=False), encoding="utf-8")


FLOOR = "431250"  # invented sealed numbers: they must appear nowhere but in their files
CEILING = "512750"


def seal(work: Path, tmp_path: Path, item: str, value: str) -> tuple[Path, str]:
    """Seal a number on the example; return the sealed file and its commitment."""
    safe = tmp_path / "safe"
    code = main(
        ["deal", "seal", str(work / "pack.yaml"), item, "-o", str(safe)]
        + ["--value", value, "--date", "2026-11-03"]
    )
    assert code == 0
    path = next(safe.glob(f"sealed_*_{item}.yaml"))
    return path, commitment_of(load_task(path, "task_sealed"))
