"""Markdown digest of a board set: one line per element, for search and review."""

from __future__ import annotations

from typing import Any

from smd_engine.profile import profile_of
from smd_engine.render.text import LABELS, MOVE_NAMES


def _line(el: dict[str, Any]) -> str:
    bits = [f"`{el['id']}` {el['kind']}: {el['label']}"]
    if el.get("frame_state"):
        bits.append(f"({el['frame_state']})")
    if el.get("in"):
        bits.append("in " + ", ".join(f"`{i}`" for i in el["in"]))
    if el.get("fillers"):
        bits.append("fillers: " + ", ".join(el["fillers"]))
    if el.get("seen_from"):
        bits.append(f"seen from `{el['seen_from']}`")
    if el.get("epistemic"):
        bits.append(f"[{el['epistemic']}]")
    if el.get("lineage"):
        bits.append("lineage: " + ", ".join(el["lineage"]))
    if el.get("move"):
        m = el["move"]
        bits.append(
            f"move: {MOVE_NAMES[m['op']]} from {', '.join(m['from'])}"
            + (f" via {m['via']}" if m.get("via") else "")
            + (f" ({m['status']})" if m.get("status") else "")
        )
    if el.get("cites"):
        bits.append("— " + ", ".join(el["cites"]))
    return "- " + " ".join(bits)


def _board_line(board: dict[str, Any]) -> str:
    bits = [f"`{board['id']}` board of `{board['template']}`"]
    if board.get("unfolds"):
        bits.append(f"unfolds `{board['unfolds']}`")
    if board.get("seen_from"):
        bits.append(f"seen from `{board['seen_from']}`")
    if board.get("cites"):
        bits.append("— " + ", ".join(board["cites"]))
    return " ".join(bits)


def render_markdown(data: dict[str, Any], lang: str = "ru") -> str:
    lab = LABELS[lang]
    out = [f"# {data['title']}", ""]
    meta = [f"id `{data['id']}`", f"{lab['cycle']} {data['cycle']}", data["status"]]
    if data.get("revises"):
        meta.append(f"revises `{data['revises']}`")
    if data.get("date"):
        meta.append(data["date"])
    out += [" · ".join(meta), ""]
    # one section per board of the profile, or per half
    profile = profile_of(data)
    sections = [
        (b.id, b.label[lang], half)
        for b in profile.boards
        for half in (b.halves or (None,))
    ]
    made = {b["id"]: b for b in data.get("boards", [])}
    for board, name, half in sections:
        items = [
            e
            for e in data["elements"]
            if e["board"] == board and (half is None or e.get("half") == half)
        ]
        if not items and board not in made:  # a record board is always listed
            continue
        title = name + (f" — {lab[half]}" if half else "")
        out += [f"## {title}", ""]
        if board in made:  # a board the record makes of a template
            out += [_board_line(made[board]), ""]
        out += [_line(e) for e in items] + ([""] if items else [])
    tables = [e for e in data["elements"] if e.get("detail")]
    if tables:
        out += [f"## {lab['details']}", ""]
    for e in tables:
        d = e["detail"]
        out += [f"### `{e['id']}` {d.get('title', '')}".rstrip(), ""]
        out += ["| " + " | ".join(d["columns"]) + " |"]
        out += ["|" + "---|" * len(d["columns"])]
        out += ["| " + " | ".join(row) + " |" for row in d["rows"]] + [""]
    if data.get("relations"):
        out += [f"## {lab['relations']}", ""]
        for r in data["relations"]:
            label = f" — {r['label']}" if r.get("label") else ""
            out.append(f"- `{r['from']}` → `{r['to']}` ({r['kind']}){label}")
        out.append("")
    if data.get("transitions"):
        out += [f"## {lab['transitions']}", ""]
        for t in sorted(data["transitions"], key=lambda t: t["n"]):
            label = f" — {t['label']}" if t.get("label") else ""
            cites = f" ({', '.join(t['cites'])})" if t.get("cites") else ""
            out.append(f"{t['n']}. `{t['from']}` → `{t['to']}`{label}{cites}")
        out.append("")
    if data.get("qualifications"):
        out += [f"## {lab['qualifications']}", ""]
        for q in data["qualifications"]:
            targets = ", ".join(f"`{t}`" for t in q.get("targets", []))
            by = f" — {q['by']}" if q.get("by") else ""
            out.append(
                f"- **{q['id']}** [{lab['status'][q['status']]}] {q['text']}"
                f"{' (' + targets + ')' if targets else ''}{by}"
            )
        out.append("")
    if data.get("theses"):
        out += [f"## {lab['theses']}", ""]
        for t in data["theses"]:
            cites = f" — {', '.join(t['cites'])}" if t.get("cites") else ""
            feeds = (
                " → " + ", ".join(f"`{f}`" for f in t["feeds"])
                if t.get("feeds")
                else ""
            )
            out.append(
                f"- **{t['id']}** [{lab['thesis_status'][t['status']]}] "
                f"{t['voice']}, {t['belt']}, {t['kind']}: {t['claim']}{feeds}{cites}"
            )
        out.append("")
    if data.get("hypotheses"):
        out += [f"## {lab['hypotheses']}", ""]
        for h in data["hypotheses"]:
            bits = [
                f"- **{h['id']}** [{lab['hyp_status'][h['status']]}] {h['assumes']}"
            ]
            for key in ("action", "result", "changes"):
                if h.get(key):
                    bits.append(f"{key}: {h[key]}")
            if h.get("artefacts"):
                bits.append("— " + ", ".join(h["artefacts"]))
            out.append(" ".join(bits))
        out.append("")
    if data.get("ontology"):
        out += [f"## {lab['ontology']}", ""]
        for o in data["ontology"]:
            positions = ", ".join(f"`{p}`" for p in o["valid_for"])
            line = f"- **{o['id']}** {o['object']} ({lab['valid_for']} {positions})"
            if o.get("cooperation"):
                line += f"; cooperation `{o['cooperation']}`"
            if o.get("test"):
                line += f"; test {o['test']}"
            out.append(line)
            for sub in o.get("subjects", []):
                out.append(f"  - `{sub['position']}`: {sub['subject']}")
            if o.get("competes"):
                out.append(f"  - competes: {o['competes']}")
        out.append("")
    if data.get("signoffs"):
        out += [f"## {lab['signoffs']}", ""]
        for s in data["signoffs"]:
            target = f" `{s['target']}`" if s.get("target") else ""
            note = f" — {s['note']}" if s.get("note") else ""
            out.append(f"- {s['function']}{target}: {s['by']}{note}")
        out.append("")
    state = data.get("state")
    if state:
        out += [f"## {lab['state']}", ""]
        if state.get("version"):
            out.append(f"- version: {state['version']}")
        if state.get("difficulty"):
            out.append(f"- {lab['difficulty']}: {state['difficulty']}")
        for key in ("accepted", "open"):
            for item in state.get(key, []):
                out.append(f"- {lab[key]}: {item}")
        if state.get("next_move"):
            out.append(f"- {lab['next']}: {state['next_move']}")
        out.append("")
    return "\n".join(out)
