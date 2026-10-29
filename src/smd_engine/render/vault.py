"""A board set as an Obsidian vault (`smd vault`).

One note per element, thesis, hypothesis, K, ontology record and source. Each outgoing link
is also a note property named after its kind, so graph plugins can colour and filter links
by type. The screen itself is a JSON Canvas file with the organisers' layout and labelled,
coloured links; Obsidian opens it without plugins.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from smd_engine.profile import Profile, profile_of
from smd_engine.render.graph import graph_model
from smd_engine.render.layout import plan
from smd_engine.render.text import cut

FOLDERS = {
    "ru": {
        "thesis": "Тезисы",
        "hypothesis": "Гипотезы",
        "qualification": "Квалификации",
        "ontology": "Онтология",
        "source": "Источники",
    },
    "en": {
        "thesis": "Theses",
        "hypothesis": "Hypotheses",
        "qualification": "Qualifications",
        "ontology": "Ontology",
        "source": "Sources",
    },
}
# Obsidian graph colours per folder (RGB as integers) and canvas colours per link kind;
# a board's folder and cards take the board's ink colour from the profile.
FOLDER_RGB = {
    "thesis": 0x7A4FA0,
    "hypothesis": 0xC0392B,
    "qualification": 0xD68910,
    "ontology": 0x1F8A9A,
    "source": 0x8A8A84,
}
CANVAS_COLOR = {
    "flow": "#1f77b4",
    "shift": "#d62728",
    "opposes": "#ff7f0e",
    "produces": "#2ca02c",
    "uses": "#17becf",
    "belongs": "#8c564b",
    "represents": "#9467bd",
    "refers": "#a3a39c",
    "other": "#7f7f7f",
    "in": "#bcbd22",
    "transition": "#e377c2",
}
TEXT: dict[str, dict[str, Any]] = {
    "ru": {
        "out": "Связи отсюда",
        "inc": "Связи сюда",
        "note": "Пометка",
        "fillers": "Кто может занять",
        "cites": "Источники",
        "start": "Начало",
        "canvas": "Экран — {boards}",
        "intro": (
            "Хранилище собрано движком из записи доски. Каждая заметка — элемент доски, "
            "тезис, гипотеза, К, запись онтологии или источник. Связи между заметками — "
            "связи записи; вид связи — свойство заметки с тем же именем."
        ),
        "how": [
            "Экран — файл «{canvas}»: {boards} в раскладке экрана, связи подписаны и окрашены по виду.",
            "Граф (Ctrl/Cmd+G): цвета — по папкам (доски, тезисы, гипотезы, К, онтология, источники).",
            "Плагин Extended Graph окрашивает и отбирает связи по виду: свойства «поток», «ссылается» и другие.",
            "Плагин Dataview строит таблицы ниже; без него они видны как код.",
        ],
        "tables": "Таблицы",
        "hyp_table": "Гипотезы и их статус",
        "k_table": "Открытые и частично закрытые К",
        "by_board": "Элементы по доскам",
    },
    "en": {
        "out": "Links from here",
        "inc": "Links to here",
        "note": "Note",
        "fillers": "Who can fill it",
        "cites": "Sources",
        "start": "Start",
        "canvas": "Screen — {boards}",
        "intro": (
            "This vault is built by the engine from a board record. Each note is a board "
            "element, thesis, hypothesis, K, ontology record or source. Links between notes "
            "are the record's links; the kind of a link is a note property of the same name."
        ),
        "how": [
            "The screen is the file «{canvas}»: {boards} in the screen layout, links labelled and coloured by kind.",
            "Graph view (Ctrl/Cmd+G): colours by folder (boards, theses, hypotheses, K, ontology, sources).",
            "The Extended Graph plugin colours and filters links by kind: the properties «flow», «refers» and others.",
            "The Dataview plugin builds the tables below; without it they show as code.",
        ],
        "tables": "Tables",
        "hyp_table": "Hypotheses and their status",
        "k_table": "Open and partly closed K",
        "by_board": "Elements by board",
    },
}

# The number of boards in words, for the help text and the canvas name.
BOARDS_N = {
    "ru": {1: "одна доска", 2: "две доски", 3: "три доски", 4: "четыре доски"},
    "en": {1: "one board", 2: "two boards", 3: "three boards", 4: "four boards"},
}

_BAD = re.compile(r'[\\/:*?"<>|#^\[\]]')


def _name(node: dict[str, Any]) -> str:
    """File name of a note: id plus short label, safe for Obsidian links."""
    short = node["short"] if node["g"] == "element" else cut(node["label"], 50)
    if node["label"] == node["id"]:
        short = ""
    base = f"{node['id'].replace('src:', '')} {short}".strip()
    base = _BAD.sub(" ", base)
    base = " ".join(base.split())
    return base[:90].rstrip(" .")


def _safe(text: str) -> str:
    return " ".join(_BAD.sub(" ", text).split())


def _folders(labels: dict[str, str], profile: Profile) -> dict[str, str]:
    """A folder name per board, from its label: a record board's label is free
    text, so what a path or an Obsidian link cannot hold is dropped (no profile
    board label has any). A record board whose own label leaves nothing, or
    whose name an earlier board of the profile already has, gets its id after
    the name. The names are returned in the order of `labels`."""
    named: dict[str, str] = {}
    for board in profile.boards:
        name = _safe(labels[board.id])
        template = profile.template(board.template)
        bare = template is not None and name in {
            _safe(f"{text}:") for text in template.label.values()
        }
        if not name or bare or name in named.values():
            name = f"{name} {board.id}".strip()
        named[board.id] = name
    return {bid: named[bid] for bid in labels}


def _folder(node: dict[str, Any], lang: str, boards: dict[str, str]) -> str:
    if node["g"] == "element":
        return boards[node["b"]]
    return FOLDERS[lang][node["g"]]


def _prop(kind: str, edge_kinds: dict[str, str]) -> str:
    return edge_kinds[kind].replace(" ", "_")


def export_vault(
    data: dict[str, Any],
    out: Path,
    lang: str = "ru",
    manifest: dict[str, Any] | None = None,
) -> list[Path]:
    """Write the vault under `out`; return the files written."""
    model = graph_model(data, lang, manifest)
    txt = dict(TEXT[lang])
    profile = profile_of(data)
    made = len(profile.record_boards)  # the boards the record makes of templates
    n = len(profile.boards) - made
    n_boards = BOARDS_N[lang].get(n, f"{n} досок" if lang == "ru" else f"{n} boards")
    if made:
        n_boards += f" и ещё {made}" if lang == "ru" else f" and {made} more"
    txt["canvas"] = txt["canvas"].format(boards=n_boards)
    boards = _folders(model["boards"], profile)
    rgb = {b: int(c[1:], 16) for b, c in model["board_colours"].items()}
    kinds = model["edge_kinds"]
    nodes = {n["id"]: n for n in model["nodes"]}
    names = {i: _name(n) for i, n in nodes.items()}
    paths = {i: f"{_folder(n, lang, boards)}/{names[i]}" for i, n in nodes.items()}
    outgoing: dict[str, list[dict[str, Any]]] = {i: [] for i in nodes}
    incoming: dict[str, list[dict[str, Any]]] = {i: [] for i in nodes}
    for e in model["edges"]:
        outgoing[e["s"]].append(e)
        incoming[e["t"]].append(e)
    written: list[Path] = []

    def write(rel: str, text: str) -> None:
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(path)

    for i, n in nodes.items():
        props: dict[str, Any] = {"id": i.replace("src:", "")}
        props["вид" if lang == "ru" else "kind"] = n["kind"]
        if n["g"] == "element":
            props["доска" if lang == "ru" else "board"] = boards[n["b"]]
        for key in ("status", "voice", "epistemic"):
            if n.get(key):
                props[key] = n[key]
        if n.get("url"):
            props["url"] = n["url"]
        if n["cites"]:
            props["cites"] = n["cites"]
        for e in outgoing[i]:
            props.setdefault(_prop(e["k"], kinds), []).append(
                f"[[{paths[e['t']]}|{names[e['t']]}]]"
            )
        tag_group = f"доска/{n['b']}" if n["g"] == "element" else n["g"]
        props["tags"] = [tag_group]
        body = [
            "---",
            yaml.safe_dump(
                props, allow_unicode=True, sort_keys=False, width=100000
            ).rstrip(),
            "---",
            "",
        ]
        body.append(f"# {n['label']}")
        body.append("")
        if n.get("note"):
            body += [f"> {txt['note']}: {n['note']}", ""]
        for k, v in (n.get("extra") or {}).items():
            body += [f"**{k}**: {v}", ""]
        if n.get("fillers"):
            body += [f"**{txt['fillers']}**: " + "; ".join(n["fillers"]), ""]
        if n.get("detail"):
            d = n["detail"]
            if d.get("title"):
                body.append(f"**{d['title']}**")
            body.append("| " + " | ".join(d["columns"]) + " |")
            body.append("|" + " --- |" * len(d["columns"]))
            for row in d["rows"]:
                body.append("| " + " | ".join(c.replace("|", "/") for c in row) + " |")
            body.append("")
        if outgoing[i]:
            body += [f"## {txt['out']}", ""]
            for e in outgoing[i]:
                tail = f" — {e['l']}" if e["l"] else ""
                body.append(
                    f"- {kinds[e['k']]} → [[{paths[e['t']]}|{names[e['t']]}]]{tail}"
                )
            body.append("")
        if incoming[i]:
            body += [f"## {txt['inc']}", ""]
            for e in incoming[i]:
                tail = f" — {e['l']}" if e["l"] else ""
                body.append(
                    f"- [[{paths[e['s']]}|{names[e['s']]}]] → {kinds[e['k']]}{tail}"
                )
            body.append("")
        write(f"{paths[i]}.md", "\n".join(body))

    # The screen as a canvas: the organisers' layout, element notes as cards.
    _, boxes = plan(data)
    cards = []
    for e in data["elements"]:
        if e["id"] not in boxes:
            continue
        box = boxes[e["id"]]
        cards.append(
            {
                "id": e["id"],
                "type": "file",
                "file": f"{paths[e['id']]}.md",
                "x": round(box.x * 1.6),
                "y": round(box.y * 1.6),
                "width": max(220, round(box.w * 1.6)),
                "height": max(90, round(box.h * 1.6)),
                "color": f"#{rgb[e['board']]:06x}",
            }
        )
    card_ids = {c["id"] for c in cards}
    links = [
        {
            "id": f"e{n}",
            "fromNode": e["s"],
            "toNode": e["t"],
            "toEnd": "arrow",
            "color": CANVAS_COLOR.get(e["k"], "#7f7f7f"),
            "label": kinds[e["k"]] + (f": {e['l']}" if e["l"] else ""),
        }
        for n, e in enumerate(model["edges"])
        if e["s"] in card_ids and e["t"] in card_ids
    ]
    canvas = f"{txt['canvas']}.canvas"
    write(
        canvas,
        json.dumps({"nodes": cards, "edges": links}, ensure_ascii=False, indent=1),
    )

    # Graph colours by folder.
    groups = [
        {"query": f'path:"{boards[b]}"', "color": {"a": 1, "rgb": rgb[b]}}
        for b in boards
    ] + [
        {"query": f'path:"{FOLDERS[lang][g]}"', "color": {"a": 1, "rgb": FOLDER_RGB[g]}}
        for g in ("thesis", "hypothesis", "qualification", "ontology", "source")
    ]
    write(
        ".obsidian/graph.json",
        json.dumps({"colorGroups": groups, "showArrow": True}, indent=1),
    )

    start: list[str] = [
        f"# {model['title']}",
        "",
        f"{model['id']} · {model['date']}",
        "",
        txt["intro"],
        "",
    ]
    start += [
        f"- {line.format(canvas=txt['canvas'], boards=n_boards)}" for line in txt["how"]
    ]
    start += ["", f"## {txt['tables']}", "", f"### {txt['hyp_table']}", ""]
    start += [
        "```dataview",
        f'TABLE status, voice FROM "{FOLDERS[lang]["hypothesis"]}" SORT file.name',
        "```",
        "",
        f"### {txt['k_table']}",
        "",
        "```dataview",
        f'TABLE status FROM "{FOLDERS[lang]["qualification"]}" WHERE status != "closed" SORT file.name',
        "```",
        "",
        f"### {txt['by_board']}",
        "",
    ]
    for board in boards:
        start += [
            f"**{boards[board]}**",
            "",
            "```dataview",
            f'LIST FROM "{boards[board]}" SORT file.name',
            "```",
            "",
        ]
    write(f"{txt['start']}.md", "\n".join(start))
    return written
