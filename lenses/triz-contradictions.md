---
id: triz-contradictions
title: TRIZ route for a contradiction inside an object
version: 0.1.1
source: ARIZ85V parts 1-3, 6, 7, 9 and table 2; ALT1975; ALT1979; GP-Guide9 for the SMD route (docs/method/triz-systems.md section 6, docs/method/reconciliation.md section 8)
route: triz
offered_by: [problematization, functional-plan]
---

# TRIZ route for a contradiction inside an object

Source keys are those of `docs/method/sources.md`. Marks: **[V]** read in the primary text, **[ANALYSIS]** the engine's own reading or extrapolation, **[UNVERIFIED]** not found in a primary text. Examples use the invented bakeries case.

This lens takes a contradiction that sits inside one object and works it with the technique of Altshuller's ARIZ-85В: write the contradiction as a pair, push it to the limit, find where and when it acts, list what is at hand, state the result that would need nothing new, and separate the conflicting demands. It is a different route from the SMD one. A session must say which it takes (`reconciliation.md` section 8, [ANALYSIS]).

## When to use

Where it is offered: `problematization` section 6 (the procedure flags a problem as a contradiction inside the object and writes no TRIZ terms itself; the lens then runs as a separate pass on that problem) and `functional-plan` section 6 (a function that must carry two opposed demands). `solo-session` has no step of its own for it and inherits these two.

Offer it when all of these are true:
1. The difficulty is a conflict between two demands on one thing: improving one property spoils another (a technical contradiction, ТП), or one part must be in two opposite states (a physical contradiction, ФП) [V ARIZ85V-1, ARIZ85V-3].
2. The object, its parts and its function can be named, so that an operative zone and time can be found.
3. The group wants a solution that changes the object with the fewest additions, not a new concept of the object.

Do not offer it, and use the SMD route instead (`positional-construction`, ontology record), when the paradox is between two positions' representations of the same object. GP treats a paradox of two justified, opposite statements as a problem to be resolved by changing means and concepts, a turn to the activity side [V GP-Guide9]. TRIZ resolves the contradiction inside the object by separation and resources [V ARIZ85V]. Which of the two fits a given paradox is [ANALYSIS]; ask the group and record the answer.

Write in simple words. The ARIZ notes ask for "simple, non-technical, even childish words", so that special terms do not add psychological inertia [V ARIZ85V-3].

## Questions

Step numbers refer to ARIZ-85В [V ARIZ85V]. Ask them in order; skip none without saying why.

0. Which route are we on? Is the paradox inside one object, or between two views of it? If between views, stop and hand over to the SMD route.
1. What is the system, what is it for, and what are its parts? What do we want to obtain "with minimal changes"? (1.1)
2. Write the two forms of the contradiction. TP-1: "if we do A, we gain X but lose Y." TP-2: "if we do not do A (or do the opposite), we gain Y but lose X." (1.1)
3. Name the conflicting pair: the thing that is made or changed (the product) and the means that acts on it (the tool). The reading of product and tool for an organisation, as the output and the arrangement acting on it, is [ANALYSIS]. (1.2)
4. Which of TP-1 and TP-2 serves the main purpose of the system better? Take that one. (1.4)
5. Push the chosen contradiction to its limit: what if A were done fully, or not at all? Write the extreme version. The notes record only the step title, so the wording of the intensification rule is [UNVERIFIED]. (1.5)
6. Where exactly does the conflict act (operative zone), and during which interval (operative time)? Which part of the organisation, which process step, which hours or seasons? (2.1, 2.2)
7. What is already available in the zone and the time, and in the system around it, that costs nothing new: people, spaces, hours, money flows, information, rules, contracts, other participants' idle capacity? The list of organisational resource kinds is [ANALYSIS]; ARIZ speaks of substance-field resources (ВПР). (2.3)
8. State the ideal final result: "the X-element, without making the system any more complex and without harmful effects, removes the harmful action during the operative time within the operative zone, while the tool keeps its useful action." Then strengthen it: no new elements, only the resources from question 7. (3.1, 3.2)
9. State the physical contradiction: during the operative time the zone must be in state X to do one thing and must not be (or be in the opposite state) to do the other. (3.3)
10. Could the zone itself, in its time, supply the opposite state with no outside help? (3.5)
11. Try the three separations [V table 2; the grouping of the three is the engine's, reconciliation.md section 8]:
    - in space: the demands apply in different places;
    - in time: they apply at different moments;
    - at system level: the whole has property C and its parts have the opposite (the whole is large, the parts are small).
    For each, say what it would mean here, or why it does not apply.
12. If no separation works inside the system: restate the mini-problem for the system above it. What is the supersystem here, and what does the contradiction look like from it? Repeat upward if needed. (6.4) Altshuller's laws of system development list the transition to the supersystem as a regular direction [V ALT1979].
13. Check the chosen resolution: does it need a new element? If yes, can that need be met from the resources of question 7? (7.1)
14. After the solution: how did the real course of thinking differ from this order, and what new principle, if any, did the group use? (9.1, 9.2)

## Output slots

Every element carries `lens: triz-contradictions` and `seen_from` the position whose contradiction it is. `voice` is as spoken: `group`, or `AI` where the model wrote the wording. `epistemic` is `hypothesis` for a resolution and `stated` for the group's own contradiction. The record has no `route` field (see Limits); the lens id on each element is what marks the route.

| Question | Element kind | Board | Fields |
|---|---|---|---|
| 1 mini-problem | `note` | `oo` | label "mini-problem: ..." |
| 1 useful action to keep | `function` | `oo` | `in: [<frame>]` |
| 2 TP-1, TP-2 | two `note`s | `oo` | labels "TP-1: ...", "TP-2: ..."; relation `{kind: opposes}` between them |
| 3 pair | named in the TP labels | | no separate element |
| 4, 5 chosen and intensified contradiction | `note` | `oo` | label "intensified: ..."; relation `refers` to the chosen TP note |
| 6 operative zone and time | `situation` | `s`, `half` where it acts | label begins "operative zone and time: ..." |
| 7 each resource | `fact` | `s`, same `half` | `in: [<zone>]`; `epistemic: unverified` until checked; `cites` if sourced |
| 8, 10 ideal final result | `goal` | `od` | label begins "IFR: ..." |
| 9 physical contradiction | `note` | `oo` | label "PC: ..."; relation `refers` to the zone |
| 11 resolution by separation | `model` | `oo` | label begins "resolution by separation in space / time / system level: ..."; `epistemic: hypothesis` |
| 12 supersystem restatement | `frame` | `oo` | `frame_state: new`; label begins "supersystem frame: ..." |
| 13 a new element is unavoidable | `gap` | `od` | `of: means` (or the block it is missing from) |
| 14 reflection | thesis, `kind: statement`, `belt: m` | | `lens: triz-contradictions`; `voice` as spoken |

How the resolution is recorded:
- The resolution is the `model` element of question 11, or the new `frame` of question 12. It stays a hypothesis until tested.
- Test it in the field as a hypothesis (`hypotheses` list, `targets` the model, `lens: triz-contradictions`).
- The group accepts the resolution by an `accept_move` sign-off if the element carries a `move`, and by a hypothesis result with an `accept_result` sign-off after the field test.
- Set `move` on a resolution only if the group names it, or the model reads it, as one of the four structural moves (`adjoin`, `rescale`, `respecify`, `glue`), with `status: candidate` for a reading. A separation is not one of the four, and no mapping from separations to moves is claimed here.

Example (invented bakeries case):
- TP-1: "if each bakery makes its own dough at night, it controls freshness but carries a night shift that costs a large part of its payroll."
- TP-2: "if one plant makes dough for all, the night shift cost falls but each bakery loses control of timing."
- Operative zone and time: the dough step, between closing and the morning bake.
- Resources: the mills' night operation, the bakeries' idle ovens by day, the delivery routes already running.
- Separation at system level: the whole network is large (volume for the mills) while each bakery stays small and independent.

## Limits

- ARIZ is, in Altshuller's words, "first of all a tool for solving concrete technical problems" [V ALT1975]. That it works on organisational problems is [ANALYSIS], not shown. The one survey of practical TRIZ use outside engineering, including organisational and cultural obstacles, was read in abstract only [S ILE2013]; business-TRIZ schools are later adaptations whose claims were not verified.
- The items this lens takes over (pair format, intensification, zone and time, resources, ideal final result with no new elements, the three separations, supersystem shift, post-solution reflection) are the engine's selection from ARIZ [ANALYSIS, triz-systems.md section 6.6].
- Left out because they do not transfer as such [ANALYSIS]: the index of physical effects, su-field standards, the 39 physical parameters, micro-level transitions (steps 3.4 and 4 onward), phase and physico-chemical transitions (table 2). The 40 principles and the contradiction matrix are not used: the table cells were not verified, and the notes record names 24 and 38 only as [UNVERIFIED].
- The notes record ARIZ step titles. The exact rules inside a step (for example how to intensify at 1.5) were not reproduced, so this lens states them in the engine's words.
- Steps 6.2 and 6.3 (check whether the mini-problem hides several problems; take the other contradiction) exist in ARIZ and are not asked here. If question 11 fails, the facilitator may go back to question 4 and take the other contradiction; this is [ANALYSIS].
- GP held a seminar on inventive activity (ОДИ И-4, 1980) [V GP1983 list]; its content and any link to TRIZ is [UNVERIFIED].
- The data model has no `route: smd | triz` field. `reconciliation.md` section 8 says a resolution records its route; until the schema has the field, the route is read from the `lens` id of the elements. Adding the field is a schema decision for the owner.
- Answers are the group's. A model that fills the pair or the resources from its own knowledge marks them `voice: ai`, `epistemic: hypothesis`, and does not treat an unlisted resource as available.
