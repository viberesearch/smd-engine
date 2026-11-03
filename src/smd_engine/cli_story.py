"""Commands of `smd story`: paths, check, render (the parser is in `cli.py`)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from smd_engine.cli_boards import _load_taxonomies, _manifest_kinds
from smd_engine.records import (
    RecordError,
    dump_record,
    load_record,
)
from smd_engine.story.check import check_story
from smd_engine.story.gaps import gap_report, report_dict
from smd_engine.story.model import Boards, load_boards
from smd_engine.story.paths import enumerate_candidates, skeleton, walk_text
from smd_engine.story.render import render_story_md


def _story_boards(args: argparse.Namespace) -> Boards | None:
    """The board sets of a story command, checked as `smd validate` checks them,
    against the source manifest and taxonomies when given."""
    try:
        return load_boards(
            [Path(p) for p in args.boards],
            _manifest_kinds(args.sources),
            _load_taxonomies(args.taxonomies),
        )
    except RecordError as exc:
        print(exc, file=sys.stderr)
        return None


def _story_pairs(args: argparse.Namespace) -> list[tuple[str, str]] | None:
    audiences = args.audience
    protagonists = args.protagonist or audiences
    if len(protagonists) != len(audiences):
        print("give one --protagonist for each --audience", file=sys.stderr)
        return None
    return list(zip(audiences, protagonists))


def cmd_story_paths(args: argparse.Namespace) -> int:
    boards = _story_boards(args)
    pairs = _story_pairs(args)
    if boards is None or pairs is None:
        return 2
    for item in {i for pair in pairs for i in pair}:
        if item not in boards.elements:
            print(f"unknown element '{item}'", file=sys.stderr)
            return 2
    stamp = ", ".join(
        f"{s['id']}@{s['version']} {s['sha256'][:12]}" for s in boards.stamps
    )
    out: list[str] = []
    docs: list[dict[str, Any]] = []
    for audience, protagonist in pairs:
        head = f"audience {audience}, protagonist {protagonist}"
        if args.gaps:
            rep = gap_report(boards, audience, protagonist, args.limit)
            docs.append(report_dict(rep))
            out += _gap_lines(boards, rep, head)
            continue
        found, truncated = enumerate_candidates(
            boards, protagonist, args.allow_refers, args.limit
        )
        out.append(f"{head}, form {args.form}; boards {stamp}")
        links = "typed and weak (refers) links" if args.allow_refers else "typed links"
        out.append(f"{len(found)} walk(s) of 4-9 items over {links}, best first")
        if truncated:
            out.append("search stopped at its step limit: the list may be incomplete")
        for n, cand in enumerate(found, 1):
            docs.append(skeleton(boards, cand, audience, protagonist, args.form))
            out.append(
                f"{n}. typed {len(cand.steps) - cand.weak}/{len(cand.steps)}, "
                f"components {cand.components}, against the direction {cand.backward}"
            )
            out.append(f"   walk: {walk_text(cand)}")
            out.append(f"   conflict: {', '.join(cand.conflict)}")
            out.append(f"   resolution: {cand.resolution}")
            out.append(f"   open: {', '.join(cand.open) or '-'}")
        out.append("")
    if args.yaml:
        sys.stdout.write("\n---\n".join(dump_record(d) for d in docs))
    else:
        sys.stdout.write("\n".join(out) + "\n")
    return 0


def _gap_lines(boards: Boards, rep: Any, head: str) -> list[str]:
    if rep.status == "path":
        best = rep.typed[0]
        return [
            f"{head}: a typed walk exists ({len(rep.typed)} shown at most)",
            f"   best: {walk_text(best)}",
            "",
        ]
    lines = [f"{head}: NO typed walk"]
    lines.append(
        f"   typed component: {rep.component} item(s); conflict objects in it: "
        f"{', '.join(rep.conflict) or '-'}; resolution objects in it: "
        f"{', '.join(rep.resolution) or '-'}"
    )
    lines += [f"   {r}" for r in rep.reasons]
    if rep.route:
        lines.append(f"   cheapest route: {' > '.join(rep.route)}")
    for m in rep.missing:
        carries = f"({m.carries})" if m.carries else ""
        named = f" in {', '.join(m.evidence)}" if m.evidence else ""
        lines.append(
            f"   missing: {m.a} -> {m.b}: {m.kind}{carries}  [{m.now}{named}; {m.why}]"
        )
    lines.append("")
    return lines


def cmd_story_check(args: argparse.Namespace) -> int:
    story = load_record(Path(args.story))
    if story["record"] != "story":
        print("story check takes a story record", file=sys.stderr)
        return 2
    boards = _story_boards(args)
    if boards is None:
        return 2
    findings = check_story(story, boards)
    for f in findings:
        print(f)
    errors = sum(f.level == "error" for f in findings)
    warnings = sum(f.level == "warning" for f in findings)
    hints = sum(f.level == "hint" for f in findings)
    print(f"{args.story}: {errors} error(s), {warnings} warning(s), {hints} hint(s)")
    return 1 if errors else 0


def _story_sources(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--sources", type=Path, help="source manifest: citations of the boards checked"
    )
    parser.add_argument(
        "--taxonomies", type=Path, help="taxonomy file: tags of the boards checked"
    )


def cmd_story_render(args: argparse.Namespace) -> int:
    story = load_record(Path(args.story))
    if story["record"] != "story":
        print("story render takes a story record", file=sys.stderr)
        return 2
    boards = _story_boards(args) if args.boards else None
    if args.boards and boards is None:
        return 2
    text = render_story_md(story, boards, args.lang)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0
