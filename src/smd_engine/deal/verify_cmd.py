"""`smd deal verify`: audit a verdict ledger (see `verify.py`)."""

from __future__ import annotations

import argparse
from pathlib import Path

from smd_engine.deal.signing import signatures_on, ssh_keygen
from smd_engine.deal.verify import verify_ledger
from smd_engine.records import RecordError
from smd_engine.task.cli import valid_pack
from smd_engine.task.model import load_task


def cmd_verify(args: argparse.Namespace) -> int:
    pack, pack_sha = valid_pack(Path(args.pack))
    if not pack.get("deal") or not pack.get("holder"):
        raise RecordError(f"{args.pack}: verify is for a deal pack with a holder")
    if signatures_on(pack):
        ssh_keygen()  # a sealed-floor audit needs it: fail early, with the reason
    ledger = load_task(Path(args.ledger), "task_verdicts")
    diff = load_task(Path(args.diff), "task_diff") if args.diff else None
    report = verify_ledger(
        pack,
        pack_sha,
        ledger,
        [Path(p) for p in args.answers],
        Path(args.sealed) if args.sealed else None,
        diff,
    )
    print(report.as_json() if args.json else "\n".join(report.lines()))
    ok = report.ok if args.allow_unbound else report.complete
    return 0 if ok else 1
