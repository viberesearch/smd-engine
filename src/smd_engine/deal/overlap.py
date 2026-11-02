"""The comparison of a sealed floor with a sealed ceiling, behind a protocol.

The files, the commitments, the ledger and the verdict keep their formats when
the comparison is replaced; only `holder.method` of the pack changes. One bound
against another is the millionaires' problem: one comparison and one bit out.
`local-v1` is the simple version: the holder's program reads both numbers in
memory, on its own machine, and trusts that machine and its operator. A
two-party or split-trust protocol would be another class here with another
method name."""

from __future__ import annotations

from typing import Protocol

from smd_engine.records import RecordError


class Comparator(Protocol):
    method: str

    def compare(self, floor: float, ceiling: float) -> bool:
        """Whether the seller's floor can be met by the buyer's ceiling. Only
        this bit leaves the comparison, never the gap."""
        ...


class LocalComparator:
    method = "local-v1"

    def compare(self, floor: float, ceiling: float) -> bool:
        return floor <= ceiling


COMPARATORS: dict[str, type[LocalComparator]] = {"local-v1": LocalComparator}


def comparator_for(method: str) -> Comparator:
    if method not in COMPARATORS:
        raise RecordError(f"holder method {method} is not known to this engine")
    return COMPARATORS[method]()
