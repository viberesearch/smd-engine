"""Commands of `smd` that read, check, migrate, render and patch boards:
validate, migrate, render, frames, sources, compare, eval, apply, graph, index
(the parser is in `cli.py`)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

from smd_engine.apply import PatchError, apply_patch
from smd_engine.compare import merge, report
from smd_engine.eval import evaluate, format_result
from smd_engine.migrate import migrate, migrate_text
from smd_engine.profile import ProfileError
from smd_engine.records import (
    RecordError,
    discover,
    dump_record,
    load_record,
    parse_text,
)
from smd_engine.render.frames import (
    Frame,
    apply_notes,
    cycle_frames,
    lighten_frames,
    parse_notes,
    reading_frames,
    write_notes,
    zoom_frames,
)
from smd_engine.render.frames_page import render_frames_html
from smd_engine.render.graph import render_graph_html
from smd_engine.render.html import render_html
from smd_engine.render.index import render_index
from smd_engine.render.light import lighten
from smd_engine.render.markdown import render_markdown
from smd_engine.render.mermaid import render_mermaid
from smd_engine.render.sessionflow import render_sessionflow
from smd_engine.render.svg import render_svg
from smd_engine.sources import (
    check_files,
    clean_room,
    find_file,
    line_count,
    refresh,
    refresh_targets,
    rewrite_line_counts,
    rewrite_sha_lines,
    source_kinds,
)
from smd_engine.validate import Finding, taxonomy_values, validate_record

RENDERERS: dict[str, Callable[[dict[str, Any], str], str]] = {
    "svg": render_svg,
    "html": render_html,
    "md": render_markdown,
    "mermaid": render_mermaid,
    "sessionflow": render_sessionflow,
}


def _load_manifest(path: Path) -> dict[str, Any]:
    manifest = load_record(path)
    if manifest["record"] != "source_manifest":
        raise RecordError(f"{path}: not a source manifest")
    errors = [f for f in validate_record(manifest) if f.level == "error"]
    if errors:
        raise RecordError(f"{path}: invalid manifest: {errors[0]}")
    return manifest


def _manifest_kinds(path: Path | None) -> dict[str, str] | None:
    """Source id to its kind; its keys are the manifest's ids."""
    if path is None:
        return None
    return source_kinds(_load_manifest(path))


def _load_taxonomies(path: Path | None) -> dict[str, set[str]] | None:
    if path is None:
        return None
    record = load_record(path)
    if record["record"] != "taxonomies":
        raise RecordError(f"{path}: not a taxonomy file")
    errors = [f for f in validate_record(record) if f.level == "error"]
    if errors:
        raise RecordError(f"{path}: invalid taxonomy file: {errors[0]}")
    return taxonomy_values(record)


def cmd_validate(args: argparse.Namespace) -> int:
    kinds = _manifest_kinds(args.sources)
    ids = None if kinds is None else set(kinds)
    taxonomies = _load_taxonomies(args.taxonomies)
    files = discover([Path(p) for p in args.paths])
    if not files:
        print("no records found", file=sys.stderr)
        return 2
    errors = warnings = 0
    loaded: dict[Path, dict[str, Any] | RecordError] = {}
    for path in files:
        try:
            loaded[path] = load_record(path)
        except RecordError as exc:
            loaded[path] = exc
    boards = {
        d["id"]: d
        for d in loaded.values()
        if isinstance(d, dict) and d["record"] == "board_set"
    }
    for path, data in loaded.items():
        if isinstance(data, RecordError):
            print(f"FAIL {path}\n  error: {data}")
            errors += 1
            continue
        if data["record"] == "board_set":
            previous = boards.get(data.get("revises", ""))
            findings = validate_record(data, ids, previous, taxonomies, kinds)
        else:
            findings = validate_record(data)
        shown = [f for f in findings if args.hints or f.level != "hint"]
        errors += sum(f.level == "error" for f in findings)
        warnings += sum(f.level == "warning" for f in findings)
        status = "FAIL" if any(f.level == "error" for f in findings) else "ok"
        print(f"{status} {path}")
        for f in shown:
            print(f"  {f}" + (f" → {f.procedure}" if f.procedure else ""))
    print(f"{len(files)} record(s), {errors} error(s), {warnings} warning(s)")
    if errors or (args.strict and warnings):
        return 1
    return 0


QUOTED = re.compile(r'"(?:[^"\\]|\\.)*"|\'[^\']*\'')


def _comment_lines(text: str) -> int:
    """Lines with a comment, whole or after a value; quoted text is skipped, so
    the count is approximate."""
    return sum(
        bool(re.search(r"(^|\s)#", QUOTED.sub("''", line)))
        for line in text.splitlines()
    )


def cmd_migrate(args: argparse.Namespace) -> int:
    files = discover([Path(p) for p in args.paths])
    if not files:
        print("no records found", file=sys.stderr)
        return 2
    changed = failed = 0
    for path in files:
        notes: list[str] = []
        try:
            new = migrate(load_record(path), notes)
        except (RecordError, ValueError) as exc:
            print(f"FAIL {path}\n  error: {exc}")
            failed += 1
            continue
        if not notes:
            print(f"ok {path}: schema {new['schema_version']}, nothing to change")
            continue
        changed += 1
        print(f"{'migrated' if args.write else 'to migrate'} {path}")
        for note in notes:
            print(f"  {note}")
        # Edit the text in place; rewrite the whole file only when that fails.
        text = path.read_text(encoding="utf-8")
        edited = migrate_text(text, path.suffix == ".json")
        if edited is None:
            n = _comment_lines(text)
            if args.write:
                print(f"  rewritten, about {n} comment line(s) not kept")
            else:
                print(
                    f"  would be rewritten, about {n} comment line(s) would not be kept"
                )
            if path.suffix == ".json":
                edited = json.dumps(new, ensure_ascii=False, indent=2) + "\n"
            else:
                edited = dump_record(new)
        if args.write:
            path.write_text(edited, encoding="utf-8")
    done = "written" if args.write else "to migrate (run with --write)"
    print(f"{len(files)} record(s), {changed} {done}, {failed} error(s)")
    return 1 if failed else 0


def cmd_render(args: argparse.Namespace) -> int:
    data = load_record(Path(args.file))
    if data["record"] != "board_set":
        print("render takes a board_set record", file=sys.stderr)
        return 2
    findings = [f for f in validate_record(data) if f.level == "error"]
    if findings:
        for f in findings:
            print(f, file=sys.stderr)
        return 1
    try:
        if args.light and args.format == "html":
            text = render_html(data, args.lang, screen=lighten(data))
        else:
            screen = lighten(data) if args.light else data
            text = RENDERERS[args.format](screen, args.lang)
    except ProfileError as exc:  # a format the record's profile does not have
        print(exc, file=sys.stderr)
        return 2
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


def _build_frames(
    records: list[dict[str, Any]], by: str, lang: str, light: bool, zoom: bool
) -> list[Frame]:
    """Frames of one record (`reading`) or of a chain of cycles (`cycle`)."""
    frames = (
        reading_frames(records[0], lang)
        if by == "reading"
        else cycle_frames(records, lang)
    )
    if light:
        frames = lighten_frames(frames, lang)
    if zoom:
        frames = zoom_frames(frames, lang)
    return frames


def cmd_frames(args: argparse.Namespace) -> int:
    records = [load_record(Path(f)) for f in args.files]
    if any(r["record"] != "board_set" for r in records):
        print("frames takes board_set records", file=sys.stderr)
        return 2
    for data in records:
        errors = [f for f in validate_record(data) if f.level == "error"]
        if errors:
            for f in errors:
                print(f, file=sys.stderr)
            return 1
    if args.by == "reading" and len(records) != 1:
        print("--by reading takes one record", file=sys.stderr)
        return 2
    try:
        frames = _build_frames(records, args.by, args.lang, args.light, args.zoom)
    except ProfileError as exc:  # a chain of records of two profiles
        print(exc, file=sys.stderr)
        return 2
    if args.notes:
        notes_path = Path(args.notes)
        notes = (
            parse_notes(notes_path.read_text(encoding="utf-8"))
            if notes_path.exists()
            else {}
        )
        missing = apply_notes(frames, notes)
        if args.write_notes:
            notes_path.write_text(
                write_notes(frames, args.by, args.lang), encoding="utf-8"
            )
        elif missing:
            print(f"drafted, not in notes: {', '.join(missing)}", file=sys.stderr)
    text = render_frames_html(frames, args.lang)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


def _refresh_sources(args: argparse.Namespace, manifest: dict[str, Any]) -> int:
    if not args.folder:
        print("--refresh needs --folder", file=sys.stderr)
        return 2
    folder = Path(args.folder)
    try:
        changed = refresh(manifest, folder, args.refresh)
        targets = refresh_targets(manifest, args.refresh)
        changes = {s["id"]: s["sha256"] for s in targets if s["id"] in changed}
        manifest_path = Path(args.manifest)
        text = rewrite_sha_lines(manifest_path.read_text("utf-8"), changes)
        counts = {
            s["id"]: s["lines"] for s in targets if s["id"] in changed and "lines" in s
        }
        text = rewrite_line_counts(text, counts)
    except (ValueError, FileNotFoundError) as exc:
        print(exc, file=sys.stderr)
        return 1
    for src in targets:
        if not src.get("file"):
            continue
        if src["id"] in changed:
            path = find_file(folder, src["file"])
            assert path is not None
            print(f"{src['id']}: sha256 updated, {line_count(path)} lines")
        else:
            print(f"{src['id']}: unchanged")
    if changed:
        manifest_path.write_text(text, "utf-8")
    return 0


def cmd_sources(args: argparse.Namespace) -> int:
    manifest = _load_manifest(Path(args.manifest))
    if args.refresh is not None:
        return _refresh_sources(args, manifest)
    if args.folder:
        missing = check_files(manifest, Path(args.folder))
        for line in missing:
            print(line)
        if missing:
            return 1
    if args.clean_room:
        allowed, denied = clean_room(manifest, set(args.deny_lineage))
        print("allowed:")
        for s in allowed:
            print(f"  {s['id']}: {s.get('file') or s.get('url', '')}")
        print("denied:")
        for s in denied:
            print(f"  {s['id']}: {s.get('file') or s.get('url', '')}")
    else:
        for s in manifest["sources"]:
            print(f"{s['id']}\t{s['kind']}\t{s.get('clean_room', '?')}\t{s['title']}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    a, b = load_record(Path(args.a)), load_record(Path(args.b))
    if a["record"] != "board_set" or b["record"] != "board_set":
        print("compare takes two board_set records", file=sys.stderr)
        return 2
    try:
        text = report(a, b)
    except ProfileError as exc:  # two profiles
        print(exc, file=sys.stderr)
        return 2
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    if args.merge:
        proposal = merge(a, b, Path(args.merge).name.removesuffix(".board.yaml"))
        Path(args.merge).write_text(dump_record(proposal), encoding="utf-8")
        errors = [f for f in validate_record(proposal) if f.level == "error"]
        for f in errors:
            print(f, file=sys.stderr)
        return 1 if errors else 0
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    run, expected = load_record(Path(args.run)), load_record(Path(args.expected))
    if run["record"] != "board_set" or expected["record"] != "board_set":
        print("eval takes two board_set records", file=sys.stderr)
        return 2
    result = evaluate(run, expected, args.min_agreement, args.max_only_expected)
    sys.stdout.write(format_result(result))
    return 1 if result.failures else 0


ITEM_LISTS = ("elements", "qualifications", "theses", "hypotheses", "ontology")


def _with_item_id(record: dict[str, Any], finding: Finding) -> str:
    """The finding, with the id of the item its path points into
    (elements/3/label -> elements/3 [fact-x]/label)."""
    parts = finding.ref.split("/")
    if len(parts) > 1 and parts[0] in ITEM_LISTS and parts[1].isdigit():
        items = record.get(parts[0], [])
        n = int(parts[1])
        if n < len(items) and isinstance(items[n], dict) and "id" in items[n]:
            parts[1] += f" [{items[n]['id']}]"
            return f"{finding.level}: {'/'.join(parts)}: {finding.message}"
    return str(finding)


def cmd_apply(args: argparse.Namespace) -> int:
    board = load_record(Path(args.board))
    patch = load_record(Path(args.patch))
    if board["record"] != "board_set" or patch["record"] != "board_patch":
        print(
            "apply takes a board_set record and a board_patch record", file=sys.stderr
        )
        return 2
    # An unquoted version: 5.8 is read as a number; the record keeps it as text.
    if isinstance(patch.get("version"), (int, float)):
        patch["version"] = str(patch["version"])
    invalid = [f for f in validate_record(patch) if f.level == "error"]
    kinds = _manifest_kinds(args.sources)
    ids = None if kinds is None else set(kinds)
    if ids is not None:
        invalid += [
            Finding("error", "cites", f"cites unknown source '{c}'")
            for c in patch.get("cites", [])
            if c.split("#")[0] not in ids
        ]
    for f in invalid:
        print(f"{args.patch}: {f}", file=sys.stderr)
    if invalid:
        return 2
    try:
        new = apply_patch(board, patch)
    except PatchError as exc:
        print(exc, file=sys.stderr)
        return 2
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    text = dump_record(new)
    result = parse_text(text)
    # The board as it will be read back; no cycle is revised, so no `previous`.
    taxonomies = _load_taxonomies(args.taxonomies)
    findings = validate_record(result, ids, None, taxonomies, kinds)
    errors = [f for f in findings if f.level == "error"]
    for f in errors:
        print(_with_item_id(result, f), file=sys.stderr)
    if errors and not args.force:
        print(f"not written: {len(errors)} error(s)", file=sys.stderr)
        return 1
    Path(args.output).write_text(text, encoding="utf-8")
    warnings = sum(f.level == "warning" for f in findings)
    print(
        f"{args.output}: {patch['id']} applied, version {patch['version']}, "
        f"{len(errors)} error(s), {warnings} warning(s)"
    )
    return 1 if errors else 0


def _board_or_error(path: str, command: str) -> dict[str, Any] | None:
    data = load_record(Path(path))
    if data["record"] != "board_set":
        print(f"{command} takes a board_set record", file=sys.stderr)
        return None
    errors = [f for f in validate_record(data) if f.level == "error"]
    for f in errors:
        print(f, file=sys.stderr)
    return None if errors else data


def cmd_graph(args: argparse.Namespace) -> int:
    data = _board_or_error(args.file, "graph")
    if data is None:
        return 1
    manifest = _load_manifest(Path(args.sources)) if args.sources else None
    text = render_graph_html(data, args.lang, manifest)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    data = _board_or_error(args.file, "index")
    if data is None:
        return 1
    manifest = _load_manifest(Path(args.sources)) if args.sources else None
    archive = Path(args.archive) if args.archive else None
    # links relative to the page's folder (the current one when printed), so
    # that the page holds no absolute path of this machine
    base = Path(args.output).parent if args.output else Path.cwd()
    text = render_index(data, Path(args.file), args.lang, manifest, archive, base)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0
