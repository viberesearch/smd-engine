"""The ontology slice of a pack as an inline SVG, drawn in Python from the pack.

Every label is wrapped into lines (tspan) inside its box and the box is sized to
the lines, so no text is cut. Two layouts, both deterministic:

- grouped: when no element has a tier and every relation points from a source to a
  target that has no relation of its own (many sources, one target), each target
  is a box with its sources stacked under it, joined by arrows; the groups flow
  into columns;
- rows: otherwise elements in rows by tier (rows that do not fit the width wrap),
  the relations as arrows that bend round the boxes in their way.

No namespace attribute and no external reference: the SVG sits inside an HTML
page. `ontology_figure` gives a wide and a narrow drawing; the style picks one."""

from __future__ import annotations

from typing import Any, NamedTuple

from smd_engine.render.text import esc
from smd_engine.task.labels import LABELS

FONT = 12.0
LINE = 15.0  # line height of a box label
PAD_X = 9.0  # between a box edge and its text
PAD_Y = 8.0
CHAR = 0.6  # estimated glyph width as a share of the font size (wide on purpose)
NODE_W = 200.0
GAP_X = 36.0
ROW_GAP = 70.0  # between rows of boxes, room for arrows and their labels
TITLE_H = 20.0  # the tier title above a row
MARGIN = 14.0
LANE = 70.0  # free strip at each side of the rows, where arrows can pass
WIDE = 1000.0
NARROW = 380.0
COL_GAP = 24.0
GROUP_GAP = 22.0
INDENT = 26.0
SRC_GAP = 6.0


class Box(NamedTuple):
    x: float
    y: float
    w: float
    h: float


def text_width(text: str, size: float = FONT) -> float:
    """Estimated width of a line; the drawing sizes boxes by it."""
    return len(text) * size * CHAR


def wrap_lines(text: str, width: float, size: float = FONT) -> list[str]:
    """Words into lines no wider than `width`; a word longer than a line is cut."""
    limit = max(4, int(width / (size * CHAR)))
    lines: list[str] = []
    line = ""
    for word in text.split():
        while len(word) > limit:
            if line:
                lines.append(line)
                line = ""
            lines.append(word[:limit])
            word = word[limit:]
        candidate = f"{line} {word}".strip()
        if len(candidate) <= limit:
            line = candidate
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines or [""]


def _node(box: Box, lines: list[str], css: str = "node", tip: str = "") -> str:
    """A rect with its lines of text, centred or left aligned by class."""
    top = box.y + PAD_Y + FONT
    tspans = "".join(
        f'<tspan x="{box.x + PAD_X:.1f}" y="{top + LINE * i:.1f}">{esc(t)}</tspan>'
        for i, t in enumerate(lines)
    )
    title = f"<title>{esc(tip)}</title>" if tip else ""
    return (
        f"<g>{title}"
        f'<rect x="{box.x:.1f}" y="{box.y:.1f}" width="{box.w:.1f}" '
        f'height="{box.h:.1f}" rx="8" class="{css}"/>'
        f'<text class="nodelab">{tspans}</text></g>'
    )


def _height(lines: list[str]) -> float:
    return 2 * PAD_Y + LINE * len(lines)


def _defs(uid: str) -> str:
    return (
        f'<defs><marker id="{uid}-arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" class="arrowhead"/></marker></defs>'
    )


def _svg(width: float, height: float, lang: str, uid: str, parts: list[str]) -> str:
    return (
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" width="{width:.0f}" '
        f'class="onto" role="img" aria-label="{esc(LABELS[lang]["relations"])}">'
        f'{_defs(uid)}{"".join(parts)}</svg>'
    )


def _known_relations(ontology: dict[str, Any]) -> list[dict[str, Any]]:
    ids = {e["id"] for e in ontology["elements"]}
    return [
        r
        for r in ontology["relations"]
        if r["from"] in ids and r["to"] in ids and r["from"] != r["to"]
    ]


def is_grouped(ontology: dict[str, Any]) -> bool:
    """Many sources to one target: no tiers, one outgoing relation per element at
    most, and no target that is itself a source."""
    if any("tier" in e for e in ontology["elements"]):
        return False
    rels = _known_relations(ontology)
    if not rels:
        return False
    sources = [r["from"] for r in rels]
    return len(set(sources)) == len(sources) and not set(sources) & {
        r["to"] for r in rels
    }


# --- grouped layout ---------------------------------------------------------


def _grouped(
    ontology: dict[str, Any], lang: str, uid: str, max_w: float
) -> tuple[str, list[Box]]:
    lab = LABELS[lang]
    elements = ontology["elements"]
    by_id = {e["id"]: e for e in elements}
    rels = _known_relations(ontology)
    cols = max(1, int((max_w - 2 * MARGIN + COL_GAP) // (300 + COL_GAP)))
    gw = (max_w - 2 * MARGIN - (cols - 1) * COL_GAP) / cols
    targets = [e["id"] for e in elements if e["id"] in {r["to"] for r in rels}]
    linked = {r["from"] for r in rels} | set(targets)
    loose = [e["id"] for e in elements if e["id"] not in linked]
    heights = [MARGIN] * cols
    parts: list[str] = []
    boxes: list[Box] = []
    arrows: list[str] = []

    def place(head: str | None, members: list[dict[str, Any]], tid: str | None) -> None:
        c = heights.index(min(heights))
        x, y = MARGIN + c * (gw + COL_GAP), heights[c]
        spine = x + INDENT / 2
        if head is not None:
            hl = wrap_lines(head, gw - 2 * PAD_X)
            hb = Box(x, y, gw, _height(hl))
            parts.append(_node(hb, hl, "node head", head))
            boxes.append(hb)
            y = hb.y + hb.h
        kinds = {r["kind"] for r in members}
        if tid is not None and len(kinds) == 1:
            parts.append(
                f'<text x="{x + INDENT:.1f}" y="{y + 13:.1f}" class="edgelab">'
                f"{esc(next(iter(kinds)))}</text>"
            )
            y += 18
        elif tid is not None:
            y += 8
        for r in members:
            el = by_id[r["from"]] if tid is not None else by_id[r["id"]]
            ind = INDENT if tid is not None else 0
            lines = wrap_lines(el["label"], gw - ind - 2 * PAD_X)
            kind_line = tid is not None and len(kinds) > 1
            shown = ([r["kind"]] if kind_line else []) + lines
            sb = Box(x + ind, y, gw - ind, _height(shown))
            parts.append(_node(sb, shown, "node", el["label"]))
            boxes.append(sb)
            if tid is not None:
                mid = sb.y + min(sb.h / 2, PAD_Y + FONT)
                arrows.append(
                    f'<path d="M{sb.x:.1f},{mid:.1f} H{spine:.1f} V{hb.y + hb.h:.1f}" '
                    f'class="edge" marker-end="url(#{uid}-arrow)"/>'
                )
            y += sb.h + SRC_GAP
        heights[c] = y + GROUP_GAP - SRC_GAP

    for tid in targets:
        place(by_id[tid]["label"], [r for r in rels if r["to"] == tid], tid)
    if loose:
        place(lab["no_relation"], [{"id": i, "kind": ""} for i in loose], None)
    width = max_w
    height = max(heights) - GROUP_GAP + MARGIN
    # arrows first so the boxes sit on top of any line end
    return _svg(width, height, lang, uid, arrows + parts), boxes


# --- rows layout ------------------------------------------------------------


def _rows(
    elements: list[dict[str, Any]], lang: str
) -> list[tuple[str, list[dict[str, Any]]]]:
    lab = LABELS[lang]
    tiers = sorted({e["tier"] for e in elements if "tier" in e})
    rows = [
        (lab["tier_n"].format(n=t), [e for e in elements if e.get("tier") == t])
        for t in tiers
    ]
    rest = [e for e in elements if "tier" not in e]
    if rest:
        rows.append((lab["no_tier"] if tiers else "", rest))
    return rows


def _edge_point(a: Box, toward: tuple[float, float]) -> tuple[float, float]:
    """Where the line from the centre of box a to a point leaves the box."""
    cx, cy = a.x + a.w / 2, a.y + a.h / 2
    dx, dy = toward[0] - cx, toward[1] - cy
    if dx == 0 and dy == 0:
        return cx, cy
    scale = min(
        (a.w / 2) / abs(dx) if dx else float("inf"),
        (a.h / 2) / abs(dy) if dy else float("inf"),
    )
    return cx + dx * scale, cy + dy * scale


def _inside(p: tuple[float, float], b: Box, grow: float = 3.0) -> bool:
    return b.x - grow < p[0] < b.x + b.w + grow and b.y - grow < p[1] < b.y + b.h + grow


def _curve(
    p: tuple[float, float], c: tuple[float, float], q: tuple[float, float], t: float
) -> tuple[float, float]:
    u = 1 - t
    return (
        u * u * p[0] + 2 * u * t * c[0] + t * t * q[0],
        u * u * p[1] + 2 * u * t * c[1] + t * t * q[1],
    )


def _route(
    a: Box, b: Box, others: list[Box], width: float, height: float
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float], float]:
    """A quadratic curve from box a to box b that keeps clear of the other boxes:
    straight when it can be, else bent to the side by the first offset that
    clears. Returns the two end points, the control point and the offset."""
    ac, bc = (a.x + a.w / 2, a.y + a.h / 2), (b.x + b.w / 2, b.y + b.h / 2)
    mid = ((ac[0] + bc[0]) / 2, (ac[1] + bc[1]) / 2)
    dx, dy = bc[0] - ac[0], bc[1] - ac[1]
    norm = (dx * dx + dy * dy) ** 0.5 or 1.0
    nx, ny = -dy / norm, dx / norm
    straight = (_edge_point(a, bc), _edge_point(b, ac), mid, 0.0)
    for off in (0, 40, -40, 80, -80, 130, -130, 190, -190, 260, -260, 340, -340):
        c = (mid[0] + nx * off, mid[1] + ny * off)
        if off == 0:
            ends = [(straight[0], straight[1])]
        else:  # leave by the sides that face the bend
            ends = [(p, q) for p in _facing(a, c) for q in _facing(b, c)]
        for p, q in ends:
            pts = [_curve(p, c, q, i / 24) for i in range(1, 24)]
            if all(not _inside(pt, o) for pt in pts for o in others) and all(
                4 <= pt[0] <= width - 4 and 4 <= pt[1] <= height - 4 for pt in pts
            ):
                return p, q, c, float(off)
    return straight


def _facing(box: Box, toward: tuple[float, float]) -> list[tuple[float, float]]:
    """The two side midpoints of a box nearest to a point."""
    mids = [
        (box.x + box.w / 2, box.y),
        (box.x + box.w / 2, box.y + box.h),
        (box.x, box.y + box.h / 2),
        (box.x + box.w, box.y + box.h / 2),
    ]
    mids.sort(key=lambda m: (m[0] - toward[0]) ** 2 + (m[1] - toward[1]) ** 2)
    return mids[:2]


def _rows_layout(
    ontology: dict[str, Any], lang: str, uid: str, max_w: float
) -> tuple[str, list[Box]]:
    elements = ontology["elements"]
    box_w = min(NODE_W, max_w - 2 * MARGIN - 2 * LANE)
    cap = max(1, int((max_w - 2 * MARGIN - 2 * LANE + GAP_X) // (box_w + GAP_X)))
    lines_of = {e["id"]: wrap_lines(e["label"], box_w - 2 * PAD_X) for e in elements}
    # physical lines: (title, elements)
    phys: list[tuple[str, list[dict[str, Any]]]] = []
    for title, items in _rows(elements, lang):
        for i in range(0, len(items), cap):
            phys.append((title if i == 0 else "", items[i : i + cap]))
    widest = max(len(items) for _, items in phys)
    width = widest * box_w + (widest - 1) * GAP_X + 2 * MARGIN + 2 * LANE
    boxes: dict[str, Box] = {}
    texts: list[str] = []
    y = MARGIN
    for title, items in phys:
        if title:
            texts.append(
                f'<text x="{MARGIN:.1f}" y="{y + 12:.1f}" class="rowlab">{esc(title)}</text>'
            )
            y += TITLE_H
        row_h = max(_height(lines_of[e["id"]]) for e in items)
        row_w = len(items) * box_w + (len(items) - 1) * GAP_X
        x0 = (width - row_w) / 2
        for col, el in enumerate(items):
            boxes[el["id"]] = Box(x0 + col * (box_w + GAP_X), y, box_w, row_h)
        y += row_h + ROW_GAP
    height = y - ROW_GAP + MARGIN
    drawn = list(boxes.values())
    edges: list[str] = []
    labels: list[tuple[float, float, str]] = []
    taken: list[Box] = []
    for rel in _known_relations(ontology):
        a, b = boxes[rel["from"]], boxes[rel["to"]]
        others = [bx for bx in drawn if bx not in (a, b)]
        p, q, c, off = _route(a, b, others, width, height)
        path = (
            f"M{p[0]:.1f},{p[1]:.1f} L{q[0]:.1f},{q[1]:.1f}"
            if off == 0
            else f"M{p[0]:.1f},{p[1]:.1f} Q{c[0]:.1f},{c[1]:.1f} {q[0]:.1f},{q[1]:.1f}"
        )
        edges.append(f'<path d="{path}" class="edge" marker-end="url(#{uid}-arrow)"/>')
        kind = rel["kind"]
        lw, lh = text_width(kind, 11) + 6, 14.0
        pick = None
        for t in (0.5, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8):
            lx, ly = _curve(p, c, q, t)
            lx = min(max(lx, lw / 2 + 2), width - lw / 2 - 2)
            cand = Box(lx - lw / 2, ly - lh + 3, lw, lh)
            if pick is None:
                pick = cand
            if not any(_overlap(cand, o) for o in drawn + taken):
                pick = cand
                break
        assert pick is not None
        taken.append(pick)
        labels.append((pick.x + pick.w / 2, pick.y + lh - 3, kind))
    for lx, ly, kind in labels:
        edges.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" class="edgelab" text-anchor="middle">{esc(kind)}</text>'
        )
    nodes = [
        _node(boxes[e["id"]], lines_of[e["id"]], "node", e["label"])
        for _, items in phys
        for e in items
    ]
    return _svg(width, height, lang, uid, texts + edges + nodes), drawn


def _overlap(a: Box, b: Box) -> bool:
    return not (
        a.x + a.w <= b.x or b.x + b.w <= a.x or a.y + a.h <= b.y or b.y + b.h <= a.y
    )


# --- public -----------------------------------------------------------------


def ontology_svg(
    ontology: dict[str, Any], lang: str, uid: str = "onto", max_w: float = WIDE
) -> str:
    """One drawing no wider than `max_w`; empty when there are no elements."""
    if not ontology["elements"]:
        return ""
    if is_grouped(ontology):
        return _grouped(ontology, lang, uid, max_w)[0]
    return _rows_layout(ontology, lang, uid, max_w)[0]


def ontology_figure(ontology: dict[str, Any], lang: str, uid: str = "onto") -> str:
    """The wide drawing and a narrow one for a phone; the style shows one. When
    both come out alike, only one is written."""
    wide = ontology_svg(ontology, lang, uid + "-w", WIDE)
    if not wide:
        return ""
    narrow = ontology_svg(ontology, lang, uid + "-n", NARROW)
    if narrow.split(">", 1)[0] == wide.split(">", 1)[0]:
        return f'<div class="onto-fig">{wide}</div>'
    return (
        f'<div class="onto-fig"><div class="onto-wide">{wide}</div>'
        f'<div class="onto-narrow">{narrow}</div></div>'
    )
