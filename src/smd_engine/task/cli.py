"""`smd task check | render | diff | agenda`. The parser is added to the main one
by `add_task_parser` (see `smd_engine.cli`)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from smd_engine.records import RecordError, dump_record
from smd_engine.task.agenda import build_agenda
from smd_engine.task.check import check_answers, check_pack, check_replies
from smd_engine.task.diff import build_diff, load_answers
from smd_engine.task.diff_html import render_diff_html
from smd_engine.task.diff_md import render_agenda_md, render_diff_md
from smd_engine.task.model import (
    Issue,
    load_task,
    member_ids,
    read_bytes,
    sha256_bytes,
)
from smd_engine.task.pack_html import render_pack_html
from smd_engine.task.pack_md import render_pack_md


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path}")


def _report(where: str, issues: list[Issue]) -> int:
    for issue in issues:
        print(issue)
    errors = sum(1 for i in issues if i.level == "error")
    warnings = len(issues) - errors
    print(f"{where}: {errors} error(s), {warnings} warning(s)")
    return errors


def _valid_pack(path: Path) -> tuple[dict[str, Any], str]:
    """The pack and the sha256 of its file; refused when it has an error."""
    pack = load_task(path, "task_pack")
    errors = [i for i in check_pack(pack, str(path)) if i.level == "error"]
    if errors:
        raise RecordError(f"{path}: {errors[0].message}")
    return pack, sha256_bytes(read_bytes(path))


def cmd_check(args: argparse.Namespace) -> int:
    path = Path(args.pack)
    pack = load_task(path, "task_pack")
    pack_sha = sha256_bytes(read_bytes(path))
    errors = _report(str(path), check_pack(pack, str(path)))
    if errors:
        return 1
    diff = None
    diff_sha = None
    if args.diff:
        diff = load_task(Path(args.diff), "task_diff")
        diff_sha = sha256_bytes(read_bytes(Path(args.diff)))
    for name in args.answers:
        ans = load_task(Path(name), "task_answers")
        errors += _report(
            name, check_answers(pack, pack_sha, ans, name, Path(name).parent)
        )
    for name in args.replies:
        rep = load_task(Path(name), "task_replies")
        errors += _report(
            name, check_replies(member_ids(pack), rep, name, diff, diff_sha)
        )
    return 1 if errors else 0


def cmd_render(args: argparse.Namespace) -> int:
    path = Path(args.file)
    data = load_task(path)
    out = Path(args.output)
    sha = sha256_bytes(read_bytes(path))
    if data.get("record") == "task_pack":
        pack, sha = _valid_pack(path)
        _write(out / "pack.md", render_pack_md(pack))
        _write(out / "pack.html", render_pack_html(pack, sha))
    elif data.get("record") == "task_diff":
        _write(out / "diff.md", render_diff_md(data))
        _write(out / "diff.html", render_diff_html(data, sha))
    else:
        raise RecordError(f"{path}: render takes a task pack or a task diff")
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    pack, pack_sha = _valid_pack(Path(args.pack))
    loaded = load_answers(pack, pack_sha, [Path(p) for p in args.answers])
    diff = build_diff(pack, pack_sha, loaded)
    out = Path(args.output)
    text = dump_record(diff)
    target = out / "diff.yaml"
    if (
        target.exists()
        and target.read_text(encoding="utf-8") != text
        and not args.force
    ):
        raise RecordError(
            f"{target} exists and differs (a model may have written into it, or "
            "the answers changed); move it or pass --force"
        )
    _write(target, text)
    _write(out / "diff.md", render_diff_md(diff))
    _write(
        out / "diff.html", render_diff_html(diff, sha256_bytes(text.encode("utf-8")))
    )
    s = diff["summary"]
    print(
        f"{s['points']} points, {s['open']} open: "
        + ", ".join(f"{n} {c}" for c, n in s["by_class"].items())
    )
    return 0


def cmd_agenda(args: argparse.Namespace) -> int:
    path = Path(args.diff)
    diff = load_task(path, "task_diff")
    diff_sha = sha256_bytes(read_bytes(path))
    members = [m.strip() for m in args.members.split(",") if m.strip()]
    replies = []
    errors = 0
    for name in args.replies:
        rep = load_task(Path(name), "task_replies")
        issues = check_replies(members, rep, name, diff, diff_sha)
        errors += _report(name, issues) if issues else 0
        replies.append(rep)
    if errors:
        return 1
    agenda = build_agenda(diff, diff_sha, replies, members)
    target = Path(args.output)
    _write(target, render_agenda_md(agenda))
    _write(target.with_suffix(".yaml"), dump_record(agenda))
    c = agenda["counts"]
    print(f"{c['call']} point(s) for the call, {c['settled']} settled")
    return 0


def add_task_parser(sub: Any) -> None:
    t = sub.add_parser(
        "task",
        help="task packs for async group work: check, render, diff, agenda",
    )
    tsub = t.add_subparsers(dest="task_command", required=True)
    c = tsub.add_parser("check", help="schema and cross checks of a pack and its files")
    c.add_argument("pack")
    c.add_argument("answers", nargs="*", help="answers files")
    c.add_argument("--replies", nargs="+", default=[], help="replies files")
    c.add_argument("--diff", help="diff.yaml the replies are checked against")
    c.set_defaults(func=cmd_check)
    r = tsub.add_parser(
        "render",
        help="pack.md and pack.html from a pack; diff.md and diff.html from a diff",
    )
    r.add_argument("file", help="pack.yaml or diff.yaml")
    r.add_argument("-o", "--output", required=True, help="folder to write into")
    r.set_defaults(func=cmd_render)
    d = tsub.add_parser(
        "diff", help="answers side by side: diff.yaml, diff.md, diff.html"
    )
    d.add_argument("pack")
    d.add_argument("answers", nargs="+")
    d.add_argument("-o", "--output", required=True, help="folder to write into")
    d.add_argument(
        "--force", action="store_true", help="overwrite a diff.yaml that differs"
    )
    d.set_defaults(func=cmd_diff)
    a = tsub.add_parser(
        "agenda", help="the points for the call, from a diff and the replies"
    )
    a.add_argument("diff")
    a.add_argument("replies", nargs="*")
    a.add_argument("--members", required=True, help="member ids, comma separated")
    a.add_argument(
        "-o",
        "--output",
        default="agenda.md",
        help="agenda.md; agenda.yaml is written beside it",
    )
    a.set_defaults(func=cmd_agenda)
