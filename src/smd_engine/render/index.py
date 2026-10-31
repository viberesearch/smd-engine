"""Index page of a board record: every K, thesis, hypothesis, ontology record, sign-off
and element, each linked to its line in the YAML and to the local files it cites.

Without `base` the links hold absolute paths (`file://`, `vscode://file/`), for use on
the machine that built the page. With `base` (the folder the page is written to; `smd
index` and `smd publish` always pass it) they are relative to it, so the folder can be
moved or sent: a file that shares no folder with `base` but the root is not linked, and
YAML lines, which only an absolute `vscode://` link opens, are shown as numbers."""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import quote

from smd_engine.leverage import Leverage, leverage_order
from smd_engine.profile import profile_of
from smd_engine.render.text import (
    LABELS,
    board_text,
    continuum_lines,
    element_lines,
    esc,
    field_lines,
    hypothesis_parts,
    pace_text,
    title_line,
    value_word,
)

CSS = """body{font:14px/1.45 -apple-system,Helvetica,Arial,sans-serif;margin:0;color:#1d2433;background:#fff}
header{position:sticky;top:0;background:#fff;border-bottom:1px solid #ddd;padding:10px 16px;z-index:1}
h1{font-size:17px;margin:0 0 4px}main{padding:0 16px 40px}h2{font-size:16px;margin:28px 0 8px;color:#1f3a68}
table{border-collapse:collapse;width:100%}th,td{border-bottom:1px solid #e3e3e3;padding:5px 6px;vertical-align:top;text-align:left}
th{background:#f4f5f8;position:sticky;top:84px}a{color:#1f5fbf}a.y{font-size:12px;color:#777}small{color:#666}
:target{background:#fff4c2}td:nth-child(1){white-space:nowrap}"""

ID_AT = re.compile(r"(?:^\s*-\s+|[{,]\s*)id:\s*[\"']?([^\s,\"'}\]]+)")


def _is_web(url: str) -> bool:
    return bool(re.match(r"https?://", url, re.I))


def _web_link(url: str, text: str) -> str:
    """`<a href>` only for http(s) URLs; any other scheme (`javascript:`) is plain text."""
    if _is_web(url):
        return f'<a href="{esc(url)}">{esc(text)}</a>'
    return esc(text)


def _relative(path: Path, base: Path) -> str | None:
    """`path` relative to the folder `base`, or None when they share only the root."""
    target, folder = path.resolve(), base.resolve()
    if os.path.commonpath([target, folder]) == target.anchor:
        return None
    return Path(os.path.relpath(target, folder)).as_posix()


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _id_lines(lines: list[str]) -> dict[str, int]:
    """Record id -> number of the first line that declares it (`- id: X`, `{id: X,`)."""
    found: dict[str, int] = {}
    for n, line in enumerate(lines, 1):
        for m in ID_AT.finditer(line):
            found.setdefault(m.group(1), n)
    return found


def _signoff_line(lines: list[str], signoff: dict[str, Any]) -> int | None:
    """A sign-off has no id: the line of its `function`, with its `target` on that
    line or within the next four."""
    function, target = signoff["function"], signoff.get("target", "")
    for n, line in enumerate(lines):
        if f"function: {function}" not in line:
            continue
        if not target or any(f"target: {target}" in x for x in lines[n : n + 5]):
            return n + 1
    return None


class _Index:
    def __init__(
        self,
        data: dict[str, Any],
        lang: str,
        manifest: dict[str, Any] | None,
        record: Path,
        archive: Path | None,
        base: Path | None = None,
    ) -> None:
        self.data, self.lang, self.record, self.base = data, lang, record, base
        self.lab = LABELS[lang]
        self.idx = self.lab["index"]
        self.lines = record.read_text(encoding="utf-8").splitlines()
        self.ids = _id_lines(self.lines)
        self.sources = {s["id"]: s for s in (manifest or {}).get("sources", [])}
        self.files = (
            {_nfc(p.name): p for p in archive.rglob("*") if p.is_file()}
            if archive
            else {}
        )

    def _href(self, path: Path) -> str | None:
        """A link to a local file: its `file://` URL, or with `base` its relative path
        (None when it cannot be relative)."""
        if self.base is None:
            return f"file://{quote(str(path.resolve()))}"
        relative = _relative(path, self.base)
        return quote(relative) if relative is not None else None

    def _yaml(self, line: int | None) -> str:
        if not line:
            return ""
        if self.base is not None:
            return f'<a class="y">YAML:{line}</a>'
        href = f"vscode://file/{quote(str(self.record.resolve()))}:{line}"
        return f'<a class="y" href="{esc(href)}">YAML:{line}</a>'

    def _anchor(self, id_: str) -> str:
        return f'<b id="{esc(id_)}">{esc(id_)}</b><br>{self._yaml(self.ids.get(id_))}'

    def _local(self, source: dict[str, Any] | None) -> Path | None:
        """The cited file in the archive folder, matched by NFC file name; with `base`,
        only a file that can be linked relative to it."""
        if not source or not source.get("file"):
            return None
        found = self.files.get(_nfc(Path(source["file"]).name))
        if found is None or self._href(found) is None:
            return None
        return found.resolve()

    def _cite(self, cite: str) -> str:
        sid, _, addr = cite.partition("#")
        source = self.sources.get(sid)
        if source is None:
            return esc(cite)
        title = esc(source.get("title", ""))
        path = self._local(source)
        if path is not None:
            href = self._href(path) or ""
            if addr.startswith("l=") and self.base is None:
                href = f"vscode://file/{quote(str(path))}:{addr[2:]}"
            elif addr.startswith("p=") and path.suffix == ".pdf" and addr[2:].isdigit():
                href += f"#page={addr[2:]}"
            return f'<a href="{esc(href)}" title="{title}">{esc(cite)}</a>'
        if source.get("url"):
            shown = f"{title} ({esc(self.idx['web'])}"
            if not _is_web(source["url"]):
                shown += f": {esc(source['url'])}"
            return f"{_web_link(source['url'], cite)} <small>{shown})</small>"
        return f"{esc(cite)} <small>{title}</small>"

    def _cites(self, items: list[str] | None) -> str:
        return " · ".join(self._cite(c) for c in items or [])

    def _refs(self, items: list[str | None] | None) -> str:
        return ", ".join(f'<a href="#{esc(x)}">{esc(x)}</a>' for x in items or [] if x)

    def _continuum(self, o: dict[str, Any]) -> str:
        """Lives in, tempos, horizon and covers of an ontology record, under its
        object; empty when it has none of them."""
        lines = continuum_lines(o, self.lang)
        return f"<br><small>{esc('; '.join(lines))}</small>" if lines else ""

    def _hypothesis(self, h: dict[str, Any]) -> str:
        """Type, decision rule and observed count of a hypothesis, under its
        text; empty when it has none of them."""
        lines = field_lines(hypothesis_parts(h, self.lang), self.lang)
        return f"<br><small>{esc('; '.join(lines))}</small>" if lines else ""

    def _fields(self, x: dict[str, Any]) -> str:
        """Beer's systems, threshold, recovery time, the place a position takes
        and its stance, under the element's label; empty when it has none."""
        lines = element_lines(x, self.lang)
        return f"<br><small>{esc('; '.join(lines))}</small>" if lines else ""

    def _reach(self, found: Leverage | None) -> str:
        """The score of an untested hypothesis, its parts as the tooltip."""
        if found is None:
            return ""
        parts = ", ".join(f"{k} {n}" for k, n in found.counts.items())
        return f'<span title="{esc(parts)}">{found.score}</span>'

    def _where(self, sid: str) -> str:
        source = self.sources.get(sid)
        if source is None:
            return esc(self.idx["no_entry"])
        path = self._local(source)
        if path is not None:
            shown = str(path) if self.base is None else _relative(path, self.base)
            return f'<a href="{esc(self._href(path) or "")}">{esc(shown or "")}</a>'
        if source.get("url"):
            return _web_link(source["url"], source["url"])
        return esc(self.idx["no_file"])

    def _table(
        self, key: str, title: str, cols: list[str], rows: list[list[str]]
    ) -> str:
        head = "".join(f"<th>{esc(c)}</th>" for c in cols)
        body = "".join(
            "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows
        )
        return (
            f'<h2 id="sec-{key}">{esc(title)}</h2><table><tr>{head}</tr>{body}</table>'
        )

    def sections(self) -> list[tuple[str, str, list[str], list[list[str]]]]:
        d, lab, idx = self.data, self.lab, self.idx
        profile = profile_of(d)
        anchor, refs, cites, e = self._anchor, self._refs, self._cites, esc
        qualifications = [
            [
                anchor(q["id"]),
                e(lab["status"].get(q["status"], q["status"])),
                e(q["text"]),
                refs(q.get("targets")),
                e(q.get("note", "")),
                cites(q.get("cites")),
            ]
            for q in d.get("qualifications", [])
        ]
        theses = [
            [
                anchor(t["id"]),
                e(
                    f"{value_word('voice', t['voice'], self.lang)}, "
                    f"{lab['thesis_status'].get(t['status'], t['status'])}"
                ),
                e(t["claim"]),
                refs(t.get("feeds"))
                + (" / " + refs(t["about"]) if t.get("about") else ""),
                e(
                    " ".join(
                        x
                        for x in (
                            t.get("grounds", ""),
                            t.get("consequence", ""),
                            t.get("note", ""),
                        )
                        if x
                    )
                ),
                cites(t.get("cites")),
            ]
            for t in d.get("theses", [])
        ]
        # the reach of an untested hypothesis, a proposal (leverage.py)
        reach = {x.id: x for x in leverage_order(d)}
        hypotheses = [
            [
                anchor(h["id"]),
                e(lab["hyp_status"].get(h["status"], h["status"])),
                e(h["assumes"]) + self._hypothesis(h),
                e(h.get("action", "")),
                e(h.get("revise_if", "")),
                refs(h.get("targets")) + " · " + refs(h.get("qualifications")),
                self._reach(reach.get(h["id"])),
                cites(h.get("cites")),
            ]
            for h in d.get("hypotheses", [])
        ]
        ontology = [
            [
                anchor(o["id"]),
                e(o["object"]) + self._continuum(o),
                refs(o.get("valid_for")),
                refs([o.get("cooperation")]) + " · " + refs([o.get("test")]),
                e(o.get("note", "")),
                cites(o.get("cites")),
            ]
            for o in d.get("ontology", [])
        ]
        signoffs = [
            [
                e(value_word("function", s["function"], self.lang))
                + f"<br>{self._yaml(_signoff_line(self.lines, s))}",
                refs([s.get("target")]),
                e(f"{s['by']}, {s.get('date', '')}"),
                e(s.get("note", "")),
                cites(s.get("cites")),
            ]
            for s in d.get("signoffs", [])
        ]
        elements = [
            [
                anchor(x["id"]),
                e(board_text(profile, x, self.lang)),
                e(profile.kind_label_one(x["kind"], self.lang)),
                e(x.get("short", x["label"])),
                e(x["label"])
                + (
                    f"<br><small>{e(x['label_note'])}</small>"
                    if x.get("label_note")
                    else ""
                )
                + (
                    f"<br><small>{e(pace_text(x, self.lang))}</small>"
                    if "pace" in x
                    else ""
                )
                + self._fields(x),
                e(", ".join(x.get("fillers", []))),
                cites(x.get("cites")),
            ]
            for x in d["elements"]
        ]
        boards = [
            [
                anchor(x["id"]),
                # the template by its label (gate Г7б Б); an unknown one as recorded
                e(
                    template.label[self.lang]
                    if (template := profile.template(x["template"]))
                    else x["template"]
                ),
                # the board by its own label: the column before names the
                # template (gate Г8г Б)
                e(x["label"]),
                refs([x.get("seen_from")]),
                refs([x.get("unfolds")]),
                cites(x.get("cites")),
            ]
            for x in d.get("boards", [])
        ]
        used = sorted(
            {
                c.partition("#")[0]
                for key in (
                    "boards",
                    "elements",
                    "theses",
                    "hypotheses",
                    "qualifications",
                    "ontology",
                    "signoffs",
                )
                for o in d.get(key, [])
                for c in o.get("cites", [])
            }
        )
        sources = [
            [
                f"<b>{e(sid)}</b>",
                e(self.sources[sid].get("title", "")) if sid in self.sources else "",
                self._where(sid),
            ]
            for sid in used
        ]
        # the boards a record makes of templates, only in a record that has them
        made = [("b", lab["record_boards"], idx["b_columns"], boards)] if boards else []
        return [
            ("k", lab["qualifications"], idx["k_columns"], qualifications),
            ("t", lab["theses"], idx["t_columns"], theses),
            ("h", lab["hypotheses"], idx["h_columns"], hypotheses),
            ("o", lab["ontology"], idx["o_columns"], ontology),
            ("s", lab["signoffs"], idx["s_columns"], signoffs),
            *made,
            ("e", lab["elements"], idx["e_columns"], elements),
            ("src", idx["src_title"], idx["src_columns"], sources),
        ]

    def page(self) -> str:
        sections = self.sections()
        nav = " · ".join(
            f'<a href="#sec-{key}">{esc(title)}</a>' for key, title, _, _ in sections
        )
        body = "".join(self._table(*s) for s in sections)
        title = title_line(self.data, self.lang)
        href = self._href(self.record)
        record = (
            f'<a href="{esc(href)}">{esc(self.record.name)}</a>'
            if href is not None
            else esc(self.record.name)
        )
        hint = self.idx["hint" if self.base is None else "hint_relative"]
        return (
            f'<!doctype html><html lang="{self.lang}"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{esc(self.data['id'])}: {esc(self.idx['suffix'])}</title>"
            f"<style>{CSS}</style></head><body><header><h1>{esc(title)}</h1>"
            f"<div>{esc(self.idx['file'])}: {record}. "
            f"{esc(hint)} {nav}</div></header>"
            f"<main>{body}</main></body></html>\n"
        )


def render_index(
    data: dict[str, Any],
    record: Path,
    lang: str = "ru",
    manifest: dict[str, Any] | None = None,
    archive: Path | None = None,
    base: Path | None = None,
) -> str:
    """One page listing every item of the record with its YAML line. A cited source is
    linked to its file only when `archive` holds a file of that name; otherwise the
    cite is followed by the source title. With `base`, the folder the page goes to,
    links to local files are relative to it (see the module docstring)."""
    return _Index(data, lang, manifest, record, archive, base).page()
