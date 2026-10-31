"""Source manifest: ids for citation, clean-room filtering, checksum checks."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Any


def source_ids(manifest: dict[str, Any]) -> set[str]:
    return {s["id"] for s in manifest["sources"]}


def source_kinds(manifest: dict[str, Any]) -> dict[str, str]:
    """Source id to its kind (`field_artefact`, `transcript`, ...)."""
    return {s["id"]: s["kind"] for s in manifest["sources"]}


def clean_room(
    manifest: dict[str, Any], deny_lineage: set[str] | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split sources into (allowed, denied) for a clean-room run.

    A source is denied when marked so, when its clean_room is undecided,
    or when it carries a lineage tag listed in deny_lineage.
    """
    deny_lineage = deny_lineage or set()
    allowed: list[dict[str, Any]] = []
    denied: list[dict[str, Any]] = []
    for src in manifest["sources"]:
        tainted = bool(deny_lineage & set(src.get("lineage", [])))
        if src.get("clean_room") == "allow" and not tainted:
            allowed.append(src)
        else:
            denied.append(src)
    return allowed, denied


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check_files(manifest: dict[str, Any], folder: Path) -> list[str]:
    """Compare listed files with a local folder; return problems found."""
    problems: list[str] = []
    for src in manifest["sources"]:
        name = src.get("file")
        if not name:
            continue
        path = folder / name
        if not path.exists():
            problems.append(f"{src['id']}: file not found: {path}")
        elif "sha256" not in src:
            problems.append(f"{src['id']}: no sha256 to compare: {path}")
        elif sha256_of(path) != src["sha256"]:
            problems.append(f"{src['id']}: checksum differs: {path}")
    return problems


def refresh_targets(manifest: dict[str, Any], ids: list[str]) -> list[dict[str, Any]]:
    """Sources a refresh touches: the named ones, else every decision_log."""
    by_id = {s["id"]: s for s in manifest["sources"]}
    if not ids:
        return [s for s in manifest["sources"] if s.get("kind") == "decision_log"]
    unknown = [i for i in ids if i not in by_id]
    if unknown:
        raise ValueError(f"unknown source id: {', '.join(unknown)}")
    return [by_id[i] for i in ids]


def find_file(folder: Path, name: str) -> Path | None:
    """The file called name in folder, matched after NFC normalisation (macOS stores NFD)."""
    path = folder / name
    if path.exists():
        return path
    wanted = unicodedata.normalize("NFC", path.name)
    if path.parent.is_dir():
        for found in path.parent.iterdir():
            if unicodedata.normalize("NFC", found.name) == wanted:
                return found
    return None


def line_count(path: Path) -> int:
    return len(path.read_bytes().splitlines())


def refresh(manifest: dict[str, Any], folder: Path, ids: list[str]) -> list[str]:
    """Recompute sha256 in place for the named sources (default: decision logs),
    and `lines` for a source that carries it.

    Returns the ids whose checksum or line count changed. A source with no file
    is skipped when it was picked by kind and is an error when named.
    """
    changed: list[str] = []
    for src in refresh_targets(manifest, ids):
        name = src.get("file")
        if not name:
            if ids:
                raise ValueError(f"{src['id']}: no file to checksum")
            continue
        path = find_file(folder, unicodedata.normalize("NFC", name))
        if path is None:
            raise FileNotFoundError(f"{src['id']}: file not found: {folder / name}")
        digest = sha256_of(path)
        count = line_count(path)
        stale = src.get("sha256") != digest or (
            "lines" in src and src["lines"] != count
        )
        if src.get("sha256") != digest:
            src["sha256"] = digest
        if "lines" in src:
            src["lines"] = count
        if stale:
            changed.append(src["id"])
    return changed


_ITEM = re.compile(r"^(\s*)- id:\s*[\"']?([^\"'\s#]+)[\"']?\s*(#.*)?$")
_SHA_LINE = re.compile(r"^(\s+sha256:\s*)([\"']?)[^\"'\s#]*[\"']?(.*)$")
_FILE_LINE = re.compile(r"^(\s+)file:")
_LINES_LINE = re.compile(r"^(\s+lines:\s*)\d+(.*)$")


def _item_span(lines: list[str], src_id: str) -> tuple[int, int]:
    """The line of `- id: src_id` and the line after the last line of its item."""
    start, dash = -1, 0
    for i, ln in enumerate(lines):
        m = _ITEM.match(ln)
        if m and m.group(2) == src_id:
            start, dash = i, len(m.group(1))
            break
    if start < 0:
        raise ValueError(f"{src_id}: no '- id:' item in the manifest text")
    end = start + 1
    while end < len(lines) and (
        not lines[end].strip() or len(lines[end]) - len(lines[end].lstrip()) > dash
    ):
        end += 1
    return start, end


def rewrite_sha_lines(text: str, changes: dict[str, str]) -> str:
    """Set sha256 of the listed sources in manifest text, touching no other line.

    Keeps indentation, quote style and comments; a source with a file line but
    no sha256 line gets one after the file line.
    """
    lines = text.split("\n")
    for src_id, digest in changes.items():
        start, end = _item_span(lines, src_id)
        for i in range(start + 1, end):
            if m := _SHA_LINE.match(lines[i]):
                lines[i] = f"{m.group(1)}{m.group(2)}{digest}{m.group(2)}{m.group(3)}"
                break
        else:
            for i in range(start + 1, end):
                if m := _FILE_LINE.match(lines[i]):
                    lines.insert(i + 1, f"{m.group(1)}sha256: {digest}")
                    break
            else:
                raise ValueError(f"{src_id}: no file or sha256 line to edit")
    return "\n".join(lines)


def rewrite_line_counts(text: str, counts: dict[str, int]) -> str:
    """Set `lines` of the listed sources in manifest text, touching no other line."""
    lines = text.split("\n")
    for src_id, count in counts.items():
        start, end = _item_span(lines, src_id)
        for i in range(start + 1, end):
            if m := _LINES_LINE.match(lines[i]):
                lines[i] = f"{m.group(1)}{count}{m.group(2)}"
                break
        else:
            raise ValueError(f"{src_id}: no lines line to edit")
    return "\n".join(lines)
