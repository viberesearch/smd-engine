"""The shell of the task pages: one self-contained HTML file with the style and
the script inline, no network reference, no external script or stylesheet."""

from __future__ import annotations

import json
from functools import cache
from importlib.resources import files
from typing import Any

from smd_engine.render.text import esc


@cache
def asset_text(name: str) -> str:
    return (files("smd_engine.task") / "assets" / name).read_text(encoding="utf-8")


def cfg_json(cfg: dict[str, Any]) -> str:
    """JSON for a script block: `</` and the line separators are escaped."""
    text = json.dumps(cfg, ensure_ascii=False, sort_keys=True)
    return (
        text.replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def table(head: list[str], rows: list[list[str]], cls: str = "") -> str:
    """A table. Cells are HTML, already escaped. Each cell carries its column
    name (`data-l`), which the style shows above the cell on a narrow screen,
    where a row becomes a block."""
    th = "".join(f"<th>{esc(h)}</th>" for h in head)
    body = "".join(
        "<tr>"
        + "".join(f'<td data-l="{esc(h)}">{c}</td>' for h, c in zip(head, row))
        + "</tr>"
        for row in rows
    )
    return f'<table{f" class={chr(34)}{cls}{chr(34)}" if cls else ""}><tr>{th}</tr>{body}</table>'


def page(
    title: str,
    lang: str,
    subtitle: str,
    tabs: list[tuple[str, str, str]],
    cfg: dict[str, Any],
) -> str:
    """tabs: (name, label, inner HTML). The first tab shows first. The form `f`
    wraps every tab so that the script finds all fields."""
    nav = "".join(
        f'<button type="button" data-tab="{esc(n)}">{esc(label)}</button>'
        for n, label, _ in tabs
    )
    sections = "".join(
        f'<section class="tab" id="tab-{esc(n)}">{html}</section>'
        for n, _, html in tabs
    )
    return (
        f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{esc(title)}</title><style>{asset_text('task.css')}</style></head><body>"
        f"<header><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></header><main>"
        f'<nav class="tabs">{nav}</nav><form id="f" onsubmit="return false">{sections}</form></main>'
        f'<script type="application/json" id="cfg">{cfg_json(cfg)}</script>'
        f"<script>{asset_text('task.js')}</script></body></html>\n"
    )
