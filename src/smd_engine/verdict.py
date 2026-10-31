"""A proposed verdict for a hypothesis by its pre-registered decision rule.

A hypothesis may carry `rule` (`{metric, op, threshold, n_min, basis}`: the
refutation condition written before the field, like `revise_if`) and
`observed` (`{k, n, artefact}`: k of n cases in a field artefact). When the
threshold is a share (strictly between 0 and 1), the engine computes the Wilson score interval
of k/n and proposes a verdict:

- `too_few`: n is below `n_min`;
- `refuted`: the whole interval lies on the refuting side of the threshold;
- `confirmed`: the whole interval lies on the holding side;
- `inconclusive`: the interval straddles the threshold; H stays `testing`.

`op` states when the hypothesis is refuted: `{metric: "доля 55+", op: "<",
threshold: 0.20}` is refuted if the share is below 0.20. The interval is
two-sided 95% and read on one side, so the proposal is conservative.

The verdict is a proposal (audit of 31.10, formal section 4, row 6; gate Ф В):
the record changes only after an `accept_result` sign-off by a human.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

# The 0.975 quantile of the standard normal distribution: a 95% interval.
Z95 = 1.959963984540054

Outcome = Literal["too_few", "refuted", "confirmed", "inconclusive"]


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """The Wilson score interval of the proportion k/n, without continuity
    correction (Wilson, E. B. (1927). Probable inference, the law of
    succession, and statistical inference. *Journal of the American
    Statistical Association*, 22(158), 209-212). For k = 81, n = 263 it gives
    0.2553 to 0.3662, the Wilson-score value of Newcombe, R. G. (1998).
    Two-sided confidence intervals for the single proportion: comparison of
    seven methods. *Statistics in Medicine*, 17(8), 857-872. Ends are clamped
    to [0, 1] against rounding."""
    if n < 1 or not 0 <= k <= n:
        raise ValueError(f"need 0 <= k <= n and n >= 1, got k={k}, n={n}")
    p = k / n
    zz = z * z
    denom = 1 + zz / n
    centre = (p + zz / (2 * n)) / denom
    half = z / denom * math.sqrt(p * (1 - p) / n + zz / (4 * n * n))
    return max(0.0, centre - half), min(1.0, centre + half)


def _sides(op: str, t: float, low: float, high: float) -> tuple[bool, bool]:
    """(the whole interval refutes, the whole interval holds) for the
    refutation condition `share <op> t`."""
    if op == "<":
        return high < t, low >= t
    if op == "<=":
        return high <= t, low > t
    if op == ">":
        return low > t, high <= t
    if op == ">=":
        return low >= t, high < t
    raise ValueError(f"unknown op '{op}'")


@dataclass(frozen=True)
class Verdict:
    outcome: Outcome
    k: int
    n: int
    low: float
    high: float

    @property
    def share(self) -> float:
        return self.k / self.n


def is_share(rule: dict[str, Any]) -> bool:
    """A rule whose threshold is a share strictly between 0 and 1: the only
    kind with a verdict (no share is below 0 or above 1)."""
    t = rule.get("threshold")
    return isinstance(t, (int, float)) and 0 < t < 1


def propose(rule: dict[str, Any], observed: dict[str, Any]) -> Verdict | None:
    """The proposed verdict, or None when the threshold is not a share."""
    if not is_share(rule):
        return None
    k, n = observed["k"], observed["n"]
    low, high = wilson(k, n)
    outcome: Outcome
    if n < rule.get("n_min", 0):
        outcome = "too_few"
    else:
        refutes, holds = _sides(rule["op"], rule["threshold"], low, high)
        outcome = "refuted" if refutes else "confirmed" if holds else "inconclusive"
    return Verdict(outcome, k, n, low, high)


def of_hypothesis(h: dict[str, Any]) -> Verdict | None:
    """The proposed verdict of a hypothesis with `rule` and a consistent
    `observed` (k <= n), else None."""
    rule, obs = h.get("rule"), h.get("observed")
    if not rule or not obs or obs["k"] > obs["n"]:
        return None
    return propose(rule, obs)


# What a proposal says against the recorded status: the opposite result.
CONTRADICTS = {"confirmed": "refuted", "refuted": "confirmed"}


def rule_line(rule: dict[str, Any]) -> str:
    """`доля 55+ < 0.2` with `, n >= 30` when n_min is set."""
    line = f"{rule['metric']} {rule['op']} {rule['threshold']:g}"
    return line + (f", n >= {rule['n_min']}" if "n_min" in rule else "")


def verdict_line(v: Verdict) -> str:
    """`12/40 = 0.30, Wilson 95% 0.18-0.45`."""
    return f"{v.k}/{v.n} = {v.share:.2f}, Wilson 95% {v.low:.2f}-{v.high:.2f}"
