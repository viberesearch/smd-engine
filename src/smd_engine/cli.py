"""Command line: smd new | validate | migrate | render | frames | graph | index | publish
| vault | sources | compare | eval | agree | pack | revise | apply | status | next
| story paths | story check | story render | task check | task render | task diff
| task agenda | deal views."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from smd_engine.agree import FIELDS
from smd_engine.cli_boards import (
    RENDERERS,
    cmd_apply,
    cmd_compare,
    cmd_eval,
    cmd_frames,
    cmd_graph,
    cmd_index,
    cmd_migrate,
    cmd_render,
    cmd_sources,
    cmd_validate,
)
from smd_engine.cli_session import (
    cmd_agree,
    cmd_new,
    cmd_next,
    cmd_pack,
    cmd_publish,
    cmd_revise,
    cmd_status,
    cmd_vault,
)
from smd_engine.cli_story import (
    _story_sources,
    cmd_story_check,
    cmd_story_paths,
    cmd_story_render,
)
from smd_engine.deal.cli import add_deal_parser
from smd_engine.profile import DEFAULT_PROFILE
from smd_engine.records import RecordError
from smd_engine.task.cli import add_task_parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="smd", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    nw = sub.add_parser(
        "new", help="scaffold a case folder: a first record, a manifest and a README"
    )
    nw.add_argument("folder", help="the case folder (made if missing)")
    nw.add_argument(
        "--profile", default=DEFAULT_PROFILE, help="profile id (default: %(default)s)"
    )
    nw.add_argument("--lang", choices=["ru", "en"], default="ru")
    nw.add_argument("--case", help="case id (default: made from the folder name)")
    nw.add_argument("--title", help="title of the first record")
    nw.set_defaults(func=cmd_new)

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

    ag = sub.add_parser(
        "agree", help="how stable are the labels across N runs of one procedure"
    )
    ag.add_argument("records", nargs="+", help="N board sets, runs of one procedure")
    ag.add_argument(
        "--fields",
        help=f"comma-separated label fields (default: all of {', '.join(FIELDS)})",
    )
    ag.add_argument("--json", action="store_true", help="print JSON, not text")
    ag.set_defaults(func=cmd_agree)

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

    st = sub.add_parser(
        "status",
        help="the core view of a board set on one page: open K, hypotheses, "
        "waiting sign-offs, transitions, counts",
    )
    st.add_argument("file")
    st.add_argument("--lang", choices=["ru", "en"], default="ru")
    st.add_argument("-o", "--output", help="write the Markdown here")
    st.set_defaults(func=cmd_status)

    nx = sub.add_parser(
        "next", help="the procedure to run next on a board set, by a rule table"
    )
    nx.add_argument("file")
    nx.set_defaults(func=cmd_next)

    sy = sub.add_parser(
        "story",
        help="stories as a checked view over boards: walks (paths) and rules (check)",
    )
    sysub = sy.add_subparsers(dest="story_command", required=True)
    sp = sysub.add_parser(
        "paths",
        help="walks from a protagonist through a conflict to a resolution, "
        "typed links only; --gaps lists where none exists",
    )
    sp.add_argument("boards", nargs="+", help="board sets of one case")
    sp.add_argument("--audience", action="append", required=True, metavar="ID")
    sp.add_argument(
        "--protagonist",
        action="append",
        metavar="ID",
        help="one for each --audience (default: the audience itself)",
    )
    sp.add_argument(
        "--form", choices=["scqa", "premortem", "scenarios"], default="scqa"
    )
    sp.add_argument(
        "--allow-refers",
        action="store_true",
        help="also walk weak (refers) links, marked ~",
    )
    _story_sources(sp)
    sp.add_argument("--limit", type=int, default=5, help="walks shown (default 5)")
    sp.add_argument(
        "--gaps",
        action="store_true",
        help="where no typed walk exists and the links that would make one",
    )
    sp.add_argument(
        "--yaml", action="store_true", help="story skeletons (or gap reports) as YAML"
    )
    sp.set_defaults(func=cmd_story_paths)
    sc = sysub.add_parser(
        "check", help="hold a story file to rules G1-G7 against its boards"
    )
    sc.add_argument("story")
    sc.add_argument("--boards", nargs="+", required=True, help="board sets it reads")
    _story_sources(sc)
    sc.set_defaults(func=cmd_story_check)
    sr = sysub.add_parser(
        "render", help="a story as readable Markdown: sentences with their board ids"
    )
    sr.add_argument("story")
    sr.add_argument("--md", action="store_true", required=True, help="Markdown")
    sr.add_argument(
        "--boards",
        nargs="+",
        default=[],
        help="board sets it reads: the open questions then show what they assume",
    )
    _story_sources(sr)
    sr.add_argument("--lang", choices=["ru", "en"], default="ru")
    sr.add_argument("-o", "--output")
    sr.set_defaults(func=cmd_story_render)
    add_task_parser(sub)
    add_deal_parser(sub)
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
