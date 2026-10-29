"""Automatic placement of board-set elements on the screen of their profile.

The boards, their regions, where the halves of a board meet (`split`) and the
order of kinds come from the record's profile (profiles/*.yaml). Boards whose
regions overlap vertically form a row (`Profile.rows`).

A dense record does not fit the regions. A row whose content overflows grows
downwards as one and pushes the rows below it down. On the `triangles` screen
(the program's: Girenko, day 4, 17.10.2026) the board below the triangles'
apex does not grow; if it overflows, it is extended below its triangle into a
band as wide as the screen, where each half gets the full half width.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from smd_engine.profile import Board, Profile, default_profile, profile_of
from smd_engine.render.text import screen_label, text_width, wrap
from smd_engine.screen import BOARD_BOTTOM, CENTER, LEFT_CORNER, WIDTH, Rect

GAP = 14


def regions(profile: Profile) -> dict[str, Rect]:
    """Inner rectangles where automatic layout places items: a board's region,
    or, for a board with halves, one region per half (`s.small`, `s.big`),
    20 apart around the board's `split`."""
    out: dict[str, Rect] = {}
    for b in profile.boards:
        x0, y0, x1, y1 = b.region
        if len(b.halves) == 2:
            out[f"{b.id}.{b.halves[0]}"] = (x0, y0, b.split - 10, y1)
            out[f"{b.id}.{b.halves[1]}"] = (b.split + 10, y0, x1, y1)
        elif b.halves:
            out[f"{b.id}.{b.halves[0]}"] = b.region
        else:
            out[b.id] = b.region
    return out


@dataclass
class Geometry:
    """Where the boards are; the defaults are the organisers' screen."""

    cy: float = CENTER[1]
    corner_y: float = LEFT_CORNER[1]
    bottom: float = BOARD_BOTTOM
    wide: bool = False  # the board below the triangles extended into a band
    regions: dict[str, Rect] = field(default_factory=lambda: regions(default_profile()))

    def board(self, board_id: str) -> Rect:
        """A board's placed region: its own, or the span of its halves."""
        rects = [r for k, r in self.regions.items() if k.partition(".")[0] == board_id]
        return (
            min(r[0] for r in rects),
            min(r[1] for r in rects),
            max(r[2] for r in rects),
            max(r[3] for r in rects),
        )


@dataclass
class Box:
    id: str
    x: float
    y: float
    w: float
    h: float
    lines: list[str] = field(default_factory=list)
    children: list["Box"] = field(default_factory=list)

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


def region_of(el: dict[str, Any]) -> str:
    """`od`, or `s.small` for an element on a half (only boards with halves take `half`)."""
    return f"{el['board']}.{el['half']}" if "half" in el else str(el["board"])


def _measure(
    el: dict[str, Any], region_w: float, n_children: int, profile: Profile
) -> Box:
    shape = profile.kind(el["kind"]).shape
    label = screen_label(el)
    if shape == "marker":
        lines = wrap(label, 200, 12)
        w = 30 + max(text_width(ln, 12) for ln in lines)
        return Box(el["id"], 0, 0, w, max(24, len(lines) * 15), lines)
    if shape == "figure":
        lines = wrap(label, 190, 13)
        w = max(70, max(text_width(ln, 13) for ln in lines) + 8)
        return Box(el["id"], 0, 0, w, 52 + len(lines) * 15, lines)
    if shape == "ellipse":
        lines = wrap(label, 200, 12)
        w = max(text_width(ln, 12) for ln in lines) + 40
        return Box(el["id"], 0, 0, w, len(lines) * 14 + 22, lines)
    if shape == "question":
        lines = wrap(label, 200, 12)
        w = 40 + max(text_width(ln, 12) for ln in lines)
        return Box(el["id"], 0, 0, w, max(34, len(lines) * 14 + 6), lines)
    if shape == "frame":
        if n_children:
            w = region_w
        else:
            w = min(
                region_w, max(text_width(ln, 13) for ln in wrap(label, 240, 13)) + 28
            )
        lines = wrap(label, w - 24, 13)
        return Box(el["id"], 0, 0, w, len(lines) * 16 + 20, lines)
    if shape in ("heading", "paragraph") and profile.board(el["board"]).halves:
        heading = shape == "heading"
        size = 13 if heading else 12
        # bold headings run wider than the average glyph estimate
        lines = wrap(label, region_w * (0.9 if heading else 0.97), size)
        return Box(el["id"], 0, 0, region_w, len(lines) * (size + 3) + 6, lines)
    lines = wrap(label, 240, 12)
    w = min(region_w, max(text_width(ln, 12) for ln in lines) + 24)
    return Box(el["id"], 0, 0, w, len(lines) * 15 + 14, lines)


def _chip(el: dict[str, Any]) -> Box:
    lines = wrap(screen_label(el), 130, 11.5)
    w = max(text_width(ln, 11.5) for ln in lines) + 16
    return Box(el["id"], 0, 0, w, len(lines) * 13 + 12, lines)


def _flow(boxes: list[Box], x0: float, y0: float, x1: float) -> float:
    """Place boxes left to right in rows; return the bottom edge used."""
    x, y, row_h = x0, y0, 0.0
    for box in boxes:
        if x > x0 and x + box.w > x1:
            x, y, row_h = x0, y + row_h + GAP, 0.0
        box.x, box.y = x, y
        x += box.w + GAP
        row_h = max(row_h, box.h)
    return y + row_h


def _place(
    items: list[dict[str, Any]],
    children: dict[str, list[dict[str, Any]]],
    region: Rect,
    profile: Profile,
) -> tuple[list[Box], float]:
    """Measure and flow one region's items; return the boxes and their bottom."""
    x0, y0, x1, _y1 = region
    measured = [
        _measure(e, x1 - x0, len(children.get(e["id"], [])), profile) for e in items
    ]
    for box in measured:
        kids = [_chip(c) for c in children.get(box.id, [])]
        if kids:
            header = box.h
            bottom = _flow(kids, 12, header, box.w - 12)
            box.h = bottom + 12
            box.children = kids
    bottom = _flow(measured, x0, y0, x1) if measured else y0
    for box in measured:
        for kid in box.children:
            kid.x += box.x
            kid.y += box.y
    return measured, bottom


def plan(data: dict[str, Any], height: float = 960) -> tuple[Geometry, dict[str, Box]]:
    """Return the board geometry and a box per element id (frame children included)."""
    profile = profile_of(data)
    elements: list[dict[str, Any]] = data["elements"]
    by_id = {e["id"]: e for e in elements}

    def framed(e: dict[str, Any]) -> bool:
        return profile.kind(e["kind"]).shape == "frame"

    frames = {e["id"] for e in elements if framed(e)}
    children: dict[str, list[dict[str, Any]]] = {}
    for el in elements:
        parent = next((p for p in el.get("in", []) if p in frames), None)
        if parent and "geom" not in el and not framed(el):
            children.setdefault(parent, []).append(el)
    child_ids = {c["id"] for kids in children.values() for c in kids}
    order = {k: i for i, k in enumerate(profile.kind_order)}
    start = regions(profile)
    items: dict[str, list[dict[str, Any]]] = {r: [] for r in start}
    for e in elements:
        if e["id"] not in child_ids and "geom" not in e:
            items[region_of(e)].append(e)
    for region_items in items.values():
        region_items.sort(key=lambda e: order.get(e["kind"], len(order)))

    geo = Geometry(regions=dict(start))
    triangles = profile.screen == "triangles"
    placed: dict[str, list[Box]] = {}
    shift: float = 0  # how far the rows above have grown
    rows = profile.rows
    for n, row in enumerate(rows):
        ids = {b.id for b in row}
        keys = [r for r in start if r.partition(".")[0] in ids]
        for r in keys:
            x0, y0, x1, y1 = start[r]
            geo.regions[r] = (x0, y0 + shift, x1, y1 + shift)
        if triangles and n == len(rows) - 1:
            geo.cy += shift
            geo.corner_y += shift
            geo.bottom += shift
            _below_triangles(geo, keys, items, children, placed, profile, row[0])
            break
        bottoms: dict[str, float] = {}
        for r in keys:
            placed[r], bottoms[r] = _place(items[r], children, geo.regions[r], profile)
        grow = max([0.0] + [bottoms[r] + GAP - geo.regions[r][3] for r in keys])
        for r in keys:
            x0, y0, x1, y1 = geo.regions[r]
            geo.regions[r] = (x0, y0, x1, y1 + grow)
        shift += grow
    if not triangles:  # the boards end just below their regions
        geo.bottom = max(r[3] for r in geo.regions.values()) + 10

    boxes: dict[str, Box] = {}
    for measured in placed.values():
        for box in measured:
            boxes[box.id] = box
            for kid in box.children:
                boxes[kid.id] = kid

    for el in elements:
        if "geom" in el:
            gx, gy, gw, gh = el["geom"]
            box = _measure(el, gw * WIDTH, 0, profile)
            box.x, box.y, box.w, box.h = (
                gx * WIDTH,
                gy * height,
                gw * WIDTH,
                gh * height,
            )
            kids = [_chip(c) for c in children.get(el["id"], [])]
            if kids:
                _flow(
                    kids,
                    box.x + 12,
                    box.y + len(box.lines) * 16 + 20,
                    box.x + box.w - 12,
                )
                box.children = kids
                for kid in kids:
                    boxes[kid.id] = kid
            boxes[el["id"]] = box
    missing = set(by_id) - set(boxes)
    for eid in missing:  # pragma: no cover - every element is placed in a region
        boxes[eid] = Box(eid, 60, 150, 100, 30, [screen_label(by_id[eid])])
    return geo, boxes


def _below_triangles(
    geo: Geometry,
    keys: list[str],
    items: dict[str, list[dict[str, Any]]],
    children: dict[str, list[dict[str, Any]]],
    placed: dict[str, list[Box]],
    profile: Profile,
    board: Board,
) -> None:
    """Place the board below the triangles; when it overflows, extend it into
    a band below its triangle, a half to each half of the screen."""
    over = False
    for r in keys:
        placed[r], bottom = _place(items[r], children, geo.regions[r], profile)
        over = over or bottom > geo.regions[r][3]
    if not over:
        return
    geo.wide = True
    # the triangle keeps only the room for its labels; the band does the work
    geo.corner_y = geo.cy + 200
    band = geo.corner_y + 2 * GAP
    spans = (
        [(60, board.split - 10), (board.split + 10, WIDTH - 60)]
        if len(keys) == 2
        else [(60, WIDTH - 60)]
    )
    for r, (x0, x1) in zip(keys, spans):
        geo.regions[r] = (x0, band, x1, band)
    lowest = band
    for r in keys:
        placed[r], bottom = _place(items[r], children, geo.regions[r], profile)
        lowest = max(lowest, bottom)
    geo.bottom = lowest + 36
    for r in keys:
        x0, y0, x1, _ = geo.regions[r]
        geo.regions[r] = (x0, y0, x1, lowest)


def layout(data: dict[str, Any], height: float) -> dict[str, Box]:
    """Return a box per element id (frame children included)."""
    return plan(data, height)[1]
