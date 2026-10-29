"""The frames page: one self-contained HTML file, styles and script in
assets/frames.css and assets/frames.js."""

from __future__ import annotations

import json
import re
from typing import Any

from smd_engine.profile import Profile, profile_of
from smd_engine.render import asset_text
from smd_engine.render.frames import Frame
from smd_engine.render.frames_text import STEPS
from smd_engine.render.svg import DEFS, origin, render_svg
from smd_engine.render.text import (
    LABELS,
    element_lines,
    esc,
    pace_text,
    title_line,
)
from smd_engine.screen import outline, triangle_parts, triangle_shapes


def _md(text: str) -> str:
    """Paragraphs and `- ` lists; everything else is plain text."""
    out: list[str] = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.splitlines()
        if all(ln.startswith("- ") for ln in lines):
            out.append(
                "<ul>" + "".join(f"<li>{esc(ln[2:])}</li>" for ln in lines) + "</ul>"
            )
        else:
            out.append("<p>" + "<br>".join(esc(ln) for ln in lines) + "</p>")
    return "".join(out)


# Where the counter of each triangle stands on the map (set by eye inside the
# shape): top left, top right, the board below the apex.
TRIANGLE_COUNTERS = ((300, 330), (1300, 330), (800, 770))
COUNTER_SIZE = 200  # font size of a counter on the map
# A counter is centred in its rectangle: its baseline lies half the height of
# its digits below the middle, and digits stand about 0.7 of the font size.
COUNTER_DROP = 0.35 * COUNTER_SIZE


def _outlines(profile: Profile) -> tuple[list[tuple[str, str, float, float]], str]:
    """Each board's outline on the map and where its counter goes; the view box,
    20 around the outlines. On a `regions` screen a board is the rectangle drawn
    around its region, on `triangles` its shape of the screen."""
    out: list[tuple[str, str, float, float]] = []
    if profile.screen == "triangles":
        for b, shape, (x, y) in zip(
            profile.boards, triangle_shapes(), TRIANGLE_COUNTERS
        ):
            out.append((b.id, shape, x, y))
        drawn = list(triangle_parts())
    else:
        drawn = [outline(b.region) for b in profile.boards]
        for b, (left, top, right, bottom) in zip(profile.boards, drawn):
            points = f"{left:g},{top:g} {right:g},{top:g} {right:g},{bottom:g} {left:g},{bottom:g}"
            middle = (top + bottom) / 2
            out.append((b.id, points, (left + right) / 2, middle + COUNTER_DROP))
    x0 = min(r[0] for r in drawn) - 20
    y0 = min(r[1] for r in drawn) - 20
    x1 = max(r[2] for r in drawn) + 20
    y1 = max(r[3] for r in drawn) + 20
    return out, f"{x0:g} {y0:g} {x1 - x0:g} {y1 - y0:g}"


def _map(f: Frame) -> str:
    """The boards, the step's board in colour, elements shown per board."""
    if f.counts is None:
        return ""
    profile = profile_of(f.record)
    outlines, view = _outlines(profile)
    parts = []
    for b, points, x, y in outlines:
        step = (f.board or "").partition(".")[0]
        on = step in ("", b)
        bg, ink = profile.board(b).colour if on else ("#f2f2f4", "#aaa")
        width = 24 if step == b else 8
        parts.append(
            f'<polygon points="{points}" fill="{bg}" stroke="{ink}" stroke-width="{width}"/>'
            f'<text x="{x}" y="{y}" font-size="{COUNTER_SIZE}" font-weight="600" text-anchor="middle" '
            f'fill="{ink}">{f.counts[b]}</text>'
        )
    return (
        f'<svg class="map" viewBox="{view}" aria-hidden="true">'
        + "".join(parts)
        + "</svg>"
    )


def _details(frames: list[Frame], lang: str) -> dict[str, Any]:
    """Per record: the full text of each element drawn and of each K, for the
    panel that opens on a click."""
    lab, st = LABELS[lang], STEPS[lang]
    out: dict[str, Any] = {}
    for f in frames:
        rec = out.setdefault(f.record["id"], {"el": {}, "k": {}})
        profile = profile_of(f.record)
        k_of: dict[str, list[str]] = {}
        for q in f.record.get("qualifications", []):
            text = f"{q['id']} [{lab['status'][q['status']]}] {q['text']}"
            rec["k"].setdefault(q["id"], text)
            for target in q.get("targets", []):
                k_of.setdefault(target, []).append(text)
        for e in f.record["elements"]:
            meta = [
                profile.kind_label(e["kind"], lang),
                profile.board_label(e["board"], lang),
            ]
            if origin(e) != "group":
                meta.append(st["switches"][origin(e)])
            meta += [e[k] for k in ("voice", "epistemic") if e.get(k)]
            meta += e.get("lineage", [])
            d = rec["el"].setdefault(
                e["id"],
                {"label": e["label"], "meta": " · ".join(dict.fromkeys(meta))},
            )
            for key, value in (
                ("note", e.get("label_note")),
                ("cites", ", ".join(e.get("cites", []))),
                ("folded", e.get("folded")),
                ("fillers", ", ".join(e.get("fillers", []))),
                # pace, the Beer fields, acts_as and stance, as on the page
                (
                    "fields",
                    "; ".join(
                        filter(None, [pace_text(e, lang), *element_lines(e, lang)])
                    ),
                ),
                ("detail", e.get("detail")),
            ):
                if value:
                    d[key] = value
            known = d.setdefault("k", [])
            known += [k for k in k_of.get(e["id"], []) if k not in known]
    return out


def _switches(frames: list[Frame], lang: str) -> str:
    """A show/hide button for each layer the frames have."""
    els = [e for f in frames for e in f.record["elements"]]
    origins = {origin(e) for e in els}
    kinds = {e["kind"] for e in els}
    present = {
        "ai": "ai" in origins,
        "clean-room": "clean-room" in origins,
        "function": "function" in kinds,
        "places": bool({"place_for_others", "gap"} & kinds),
        "k": any(f.record.get("qualifications") for f in frames),
        "transitions": any(f.record.get("transitions") for f in frames),
    }
    names = STEPS[lang]["switches"]
    buttons = "".join(
        f'<button class="layer" data-layer="{k}" aria-pressed="true">{esc(names[k])}</button>'
        for k, on in present.items()
        if on
    )
    return f'<span class="sw">{buttons}</span>' if buttons else ""


def render_frames_html(frames: list[Frame], lang: str = "ru") -> str:
    st = STEPS[lang]
    title = title_line(frames[-1].record, lang) if frames else ""
    sections = []
    for n, f in enumerate(frames, 1):
        svg = render_svg(f.record, lang, f.show, f.focus, f.layers, f.board).replace(
            DEFS, ""
        )
        sections.append(
            f'<section id="{esc(f.id)}" data-record="{esc(f.record["id"])}"><h2>{_map(f)}'
            f"<span>{esc(f.title)} <small>{n} / {len(frames)}</small></span></h2>"
            f'<div class="body">{svg}<div class="notes">{_md(f.text)}</div>'
            "</div></section>"
        )
    data = json.dumps(_details(frames, lang), ensure_ascii=False).replace("</", "<\\/")
    return (
        f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{esc(title)}</title><style>{asset_text('frames.css')}</style></head><body>"
        f'<svg width="0" height="0" style="position:absolute" aria-hidden="true">{DEFS}</svg>'
        f"<header><h1>{esc(title)}</h1>{_switches(frames, lang)}"
        f'<span id="hid" data-word="{esc(st["hidden_n"])}"></span>'
        f'<button id="prev">{st["prev"]}</button><span id="count"></span>'
        f'<button id="next">{st["next_btn"]}</button>'
        f'<button id="toggle" aria-pressed="true">{st["toggle"]} (T)</button></header>'
        f"<main>{''.join(sections)}</main>"
        f'<aside id="detail" hidden data-fillers="{esc(LABELS[lang]["fillers"])}">'
        f'<button id="close" aria-label="{esc(st["close"])}">×</button>'
        '<div id="dbody"></div></aside>'
        f'<script type="application/json" id="smd-data">{data}</script>'
        f"<script>{asset_text('frames.js')}</script></body></html>\n"
    )
