"""`smd deal seal`: seal a number for a bound item on the party's own machine."""

from __future__ import annotations

import argparse
import datetime as dt
import getpass
import sys
from pathlib import Path

from smd_engine.deal.sealed import (
    commitment_of,
    make_sealed,
    seal_file_name,
    unignored_in_worktree,
    usable_number,
    write_private,
)
from smd_engine.deal.signing import sign_command, sign_file, ssh_keygen
from smd_engine.records import RecordError, dump_record
from smd_engine.task.bounds import committer
from smd_engine.task.cli import valid_pack


def _number(text: str) -> float:
    try:
        return float(text.strip().replace(",", "."))
    except ValueError:
        raise RecordError("the value is not a number") from None


def _report(path: Path, member: str, item_id: str, commit: str) -> None:
    print(f"wrote {path}: keep it outside every repository; it goes to the holder only")
    print(f"commitment: {commit}")
    print(f"put this under `answers:` in answers_{member}.yaml:")
    print(f'  {item_id}: {{value: "{commit}"}}')


def cmd_seal(args: argparse.Namespace) -> int:
    pack, pack_sha = valid_pack(Path(args.pack))
    item = next(
        (i for i in pack["items"] if i["id"] == args.item and i["kind"] == "bound"),
        None,
    )
    if item is None:
        raise RecordError(f"{args.item} is not a bound item of the pack")
    who = committer(pack, item)
    member = args.member or who
    if member != who:
        raise RecordError(f"item {item['id']} is committed by {who}, not by {member}")
    if args.key:
        ssh_keygen()  # fail before the file is written
    # a prompt keeps the number out of the shell history and the process list
    value = _number(
        args.value if args.value is not None else getpass.getpass("number: ")
    )
    if not usable_number(value):
        raise RecordError("the value is not a finite number")
    date = args.date or dt.date.today().isoformat()
    sealed = make_sealed(pack, pack_sha, item, str(member), value, date)
    path = Path(args.output) / seal_file_name(str(member), item["id"])
    write_private(path, dump_record(sealed))
    commit = commitment_of(sealed)
    signed = f"{path}.sig"
    if args.key:
        try:
            sign_file(Path(args.key), path)
        except RecordError:
            # the file stands and a second seal is refused: give what is needed
            _report(path, str(member), item["id"], commit)
            print(f"sign it with your key and send {signed} with it:")
            print(f"  {sign_command('<private key>', path)}")
            raise
        print(f"signed {path}: the signature is {signed}; it goes with the file")
    else:
        print(
            f"sign it with your key ({member}'s key listed in the pack) and send {signed} with it:"
        )
        print(f"  {sign_command('<private key>', path)}")
    _report(path, str(member), item["id"], commit)
    if unignored_in_worktree(path):
        print(
            f"warning: {path} sits in a git work tree and is not ignored",
            file=sys.stderr,
        )
    return 0
