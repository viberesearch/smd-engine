---
id: schukin-interface-tax
title: Interface-tax audit of human touchpoints, with achievement and balancing metrics
version: 0.1.1
source: "Schukin, talk of 15 Oct 2026 'Онтология ИИ и предпринимательская ситуация' (program 'Третья ступень'), written text; l.N = line N of that text. Interface tax l.74, 99-101, 199-200; human judgment and the formal approver l.205; capability and mandate l.201; metrics l.211-214, 216-218."
route: smd
offered_by: [small-situation, visionary-tract, functional-plan, theses-to-board, qualification-pass, reflexive-protocol]
---

# Interface-tax audit

The interface tax is the cost of translating machine state (tests, programs, dependency graphs, constraint models) into human reports and back: delay, lost detail, fewer trials (l.74, 99-101). The source's audit rule: name the function of each human touchpoint. A touchpoint with no function is old paper-forwarding. A touchpoint with a function cannot be removed without losing verifiability (l.100-101, 199-200).

The lens has two parts: the audit (questions 1-7) and the metrics that say whether a redesigned circuit is better (questions 8-10). Question 11 applies the audit to this engine's own sign-offs.

## When to use

- In `functional-plan` section 6, after `schukin-boundaries` has proposed a merge or a shared state: the human touchpoints that remain are the ones to audit (questions 1-10). Also when a chain adds approvals, reports or reviews around AI work, or is criticised for slowing down at its hand-offs.
- Question 11 alone, before the procedure lists the sign-offs it will request: `small-situation` section 7, `visionary-tract` section 10, `theses-to-board` section 5, `qualification-pass` section 6 and `reflexive-protocol` section 6. Each of these procedures already says that a request that changes nothing is not made; question 11 is the check behind that rule. `solo-session` repeats the rule and inherits the lens from its steps.
- Not when the process has no human step to audit, or no machine side whose state must be translated. Then there is no interface and no tax.

## Questions

Audit (l.99-101, 199-200, 205):

1. List the human touchpoints in the process: where a person reads a report, approves, signs, receives a document or forwards one. For each, say which way it runs: machine state into a human report, or a human instruction into machine work.
2. For each touchpoint: what does the person do here that the next step cannot do without? Name the function. The source's examples of functions that justify a human presence are: critique of premises, sanction of irreversible acts, responsibility, re-posing goals. Another named function is allowed; mark it as the group's own.
3. If no function can be named, it is paper-forwarding: the person only passes on or re-types. What state would the next step use directly if the hand-over were removed? What would disappear with it: the translation, the delay, the loss of detail?
4. If a function is named: what would be lost if the touchpoint were removed? Name what becomes unverifiable, and who or what could verify it instead, by a different method, from independent data, with the power to stop (l.95, 144).
5. Does the person at the touchpoint have access to the grounds (the underlying state, tests, data), or only to a report? A formal approver without access to the grounds keeps the authority and loses the judgment (l.205). What would give access?
6. What does the translation cost here: delay, lost detail, fewer trials? Say it in the session's own terms. Do not supply figures the session did not give.
7. Capability is not mandate (l.201): who has the right to act at this point, and is this touchpoint where that right is exercised or passed on?

Metrics (l.211-214, 216-218):

8. Achievement metrics: what should rise if the new circuit is better? The source's list: resources per reproducible result; the class of operations that becomes accessible; quality; reliability; scale; cost and time to master a new variant of a task; reuse; change in next-cycle productivity.
9. Balancing metrics: what must not fall while the achievement metrics rise? The source's list:
   - does testing confirm a function before it is used commercially;
   - does a change of AI model keep the ability to meet an obligation;
   - which supplier changes void a guarantee;
   - where is a new human decision or a recognised verification still needed;
   - can a configuration be abandoned while the results are kept.
10. After the audit, count the touchpoints and the checks that remain. Does the added coordination erase the advantage (l.218)?

This engine:

11. For each sign-off the procedure is about to request (`close_k`, `accept_move`, `accept_thesis`, `accept_result`, `verify_record`): what status does it license, and does the target stand in the state the sign-off licenses? Is the record already in that state, so that the sign-off changes nothing? A request that changes nothing is paper-forwarding and is not made.

## Output slots

Every element carries `lens: schukin-interface-tax`. AI wording carries `voice: ai`; claims about a real process are `epistemic: hypothesis` until the group confirms them.

| Answer | Element kind / board / field |
|---|---|
| 1, 2: a touchpoint with a named function | `function`, `oo`, `in` the frame, `performed_by` the position that acts; label states the function; a `flow` relation from the machine-side function to it |
| 3: a touchpoint with no function | `note`, `oo`, `epistemic: hypothesis`, label "touchpoint with no stated function: ..."; optional candidate `move: {op: respecify, from: [...], via: "next step reads the state directly", status: candidate}` |
| 3, 4: a hypothesis that the touchpoint can go (or must stay) | hypothesis: `assumes` ("touchpoint X has no function"), `action` (skip it on a sample or run once without it), `observe`, `revise_if` ("a defect is found only there"), `targets` (the tagged element), `lens: schukin-interface-tax` |
| 4: nothing else could verify | `gap`, `oo`, `of: position` or `of: method` |
| 5: the person sees only a report | `gap`, `oo`, `of: means`; the missing access is the means |
| 6: cost of translation | said in the label of the touchpoint, or in the `note`; no new field |
| 7: where the right to act sits | `standard` or `place_for_others` as in `schukin-boundaries`; the position that exercises it in `seen_from` (or `performed_by`, on a function) |
| 8: achievement metrics | `goal`, `od`, `seen_from` the position that wants the rise (the format has no metric kind; this mapping is the engine's **(own extrapolation)**) |
| 9: balancing metrics | `standard`, `oo`; a condition that must stay true (same mapping) |
| 10: advantage erased by coordination | `note`, `oo`, `epistemic: hypothesis` |
| 11: sign-offs to request | in the procedure's hand-over message, then `signoffs` by a human. The lens writes no sign-off |

Example in the invented bakeries case (not from the source): the owner reads a weekly order summary before the plant bakes.

```yaml
- {id: n-t1, board: oo, kind: note, in: [f-new], seen_from: p-owner, voice: ai,
   epistemic: hypothesis, lens: schukin-interface-tax,
   label: "weekly order summary read by the owner: no stated function"}
```

If the owner then names a function ("I refuse orders above the plant's capacity"), the note becomes a `function` with `performed_by: p-owner`, and question 5 asks whether the summary shows the capacity.

## Relation to the engine's sign-offs

`docs/data-model.md` requires each sign-off to state its function. That is the engine's own application of the audit to its records, not something the source says about records. In the source, the audit is about human touchpoints in an organisation's work with machine state. The reading below is the engine's:

| Sign-off | The function the audit finds |
|---|---|
| `close_k` | licenses `status: closed` on a qualification |
| `accept_move` | licenses `move.status: accepted` |
| `accept_thesis` | licenses a thesis `status: refined` |
| `accept_result` | licenses a hypothesis `confirmed` or `refuted` |
| `verify_record` | licenses a record `status: verified` |

- Each licenses a change of status that an AI voice may not make. That is the function: without it the record could not tell the group's decision from the model's proposal. This is the verifiability the source says is lost when a function-bearing touchpoint is removed, applied by analogy.
- The audit's question 5 corresponds to the sign-off's `note` and `cites` fields: the grounds the person looked at. The engine asks for them to guard against a formal approver without access to the grounds. The source does not say a sign-off needs a note.
- The validator already warns about a sign-off that changes nothing. That is the engine's check for paper-forwarding.
- Rule 4 of `roles/README.md` (agreement between roles is not verification) follows the source's condition for a separate verifier: a different method, independent data and the power to stop (l.95, 144).

## Limits

- The source states the audit rule in a sentence or two (l.100-101, 199-200) and gives no worked audit and no list of admissible functions beyond the four examples. The questions are an expansion of that rule. Questions 3-7 are this lens's, built on it.
- The source does not quantify the tax. It names delay, lost detail and fewer trials as its forms (l.74, 99-101). Any measurement is for the group to define.
- "Cannot be removed without losing verifiability" is the source's claim about touchpoints that have a function. It is not tested here; the removal hypothesis in the slots is the engine's way to test it.
- The metric lists (questions 8 and 9) are the source's, given as examples for a venture to test, not a standard set. The source adds that excess coordination can erase the advantage (l.218) but gives no measure.
- The source's human functions concern organisations working with machine state. Applying them to a thinking-session record and its sign-offs is an extrapolation, stated above.
- The mapping of metrics to `goal` and `standard` is the engine's; no source or format entry defines a metric kind.
- Unverified: whether the four named functions are the only ones the source accepts. The text lists them as examples.
