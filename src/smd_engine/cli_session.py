"""Commands of `smd` that run a session: agree, pack, revise, publish, vault, new,
status, next (the parser is in `cli.py`)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from smd_engine.agree import FIELDS, agree
from smd_engine.agree import format_result as format_agreement
from smd_engine.cli_boards import (
    _board_or_error,
    _build_frames,
    _load_manifest,
    _load_taxonomies,
)
from smd_engine.nextstep import render_next
from smd_engine.pack import pack
from smd_engine.profile import ProfileError
from smd_engine.records import (
    RecordError,
    dump_record,
    load_record,
)
from smd_engine.render.frames import (
    apply_notes,
    parse_notes,
)
from smd_engine.render.frames_page import render_frames_html
from smd_engine.render.graph import render_graph_html
from smd_engine.render.html import render_html
from smd_engine.render.index import render_index
from smd_engine.render.light import lighten
from smd_engine.render.vault import export_vault
from smd_engine.revise import revise
from smd_engine.scaffold import ScaffoldError, scaffold
from smd_engine.sources import (
    source_ids,
    source_kinds,
)
from smd_engine.status import render_status
from smd_engine.validate import validate_record


def cmd_agree(args: argparse.Namespace) -> int:
    if len(args.records) < 2:
        print("agree takes two or more records", file=sys.stderr)
        return 2
    fields = args.fields.split(",") if args.fields else list(FIELDS)
    unknown = [f for f in fields if f not in FIELDS]
    if unknown:
        print(
            f"unknown field {', '.join(unknown)}; the fields are {', '.join(FIELDS)}",
            file=sys.stderr,
        )
        return 2
    records = [load_record(Path(p)) for p in args.records]
    if any(r["record"] != "board_set" for r in records):
        print("agree takes board_set records", file=sys.stderr)
        return 2
    names = [Path(p).name for p in args.records]
    try:
        result = agree(records, names, fields)
    except ProfileError as exc:  # two profiles
        print(exc, file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result.to_json(), indent=2, ensure_ascii=False))
    else:
        sys.stdout.write(format_agreement(result))
    return 0


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
    data = text.encode("utf-8")
    if args.output:
        Path(args.output).write_bytes(data)
    else:
        # Bytes, so that what reaches a redirected file is what was hashed.
        out = getattr(sys.stdout, "buffer", None)
        if out is not None:
            sys.stdout.flush()
            out.write(data)
            out.flush()
        else:
            sys.stdout.write(text)
    # The hash a run records as `run.pack_sha256`; on stderr, so a pack sent to
    # stdout stays the pack alone.
    print(f"pack sha256: {hashlib.sha256(data).hexdigest()}", file=sys.stderr)
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
    kinds = source_kinds(manifest) if manifest else None
    taxonomies = _load_taxonomies(args.taxonomies)
    chain = _chain(path, data)
    failed = False
    # errors fail anywhere in the chain; with --strict, warnings fail only on the
    # published record, and those of the earlier cycles are reported
    for n, (file, rec) in enumerate(chain):
        prev = chain[n + 1][1] if n + 1 < len(chain) else None
        for f in validate_record(rec, ids, prev, taxonomies, kinds):
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


def cmd_new(args: argparse.Namespace) -> int:
    try:
        written = scaffold(
            Path(args.folder), args.profile, args.lang, args.case, args.title
        )
    except (ScaffoldError, ProfileError) as exc:
        print(exc, file=sys.stderr)
        return 2
    for path in written:
        print(path)
    print(
        f"next: smd validate {args.folder} --sources {Path(args.folder) / 'sources.yaml'} --hints"
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    data = _board_or_error(args.file, "status")
    if data is None:
        return 1
    text = render_status(data, args.lang)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    data = _board_or_error(args.file, "next")
    if data is None:
        return 1
    sys.stdout.write(render_next(data, args.file))
    return 0
