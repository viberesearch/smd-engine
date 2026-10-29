from __future__ import annotations

from pathlib import Path

import yaml

from smd_engine.validate.hints import INGESTION

PROCEDURES = Path(__file__).resolve().parents[1] / "procedures"
KEYS = {
    "id",
    "title",
    "step",
    "version",
    "role",
    "profile",
    "inputs",
    "outputs",
    "sources",
}
PROFILES = {p.stem for p in (PROCEDURES.parent / "profiles").glob("*.yaml")}


def front_matter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), path.name
    data = yaml.safe_load(text.split("---\n")[1])
    assert isinstance(data, dict)
    return data


def test_procedures_have_front_matter() -> None:
    files = sorted(p for p in PROCEDURES.glob("*.md") if p.name != "README.md")
    assert files
    ids = {p.stem for p in files}
    for path in files:
        meta = front_matter(path)
        assert KEYS <= meta.keys(), f"{path.name}: missing {KEYS - meta.keys()}"
        assert meta["id"] == path.stem
        assert meta["profile"] == "any" or meta["profile"] in PROFILES, path.name
        assert isinstance(meta["inputs"], list) and isinstance(meta["outputs"], list)
        if "next" in meta:
            first = str(meta["next"]).split(",")[0].strip()
            assert first in ids, f"{path.name}: next names unknown procedure {first}"


def test_ingestion_hint_names_procedures() -> None:
    """cells-from-information reads `run.procedure` against these ids."""
    ids = {p.stem for p in PROCEDURES.glob("*.md")} - {"README"}
    assert set(INGESTION) <= ids
