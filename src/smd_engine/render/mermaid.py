"""Mermaid flowchart of a board set, for previews on GitHub (layout is lost)."""

from __future__ import annotations

from typing import Any

from smd_engine.profile import profile_of
from smd_engine.render.text import LABELS


def _label(text: str) -> str:
    return text.replace('"', "'").replace("\n", " ")


def render_mermaid(data: dict[str, Any], lang: str = "ru") -> str:
    lab = LABELS[lang]
    profile = profile_of(data)
    index = {e["id"]: f"n{i}" for i, e in enumerate(data["elements"])}

    def _node_id(eid: str) -> str:
        return index[eid]

    out = ["flowchart LR"]
    # a subgraph per board of the profile, or per half
    groups = [
        (
            f"{b.id}_{half}" if half else b.id,
            b.id,
            half,
            f"{b.label[lang]}: {lab[half]}" if half else b.label[lang],
        )
        for b in profile.boards
        for half in (b.halves or (None,))
    ]
    for gid, board, half, title in groups:
        items = [
            e for e in data["elements"] if e["board"] == board and e.get("half") == half
        ]
        if not items:
            continue
        out.append(f'  subgraph {gid}["{_label(title)}"]')
        for e in items:
            figure = profile.kind(e["kind"]).shape == "figure"
            shape = ('(["', '"])') if figure else ('["', '"]')
            out.append(
                f"    {_node_id(e['id'])}{shape[0]}{_label(e['label'])}{shape[1]}"
            )
        out.append("  end")
    for e in data["elements"]:
        for parent in e.get("in", []):
            out.append(f"  {_node_id(parent)} -.- {_node_id(e['id'])}")
    for r in data.get("relations", []):
        label = f"|{_label(r['label'])}|" if r.get("label") else ""
        out.append(f"  {_node_id(r['from'])} -->{label} {_node_id(r['to'])}")
    for t in sorted(data.get("transitions", []), key=lambda t: t["n"]):
        out.append(f"  {_node_id(t['from'])} ==>|{t['n']}| {_node_id(t['to'])}")
    return "\n".join(out) + "\n"
