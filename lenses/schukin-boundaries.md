---
id: schukin-boundaries
title: Why the work is cut here - five grounds, four families of change, capability probes
version: 0.1.1
source: "Schukin, talk of 15 Oct 2026 'Онтология ИИ и предпринимательская ситуация' (program 'Третья ступень'), written text; l.N = line N of that text. Boundaries l.24, 87-98; probes l.136-144; T0-T3 l.50-51, 153-154. The T0-T3 scheme is joint work with Girenko and Flyamer (l.3)."
route: smd
offered_by: [functional-plan]
---

# Why the work is cut here

A function boundary, a department, a profession or a hand-off formed in the history of human activity and reflects the limits of its carrier: "learning time, limits of attention and memory, cost of coordination, design of tools, distribution of authority" (l.24). The source's claim is that when the carrier of intellectual capability changes, the reasons for a cut change, so each inherited cut needs fresh justification (l.91). The lens asks that justification of a cut in the group's own frame, then asks how the cut could change, and how to test that a redrawn circuit still does its work.

Everything below is the source's working construction, which it hedges throughout. In the record the lens produces candidates and hypotheses, not findings.

## When to use

- In `functional-plan` section 6 (candidate moves), when two functions in the new frame sit next to each other and the group (or the AI visionary) is about to merge, split or keep them, or when the frame is said to "automate" or "add AI to" a chain without saying why the chain is cut as it is. The procedure already names the four families and the five grounds; this lens asks them as questions 1-8 and supplies the grounds a `respecify` move needs.
- In `functional-plan` section 7 (hypotheses for unchecked links), for the capability probes, questions 9-13.
- When an element claims a capability (a class of actions done under conditions) and nobody has said what it depends on.
- Not for naming the firm's legal and organisational boundaries or the boundary of "we": that is the small-situation question about the three boundaries of a firm (l.115-116), asked in `small-situation`.

Run the cut questions (1-8) on one boundary at a time. Run the probe questions (9-13) once a candidate circuit exists. Question 14 is optional, once per record.

## Questions

Cuts and their grounds (l.25, 87-90):

1. Which cut is it? Name the two functions (or positions) and what passes between them: a document, a state, a decision, a part. If nothing passes, it is not a boundary yet (the engine's rule of thumb).
2. Why is the work cut here? For each of the five grounds, say whether it produced this cut and whether it still applies for the carrier the group now has in mind (unchanged, weaker, stronger, not known):
   - specialisation gain;
   - coordination cost of rejoining the divided work;
   - the carrier: limited memory, attention and time, years to train, and the rebuilding of context at each hand-over, which "affects both the size of the working unit and its lifetime";
   - tool design: a tool can merge work or deepen specialisation;
   - norms: independent verification, separation of authority, safety, liability. Norms can require a separation even when one system could do all the work.
3. Where does the cut give a productive effect, and where does it only carry the cost of the hand-over? Which hand-over exists only because of the old carrier's limits?
4. Which boundary must stay for independent verification or responsibility? Name the norm and the position that carries it.
5. Which of four families of change describes the proposal (l.96)?
   1. the old cut stays, the operations get cheaper;
   2. functions merge or are re-split differently;
   3. a specialised unit lives only for a task;
   4. the executive boundary disappears while the normative one (right, control) stays or moves.
6. If work moves into a shared state (family 2 or 4), which error in the initial model would now reach every later step? What independent check is needed: other sources, another method, other criteria, the power to reject? Three checkers with different names but the same model and data are one checker (l.95, 144).
7. Do-not-equate checks (l.97-98): (a) an agent performing an operation shows a technical possibility, not a position; (b) a change of staff is not a change of the normative place; (c) the number of agents is not the number of functions.
8. For each ground marked "weaker", does another ground (usually norms) still require the cut? A weaker ground lets the cut move. A ground that still applies keeps the cut, or requires it to be redrawn. The source says norms can require a separation (l.90); that this decides every case is the engine's reading **(own extrapolation)**.

Capability and probes (l.72-73, 136-144):

9. Name the capability: a reproducible ability to do a class of actions under stated conditions. Name the circuit that reproduces it: carriers, memory, state, tools, feedback, criteria, rights to act, essential external dependencies (l.141). One capability can rest on different combinations (l.72).
10. For each external dependency (electricity, an outside service, a permit, internal memory): is it a member of the circuit or only a condition of it? Analyse property, authority and coordination separately (l.143).
11. Substitution probes (l.142). For each, what do we expect to see, and what result would make us revise?
    - replace the AI model;
    - change a data source;
    - remove long-term memory;
    - move a tool to another executor.
12. Independence probe (l.144): do the "independent" agents or checkers repeat one error? How would we see it? (Seeding a known error and seeing who catches it is the engine's example, not the source's.)
13. Is this combination a candidate or a verified capability? Time to a candidate differs from time to a verified capability (l.73, 103). A generated variant is a hypothesis until it is tested (l.59, 73).

Organisation of the unit (optional, l.50-51, 153-154):

14. Which of T0-T3 does the unit of activity resemble today, and which does the proposal assume? Treat the answer as a hypothesis:
    - T0: the craft wholeness of thinking and action;
    - T1: industrial slicing of operations, stable human carriers, hand-offs;
    - T2: a hybrid contour in which human and technical means are designed together;
    - T3: a research perspective of machine-scaled organisation, with the internal cut set by task, tools and checks and human places set by special grounds.
    The order is not a proof of necessity (l.51), and T3 is itself a hypothesis.

## Output slots

Every element carries `lens: schukin-boundaries`. AI wording carries `voice: ai` and `epistemic: hypothesis` until the group accepts it.

| Answer | Element kind / board / field |
|---|---|
| 1: the cut and what passes | the two `function` elements already in the frame; the hand-over is a `flow` relation between them (relations carry no `lens`; tag the note below) |
| 2, 3, 8: the five grounds for this cut, ground by ground, with the ones that changed | `note`, `oo`, `in` the frame, `seen_from` the position that does the assessing; `refers` relations to the two functions |
| 4: a norm that keeps a separation | `standard`, `oo`, `seen_from` the position that carries it |
| 4, 6: no position has the power to reject, or no different method exists | `gap`, `oo`, `of: position` (or `of: method`) |
| 5, family 1 | a `note` only; no change on the board |
| 5, family 2 | `function` elements for the merged or split functions, `in` the frame, with no `performed_by` until the human names the performer; `move: {op: respecify, from: [...], via: "<grounds>", status: candidate}` |
| 5, family 3 | a `function` whose label states the task and the lifetime; `epistemic: hypothesis` |
| 5, family 4 | the merged `function` plus the `standard` that stays; the move as in family 2 |
| 7: a thing that does an operation but occupies no position | `function` with no performer shows as a hint ("functions no one performs"); do not create a `position` for it |
| 9: the capability and its circuit | `concept`, `oo`, label names the capability; circuit parts are `function`, `standard` or `note` elements `in` it |
| 10: a dependency that is not a member | `place_for_others`, `od`, if another party controls it; otherwise a `note` on `oo` |
| 11, 12, 13: probes | a hypothesis in `hypotheses`: `assumes` (the capability survives), `action` (the substitution), `observe`, `revise_if`, `targets` (the tagged elements), `lens: schukin-boundaries`. The result goes through `field-result` and an `accept_result` sign-off |
| 14: T-level | a `model` on `oo` for the scheme, `epistemic: hypothesis`; the classification itself as a hypothesis `assumes: "unit X is organised as T2"` |

Example in the invented bakeries case (not from the source): the boundary between dough production and night logistics.

```yaml
- {id: n-b1, board: oo, kind: note, in: [f-new], seen_from: p-organiser, voice: ai,
   epistemic: hypothesis, lens: schukin-boundaries,
   label: "dough | logistics: cut held by the carrier (one night shift cannot do both); tool ground unchanged; norm ground: none stated"}
```

with `refers` relations from `n-b1` to `fn-dough` and `fn-logistics`, and a hypothesis whose action is "run one night with logistics planned from the dough plant's own order state".

## Limits

- The source is a polished written text with no discussion. Its claims are marked by the author as hypotheses or a working construction. The lens does not raise them to findings.
- The five grounds are the source's list (l.88-90). The source does not say the list is complete, and it gives no scoring rule. "Score each ground and mark which one changed" is this lens's way of using the list, not Schukin's procedure.
- The four families are the source's (l.96). Mapping merge, split and the vanishing executive boundary to the structural move `respecify` is the engine's choice (see `functional-plan`), not the source's.
- The source says the old cut "requires new justification" (l.91). It does not say that a merged cut is better, and it warns that merging creates a new verification boundary (l.95). The source gives no example of one operator passing across several domains and does not say such a pass is better; it says each cut must be re-derived from the five grounds.
- The five probes (questions 11 and 12) are the examples the source gives for testing a circuit (l.142-144). That they form a complete battery is not claimed by the source. The thresholds (how many changes a circuit must survive) are not given.
- "Dependency versus membership" (question 10) is the source's distinction (l.143). Which items count as which is for the group to decide.
- T0-T3 is a periodization from joint work (l.3, 50-51, 153-154). The source gives only short descriptions of each level. The source supplies no test that assigns a unit to a level.
- The source offers no numeric human scale (span of control, team size, number of seats). The lens does not compute one.
- Unverified: whether the five grounds hold outside production-type work (the source's running example is a network of production capacities of different owners, l.56-57).
