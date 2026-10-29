"""SVG screen of a board set in the organisers' visual grammar.

Elements: entry marker, position figures, dashed ellipses for places for
others, frames (solid = old, dashed = new) with function chips inside,
"?" gaps, K badges, numbered red transitions between boards. The shape of
each kind, the boards, their labels, colours and regions come from the
record's profile (profiles/*.yaml): the program's `triangles` screen, or
each board as a rectangle around its region (`regions`).

Each element, link, transition and K badge is a `<g>` with data attributes
(id, kind, board, origin; ends of a link; target of a badge) that the frames
viewer uses to show and hide layers and to look up details.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterator
from html import unescape
from typing import Any

from smd_engine.profile import Board, Profile, profile_of
from smd_engine.render.layout import Box, Geometry, plan
from smd_engine.render.text import LABELS, MOVE_NAMES, esc, text_width, wrap
from smd_engine.screen import BOARD_TOP, CENTER, WIDTH, outline
from smd_engine.validate import AI_VOICES

INK = "#222"
MUTED = "#555"
RED = "#c94040"
NAVY = "#12235a"
HIGHLIGHT = ("#fde9a8", "#c9a227")
FOCUS = "#e8730c"
LAYERS = frozenset({"transitions", "k", "legend"})
CLEAN_ROOM = "from-clean-room"
LABEL_SIZE = 12  # font size of a relation label
LABEL_STEP = 15.0  # a label that overlaps something may move by a line
LABEL_LEADING = 14.0  # line step of a wrapped label
LABEL_WIDTH = 220.0  # a label that overlaps something may wrap at this width
LABEL_TRIES = 4  # lines up and down a label may move (60 px)
TEXT = re.compile(
    r'<text x="([-\d.]+)" y="([-\d.]+)" font-size="([\d.]+)"([^>]*)>([^<]*)</text>'
)

DEFS = f"""<defs>
<marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8"
 orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{RED}"/></marker>
<marker id="ak" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
 orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>
<marker id="ag" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6"
 orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#888"/></marker>
<symbol id="man" viewBox="0 0 20 46"><circle cx="10" cy="5" r="5" fill="#111"/>
<rect x="3" y="12" width="14" height="18" rx="3" fill="#111"/>
<rect x="4.5" y="28" width="4.5" height="17" fill="#111"/>
<rect x="11" y="28" width="4.5" height="17" fill="#111"/></symbol>
</defs>"""


def _txt(x: float, y: float, s: str, size: float = 12, **attrs: str) -> str:
    extra = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" {extra}>{esc(s)}</text>'


def _lines(
    x: float, y: float, lines: list[str], size: float, step: float, **attrs: str
) -> str:
    return "".join(
        _txt(x, y + i * step, ln, size, **attrs) for i, ln in enumerate(lines)
    )


def origin(el: dict[str, Any]) -> str:
    """Whose content an element is on the screen: `clean-room` (an independent
    AI pass, by lineage), `ai` (AI voice) or `group` (everything else)."""
    if CLEAN_ROOM in el.get("lineage", []):
        return "clean-room"
    if (el.get("voice") or "").strip().lower() in AI_VOICES:
        return "ai"
    return "group"


def _style(el: dict[str, Any]) -> dict[str, str]:
    attrs = {"fill": INK}
    if el.get("epistemic") in ("hypothesis", "unverified"):
        attrs["font_style"] = "italic"
    return attrs


def _element(el: dict[str, Any], box: Box, profile: Profile) -> str:
    kind = profile.kind(el["kind"])
    shape = kind.shape
    # outlines take the ink of the board the kind lives on
    ink = profile.board_or_template(kind.home or el["board"]).colour[1]
    lit = bool(el.get("lineage"))
    st = _style(el)
    b = box
    if shape == "marker":
        return (
            f'<circle cx="{b.x + 11:.1f}" cy="{b.y + 11:.1f}" r="10" fill="none" '
            f'stroke="{RED}" stroke-width="3"/><circle cx="{b.x + 11:.1f}" '
            f'cy="{b.y + 11:.1f}" r="4.5" fill="{RED}"/>'
            + _lines(b.x + 28, b.y + 16, b.lines, 12, 15, fill=RED, font_weight="700")
        )
    if shape == "figure":
        icon = f'<use href="#man" x="{b.cx - 10:.1f}" y="{b.y:.1f}" width="20" height="46"/>'
        return icon + _lines(
            b.cx,
            b.y + 64,
            b.lines,
            13,
            15,
            text_anchor="middle",
            font_weight="600",
            **st,
        )
    if shape == "ellipse":
        fill = HIGHLIGHT[0] if lit else "none"
        return (
            f'<ellipse cx="{b.cx:.1f}" cy="{b.cy:.1f}" rx="{b.w / 2:.1f}" ry="{b.h / 2:.1f}" '
            f'fill="{fill}" stroke="{ink}" stroke-width="2" stroke-dasharray="5 4"/>'
            + _lines(
                b.cx,
                b.cy - (len(b.lines) - 1) * 7 + 4,
                b.lines,
                12,
                14,
                text_anchor="middle",
                **{**st, "fill": MUTED},
            )
        )
    if shape == "question":
        return f'<circle cx="{b.x + 16:.1f}" cy="{b.y + 16:.1f}" r="15" fill="#fff" stroke="{MUTED}" ' f'stroke-width="1.5" stroke-dasharray="3 3"/>' + _txt(
            b.x + 16,
            b.y + 22,
            "?",
            16,
            text_anchor="middle",
            font_weight="700",
            fill=MUTED,
        ) + _lines(
            b.x + 38, b.y + 14, b.lines, 12, 14, fill=MUTED
        )
    if shape == "frame":
        dash = ' stroke-dasharray="8 6"' if el.get("frame_state") == "new" else ""
        fill = HIGHLIGHT[0] if lit else "#fff"
        weight = "700" if el.get("frame_state") == "new" else "400"
        return (
            f'<rect x="{b.x:.1f}" y="{b.y:.1f}" width="{b.w:.1f}" height="{b.h:.1f}" rx="9" '
            f'fill="{fill}" fill-opacity="{0.9 if lit else 0.6}" stroke="{ink}" '
            f'stroke-width="2"{dash}/>'
            + _lines(b.x + 12, b.y + 20, b.lines, 13, 16, font_weight=weight, **st)
        )
    if shape in ("heading", "paragraph") and profile.board(el["board"]).halves:
        heading = shape == "heading"
        size = 13 if heading else 12
        back = (
            f'<rect x="{b.x - 4:.1f}" y="{b.y - 2:.1f}" width="{b.w + 8:.1f}" height="{b.h:.1f}" '
            f'rx="4" fill="{HIGHLIGHT[0]}"/>'
            if lit
            else ""
        )
        weight = "600" if heading else "400"
        return back + _lines(
            b.x, b.y + size, b.lines, size, size + 3, font_weight=weight, **st
        )
    fill, stroke = HIGHLIGHT if lit else ("#fff", "#888")
    return (
        f'<rect x="{b.x:.1f}" y="{b.y:.1f}" width="{b.w:.1f}" height="{b.h:.1f}" rx="5" '
        f'fill="{fill}" stroke="{stroke}"/>'
        + _lines(b.x + 8, b.y + 16, b.lines, 11.5 if b.h < 40 else 12, 13, **st)
    )


def _edge_point(box: Box, tx: float, ty: float) -> tuple[float, float]:
    dx, dy = tx - box.cx, ty - box.cy
    if dx == 0 and dy == 0:
        return box.cx, box.cy
    scale = min(
        (box.w / 2) / abs(dx) if dx else math.inf,
        (box.h / 2) / abs(dy) if dy else math.inf,
    )
    return box.cx + dx * scale, box.cy + dy * scale


def _curve(a: Box, b: Box, bend: float = 0.22) -> tuple[str, float, float]:
    x0, y0 = _edge_point(a, b.cx, b.cy)
    x1, y1 = _edge_point(b, a.cx, a.cy)
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    dist = math.hypot(x1 - x0, y1 - y0) or 1.0
    nx, ny = -(y1 - y0) / dist, (x1 - x0) / dist
    offset = max(dist * bend, 45.0) if bend else 0.0  # short hops still show as an arc
    cx, cy = mx + nx * offset, my + ny * offset
    path = f"M{x0:.1f},{y0:.1f} Q{cx:.1f},{cy:.1f} {x1:.1f},{y1:.1f}"
    return path, 0.25 * x0 + 0.5 * cx + 0.25 * x1, 0.25 * y0 + 0.5 * cy + 0.25 * y1


def _bend(rel: dict[str, Any]) -> float:
    return 0.0 if rel["kind"] == "shift" else 0.15


Rect = tuple[float, float, float, float]
Spot = tuple[float, float, list[str]]  # x, y of the first line, the lines


def _overlap(rect: Rect, others: list[Rect]) -> float:
    return sum(
        max(0.0, min(rect[2], o[2]) - max(rect[0], o[0]))
        * max(0.0, min(rect[3], o[3]) - max(rect[1], o[1]))
        for o in others
    )


def _label_box(spot: Spot) -> Rect:
    x, y, lines = spot
    half = max(text_width(ln, LABEL_SIZE) for ln in lines) / 2
    return (
        x - half,
        y - LABEL_SIZE,
        x + half,
        y + (len(lines) - 1) * LABEL_LEADING + 3,
    )


def _text_rects(svg: str) -> list[Rect]:
    """The boxes of the `<text>` items of an SVG fragment drawn by `_txt`."""
    rects = []
    for m in TEXT.finditer(svg):
        x, y, size = float(m.group(1)), float(m.group(2)), float(m.group(3))
        width = text_width(unescape(m.group(5)), size)
        if 'text-anchor="middle"' in m.group(4):
            x -= width / 2
        elif 'text-anchor="end"' in m.group(4):
            x -= width
        rects.append((x, y - size, x + width, y + 3))
    return rects


def _badge(box: Box, k: int, figure: bool) -> tuple[float, float]:
    """Top left of the k-th K badge on an element (32 x 20)."""
    bx = box.cx + 14 + k * 36 if figure else box.x + box.w - 30 - k * 36
    return bx, box.y - 10


def _obstacles(
    data: dict[str, Any], boxes: dict[str, Box], profile: Profile, screen: str
) -> list[Rect]:
    """What a relation label should not cover, on the whole record: the boxes of
    the elements (of a frame, its heading; of a figure, its icon and caption),
    the board and half headings of `screen`, and the K badges."""
    rects = _text_rects(screen)
    els = {e["id"]: e for e in data["elements"]}
    for el in data["elements"]:
        b = boxes[el["id"]]
        shape = profile.kind(el["kind"]).shape
        if shape == "frame":
            wide = max([text_width(ln, 13) for ln in b.lines] + [0.0])
            rects.append(
                (b.x, b.y, b.x + 12 + wide, b.y + 24 + (len(b.lines) - 1) * 16)
            )
        elif shape == "figure":
            half = max([text_width(ln, 13) for ln in b.lines] + [0.0]) / 2
            rects.append((b.cx - 10, b.y, b.cx + 10, b.y + 46))
            rects.append(
                (b.cx - half, b.y + 51, b.cx + half, b.y + 67 + (len(b.lines) - 1) * 15)
            )
        else:
            rects.append((b.x, b.y, b.x + b.w, b.y + b.h))
    stacked: dict[str, int] = {}
    for q in data.get("qualifications", []):
        if not q.get("targets") or q["targets"][0] not in boxes:
            continue
        target = q["targets"][0]
        k = stacked.get(target, 0)
        stacked[target] = k + 1
        figure = profile.kind(els[target]["kind"]).shape == "figure"
        bx, by = _badge(boxes[target], k, figure)
        rects.append((bx, by, bx + 32, by + 20))
    return rects


def _candidates(x: float, y: float, label: str) -> Iterator[Spot]:
    """Spots for a label whose one line stands at (x, y), nearest first: that
    spot, then lines up before down, at most LABEL_TRIES away; on each line the
    label in one line and wrapped to LABEL_WIDTH (its last line on that line),
    centred, then a quarter and a half of its width left and right."""
    shapes = [[label]]
    wrapped = wrap(label, LABEL_WIDTH, LABEL_SIZE)
    if len(wrapped) > 1:
        shapes.append(wrapped)
    for k in range(2 * LABEL_TRIES + 1):
        line = y + (k + 1) // 2 * LABEL_STEP * (-1 if k % 2 else 1)
        for lines in shapes:
            top = line - (len(lines) - 1) * LABEL_LEADING
            width = max(text_width(ln, LABEL_SIZE) for ln in lines)
            for dx in (0.0, -0.25, 0.25, -0.5, 0.5):
                yield x + dx * width, top, lines


def _label_spots(
    relations: list[dict[str, Any]], boxes: dict[str, Box], obstacles: list[Rect]
) -> list[Spot | None]:
    """Where each relation label goes, in record order: in one line above the
    middle of its link, unless that covers a label placed before it or one of
    `obstacles`. Then it takes the first of `_candidates` that covers nothing,
    or with none free the one that covers least, the middle winning ties, so a
    label never moves to a worse place. Computed on every relation of the
    record, so a frame or a cut screen keeps the spots of the full screen, and
    a label that covers nothing keeps its place."""
    placed: list[Rect] = []
    spots: list[Spot | None] = []
    for rel in relations:
        if not rel.get("label") or rel["from"] not in boxes or rel["to"] not in boxes:
            spots.append(None)
            continue
        _, x, y = _curve(boxes[rel["from"]], boxes[rel["to"]], _bend(rel))
        best: tuple[float, Spot, Rect] | None = None
        for spot in _candidates(x, y - 6, rel["label"]):
            rect = _label_box(spot)
            cost = _overlap(rect, placed) + _overlap(rect, obstacles)
            if best is None or cost < best[0]:
                best = (cost, spot, rect)
            if cost == 0:
                break
        assert best is not None
        placed.append(best[2])
        spots.append(best[1])
    return spots


def _legend(data: dict[str, Any], lang: str, top: float) -> tuple[str, float]:
    lab = LABELS[lang]
    rows: list[tuple[str, str]] = []
    trs = sorted(data.get("transitions", []), key=lambda t: t["n"])
    if trs:
        by_id = {e["id"]: e for e in data["elements"]}
        parts = [
            f"{t['n']} {by_id[t['from']]['board'].upper()} → {by_id[t['to']]['board'].upper()}"
            + (f" ({t['label']})" if t.get("label") else "")
            for t in trs
        ]
        rows.append(("b", f"{lab['transitions']}: " + " · ".join(parts)))
    for q in data.get("qualifications", []):
        status = lab["status"][q["status"]]
        rows.append(("k", f"{q['id']} [{status}] {q.get('short') or q['text']}"))
    moves = [e for e in data["elements"] if e.get("move")]
    if moves:
        parts = [
            f"{e['id']}: {MOVE_NAMES[e['move']['op']]} ← {', '.join(e['move']['from'])}"
            for e in moves
        ]
        rows.append(("b", f"{lab['moves']}: " + " · ".join(parts)))
    notes = []
    if any(e.get("lineage") for e in data["elements"]):
        tags = sorted({t for e in data["elements"] for t in e.get("lineage", [])})
        notes.append(f"{lab['lineage']}: {', '.join(tags)}")
    if any(
        e.get("epistemic") in ("hypothesis", "unverified") for e in data["elements"]
    ):
        notes.append(lab["epistemic"])
    if notes:
        rows.append(("n", " · ".join(notes)))
    state = data.get("state")
    if state:
        bits = [f"{lab['state']} {state.get('version', '')}".strip()]
        if state.get("open"):
            bits.append(f"{lab['open']}: " + "; ".join(state["open"]))
        if state.get("next_move"):
            bits.append(f"{lab['next']}: {state['next_move']}")
        rows.append(("n", " · ".join(bits)))
    out: list[str] = [
        f'<line x1="40" y1="{top:.1f}" x2="1560" y2="{top:.1f}" stroke="#ddd"/>'
    ]
    y = top + 22
    for tag, text in rows:
        lines = wrap(text, 1520, 12)
        color = NAVY if tag == "k" else MUTED
        out.append(_lines(40, y, lines, 12, 16, fill=color))
        y += len(lines) * 16 + 4
    return "".join(out), y + 8


def _halo(box: Box) -> str:
    return (
        f'<rect x="{box.x - 6:.1f}" y="{box.y - 6:.1f}" width="{box.w + 12:.1f}" '
        f'height="{box.h + 12:.1f}" rx="9" fill="none" stroke="{FOCUS}" stroke-width="3"/>'
    )


def _span(board: Board, half: str, left: float, right: float) -> tuple[float, float]:
    """The x range of a board, or of one of its two halves, which runs 10 past
    the board's `split` so that the dashed line between the halves shows."""
    if half and len(board.halves) == 2:
        if half == board.halves[0]:
            return left, board.split + 10
        return board.split - 10, right
    return left, right


def _crop(
    board: str,
    geo: Geometry,
    boxes: dict[str, Box],
    els: dict[str, dict[str, Any]],
    profile: Profile,
) -> tuple[float, float, float, float]:
    """The part of the screen one board (or one half, `s.small`, `s.big`)
    takes, from the whole record's placement, so every step on it is cut the
    same way."""
    board, _, half = board.partition(".")
    b = profile.board(board)
    ids = [
        i
        for i, e in els.items()
        if e["board"] == board and (not half or e.get("half") == half)
    ]
    triangles = profile.screen == "triangles"
    if triangles and b.id == profile.boards[-1].id:  # the board below the apex
        top = min([boxes[i].y for i in ids], default=geo.cy + 140)
        y0 = min(geo.cy + 140, top - 20)  # keeps the labels of the halves
        x0, x1 = _span(b, half, 30.0, WIDTH - 30.0)
        return x0, y0, x1 - x0, max(geo.bottom, geo.corner_y) + 10 - y0
    rx0, ry0, rx1, ry1 = geo.board(board)
    edge = outline(geo.board(board))[1]  # the top of the board as drawn
    floor = geo.cy if triangles else ry1 - 20
    bottom = max([floor] + [boxes[i].y + boxes[i].h for i in ids])
    x0, x1 = _span(b, half, rx0 - 30.0, rx1 + 30.0)
    return x0, edge - 10.0, x1 - x0, bottom + 30 - edge


def _three_boards(profile: Profile, geo: Geometry, lang: str) -> str:
    """The organisers' screen: two boards on top, the third below the apex."""
    lab = LABELS[lang]
    left, right, low = profile.boards
    od_bg, od_ink = left.colour
    oo_bg, oo_ink = right.colour
    s_bg, s_ink = low.colour
    cx, cy = CENTER[0], geo.cy
    lx, rx, ly = 40.0, WIDTH - 40.0, geo.corner_y
    ry = ly
    s_points = f"{lx},{ly} {cx},{cy} {rx},{ry}"
    if geo.wide:
        s_points += f" {rx},{geo.bottom} {lx},{geo.bottom}"
    s_label_y = geo.bottom - 12 if geo.wide else ly - 12
    dashed = halves = ""
    if len(low.halves) == 2:
        sx = low.split
        dashed = (
            f'<line x1="{sx}" y1="{cy}" x2="{sx}" y2="{geo.bottom}" stroke="{s_ink}" '
            f'stroke-width="1.5" stroke-dasharray="6 5"/>'
        )
        halves = _txt(
            sx - 10,
            cy + 160,
            lab[low.halves[0]],
            12,
            font_weight="600",
            fill=s_ink,
            text_anchor="end",
        ) + _txt(
            sx + 10, cy + 160, lab[low.halves[1]], 12, font_weight="600", fill=s_ink
        )
    return (
        f'<polygon points="40,{BOARD_TOP} {cx},{BOARD_TOP} {cx},{cy} {lx},{ly}" fill="{od_bg}"/>'
        f'<polygon points="{cx},{BOARD_TOP} {WIDTH - 40},{BOARD_TOP} {rx},{ry} {cx},{cy}" '
        f'fill="{oo_bg}"/><polygon points="{s_points}" fill="{s_bg}"/>'
        f'<g stroke="#111" stroke-width="2"><line x1="{cx}" y1="{BOARD_TOP}" x2="{cx}" y2="{cy}"/>'
        f'<line x1="{cx}" y1="{cy}" x2="{lx}" y2="{ly}"/>'
        f'<line x1="{cx}" y1="{cy}" x2="{rx}" y2="{ry}"/></g>'
        + dashed
        + _txt(60, 128, left.label[lang], 16, font_weight="600", fill=od_ink)
        + _txt(
            1540,
            128,
            right.label[lang],
            16,
            font_weight="600",
            fill=oo_ink,
            text_anchor="end",
        )
        + _txt(120, s_label_y, low.label[lang], 16, font_weight="600", fill=s_ink)
        + halves
    )


def _regions_screen(profile: Profile, geo: Geometry, lang: str) -> str:
    """Each board a rectangle around its placed region, named at its top left;
    a board with halves split by a dashed line at its `split`."""
    lab = LABELS[lang]
    parts: list[str] = []
    for b in profile.boards:
        x0, y0, x1, y1 = geo.board(b.id)
        left, top, right, bottom = outline((x0, y0, x1, y1))
        bg, ink = b.colour
        parts.append(
            f'<rect x="{left:g}" y="{top:g}" width="{right - left:g}" '
            f'height="{bottom - top:.1f}" fill="{bg}" stroke="#111" stroke-width="2"/>'
            + _txt(x0, y0 - 22, b.label[lang], 16, font_weight="600", fill=ink)
        )
        if len(b.halves) == 2:
            sx = b.split
            parts.append(
                f'<line x1="{sx:g}" y1="{y0 - 14:g}" x2="{sx:g}" y2="{bottom:.1f}" '
                f'stroke="{ink}" stroke-width="1.5" stroke-dasharray="6 5"/>'
                + _txt(
                    sx - 10,
                    y0 - 4,
                    lab[b.halves[0]],
                    12,
                    font_weight="600",
                    fill=ink,
                    text_anchor="end",
                )
                + _txt(
                    sx + 10, y0 - 4, lab[b.halves[1]], 12, font_weight="600", fill=ink
                )
            )
    return "".join(parts)


def render_svg(
    data: dict[str, Any],
    lang: str = "ru",
    show: set[str] | None = None,
    focus: set[str] | None = None,
    layers: frozenset[str] = LAYERS,
    board: str | None = None,
) -> str:
    """Draw the screen. `show` limits the elements drawn, `focus` rings the ones
    a frame adds and dims the rest, `layers` picks transitions, K badges and the
    legend, `board` (od, oo, s, s.small, s.big) cuts the screen to one board or
    half. Placement is
    always computed on the whole record, so a subset keeps the positions it has
    on the full screen."""
    lab = LABELS[lang]
    profile = profile_of(data)
    geo, boxes = plan(data, 960)
    els = {e["id"]: e for e in data["elements"]}
    shown = set(els) if show is None else show & set(els)
    parts: list[str] = []

    def dim(ids: tuple[str, ...], svg: str) -> str:
        if focus is None or any(i in focus for i in ids):
            return svg
        return f'<g opacity="0.4">{svg}</g>'

    draw_screen = _three_boards if profile.screen == "triangles" else _regions_screen
    screen = draw_screen(profile, geo, lang)
    parts.append(screen)

    # frames first so that their chips are drawn on top
    ordered = sorted(
        data["elements"],
        key=lambda e: 0 if profile.kind(e["kind"]).shape == "frame" else 1,
    )
    for el in ordered:
        if el["id"] not in shown:
            continue
        halo = _halo(boxes[el["id"]]) if focus and el["id"] in focus else ""
        parts.append(
            f'<g class="el" data-id="{esc(el["id"])}" data-kind="{el["kind"]}" '
            f'data-board="{el["board"]}" data-origin="{origin(el)}">'
            + halo
            + dim((el["id"],), _element(el, boxes[el["id"]], profile))
            + "</g>"
        )

    linked = shown
    if board:  # a cut screen keeps only the links inside its board
        part, _, half = board.partition(".")
        linked = {
            i
            for i in shown
            if els[i]["board"] == part and (not half or els[i].get("half") == half)
        }
    relations = data.get("relations", [])
    spots = _label_spots(relations, boxes, _obstacles(data, boxes, profile, screen))
    for rel, spot in zip(relations, spots):
        if rel["from"] not in linked or rel["to"] not in linked:
            continue
        a, b = boxes[rel["from"]], boxes[rel["to"]]
        start = len(parts)
        path, _, _ = _curve(a, b, _bend(rel))
        if rel["kind"] == "shift":
            parts.append(
                f'<path d="{path}" fill="none" stroke="{INK}" stroke-width="1.5" '
                f'marker-end="url(#ak)"/>'
            )
        else:
            parts.append(
                f'<path d="{path}" fill="none" stroke="#888" stroke-width="1.2" '
                f'stroke-dasharray="4 3" marker-end="url(#ag)"/>'
            )
        if spot is not None:
            x, y, lines = spot
            parts.append(
                _lines(
                    x,
                    y,
                    lines,
                    LABEL_SIZE,
                    LABEL_LEADING,
                    fill=MUTED,
                    text_anchor="middle",
                )
            )
        parts[start:] = [
            f'<g class="rel" data-from="{esc(rel["from"])}" data-to="{esc(rel["to"])}">'
            + dim((rel["from"], rel["to"]), "".join(parts[start:]))
            + "</g>"
        ]

    trs = sorted(data.get("transitions", []), key=lambda t: t["n"])
    if "transitions" not in layers:
        trs = []
    for tr in trs:
        if tr["from"] not in shown or tr["to"] not in shown:
            continue
        path, mx, my = _curve(boxes[tr["from"]], boxes[tr["to"]])
        parts.append(
            f'<g class="tr" data-from="{esc(tr["from"])}" data-to="{esc(tr["to"])}">'
            f'<path d="{path}" fill="none" stroke="{RED}" stroke-width="2.5" '
            f'marker-end="url(#ar)"/>'
        )
        parts.append(
            f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="11" fill="#fff" stroke="{RED}" '
            f'stroke-width="2"/>'
            + _txt(
                mx,
                my + 4,
                str(tr["n"]),
                12,
                fill=RED,
                font_weight="700",
                text_anchor="middle",
            )
            + "</g>"
        )

    stacked: dict[str, int] = {}
    for q in data.get("qualifications", []) if "k" in layers else []:
        if not q.get("targets") or q["targets"][0] not in shown:
            continue
        target = q["targets"][0]
        box = boxes[target]
        k = stacked.get(target, 0)
        stacked[target] = k + 1
        figure = profile.kind(els[target]["kind"]).shape == "figure"
        bx, by = _badge(box, k, figure)
        fill = NAVY if q["status"] != "closed" else "#8a94b8"
        parts.append(
            f'<g class="k" data-k="{q["id"]}" data-target="{esc(target)}">'
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="32" height="20" rx="4" fill="{fill}"/>'
            + _txt(
                bx + 16,
                by + 14,
                q["id"],
                12,
                fill="#fff",
                font_weight="700",
                text_anchor="middle",
            )
            + "</g>"
        )

    # a dense record overflows its regions; start the legend below the content
    bottom = max([geo.bottom] + [boxes[i].y + boxes[i].h for i in shown])
    if "legend" in layers:
        legend, height = _legend(data, lang, bottom + 24)
    else:
        legend, height = "", bottom + 24
    subtitle = " · ".join(
        str(v)
        for v in (
            data.get("case"),
            f"{lab['cycle']} {data['cycle']}",
            data["status"],
            data.get("date"),
        )
        if v
    )
    head = _txt(
        40, 42, subtitle.upper(), 13, fill=NAVY, font_weight="600", letter_spacing="2"
    ) + _txt(40, 78, data["title"], 26, font_weight="700", fill="#111")
    frame = (
        _crop(board, geo, boxes, els, profile) if board else (0.0, 0.0, WIDTH, height)
    )
    view = " ".join(f"{v:.0f}" for v in frame)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}" '
        f'font-family="IBM Plex Sans, Helvetica, Arial, sans-serif">{DEFS}'
        f'<rect width="{WIDTH}" height="{height:.0f}" fill="#fff"/>{head}'
        + "".join(parts)
        + legend
        + "</svg>\n"
    )
