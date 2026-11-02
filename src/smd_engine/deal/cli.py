"""`smd deal views`. The parser is added to the main one by `add_deal_parser`
(see `smd_engine.cli`)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from smd_engine.deal.agenda_views import position_agenda
from smd_engine.deal.seal_cmd import cmd_seal
from smd_engine.deal.verdict_cmd import cmd_consent, cmd_verdict
from smd_engine.deal.views import view_of
from smd_engine.records import RecordError, dump_record
from smd_engine.task.agenda import build_agenda
from smd_engine.task.cli import read_replies, valid_pack
from smd_engine.task.diff_html import render_diff_html
from smd_engine.task.diff_md import render_agenda_md, render_diff_md
from smd_engine.task.model import load_task, read_bytes, sha256_bytes
from smd_engine.task.positions import is_deal


def cmd_views(args: argparse.Namespace) -> int:
    pack, pack_sha = valid_pack(Path(args.pack))
    if not is_deal(pack):
        raise RecordError(
            f"{args.pack}: views are for a deal pack (one with positions)"
        )
    path = Path(args.diff)
    diff = load_task(path, "task_diff")
    if diff.get("view"):
        raise RecordError(f"{path}: this is a view already; give the whole diff.yaml")
    if diff["pack"]["sha256"] != pack_sha:
        raise RecordError(f"{path}: the diff is for another text of the pack")
    diff_sha = sha256_bytes(read_bytes(path))
    full = None
    if args.replies:
        if not args.members:
            raise RecordError("--replies needs --members (who is expected to reply)")
        members = [m.strip() for m in args.members.split(",") if m.strip()]
        replies = read_replies(args.replies, members, diff, diff_sha)
        if replies is None:
            return 1
        full = build_agenda(diff, diff_sha, replies, members)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    for position in args.position or [p["id"] for p in pack["positions"]]:
        view = view_of(pack, diff, diff_sha, position)
        text = dump_record(view)
        view_sha = sha256_bytes(text.encode("utf-8"))
        pages = {
            "yaml": text,
            "md": render_diff_md(view),
            "html": render_diff_html(view, view_sha),
        }
        for ext, body in pages.items():
            (out / f"diff.{position}.{ext}").write_text(body, encoding="utf-8")
        print(
            f"wrote {out}/diff.{position}.yaml, .md, .html: "
            f"{len(view['points'])} points, sha256 {view_sha}"
        )
        if full is not None:
            agenda = position_agenda(pack, diff, diff_sha, full, position)
            (out / f"agenda.{position}.yaml").write_text(
                dump_record(agenda), encoding="utf-8"
            )
            (out / f"agenda.{position}.md").write_text(
                render_agenda_md(agenda), encoding="utf-8"
            )
            c = agenda["counts"]
            print(
                f"wrote {out}/agenda.{position}.yaml, .md: "
                f"{c['call']} for the call, {c['settled']} settled"
            )
    return 0


def add_deal_parser(sub: Any) -> None:
    d = sub.add_parser(
        "deal", help="deal mode: views of a diff, sealed bounds and the verdict"
    )
    dsub = d.add_subparsers(dest="deal_command", required=True)
    v = dsub.add_parser(
        "views",
        help="diff.<position>.yaml, .md and .html: what each position is sent",
    )
    v.add_argument("pack", help="the deal pack the diff was made from")
    v.add_argument("diff", help="the whole diff.yaml")
    v.add_argument("-o", "--output", required=True, help="folder to write into")
    v.add_argument(
        "--position", action="append", help="only this position (repeat for several)"
    )
    v.add_argument(
        "--replies",
        nargs="+",
        default=[],
        help="replies files: also write agenda.<position>.yaml and .md",
    )
    v.add_argument(
        "--members", help="member ids, comma separated (with --replies, as in agenda)"
    )
    v.set_defaults(func=cmd_views)
    s = dsub.add_parser(
        "seal",
        help="seal a number for a bound item: a private file and its commitment",
    )
    s.add_argument("pack", help="the deal pack")
    s.add_argument("item", help="id of the bound item")
    s.add_argument("-o", "--output", required=True, help="folder for the sealed file")
    s.add_argument("--member", help="the member who seals (the item's committer)")
    s.add_argument("--value", help="the number; without it you are asked, unseen")
    s.add_argument("--date", help="date of the commitment (today by default)")
    s.add_argument(
        "--key",
        help="your private SSH key: sign the sealed file with it (ssh-keygen -Y sign); "
        "without it the command to run is printed",
    )
    s.set_defaults(func=cmd_seal)
    vd = dsub.add_parser(
        "verdict",
        help="the holder compares a sealed floor and ceiling and logs the verdict",
    )
    vd.add_argument("pack", help="the deal pack")
    vd.add_argument("topic", help="the topic of the bound items, e.g. price")
    vd.add_argument("--answers", nargs="+", required=True, help="the parties' answers")
    vd.add_argument("--floor", help="the seller's sealed file")
    vd.add_argument("--ceiling", help="the buyer's sealed file, if he gave one")
    vd.add_argument("--floor-sig", help="signature of the floor file (<floor>.sig)")
    vd.add_argument(
        "--ceiling-sig", help="signature of the ceiling file (<ceiling>.sig)"
    )
    vd.add_argument("--ledger", required=True, help="verdicts.yaml")
    vd.add_argument(
        "--new",
        action="store_true",
        help="start the ledger (the first run); without it the file must exist",
    )
    vd.add_argument("--date", help="date of the entry (today by default)")
    vd.set_defaults(func=cmd_verdict)
    co = dsub.add_parser(
        "consent",
        help="log a party's consent to the next run of a topic in the ledger "
        "(the seller's, naming the buyer, for every run; the buyer's too for a second)",
    )
    co.add_argument("pack", help="the deal pack")
    co.add_argument("topic", help="the topic of the bound items")
    co.add_argument("--member", required=True, help="the party who consents")
    co.add_argument(
        "--evidence", required=True, help="the party's task_consent file for the run"
    )
    co.add_argument(
        "--signature",
        help="the party's SSH signature of the evidence (<evidence>.sig); "
        "required when the pack has deal.sealed_floor",
    )
    co.add_argument("--ledger", required=True, help="verdicts.yaml")
    co.add_argument(
        "--new",
        action="store_true",
        help="start the ledger with this consent (the seller's, before the first run)",
    )
    co.add_argument("--date", help="date of the entry (today by default)")
    co.set_defaults(func=cmd_consent)
