"""Renderers for board sets: SVG screen, HTML page, Markdown digest, Mermaid."""

from __future__ import annotations

from functools import cache
from importlib.resources import files


@cache
def asset_text(name: str) -> str:
    """A script or stylesheet of a page, from render/assets/."""
    return (files("smd_engine.render") / "assets" / name).read_text(encoding="utf-8")
