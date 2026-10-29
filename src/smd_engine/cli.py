"""Command line: smd validate | migrate | render | frames | graph | index | publish | vault
| sources | compare | eval | pack | revise | apply."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

import yaml

from smd_engine.apply import PatchError, apply_patch
from smd_engine.compare import merge, report
from smd_engine.eval import evaluate, format_result
from smd_engine.migrate import migrate, migrate_text
from smd_engine.pack import pack
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
from smd_engine.render.vault import export_vault
from smd_engine.revise import revise
from smd_engine.sources import (
    check_files,
    clean_room,
    find_file,
    line_count,
    refresh,
    refresh_targets,
    rewrite_line_counts,
    rewrite_sha_lines,
    source_ids,
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


def _manifest_ids(path: Path | None) -> set[str] | None:
    if path is None:
        return None
    return source_ids(_load_manifest(path))


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
    ids = _manifest_ids(args.sources)
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
            findings = validate_record(data, ids, previous, taxonomies)
        else:
            findings = validate_record(data)
        shown = [f for f in findings if args.hints or f.level != "hint"]
        errors += sum(f.level == "error" for f in findings)
        warnings += sum(f.level == "warning" for f in findings)
        status = "FAIL" if any(f.level == "error" for f in findings) else "ok"
        print(f"{status} {path}")
        for f in shown:
            print(f"  {f}")
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


def cmd_pack(args: argparse.Namespace) -> int:
    try:
        manifest = Path(args.sources) if args.sources else None
        taxonomies = Path(args.taxonomies) if args.taxonomies else None
        text = pack(
            args.procedure,
            [Path(r) for r in args.records],
            manifest=manifest,
            taxonomies=taxonomies,
        )
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


def cmd_revise(args: argparse.Namespace) -> int:
    prev = load_record(Path(args.previous))
    if prev["record"] != "board_set":
        print("revise takes a board_set record", file=sys.stderr)
        return 2
    decisions = None
    if args.decisions:
        decisions = yaml.safe_load(Path(args.decisions).read_text(encoding="utf-8"))
    try:
        new, todo = revise(prev, args.id, args.date, decisions)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    text = dump_record(new)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    errors = [f for f in validate_record(new, None, prev) if f.level == "error"]
    for f in errors:
        print(f, file=sys.stderr)
    for line in todo:
        print(f"to do: {line}", file=sys.stderr)
    return 1 if errors else 0


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
    ids = _manifest_ids(args.sources)
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
    findings = validate_record(result, ids, None, taxonomies)
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


def _chain(path: Path, data: dict[str, Any]) -> list[tuple[Path, dict[str, Any]]]:
    """The board and the cycles it revises, found next to it by `revises`, newest first."""
    siblings: dict[str, tuple[Path, dict[str, Any]]] = {}
    for other in sorted(path.parent.glob("*.board.yaml")):
        try:
            rec = load_record(other)
        except RecordError:
            continue
        if rec["record"] == "board_set":
            siblings[rec["id"]] = (other, rec)
    chain = [(path, data)]
    while data.get("revises") in siblings and len(chain) <= len(siblings):
        path, data = siblings[data["revises"]]
        chain.append((path, data))
    return chain


def cmd_publish(args: argparse.Namespace) -> int:
    path = Path(args.board)
    data = load_record(path)
    if data["record"] != "board_set":
        print("publish takes a board_set record", file=sys.stderr)
        return 2
    manifest = _load_manifest(Path(args.sources)) if args.sources else None
    ids = source_ids(manifest) if manifest else None
    taxonomies = _load_taxonomies(args.taxonomies)
    chain = _chain(path, data)
    failed = False
    # errors fail anywhere in the chain; with --strict, warnings fail only on the
    # published record, and those of the earlier cycles are reported
    for n, (file, rec) in enumerate(chain):
        prev = chain[n + 1][1] if n + 1 < len(chain) else None
        for f in validate_record(rec, ids, prev, taxonomies):
            if f.level == "error" or (args.strict and f.level == "warning" and n == 0):
                print(f"{file}: {f}", file=sys.stderr)
                failed = True
            elif args.strict and f.level == "warning":
                print(f"{file}: {f} (earlier cycle: not failing)", file=sys.stderr)
    if failed:
        print("not published: the record does not validate", file=sys.stderr)
        return 1
    name = data["id"]
    records = [rec for _, rec in chain]
    notes: dict[str, str] = {}
    if args.notes and Path(args.notes).exists():
        notes = parse_notes(Path(args.notes).read_text(encoding="utf-8"))
    reading = _build_frames([data], "reading", args.lang, args.light, args.zoom)
    try:
        cycles = _build_frames(records, "cycle", args.lang, args.light, args.zoom)
    except ProfileError as exc:  # the chain of `revises` crosses two profiles
        print(exc, file=sys.stderr)
        return 2
    missing = apply_notes(reading, notes)
    apply_notes(cycles, notes)
    if notes and missing:
        print(f"drafted, not in notes: {', '.join(missing)}", file=sys.stderr)
    screen = lighten(data) if args.light else None
    pages = {
        f"{name}_frames.html": render_frames_html(reading, args.lang),
        f"{name}_cycle_frames.html": render_frames_html(cycles, args.lang),
        # links relative to the bundle folder, so that it can be moved or sent
        f"{name}_index.html": render_index(
            data,
            path,
            args.lang,
            manifest,
            Path(args.archive) if args.archive else None,
            base=Path(args.out),
        ),
        f"{name}_graph.html": render_graph_html(data, args.lang, manifest),
        f"{name}.html": render_html(data, args.lang, screen=screen),
    }
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for file_name, text in pages.items():
        (out / file_name).write_text(text, encoding="utf-8")
        print(out / file_name)
    return 0


def cmd_vault(args: argparse.Namespace) -> int:
    data = _board_or_error(args.file, "vault")
    if data is None:
        return 1
    manifest = _load_manifest(Path(args.sources)) if args.sources else None
    written = export_vault(data, Path(args.out), args.lang, manifest)
    print(f"{len(written)} files written to {args.out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="smd", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    v = sub.add_parser("validate", help="check records (files or directories)")
    v.add_argument("paths", nargs="+")
    v.add_argument("--sources", type=Path, help="source manifest for citation checks")
    v.add_argument("--hints", action="store_true", help="show methodological hints")
    v.add_argument("--strict", action="store_true", help="fail on warnings")
    v.add_argument(
        "--taxonomies",
        type=Path,
        help="taxonomy file for the checks of tags and bound detail columns",
    )
    v.set_defaults(func=cmd_validate)

    mg = sub.add_parser(
        "migrate", help="rewrite records to the current schema (files or directories)"
    )
    mg.add_argument("paths", nargs="+")
    mg.add_argument(
        "--write", action="store_true", help="write the files; otherwise only report"
    )
    mg.set_defaults(func=cmd_migrate)

    r = sub.add_parser("render", help="draw a board set")
    r.add_argument("file")
    r.add_argument("--format", choices=sorted(RENDERERS), default="svg")
    r.add_argument("--lang", choices=["ru", "en"], default="ru")
    r.add_argument(
        "--light",
        action="store_true",
        help="lighter screen: facts, signals, notes, candidate moves and refers links off",
    )
    r.add_argument("-o", "--output")
    r.set_defaults(func=cmd_render)

    fr = sub.add_parser(
        "frames", help="step-by-step frames of a screen, as one HTML page"
    )
    fr.add_argument("files", nargs="+", help="one record, or a chain for --by cycle")
    fr.add_argument("--by", choices=["reading", "cycle"], default="reading")
    fr.add_argument("--lang", choices=["ru", "en"], default="ru")
    fr.add_argument(
        "--light",
        action="store_true",
        help="lighter screen: facts, signals, notes, candidate moves and refers links off",
    )
    fr.add_argument(
        "--zoom",
        action="store_true",
        help="each reading step cut to its board; transitions, K, the full screen "
        "and cycles folded to their skeleton with counters",
    )
    fr.add_argument("--notes", help="Markdown texts per frame (## <frame id> sections)")
    fr.add_argument(
        "--write-notes",
        action="store_true",
        help="write the notes file: texts kept from it, the rest drafted",
    )
    fr.add_argument("-o", "--output")
    fr.set_defaults(func=cmd_frames)

    s = sub.add_parser(
        "sources", help="list a source manifest, check files, clean-room split"
    )
    s.add_argument("manifest")
    s.add_argument(
        "--folder", help="local folder holding the files; checks presence and sha256"
    )
    s.add_argument(
        "--refresh",
        nargs="*",
        metavar="ID",
        help="with --folder: recompute sha256 of the named sources (default: every "
        "decision_log) and rewrite the manifest",
    )
    s.add_argument("--clean-room", action="store_true")
    s.add_argument(
        "--deny-lineage", nargs="*", default=[], help="lineage tags to exclude"
    )
    s.set_defaults(func=cmd_sources)

    c = sub.add_parser(
        "compare", help="compare two board sets element by element; propose a merge"
    )
    c.add_argument("a", help="board set A, e.g. the clean-room version")
    c.add_argument("b", help="board set B, the base of a merge")
    c.add_argument("-o", "--output", help="write the Markdown report here")
    c.add_argument(
        "--merge", help="write a merge proposal (a new cycle on top of B) here"
    )
    c.set_defaults(func=cmd_compare)

    ev = sub.add_parser(
        "eval", help="compare a procedure run with an expected record; exit 1 on a miss"
    )
    ev.add_argument("run", help="the board set a procedure run produced")
    ev.add_argument("expected", help="the board set the run should have produced")
    ev.add_argument("--min-agreement", type=int, help="fail below this many agreements")
    ev.add_argument(
        "--max-only-expected",
        type=int,
        help="fail above this many elements only the expected record has",
    )
    ev.set_defaults(func=cmd_eval)

    pk = sub.add_parser(
        "pack", help="one Markdown file with a procedure and its context, for any model"
    )
    pk.add_argument("procedure", help="procedure id, e.g. solo-session")
    pk.add_argument("records", nargs="*", help="record files to include as data")
    pk.add_argument("--sources", help="the case's source manifest, included as data")
    pk.add_argument("--taxonomies", help="the case's taxonomy file, included as data")
    pk.add_argument("-o", "--output")
    pk.set_defaults(func=cmd_pack)

    rv = sub.add_parser(
        "revise", help="open the next cycle of a board set and apply sign-offs"
    )
    rv.add_argument("previous", help="the board set this cycle revises")
    rv.add_argument("--id", help="id of the new cycle (default: trailing number + 1)")
    rv.add_argument("--date", help="date of the new cycle (default: today)")
    rv.add_argument(
        "--decisions",
        help="YAML with signoffs, reflected_from and difficulty to apply",
    )
    rv.add_argument("-o", "--output")
    rv.set_defaults(func=cmd_revise)

    ap = sub.add_parser(
        "apply", help="apply a board patch: the next sub-version of the same cycle"
    )
    ap.add_argument("board", help="the board set the patch applies to")
    ap.add_argument("patch", help="the board_patch record")
    ap.add_argument("-o", "--output", required=True, help="the new board set")
    ap.add_argument(
        "--sources", type=Path, help="source manifest: added sources and cites checked"
    )
    ap.add_argument(
        "--force", action="store_true", help="write the result even when it has errors"
    )
    ap.add_argument("--taxonomies", type=Path, help="taxonomy file, as in validate")
    ap.set_defaults(func=cmd_apply)

    g = sub.add_parser(
        "graph", help="the board set as a 3D graph: one self-contained HTML page"
    )
    g.add_argument("file")
    g.add_argument("--lang", choices=["ru", "en"], default="ru")
    g.add_argument("--sources", help="source manifest: titles for the source layer")
    g.add_argument("-o", "--output")
    g.set_defaults(func=cmd_graph)

    ix = sub.add_parser(
        "index",
        help="every K, thesis, hypothesis, O, sign-off and element with its YAML line",
    )
    ix.add_argument("file")
    ix.add_argument("--lang", choices=["ru", "en"], default="ru")
    ix.add_argument("--sources", help="source manifest: titles of the cited sources")
    ix.add_argument(
        "--archive",
        help="folder holding the source files: cites link to a file found there",
    )
    ix.add_argument("-o", "--output")
    ix.set_defaults(func=cmd_index)

    pb = sub.add_parser(
        "publish",
        help="validate, then write everything a board sends out: frames, cycle "
        "frames, index, graph, page",
    )
    pb.add_argument("board")
    pb.add_argument("--out", required=True, help="folder for the bundle")
    pb.add_argument("--sources", help="source manifest")
    pb.add_argument("--lang", choices=["ru", "en"], default="ru")
    pb.add_argument("--light", action="store_true", help="as in frames and render")
    pb.add_argument("--zoom", action="store_true", help="as in frames")
    pb.add_argument("--notes", help="Markdown texts per frame, as in frames")
    pb.add_argument("--archive", help="folder with source files, as in index")
    pb.add_argument(
        "--strict",
        action="store_true",
        help="fail on warnings of the record; those of earlier cycles are reported",
    )
    pb.add_argument("--taxonomies", type=Path, help="taxonomy file, as in validate")
    pb.set_defaults(func=cmd_publish)

    vt = sub.add_parser(
        "vault",
        help="the board set as an Obsidian vault (notes, canvas, graph colours)",
    )
    vt.add_argument("file")
    vt.add_argument("out", help="vault folder (created if missing)")
    vt.add_argument("--lang", choices=["ru", "en"], default="ru")
    vt.add_argument("--sources", help="source manifest: titles and links for sources")
    vt.set_defaults(func=cmd_vault)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        code: int = args.func(args)
    except RecordError as exc:
        print(exc, file=sys.stderr)
        return 2
    return code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
