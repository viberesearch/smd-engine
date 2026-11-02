"""`smd deal verdict` and `smd deal consent`: the holder's commands."""

from __future__ import annotations

import argparse
import datetime as dt
from functools import partial
from pathlib import Path
from typing import Any

from smd_engine.deal.ledger import (
    ledger_head,
    load_ledger,
    new_ledger,
    save_ledger,
)
from smd_engine.deal.sealed import read_sealed
from smd_engine.deal.verdict import SIDES, Opener, add_consent, run_verdict
from smd_engine.records import RecordError
from smd_engine.task.cli import valid_pack
from smd_engine.task.deal_labels import DEAL_LABELS
from smd_engine.task.diff import load_answers


def _ledger(path: Path, pack: dict[str, Any], new: bool) -> dict[str, Any]:
    """The ledger in `path`. A missing file is an error unless `new` is set, so a
    mistyped path cannot start a ledger whose run count is zero."""
    if not new:
        if not path.exists():
            raise RecordError(
                f"{path}: no ledger there (the first `smd deal verdict` takes --new)"
            )
        return load_ledger(path, pack)
    if path.exists():
        raise RecordError(f"{path}: exists; drop --new to add to it")
    return new_ledger(pack)


def cmd_verdict(args: argparse.Namespace) -> int:
    pack, pack_sha = valid_pack(Path(args.pack))
    loaded = load_answers(pack, pack_sha, [Path(p) for p in args.answers])
    answers = {a["member"]: a for _, _, a in loaded}
    files = {"floor": args.floor, "ceiling": args.ceiling}
    ledger_path = Path(args.ledger)
    ledger = _ledger(ledger_path, pack, args.new)
    # the sealed files are read here, after the pack and the ledger are accepted
    openers: dict[str, Opener] = {
        s: partial(read_sealed, Path(files[s])) for s in SIDES if files[s]
    }
    date = args.date or dt.date.today().isoformat()
    entry = run_verdict(pack, pack_sha, args.topic, answers, openers, ledger, date)
    save_ledger(ledger_path, ledger)
    print(DEAL_LABELS[pack["lang"]]["price_verdicts"][entry["verdict"]])
    if entry.get("reason"):
        print(f"reason: {entry['reason']}")
    print(f"ledger {ledger_path}: entry {entry['seq']}, head {ledger_head(ledger)}")
    return 0


def cmd_consent(args: argparse.Namespace) -> int:
    pack, _ = valid_pack(Path(args.pack))
    evidence = Path(args.evidence)
    ledger_path = Path(args.ledger)
    ledger = _ledger(ledger_path, pack, args.new)
    date = args.date or dt.date.today().isoformat()
    entry = add_consent(pack, args.topic, ledger, args.member, evidence, date)
    save_ledger(ledger_path, ledger)
    print(
        f"ledger {ledger_path}: entry {entry['seq']}, consent of {args.member} "
        f"to run {entry['run']} of {args.topic}"
    )
    return 0
