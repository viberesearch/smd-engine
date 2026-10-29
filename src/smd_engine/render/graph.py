"""A board set as a graph: one model for the 3D page (`smd graph`) and the Obsidian vault.

The boards of the record's profile become stacked planes, the first board at the bottom, each
keeping the positions of the screen. Theses, hypotheses, K and ontology records form a layer above the boards, sources a
layer below. Edges are the typed relations plus the links the records carry: a hypothesis
tests its targets, a K qualifies its targets, a thesis feeds elements, an item cites sources.
"""

from __future__ import annotations

import json
import math
from typing import Any

from smd_engine.profile import Profile, profile_of
from smd_engine.render import asset_text
from smd_engine.render.graph_ui import UI
from smd_engine.render.layout import plan, region_of
from smd_engine.render.text import cut, esc, screen_label

SPAN = 1000.0  # width of a board plane in graph units
LAYER = 260.0  # distance between planes


def planes(profile: Profile) -> dict[str, float]:
    """Plane per board, top down (the last board on top), centred on 0; records
    above the boards, sources below. In LAYER units; `graph_model` passes the
    heights to graph.js as `planes`."""
    boards = [b.id for b in reversed(profile.boards)]
    middle = (len(boards) - 1) / 2
    z = {b: middle - n for n, b in enumerate(boards)}
    return {**z, "records": 2.0, "sources": -2.0}


# Edge kinds: the schema's relation kinds, then the links other records carry.
EDGE_KINDS: dict[str, dict[str, str]] = {
    "ru": {
        "flow": "поток",
        "shift": "сдвиг позиции",
        "opposes": "противостоит",
        "produces": "производит",
        "uses": "использует",
        "belongs": "принадлежит",
        "represents": "представляет",
        "refers": "ссылается",
        "other": "прочее",
        "in": "входит в",
        "transition": "переход",
        "tests": "проверяет",
        "qualifies": "квалифицирует",
        "feeds": "питает",
        "valid_for": "верно для позиции",
        "cooperation": "кооперация",
        "tested_by": "проверяется гипотезой",
        "cites": "источник",
    },
    "en": {
        "flow": "flow",
        "shift": "position shift",
        "opposes": "opposes",
        "produces": "produces",
        "uses": "uses",
        "belongs": "belongs",
        "represents": "represents",
        "refers": "refers",
        "other": "other",
        "in": "is in",
        "transition": "transition",
        "tests": "tests",
        "qualifies": "qualifies",
        "feeds": "feeds",
        "valid_for": "valid for position",
        "cooperation": "cooperation",
        "tested_by": "tested by hypothesis",
        "cites": "source",
    },
}
# Kinds shown by the "flows and shifts" view.
FLOW_KINDS = ["flow", "shift", "opposes", "produces", "uses", "transition"]
GROUP_LABELS = {
    "ru": {
        "thesis": "тезис",
        "hypothesis": "гипотеза",
        "qualification": "квалификация (К)",
        "ontology": "онтология",
        "source": "источник",
    },
    "en": {
        "thesis": "thesis",
        "hypothesis": "hypothesis",
        "qualification": "qualification (K)",
        "ontology": "ontology",
        "source": "source",
    },
}


def _source_id(cite: str) -> str:
    return cite.split("#", 1)[0]


def _spread(i: int, scale: float = 26.0) -> tuple[float, float]:
    """A deterministic offset so that records sharing a centre do not overlap."""
    angle = i * 2.399963  # golden angle
    r = scale * math.sqrt(i + 1)
    return r * math.cos(angle), r * math.sin(angle)


def graph_model(
    data: dict[str, Any], lang: str = "ru", manifest: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Nodes with 3D positions and typed edges for a board set."""
    profile = profile_of(data)
    plane_z = planes(profile)
    boards = [b.id for b in reversed(profile.boards)]
    _, boxes = plan(data)
    elements = data["elements"]
    by_id = {e["id"]: e for e in elements}

    # Each board keeps its screen layout, centred and stretched to a SPAN square. A region
    # that is one tall column on screen (the halves of the situation board) is reflowed
    # into a grid in screen order, so that it does not collapse into a line.
    centre: dict[str, tuple[float, float]] = {}
    for e in elements:
        if e["id"] in boxes:
            centre[e["id"]] = (boxes[e["id"]].cx, boxes[e["id"]].cy)
    regions: dict[str, list[str]] = {}
    for e in elements:
        if e["id"] in centre:
            regions.setdefault(region_of(e), []).append(e["id"])
    for ids in regions.values():
        xs = [centre[i][0] for i in ids]
        ys = [centre[i][1] for i in ids]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        if len(ids) < 4 or w >= 0.25 * h:
            continue
        cols = max(2, round(math.sqrt(len(ids) * 0.8)))
        x0, step = min(xs) - h / 4, h / 2 / (cols - 1)
        rows = math.ceil(len(ids) / cols)
        ystep = h / max(rows - 1, 1)
        order = sorted(ids, key=lambda i: (centre[i][1], centre[i][0]))
        for n, i in enumerate(order):
            centre[i] = (x0 + (n % cols) * step, min(ys) + (n // cols) * ystep)
    pos: dict[str, tuple[float, float, float]] = {}
    for board in boards:
        ids = [e["id"] for e in elements if e["board"] == board and e["id"] in centre]
        if not ids:
            continue
        xs = [centre[i][0] for i in ids]
        ys = [centre[i][1] for i in ids]
        mx, my = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        sx = SPAN / max(max(xs) - min(xs), 1.0)
        sy = SPAN / max(max(ys) - min(ys), 1.0)
        for i in ids:
            pos[i] = (
                (centre[i][0] - mx) * sx,
                (centre[i][1] - my) * sy,
                plane_z[board] * LAYER,
            )

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    def edge(src: str, dst: str, kind: str, label: str = "") -> None:
        edges.append({"s": src, "t": dst, "k": kind, "l": label})

    for e in elements:
        x, y, z = pos.get(e["id"], (0.0, 0.0, plane_z[e["board"]] * LAYER))
        nodes.append(
            {
                "id": e["id"],
                "g": "element",
                "b": e["board"],
                "kind": profile.kind_label(e["kind"], lang),
                "short": screen_label(e),
                "label": e["label"],
                "note": e.get("label_note", ""),
                "voice": e.get("voice", ""),
                "epistemic": e.get("epistemic", ""),
                "fillers": e.get("fillers", []),
                "detail": e.get("detail"),
                "cites": e.get("cites", []),
                "x": x,
                "y": y,
                "z": z,
            }
        )
        for parent in e.get("in", []):
            if parent in by_id:
                edge(e["id"], parent, "in")
    for r in data.get("relations", []):
        if r["from"] in by_id and r["to"] in by_id:
            edge(r["from"], r["to"], r["kind"], r.get("label", ""))
    for t in data.get("transitions", []):
        if t["from"] in by_id and t["to"] in by_id:
            edge(t["from"], t["to"], "transition", f"{t['n']}. {t.get('label', '')}")

    # Records above the boards, each near the elements it is about.
    records: list[tuple[str, dict[str, Any], str, str, list[str], str]] = []
    for t in data.get("theses", []):
        records.append(
            ("thesis", t, t["claim"], t.get("status", ""), t.get("feeds", []), "feeds")
        )
    for h in data.get("hypotheses", []):
        records.append(
            (
                "hypothesis",
                h,
                h["assumes"],
                h.get("status", ""),
                h.get("targets", []),
                "tests",
            )
        )
    for k in data.get("qualifications", []):
        records.append(
            (
                "qualification",
                k,
                k["text"],
                k.get("status", ""),
                k.get("targets", []),
                "qualifies",
            )
        )
    for o in data.get("ontology", []):
        records.append(
            ("ontology", o, o["object"], "", o.get("valid_for", []), "valid_for")
        )
    for n, (group, rec, text, status, targets, kind) in enumerate(records):
        anchors = [pos[t] for t in targets if t in pos]
        cx = sum(a[0] for a in anchors) / len(anchors) if anchors else 0.0
        cy = sum(a[1] for a in anchors) / len(anchors) if anchors else 0.0
        dx, dy = _spread(n)
        extra = {
            key: rec[key]
            for key in ("action", "observe", "revise_if", "competes", "test")
            if rec.get(key)
        }
        nodes.append(
            {
                "id": rec["id"],
                "g": group,
                "b": "records",
                "kind": GROUP_LABELS[lang][group],
                "short": rec["id"],
                "label": text,
                "note": rec.get("note", ""),
                "status": status,
                "voice": rec.get("voice", ""),
                "extra": extra,
                "cites": rec.get("cites", []),
                "x": cx + dx,
                "y": cy + dy,
                "z": plane_z["records"] * LAYER,
            }
        )
        for target in targets:
            if target in by_id:
                edge(rec["id"], target, kind)
        if group == "ontology":
            if rec.get("cooperation") in by_id:
                edge(rec["id"], rec["cooperation"], "cooperation")
            if rec.get("test"):
                edge(rec["id"], rec["test"], "tested_by")

    # Sources below the boards, under the items that cite them.
    titles = {s["id"]: s for s in (manifest or {}).get("sources", [])}
    known = {n["id"]: n for n in nodes}
    citing: dict[str, list[str]] = {}
    for node in nodes:
        for c in node["cites"]:
            citing.setdefault(_source_id(c), []).append(node["id"])
    for k, (sid, who) in enumerate(sorted(citing.items())):
        cx = sum(known[w]["x"] for w in who) / len(who)
        cy = sum(known[w]["y"] for w in who) / len(who)
        dx, dy = _spread(k, 18.0)
        meta = titles.get(sid, {})
        nodes.append(
            {
                "id": f"src:{sid}",
                "g": "source",
                "b": "sources",
                "kind": GROUP_LABELS[lang]["source"],
                "short": sid,
                "label": meta.get("title", sid),
                "note": meta.get("note", ""),
                "url": meta.get("url", ""),
                "cites": [],
                "x": cx + dx,
                "y": cy + dy,
                "z": plane_z["sources"] * LAYER,
            }
        )
        for who_id in sorted(set(who)):
            addresses = sorted(
                {c for c in known[who_id]["cites"] if _source_id(c) == sid}
            )
            edge(who_id, f"src:{sid}", "cites", ", ".join(addresses))

    present = {node["id"] for node in nodes}
    edges = [e for e in edges if e["s"] in present and e["t"] in present]
    return {
        "title": data.get("title", data.get("id", "")),
        "id": data.get("id", ""),
        "date": str(data.get("date", "")),
        "boards": {b: profile.board_label(b, lang) for b in boards},
        # the height of each plane, which graph.js draws them at
        "planes": {b: z * LAYER for b, z in plane_z.items()},
        # each board's ink colour, as on the screen and in the vault
        "board_colours": {b: profile.board(b).colour[1] for b in boards},
        # the engine's link kinds, then the relation kinds the profile labels
        "edge_kinds": EDGE_KINDS[lang]
        | {k: label[lang] for k, label in profile.relation_labels.items()},
        "flow_kinds": FLOW_KINDS,
        "nodes": nodes,
        "edges": edges,
    }


def render_graph_html(
    data: dict[str, Any], lang: str = "ru", manifest: dict[str, Any] | None = None
) -> str:
    """One self-contained page: no scripts or styles are loaded from outside."""
    model = graph_model(data, lang, manifest)
    ui = UI[lang]
    payload = json.dumps(model, ensure_ascii=False).replace("</", "<\\/")
    ui_json = json.dumps(ui, ensure_ascii=False).replace("</", "<\\/")
    name = cut(model["title"], 90)
    title = esc(f"{name} — граф" if lang == "ru" else f"{name} — graph")
    sub = esc(
        f"{model['id']} · {model['date']} · {len(model['nodes'])} "
        + ("точек, " if lang == "ru" else "points, ")
        + f"{len(model['edges'])} "
        + ("связей" if lang == "ru" else "links")
    )
    return (
        f'<!doctype html>\n<html lang="{lang}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{title}</title><style>{asset_text('graph.css')}</style></head><body>"
        f"<header><h1>{title}</h1><p>{sub}</p></header>"
        '<main><aside id="controls"></aside>'
        '<div id="wrap"><canvas id="c"></canvas><div id="tip"></div></div>'
        '<aside class="right" id="info"></aside></main>'
        f"<script>const DATA = {payload};\nconst UI_TEXT = {ui_json};\n{asset_text('graph.js')}</script>"
        "</body></html>\n"
    )
