# Red lines

A red line is an absolute value that a stakeholder sets and data check: a threshold (a number) or yes/no (the case owner 26.10). Its term is matched to the pace of its tier. This file gives the fields that record a red line, its value and what the data gave (gates ИИ1 Б and КЛ1 В, 31.10.2026). The other element fields are in `docs/data-model.md`, and the checks in `docs/checks.md`.

## Which elements are red lines

- An element with `red_line: true`, on any profile. It cannot be a kind the profile flags `light_off`: notes on every profile, and facts and signals on the default profile.
- An `algedonic_channel` with a `threshold` or a `line`, on `management-four-boards` (BEER1972 Гл. 17).

## `line`: the value and its term

```yaml
- id: rl-unsold
  board: oo
  kind: standard
  red_line: true
  line: {metric: "unsold dough, share of the night's volume", unit: "%", max: 5,
         since: "2026-03-01", until: "2027-02-28", recovery_days: 14}
```

| Field | Meaning |
|---|---|
| `metric`, `unit` | what is measured, and in what (text) |
| `min`, `max` | the corridor: a number on either end, or on both. One end alone makes a one-sided line |
| `expect` | the yes/no line: `true` or `false`, what the data must show; it needs `metric` (the schema refuses `expect` without it) |
| `since` | the date the line takes force. When it is absent, the line is in force from the record's `date`. It may lie after the record's `date`: a line set for the future |
| `until` | the date the line ends; required |
| `recovery_days` | how many days a value may stay outside the line before it counts as a breach |

A line is a corridor or a yes/no. Both at once is an error, and so is neither. `min` must be below `max`, and `until` after the start. On an `algedonic_channel`, the channel's own `recovery_time` stays: when both are set they must be equal, and the breach rule reads `line.recovery_days`, else `recovery_time`. The free-text `threshold` remains for records written before `line`. The hint `red-line-without-value` is satisfied by either.

## `observed`: what the data gave

```yaml
  observed:
    - {value: 4.2, date: "2026-04-30", source: s7}
    - {value: 6.8, date: "2026-05-31", source: s8}
```

`value` is a number for a corridor and `true` or `false` for a yes/no; any other type is an error. `source` is a manifest id. With a manifest, an unknown id is an error and a source not of kind `field_artefact` gets a warning, as for hypotheses. `observed` needs a `line`. One observation per date: two observations with the same date get a warning. Observations dated before the line takes force are not read, and a warning names them.

## The breach rule

The rule is in `src/smd_engine/redline.py`, and it gives the same answer for the same record:
1. Read the observations dated from the line's start (`since`, else the record's `date`) to `until`, sorted by date. Earlier ones get a warning; later ones are reported by `red-line-expired`.
2. A value is outside when it is below `min`, above `max`, or differs from `expect`.
3. Each run of consecutive outside values spans from its first date to the date of the next inside value. When no inside value follows, the run is still open. It spans to the record's `date` when that is later than the last observation, and otherwise to the last observation. It never spans past `until`. Beer's recovery time runs from the deviation to now, not to the last reading.
4. A run whose span in days is longer than the recovery time is a breach. With no recovery time, every run is a breach.

The hint `red-line-breach` lists each breach with its dates, and `smd status` lists the red lines with a breach. Observations dated after `until`, or a record dated after it, get `red-line-expired`: "the line ended on <until>: renew or drop". `red-line-outlives-pace` names a line in force longer, in years, than the `pace` of an element it is linked to. The span is `until` minus `since`, or minus the record's `date` when there is no `since`. Linked means the line itself, the elements it is `in` or that are `in` it, `performed_by` either way, or a relation of any kind either way. The procedures act in `procedures/field-result.md` §5 and `procedures/functional-plan.md` §4.

## On the pages

The page, the Markdown digest, the index, the graph details and the frames details show the line in words. An example in Russian: «красная линия: доля ФОТ от 18 до 25 %, с 01.01.2027 по 31.12.2031, восстановление 90 дней». A line with no `since` reads «по 31.12.2031». Numbers are written in plain digits, never in scientific notation. In Russian the thousands are set off by a thin space and the decimal mark is a comma («1 000 000», «2,5»). The pages also show the last observation, «наблюдено: 27 % на 01.03.2027, вне коридора»; for a yes/no line it ends in «соблюдается» or «нарушено».
