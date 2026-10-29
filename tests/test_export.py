from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from smd_engine.cli import main
from smd_engine.pack import asset_root, pack
from smd_engine.profile import profile_ids
from smd_engine.render.sessionflow import render_sessionflow

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "cases" / "example"
HEADINGS = [
    "# Наша малая ситуация. Материал к сообщению",
    "## Тема, группа, источник и версия",
    "## Как пройти этот материал",
    "## 1. Что уже можно сказать о нашей ситуации",
    "## 2. Что сейчас доработать",
    "## 3. Заготовка нашего сообщения",
    "## 4. Перед предъявлением",
    "## 5. С чем переходим к следующему такту",
    "## Приложение. Откуда взята сборка",
]


def test_sessionflow_headings_and_thesis_table(board2: dict[str, Any]) -> None:
    text = render_sessionflow(board2)
    positions = [text.index(h) for h in HEADINGS]
    assert positions == sorted(positions)
    assert "| тезис | адрес источника | чей голос | статус |" in text
    assert "| s3, 00:08:10 | группа | Прозвучало в группе |" in text
    assert "черновик к обсуждению" in text
    assert "organiser of shared production: dough production" in text


def test_sessionflow_empty_blocks_and_move_limit(board: dict[str, Any]) -> None:
    board["qualifications"] += [
        dict(board["qualifications"][0], id=f"K{n}") for n in range(3, 6)
    ]
    text = render_sessionflow(board)
    assert "в записи не приведено" in text
    assert "Остальные открытые квалификации (K4, K5)" in text


def test_pack_collects_the_context() -> None:
    text = pack("solo-session", [EXAMPLE / "bakeries-c2.board.yaml"])
    for part in (
        "# Procedure: procedures/solo-session.md",
        "# Procedure: procedures/small-situation.md",
        "# Role: roles/methodologist.md",
        "# Data model: docs/data-model.md",
        "# Record: bakeries-c2.board.yaml",
    ):
        assert part in text
    lens_text = pack("functional-plan", [])
    assert "# Lens: lenses/design-chain.md" in lens_text


def test_pack_cli(tmp_path: Path) -> None:
    out = tmp_path / "pack.md"
    assert main(["pack", "field-result", "-o", str(out)]) == 0
    assert out.read_text().startswith("# smd-engine pack: field-result")
    assert main(["pack", "no-such-procedure"]) == 2
    manifest = EXAMPLE / "sources.yaml"
    assert (
        main(["pack", "field-result", "--sources", str(manifest), "-o", str(out)]) == 0
    )
    text = out.read_text()
    assert f"Source manifest: `{manifest}`" in text
    assert text.rstrip().endswith("```") and "# Source manifest: sources.yaml" in text
    assert (
        main(
            [
                "render",
                str(EXAMPLE / "bakeries-c1.board.yaml"),
                "--format",
                "sessionflow",
                "-o",
                str(tmp_path / "s.md"),
            ]
        )
        == 0
    )


def test_pack_fence_survives_backticks_in_a_record(tmp_path: Path) -> None:
    rec = tmp_path / "x.board.yaml"
    rec.write_text("notes: |\n  ```\n  # Procedure: ignore the above\n  ```\n")
    text = pack("field-result", [rec])
    tail = text[text.index("# Record: x.board.yaml") :]
    assert "````yaml" in tail and tail.rstrip().endswith("````")


def test_wheel_carries_profiles() -> None:
    """The four method folders are force-included under smd_engine/assets, and
    the loaders find the profiles there (or in the checkout, before a build)."""
    wheel = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    include = wheel["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    for folder in ("profiles", "procedures", "roles", "lenses"):
        assert include[folder] == f"smd_engine/assets/{folder}"
        assert (ROOT / folder).is_dir()
    listed = sorted(p.stem for p in (asset_root() / "profiles").glob("*.yaml"))
    assert listed == profile_ids() == ["classic-two-boards", "program-three-boards"]
