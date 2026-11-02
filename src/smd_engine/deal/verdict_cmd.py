"""`smd deal verdict` and `smd deal consent`: the holder's commands."""

from __future__ import annotations

import argparse
import datetime as dt
from functools import partial
from pathlib import Path
from typing import Any

from smd_engine.deal.consent import verify_consents
from smd_engine.deal.ledger import (
    RUN_MAX,
    ledger_head,
    load_ledger,
    new_ledger,
    save_ledger,
    tested_runs,
)
from smd_engine.deal.sealed import read_sealed
from smd_engine.deal.signing import signatures_on, verify_file
from smd_engine.deal.verdict import (
    SIDES,
    Opener,
    add_consent,
    run_verdict,
    topic_items,
)
from smd_engine.records import RecordError
from smd_engine.task.bounds import committer
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


def _verify_signed(
    pack: dict[str, Any],
    topic: str,
    ledger: dict[str, Any],
    files: dict[str, str | None],
    sigs: dict[str, str | None],
) -> None:
    """With a sealed floor, refuse the run unless the consents it counts and the
    sealed files given are signed by their parties. Nothing is logged. Past the
    run cap nothing is counted or opened, so nothing is checked."""
    run = tested_runs(ledger, topic) + 1
    if not signatures_on(pack) or run > RUN_MAX:
        return
    items = topic_items(pack, topic)
    verify_consents(pack, ledger, topic, run)
    for side in SIDES:
        path = files[side]
        if path:
            sig = sigs[side]
            verify_file(
                pack,
                str(committer(pack, items[side])),
                Path(path),
                Path(sig) if sig else None,
            )


def cmd_verdict(args: argparse.Namespace) -> int:
    pack, pack_sha = valid_pack(Path(args.pack))
    loaded = load_answers(pack, pack_sha, [Path(p) for p in args.answers])
    answers = {a["member"]: a for _, _, a in loaded}
    files = {"floor": args.floor, "ceiling": args.ceiling}
    ledger_path = Path(args.ledger)
    ledger = _ledger(ledger_path, pack, args.new)
    sigs = {"floor": args.floor_sig, "ceiling": args.ceiling_sig}
    _verify_signed(pack, args.topic, ledger, files, sigs)
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
    sig = Path(args.signature) if args.signature else Path(f"{evidence}.sig")
    signature = sig.read_text(encoding="utf-8") if sig.is_file() else None
    entry = add_consent(
        pack, args.topic, ledger, args.member, evidence, date, signature
    )
    save_ledger(ledger_path, ledger)
    print(
        f"ledger {ledger_path}: entry {entry['seq']}, consent of {args.member} "
        f"to run {entry['run']} of {args.topic}"
    )
    return 0
