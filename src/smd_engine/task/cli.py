"""`smd task check | render | diff | agenda`. The parser is added to the main one
by `add_task_parser` (see `smd_engine.cli`)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from smd_engine.deal.agenda_views import common_agenda
from smd_engine.deal.ledger import load_ledger
from smd_engine.deal.sealed import stray_sealed_issues
from smd_engine.records import RecordError, dump_record
from smd_engine.task.acceptance import check_files as check_acceptances
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
from smd_engine.task.overwrite import replaceable
from smd_engine.task.pack_html import render_pack_html
from smd_engine.task.pack_md import render_pack_md
from smd_engine.task.positions import is_deal, pack_view, stamp_sha, stamps_text

ANNEX_WARNING = (
    "warning: full diff: holder only; send parties their views from smd deal views"
)


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


def valid_pack(path: Path) -> tuple[dict[str, Any], str]:
    """The pack and the sha256 it is stamped with (that of its file, or of its
    shared core in a deal pack); refused when it has an error."""
    pack = load_task(path, "task_pack")
    errors = [i for i in check_pack(pack, str(path)) if i.level == "error"]
    if errors:
        raise RecordError(f"{path}: {errors[0].message}")
    return pack, stamp_sha(pack, sha256_bytes(read_bytes(path)))


def cmd_check(args: argparse.Namespace) -> int:
    path = Path(args.pack)
    pack = load_task(path, "task_pack")
    errors = _report(str(path), check_pack(pack, str(path)))
    if errors:
        return 1
    pack_sha = stamp_sha(pack, sha256_bytes(read_bytes(path)))
    for line in stamps_text(pack):
        print(line)
    diff = None
    diff_sha = None
    view_sha = None
    if args.diff:
        diff = load_task(Path(args.diff), "task_diff")
        diff_sha = sha256_bytes(read_bytes(Path(args.diff)))
        if diff.get("view"):  # a per-position view: replies name the whole diff
            view_sha, diff_sha = diff_sha, diff["view"]["diff"]
    for name in args.answers:
        ans = load_task(Path(name), "task_answers")
        errors += _report(
            name, check_answers(pack, pack_sha, ans, name, Path(name).parent)
        )
    if stray := stray_sealed_issues([Path(n).parent for n in args.answers]):
        errors += _report("sealed files", stray)
    for name in args.replies:
        rep = load_task(Path(name), "task_replies")
        errors += _report(
            name,
            check_replies(member_ids(pack), rep, name, diff, diff_sha, view_sha),
        )
    for name, issues, line in check_acceptances(
        pack, args.acceptance, args.board, args.prior
    ):
        if line:
            print(line)
        errors += _report(name, issues)
    return 1 if errors else 0


def cmd_render(args: argparse.Namespace) -> int:
    path = Path(args.file)
    data = load_task(path)
    out = Path(args.output)
    sha = sha256_bytes(read_bytes(path))
    if data.get("record") == "task_pack":
        pack, sha = valid_pack(path)
        view, suffix, annex = pack_view(pack, args.position)
        if args.stage and not (pack.get("deal") or {}).get("stages"):
            raise RecordError(f"{path}: --stage needs deal.stages")
        if args.stage and args.stage not in pack["deal"]["stages"]:
            raise RecordError(f"{path}: stage {args.stage} is not in deal.stages")
        _write(out / f"pack{suffix}.md", render_pack_md(view, args.stage))
        _write(
            out / f"pack{suffix}.html", render_pack_html(view, sha, annex, args.stage)
        )
    elif args.position or args.stage:
        raise RecordError(f"{path}: --position and --stage are for a deal pack")
    elif data.get("record") == "task_diff":
        _write(out / "diff.md", render_diff_md(data))
        _write(out / "diff.html", render_diff_html(data, sha))
    else:
        raise RecordError(f"{path}: render takes a task pack or a task diff")
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    pack, pack_sha = valid_pack(Path(args.pack))
    loaded = load_answers(pack, pack_sha, [Path(p) for p in args.answers])
    ledger = load_ledger(Path(args.ledger), pack) if args.ledger else None
    diff = build_diff(pack, pack_sha, loaded, ledger)
    out = Path(args.output)
    text = dump_record(diff)
    target = out / "diff.yaml"
    if (
        target.exists()
        and target.read_text(encoding="utf-8") != text
        and not args.force
        and not replaceable(target.read_text(encoding="utf-8"), diff, ledger)
    ):
        raise RecordError(
            f"{target} exists and differs (a model may have written into it, the "
            "answers changed, or the ledger is not the one it was made from); "
            "move it or pass --force"
        )
    _write(target, text)
    _write(out / "diff.md", render_diff_md(diff))
    _write(
        out / "diff.html", render_diff_html(diff, sha256_bytes(text.encode("utf-8")))
    )
    if is_deal(pack) and any("audience" in p for p in diff["points"]):
        print(ANNEX_WARNING, file=sys.stderr)
    s = diff["summary"]
    print(
        f"{s['points']} points, {s['open']} open: "
        + ", ".join(f"{n} {c}" for c, n in s["by_class"].items())
    )
    return 0


def read_replies(
    names: list[str], members: list[str], diff: dict[str, Any], diff_sha: str
) -> list[dict[str, Any]] | None:
    """The replies files, checked against the diff; None when one has an error."""
    replies = []
    errors = 0
    for name in names:
        rep = load_task(Path(name), "task_replies")
        issues = check_replies(members, rep, name, diff, diff_sha)
        errors += _report(name, issues) if issues else 0
        replies.append(rep)
    return None if errors else replies


def cmd_agenda(args: argparse.Namespace) -> int:
    path = Path(args.diff)
    diff = load_task(path, "task_diff")
    diff_sha = sha256_bytes(read_bytes(path))
    members = [m.strip() for m in args.members.split(",") if m.strip()]
    replies = read_replies(args.replies, members, diff, diff_sha)
    if replies is None:
        return 1
    agenda = common_agenda(diff, build_agenda(diff, diff_sha, replies, members))
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
    c.add_argument("--acceptance", nargs="+", default=[], help="task_acceptance files")
    c.add_argument("--board", help="board set file the pack's map names")
    c.add_argument("--prior", help="board set file an acceptance was given on")
    c.set_defaults(func=cmd_check)
    r = tsub.add_parser(
        "render",
        help="pack.md and pack.html from a pack; diff.md and diff.html from a diff",
    )
    r.add_argument("file", help="pack.yaml or diff.yaml")
    r.add_argument("-o", "--output", required=True, help="folder to write into")
    r.add_argument(
        "--position",
        help="deal pack: pack.<position>.md and .html, the core and that position's annex",
    )
    r.add_argument(
        "--stage",
        help="deal pack: the stage the page is for; it shows the asking price "
        "from the stage that opens it on (otherwise only when it opens)",
    )
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
    d.add_argument(
        "--ledger",
        help="deal: verdicts.yaml; the verdicts and its head go into the diff",
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
