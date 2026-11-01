"""How stable are the labels a procedure writes: agreement across N runs.

An interpretive step (the `belt`, `kind`, `status` and `voice` of a thesis, the
`kind` of an element, a move's `op`, a gap's `of`) cannot be made deterministic,
but its stability can be measured. Run the same procedure on the same input N
times and give the N records to `agree`. A unit is something the runs may all
describe: a thesis (found in each run by the address it cites, as `eval` pairs
them) or an element of the first record (found in each other run by `compare`).
Each run is a rater and each label field is scored with Krippendorff's alpha.

The thresholds are Krippendorff's convention, not a law: alpha of 0.800 or more
is read as reliable, 0.667 to 0.800 as tentative, below 0.667 as not reliable.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass, field
from typing import Any

from smd_engine.compare import compare
from smd_engine.eval import match_theses

RELIABLE = 0.800
TENTATIVE = 0.667
# Below this many pairable units an alpha is shown but not read: one or two units
# swing it from 0 to 1.
FEW_UNITS = 5
NONE = "(none)"  # the label of a unit a run describes without that label
LIST_CUT = 10  # addresses listed before the list is cut

Getter = Callable[[dict[str, Any]], Any]


@dataclass(frozen=True)
class Alpha:
    units: int  # units with at least one value
    pairable_units: int  # units with two or more values
    pairable_values: int  # values in those units
    alpha: float | None
    why_not: str = ""  # when alpha is None


def alpha_nominal(units: Sequence[Sequence[Hashable | None]]) -> Alpha:
    """Krippendorff's alpha for nominal values, any number of raters, with gaps.

    Krippendorff (2011), "Computing Krippendorff's Alpha-Reliability", the
    coincidence-matrix form. Each unit is the list of the values the raters gave
    it, `None` for a rater who gave none. A unit with fewer than two values is not
    pairable and is dropped. A unit with m values adds 1/(m-1) to the coincidence
    o[c, k] for every ordered pair of its values (c, k) taken from two different
    value slots. With n_c = sum_k o[c, k] and n = sum_c n_c:

        alpha = 1 - D_o / D_e
        D_o = sum_{c != k} o[c, k]
        D_e = sum_{c != k} n_c * n_k / (n - 1)

    Alpha is undefined (None) when D_e is 0: no unit is pairable, or only one value
    occurs in all the pairable data (robustness rule R3: a status, never inf or NaN).
    """
    counted = [Counter(v for v in unit if v is not None) for unit in units]
    counted = [c for c in counted if c]
    pairable = [c for c in counted if sum(c.values()) >= 2]
    n = sum(sum(c.values()) for c in pairable)
    if not pairable:
        return Alpha(len(counted), 0, 0, None, "no unit has two values to pair")
    n_c: Counter[Hashable] = Counter()
    d_o = 0.0
    for c in pairable:
        m = sum(c.values())
        n_c.update(c)
        # ordered pairs of different values in this unit, weighted 1/(m-1)
        d_o += (m * m - sum(v * v for v in c.values())) / (m - 1)
    if len(n_c) < 2:
        return Alpha(
            len(counted), len(pairable), n, None, "only one value occurs in all units"
        )
    d_e = (n * n - sum(v * v for v in n_c.values())) / (n - 1)
    # Robustness rule R3: never divide by an expected disagreement of 0.
    if not d_e > 0:
        return Alpha(len(counted), len(pairable), n, None, "expected disagreement is 0")
    return Alpha(len(counted), len(pairable), n, 1 - d_o / d_e)


def reading(alpha: float | None) -> str:
    """Krippendorff's conventional reading of an alpha."""
    if alpha is None:
        return "n/a"
    if alpha >= RELIABLE:
        return "reliable"
    if alpha >= TENTATIVE:
        return "tentative"
    return "not reliable"


def _move_op(item: dict[str, Any]) -> Any:
    move = item.get("move")
    return move.get("op") if isinstance(move, dict) else None


# field name -> (what carries it, how to read it)
THESIS_FIELDS: dict[str, Getter] = {
    "belt": lambda t: t.get("belt"),
    "kind": lambda t: t.get("kind"),
    "status": lambda t: t.get("status"),
    "voice": lambda t: t.get("voice"),
    "of": lambda t: t.get("of"),
    "op": _move_op,
}
ELEMENT_FIELDS: dict[str, Getter] = {
    "element.kind": lambda e: e.get("kind"),
    "element.of": lambda e: e.get("of"),
    "element.op": _move_op,
}
FIELDS = (*THESIS_FIELDS, *ELEMENT_FIELDS)


@dataclass
class FieldResult:
    name: str
    alpha: Alpha

    @property
    def reading(self) -> str:
        if self.alpha.alpha is not None and self.alpha.pairable_units < FEW_UNITS:
            return f"{reading(self.alpha.alpha)}, few units"
        return reading(self.alpha.alpha)


@dataclass
class Coverage:
    runs: int
    addresses: int
    by_all: int
    by_some: int
    by_one: int
    one_run_only: list[tuple[str, str]]  # (address, name of the run)
    without_cites: int  # theses with no cite: they have no address and are left out


@dataclass
class AgreeResult:
    names: list[str]
    warnings: list[str]
    coverage: Coverage
    fields: list[FieldResult]
    elements: int  # units of the element fields: elements of the first record

    def to_json(self) -> dict[str, Any]:
        cov = self.coverage
        return {
            "runs": self.names,
            "warnings": self.warnings,
            "coverage": {
                "addresses": cov.addresses,
                "by_all": cov.by_all,
                "by_some": cov.by_some,
                "by_one": cov.by_one,
                "one_run_only": [{"address": a, "run": r} for a, r in cov.one_run_only],
                "theses_without_cites": cov.without_cites,
            },
            "element_units": self.elements,
            "fields": [
                {
                    "field": f.name,
                    "units": f.alpha.units,
                    "pairable_units": f.alpha.pairable_units,
                    "pairable_values": f.alpha.pairable_values,
                    "alpha": f.alpha.alpha,
                    "reading": f.reading,
                    "why_not": f.alpha.why_not,
                }
                for f in self.fields
            ],
        }


def check_runs(records: list[dict[str, Any]], names: list[str]) -> list[str]:
    """Warnings when the records may not be runs of one procedure on one input."""
    warnings: list[str] = []
    for key in ("procedure", "pack_sha256", "inputs"):
        values = [(r.get("run") or {}).get(key) for r in records]
        shown = {name: v for name, v in zip(names, values) if v is not None}
        if not shown:
            warnings.append(f"no record has run.{key}")
        elif len(shown) < len(records):
            gone = ", ".join(n for n, v in zip(names, values) if v is None)
            warnings.append(f"run.{key} is missing in {gone}")
        if len({repr(v) for v in shown.values()}) > 1:
            warnings.append(f"run.{key} differs between the records")
    return warnings


def _thesis_units(
    records: list[dict[str, Any]],
) -> tuple[list[list[dict[str, Any] | None]], int]:
    """Theses grouped by cite address: one list per unit, a slot per run.

    Runs are taken in order. Each run's theses are paired one to one with the units
    built so far by `eval.match_theses` (a unit stands for a thesis citing all the
    addresses of its members); a thesis that pairs with none opens a unit. Theses
    with no cites have no address and are counted apart.
    """
    units: list[list[dict[str, Any] | None]] = []
    without = 0
    for r, record in enumerate(records):
        cited = [t for t in record.get("theses", []) if t.get("cites")]
        without += len(record.get("theses", [])) - len(cited)
        anchor = {
            "theses": [
                {
                    "id": str(i),
                    "cites": [c for t in u if t for c in t.get("cites", [])],
                }
                for i, u in enumerate(units)
            ]
        }
        matched, only_run, _ = match_theses({"theses": cited}, anchor)
        by_id = {t["id"]: t for t in cited}
        for m in matched:
            units[int(m.expected)][r] = by_id[m.run]
        unmatched = {tid for tid, _ in only_run}
        for t in cited:
            if t["id"] in unmatched:
                slots: list[dict[str, Any] | None] = [None] * len(records)
                slots[r] = t
                units.append(slots)
    return units, without


def _element_units(
    records: list[dict[str, Any]],
) -> list[list[dict[str, Any] | None]]:
    """Elements of the first record, each with its `compare` match in every other run."""
    first = records[0]
    by_id = [{e["id"]: e for e in r["elements"]} for r in records]
    units: dict[str, list[dict[str, Any] | None]] = {}
    for r in range(1, len(records)):
        for pair in compare(first, records[r]):
            if pair.a is None:
                continue
            slots = units.setdefault(
                pair.a, [by_id[0][pair.a]] + [None] * (len(records) - 1)
            )
            slots[r] = by_id[r][pair.b] if pair.b else None
    return list(units.values())


def _score(units: list[list[dict[str, Any] | None]], get: Getter) -> Alpha:
    """Alpha of one field. A run that has the unit but not the label gives NONE;
    a unit no run labels is not a unit of this field."""
    rows: list[list[Hashable | None]] = []
    for unit in units:
        row = [None if x is None else (get(x) or NONE) for x in unit]
        if any(v is not None and v != NONE for v in row):
            rows.append(row)
    return alpha_nominal(rows)


def _address(unit: list[dict[str, Any] | None]) -> str:
    return str(next(t["cites"][0] for t in unit if t))


def agree(
    records: list[dict[str, Any]],
    names: list[str],
    fields: Sequence[str] = FIELDS,
) -> AgreeResult:
    """Agreement of N runs (records in the same order as names) on the given fields."""
    n = len(records)
    theses, without = _thesis_units(records)
    shared = [sum(1 for t in u if t) for u in theses]
    one = [
        (_address(u), names[next(i for i, t in enumerate(u) if t)])
        for u, k in zip(theses, shared)
        if k == 1
    ]
    coverage = Coverage(
        n,
        len(theses),
        sum(1 for k in shared if k == n),
        sum(1 for k in shared if 1 < k < n),
        len(one),
        one,
        without,
    )
    elements = (
        _element_units(records) if any(f in ELEMENT_FIELDS for f in fields) else []
    )
    results: list[FieldResult] = []
    for name in fields:
        if name in THESIS_FIELDS:
            results.append(FieldResult(name, _score(theses, THESIS_FIELDS[name])))
        else:
            results.append(FieldResult(name, _score(elements, ELEMENT_FIELDS[name])))
    return AgreeResult(
        names, check_runs(records, names), coverage, results, len(elements)
    )


def _pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:.0f}%" if whole else "-"


def format_result(result: AgreeResult) -> str:
    """Plain text: warnings, the table per field, the coverage, the reading."""
    cov = result.coverage
    out = [f"agreement of {len(result.names)} runs: " + ", ".join(result.names), ""]
    out += [f"WARNING: {w}" for w in result.warnings]
    if result.warnings:
        out.append("")
    out.append(f"{'field':<14}{'units':>6}{'values':>8}{'alpha':>8}  reading")
    for f in result.fields:
        a = f.alpha
        shown = "n/a" if a.alpha is None else f"{a.alpha:.3f}"
        out.append(
            f"{f.name:<14}{a.units:>6}{a.pairable_values:>8}{shown:>8}  {f.reading}"
        )
    for f in result.fields:
        if f.alpha.alpha is None:
            out.append(f"  {f.name}: alpha is n/a, {f.alpha.why_not}")
    out += ["", f"theses by cite address ({cov.addresses} addresses, {cov.runs} runs):"]
    out.append(
        f"  found by all runs:  {cov.by_all} ({_pct(cov.by_all, cov.addresses)})"
    )
    out.append(
        f"  found by some runs: {cov.by_some} ({_pct(cov.by_some, cov.addresses)})"
    )
    out.append(
        f"  found by one run:   {cov.by_one} ({_pct(cov.by_one, cov.addresses)})"
    )
    for address, run in cov.one_run_only[:LIST_CUT]:
        out.append(f"    {address}  ({run})")
    if len(cov.one_run_only) > LIST_CUT:
        out.append(f"    ... and {len(cov.one_run_only) - LIST_CUT} more")
    if cov.without_cites:
        out.append(f"  {cov.without_cites} theses without cites are not counted")
    if result.elements:
        out.append(
            f"elements: {result.elements} units, the elements of {result.names[0]}"
        )
    scored = [f for f in result.fields if f.alpha.alpha is not None]
    few = [f.name for f in scored if f.alpha.pairable_units < FEW_UNITS]
    scored = [f for f in scored if f.alpha.pairable_units >= FEW_UNITS]
    out.append("")
    if few:
        out.append(
            f"Not read, fewer than {FEW_UNITS} pairable units: " + ", ".join(few)
        )
    if scored:
        low = min(scored, key=lambda f: f.alpha.alpha or 0.0)
        out.append(
            f"Reading: the least stable field is {low.name}, alpha {low.alpha.alpha:.3f}, "
            f"{low.reading}."
        )
    else:
        out.append("Reading: no field has an alpha.")
    out.append(
        "Convention (Krippendorff), not a law: alpha >= 0.800 reliable; "
        "0.667 to 0.800 tentative; below 0.667 not reliable."
    )
    return "\n".join(out) + "\n"
