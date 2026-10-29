"""Step-by-step frames of a board set, for presenting a screen.

Two cuts: `reading` builds one record up in the organisers' reading order
(entry, positions, places, small and big situation, old and new frame, the rest
of the object board, transitions, the К layer, the full screen; the steps and
the board each is cut to are the `reading` list of the record's profile); `cycle` shows
each record of a chain with what it added over the one before. Every frame has a
text to read aloud. The texts come from a Markdown notes file keyed by frame id
when there is one, and are drafted from the record otherwise.

`zoom_frames` cuts each reading step to the board it is about, with a small map
of the boards, and folds the overview steps (transitions, К, the full
screen, every cycle) to their skeleton with counters. The page has switches to
show and hide AI and clean-room content, functions, places and gaps, К and
transitions, and a panel with the full text of an element on click.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from smd_engine.profile import Pick, ProfileError, matches, profile_id, profile_of
from smd_engine.render.frames_text import STEPS
from smd_engine.render.light import fold, lighten
from smd_engine.render.svg import LAYERS
from smd_engine.render.text import LABELS

Element = dict[str, Any]


@dataclass
class Frame:
    id: str
    title: str
    record: dict[str, Any]
    show: set[str] | None
    focus: set[str] | None
    layers: frozenset[str]
    text: str
    elements: list[str] = field(default_factory=list)
    board: str | None = None  # od, oo, s.small or s.big: the step is cut to it
    counts: dict[str, int] | None = None  # elements shown per board, for the map


def _children(data: dict[str, Any], frame_ids: set[str]) -> set[str]:
    return {
        e["id"] for e in data["elements"] if set(e.get("in", [])) & frame_ids
    } | frame_ids


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {i}" for i in items)


def _reading_selectors(
    data: dict[str, Any],
) -> list[tuple[str, Callable[[Element], bool]]]:
    """The profile's reading steps, each with the test of what it adds; a step
    adds only what earlier steps did not show."""
    profile = profile_of(data)
    framed = profile.kinds_shaped("frame")
    frames = {e["id"]: e for e in data["elements"] if e["kind"] in framed}
    old = {i for i, f in frames.items() if f.get("frame_state") != "new"}
    new = set(frames) - old
    in_old, in_new = _children(data, old), _children(data, new) - _children(data, old)
    named = {"old-frames": in_old, "new-frames": in_new}

    def selector(pick: Pick) -> Callable[[Element], bool]:
        if isinstance(pick, str):
            ids = named[pick]
            return lambda e: e["id"] in ids
        return lambda e: matches(e, pick)

    return [(step.id, selector(step.pick)) for step in profile.reading]


def reading_frames(data: dict[str, Any], lang: str = "ru") -> list[Frame]:
    """Build one record up step by step; empty steps are skipped."""
    st = STEPS[lang]
    shown: set[str] = set()
    out: list[Frame] = []
    for fid, pick in _reading_selectors(data):
        added = [e for e in data["elements"] if e["id"] not in shown and pick(e)]
        if not added:
            continue
        shown |= {e["id"] for e in added}
        title, lead = st[fid]
        text = lead + "\n\n" + _bullets([e["label"] for e in added])
        out.append(
            Frame(
                fid,
                title,
                data,
                set(shown),
                {e["id"] for e in added},
                frozenset(),
                text,
                [e["id"] for e in added],
            )
        )
    by_id = {e["id"]: e for e in data["elements"]}
    trs = sorted(data.get("transitions", []), key=lambda t: t["n"])
    if trs:
        title, lead = st["transitions"]
        lines = [
            f"{t['n']}. {by_id[t['from']]['label']} → {by_id[t['to']]['label']}"
            + (f": {t['label']}" if t.get("label") else "")
            for t in trs
        ]
        ends = {t["from"] for t in trs} | {t["to"] for t in trs}
        out.append(
            Frame(
                "transitions",
                title,
                data,
                set(shown),
                ends,
                frozenset({"transitions"}),
                lead + "\n\n" + _bullets(lines),
                sorted(ends),
            )
        )
    ks = data.get("qualifications", [])
    if ks:
        title, lead = st["k"]
        status = LABELS[lang]["status"]
        lines = [f"{q['id']} ({status[q['status']]}): {q['text']}" for q in ks]
        targets = {t for q in ks for t in q.get("targets", [])}
        out.append(
            Frame(
                "k",
                title,
                data,
                set(shown),
                targets,
                frozenset({"transitions", "k"}),
                lead + "\n\n" + _bullets(lines),
                sorted(targets),
            )
        )
    title, lead = st["full"]
    nxt = (data.get("state") or {}).get("next_move")
    text = lead + (f"\n\n{st['next']}: {nxt}" if nxt else "")
    out.append(Frame("full", title, data, None, None, LAYERS, text))
    return out


def cycle_frames(records: list[dict[str, Any]], lang: str = "ru") -> list[Frame]:
    """One frame per record of a chain, ringing what it added to the previous.
    The records follow one profile, as for `smd compare`."""
    other = [r for r in records if profile_id(r) != profile_id(records[0])]
    if other:
        a, b = records[0], other[0]
        raise ProfileError(
            f"a chain of cycles takes records of one profile: {a['id']} follows "
            f"{profile_id(a)}, {b['id']} follows {profile_id(b)}"
        )
    st = STEPS[lang]
    out: list[Frame] = []
    prev: dict[str, Element] = {}
    for data in sorted(records, key=lambda r: r["cycle"]):
        els = {e["id"]: e for e in data["elements"]}
        added = [e for i, e in els.items() if i not in prev]
        removed = [i for i in prev if i not in els]
        word, lead = st["cycle"]
        text = data["title"]
        if prev:
            text += f"\n\n{lead} ({len(added)}):\n\n" + _bullets(
                [e["label"] for e in added]
            )
            if removed:
                text += f"\n\n{st['removed']}: " + ", ".join(removed)
        focus = {e["id"] for e in added} if prev else None
        out.append(
            Frame(
                data["id"],
                f"{word} {data['cycle']}",
                data,
                None,
                focus,
                LAYERS,
                text,
                [e["id"] for e in added],
            )
        )
        prev = els
    return out


def lighten_frames(frames: list[Frame], lang: str = "ru") -> list[Frame]:
    """Draw each frame on the lighter screen. A reading step still names what
    it adds off the screen, so the speaker can say it."""
    st = STEPS[lang]
    light: dict[str, dict[str, Any]] = {}
    for f in frames:
        full = f.record
        if full["id"] not in light:
            light[full["id"]] = lighten(full)
        f.record = light[full["id"]]
        vis = {e["id"] for e in f.record["elements"]}
        f.show = None if f.show is None else f.show & vis
        f.focus = None if f.focus is None else f.focus & vis
        if f.id not in st or f.id in ("transitions", "k", "full"):
            continue
        labels = {e["id"]: e["label"] for e in full["elements"]}
        lead = f.text.split("\n\n")[0]
        on = [labels[i] for i in f.elements if i in vis]
        off = [labels[i] for i in f.elements if i not in vis]
        f.text = lead + ("\n\n" + _bullets(on) if on else "")
        if off:
            f.text += f"\n\n{st['hidden']}:\n\n" + _bullets(off)
    return frames


def zoom_frames(frames: list[Frame], lang: str = "ru") -> list[Frame]:
    """Cut each reading step to its board (from the profile's reading steps);
    fold the other frames to the skeleton, without the legend. A cycle frame
    keeps what it adds unfolded."""
    for f in frames:
        els = f.record["elements"]
        profile = profile_of(f.record)
        step_board = {s.id: s.board for s in profile.reading}
        f.counts = {
            b.id: sum(
                1
                for e in els
                if e["board"] == b.id and (f.show is None or e["id"] in f.show)
            )
            for b in profile.boards
        }
        if f.id in step_board:
            f.board = step_board[f.id]
            continue
        cycle = f.id not in STEPS[lang]
        f.record, to_counter = fold(f.record, lang, f.focus if cycle else None)
        f.show = None
        f.layers = f.layers - {"legend"}  # K texts are in the step texts and on click
        if f.focus is not None:
            f.focus = {to_counter.get(i, i) for i in f.focus}
    return frames


# --- notes file ---

HEAD = re.compile(r"^## (\S+)")


def parse_notes(text: str) -> dict[str, str]:
    """Frame id -> text from a notes file: one `## <id> · <title>` section per
    frame; `<!-- ... -->` lines are metadata and are dropped."""
    out: dict[str, str] = {}
    current: str | None = None
    body: list[str] = []
    for line in text.splitlines() + ["## end-of-file"]:
        m = HEAD.match(line)
        if m:
            if current is not None:
                out[current] = "\n".join(body).strip()
            current, body = m.group(1), []
        elif current is not None and not line.strip().startswith("<!--"):
            body.append(line)
    out.pop("end-of-file", None)
    return out


def write_notes(frames: list[Frame], by: str, lang: str = "ru") -> str:
    ids = sorted({f.record["id"] for f in frames})
    out = [
        f"# {STEPS[lang]['notes_title']}: {', '.join(ids)}",
        "",
        f"<!-- smd frames; by: {by}; records: {', '.join(ids)} -->",
        "",
    ]
    for f in frames:
        meta = f"<!-- frame: {f.id}; record: {f.record['id']}"
        if f.elements:
            meta += f"; elements: {', '.join(f.elements)}"
        out += [f"## {f.id} · {f.title}", meta + " -->", "", f.text, ""]
    return "\n".join(out)


def apply_notes(frames: list[Frame], notes: dict[str, str]) -> list[str]:
    """Replace drafted texts with the notes; return frame ids the notes lack."""
    missing = []
    for f in frames:
        if notes.get(f.id):
            f.text = notes[f.id]
        else:
            missing.append(f.id)
    return missing
