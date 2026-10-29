from __future__ import annotations

from pathlib import Path

from test_procedures import front_matter

ROOT = Path(__file__).resolve().parents[1]
KEYS = {"id", "title", "version", "source", "route", "offered_by"}


def test_lenses_have_front_matter_and_known_procedures() -> None:
    procedures = {p.stem for p in (ROOT / "procedures").glob("*.md")} - {"README"}
    files = sorted(p for p in (ROOT / "lenses").glob("*.md") if p.name != "README.md")
    assert files
    for path in files:
        meta = front_matter(path)
        assert KEYS <= meta.keys(), f"{path.name}: missing {KEYS - meta.keys()}"
        assert meta["id"] == path.stem
        assert meta["route"] in ("smd", "triz", "both")
        offered = meta["offered_by"]
        assert isinstance(offered, list) and offered, path.name
        unknown = set(offered) - procedures
        assert not unknown, f"{path.name}: offered by unknown {unknown}"
