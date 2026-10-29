"""The screen's fixed geometry, in screen units (x to the right, y down).

One place for the numbers the profile checks (profile.py) and the renderers
(render/layout.py, render/svg.py, render/frames_page.py) share: the screen's
width and top, the margins a board is drawn with around its region, and the
program's triangles screen (Girenko, day 4, 17.10.2026).
"""

from __future__ import annotations

Rect = tuple[float, float, float, float]

WIDTH = 1600
BOARD_TOP = 100  # the top edge of every board as drawn
# Around its region a board is drawn 20 wider to each side, 50 taller above
# (for its name) and 10 below: left, top, right, bottom.
MARGIN = (20.0, 50.0, 20.0, 10.0)
# The height of a region of a board a record makes of a profile's template.
RECORD_BOARD_HEIGHT = 300.0

# The triangles screen: the two top boards meet at the apex, the third lies
# below it, between the lower corners.
BOARD_BOTTOM = 860
CENTER = (800.0, 440.0)
LEFT_CORNER = (40.0, 860.0)
RIGHT_CORNER = (1560.0, 860.0)


def outline(region: Rect) -> Rect:
    """The rectangle a board is drawn as around its region."""
    x0, y0, x1, y1 = region
    left, top, right, bottom = MARGIN
    return (x0 - left, y0 - top, x1 + right, y1 + bottom)


def overlap(a: Rect, b: Rect) -> bool:
    """Whether two rectangles share area; touching edges do not."""
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def inside(a: Rect, b: Rect) -> bool:
    """Whether rectangle `a` lies within `b`."""
    return b[0] <= a[0] and b[1] <= a[1] and a[2] <= b[2] and a[3] <= b[3]


def record_regions(fixed: list[Rect], n: int, columns: int) -> list[Rect]:
    """Regions of `n` record boards below the fixed boards' regions `fixed`:
    rows of `columns` across the span of the fixed boards, as close as the
    margins they are drawn with allow (40 side by side, 60 one above the
    other), each RECORD_BOARD_HEIGHT tall."""
    left, top, right, bottom = MARGIN
    x0, x1 = min(r[0] for r in fixed), max(r[2] for r in fixed)
    y0 = max(r[3] for r in fixed) + bottom + top
    gap = left + right
    width = (x1 - x0 - (columns - 1) * gap) / columns
    out: list[Rect] = []
    for i in range(n):
        row, col = divmod(i, columns)
        rx = x0 + col * (width + gap)
        ry = y0 + row * (RECORD_BOARD_HEIGHT + top + bottom)
        out.append((rx, ry, rx + width, ry + RECORD_BOARD_HEIGHT))
    return out


def triangle_parts() -> tuple[Rect, Rect, Rect]:
    """Where each board of the triangles screen stands, outline included: the
    first left of the apex and above it, the second right of it, the third
    between the apex and the lower corners. The top two parts lie inside their
    shapes; the third reaches past the slanted edges at its top corners, since
    the board below may grow into a band below its triangle anyway."""
    cx, cy = CENTER
    return (
        (LEFT_CORNER[0], BOARD_TOP, cx, cy),
        (cx, BOARD_TOP, RIGHT_CORNER[0], cy),
        (LEFT_CORNER[0], cy, RIGHT_CORNER[0], BOARD_BOTTOM),
    )


def triangle_shapes() -> tuple[str, str, str]:
    """The three shapes of the triangles screen, as SVG polygon points: top
    left, top right, the board below the apex."""
    cx, cy = CENTER
    (lx, ly), (rx, ry) = LEFT_CORNER, RIGHT_CORNER

    def points(*corners: tuple[float, float]) -> str:
        return " ".join(f"{x:g},{y:g}" for x, y in corners)

    return (
        points((lx, BOARD_TOP), (cx, BOARD_TOP), (cx, cy), (lx, ly)),
        points((cx, BOARD_TOP), (rx, BOARD_TOP), (rx, ry), (cx, cy)),
        points((lx, ly), (cx, cy), (rx, ry)),
    )
