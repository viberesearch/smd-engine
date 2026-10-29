---
id: khaprov-ontology
title: Three scales, the ontology test and managing not-knowing
version: 0.1.0
source: "Khaprov, expert lecture on the entrepreneur as organizer of complexity, program day 4, read through a local digest of the automatic transcript and the Q&A file (digest sections 2.4, 3, 4 items 3-4 and 11, Q&A 6, 8 and 9; the digest is not in the repo); reconciliation of the test with the classic method: docs/method/reconciliation.md section 2 (GP1981)"
route: smd
offered_by: [small-situation, visionary-tract, positional-construction, problematization, qualification-pass]
---

# Khaprov: scales, ontology test, not-knowing

A lens for the step "view of oneself" and for the ontology records of a case. It asks at which scale the group works and which scale its target needs, what the group says it makes and what competes with it, and what the group does not know. Output goes to the `ontology` list of the record (fields `object`, `valid_for`, `subjects`, `competes`, `test`) and to a few elements.

Terms are Khaprov's, from a lecture heard through an automatic transcript. Items marked **[unverified]** must be checked against the recording or slides before being quoted.

## When to use

- At step 5, "view of oneself", of `visionary-tract`, as the grain options of the `rescale` move (questions 1-4).
- In `positional-construction` section 5, when two or more positions describe one object differently and the group wants one record of what is built and for whom (questions 5-11). The procedure already names the ontology test for `competes`.
- In `small-situation` section 2, only question 1 (the scale the group works at), and only if the human is unsure of it. The answer goes into the label of the fragment element; the procedure writes no other element from this lens.
- In `problematization` section 2, questions 12-14, when a difficulty may be a wrongly posed problem. The output is a thesis, not new board elements.
- In `qualification-pass`, as questions behind a K, with no elements written: criterion C7 (scale and the reason for the concept) takes questions 1-4; the realizability row takes questions 9-11. The K text names the lens id.
- When the group says "our competitors" without saying what competes.
- Do not use it to decide which ontology is true. The engine's reading, from the classic method, is that a picture is checked for realizability in activity, not for truth (docs/method/reconciliation.md section 2). Khaprov's own position is stronger: a wrong ontology is fatal. Reading "fatal" as "fails the realizability test" reconciles them, but that is the engine's reading **(own extrapolation)**; Khaprov does not say it.

## What the source gives

**Scale (масштаб).** Measured by the complexity handled, not by headcount. Three scales, illustrated with aircraft:

| Scale | Name | What the source says |
|---|---|---|
| 1 | a technical object | a single product; Khaprov says most firms in his context make objects at this scale |
| 2 | a production ecosystem | a flow of products with the components and suppliers behind it; suppliers need to be sound well before serial production starts |
| 3 | the market around the product | suppliers, sales and after-sales, operators, infrastructure; entering means facing a large organization with a few people; needs alliances, accumulated volume, infrastructure, investment and state policy |

- "People go to scale 3 with products of scale 1 and with money for that product."
- The move he names is from the level of the object to the level of the mega-system.
- Aircraft numbers and market sizes in the lecture are ASR figures **[unverified]**.

**Ontology.** What exists and what does not; "the world your enterprise, technology or project lives in"; the algorithm by which that world is arranged. Points the source makes:
- there are no systems without an ontology: the owner may not know it, but it exists;
- ontologies can be mixed: objects bought from one, management systems taken from another;
- groups can work in different ontologies without knowing it, with a risk of conflict;
- scope varies: a firm, an industry, a city, a civilization; a participant distinguished a "small" and a "big" ontology of a city, which concerns depth;
- the default failure is to repeat past experience;
- going into someone else's ontology is called a losing course except for very large actors **[unverified]**;
- the source gives no procedure for choosing or building an ontology.

**The ontology test.** The example: two phone makers; one decided it made a device for voice messages, the other an entrance to a digital universe. Their objects differ because their ontologies differ. A second example: aircraft do not compete (they have no bank accounts); corporations and consortia do. The test, as the engine reads it from these examples **(own formulation)**:
1. What do we say we make?
2. What does the competitor say it makes?
3. Do the objects differ because the ontologies differ?
4. Do objects compete here, or corporations and consortia?

**Managing not-knowing (управление незнанием).** A stage zero before knowledge management: "Do I have knowledge of all the levels of complexity I need? Maybe I formulate the problem wrongly?" The source says ontology-level thinking is hard for adults to learn, suggests a bridge through technical and mathematical language, and mentions AI simulators in which a founder loads projects, staff and tasks and gets variants of decisions. It gives no further method.

## Questions

Scale (view of oneself):
1. At which scale does the group work today: one object (one deal, one product), a production ecosystem, or the market around the product? Name the evidence, not the headcount.
2. At which scale does the target need to be worked? What does the target's market require that the group does not have: alliances, volume, infrastructure, investment, state policy?
3. If scale 1 means going to scale 3, who in the case carries the gap between them, and with what money and products?
4. What does the group see at each of the three scales that it did not see at the others?

Ontology test:
5. In one sentence: what do we say we make or do? Say it separately from each position that takes part (these become the subjects).
6. In one sentence: what does the nearest competitor say it makes?
7. Do the answers to 5 and 6 differ because of different pictures of the world, or only because of different features of the same object?
8. What competes with what here: the products, the firms, or groups of firms? Write it as a statement the group can reject.
9. For which set of positions is this picture valid? Which positions would reject it?
10. If several positions take part, through which cooperation is the common object built?
11. What would show, in activity, that the picture is not realizable? Name the action and the observation (this becomes the hypothesis behind `test`).

Not-knowing (stage zero):
12. Which levels of complexity (see `khaprov-levels`) does the group need to know, and for which does it know nothing?
13. Where might the problem itself be formulated wrongly? Which question would the group ask if it assumed that?
14. Which ontology is the group acting in without having named it? Is any management system or tool in the case taken from another picture?
15. What is the next step that reduces not-knowing the most, and who takes it?

## Output slots

Every element, thesis, hypothesis and ontology record it produces carries `lens: khaprov-ontology`; `smd compare` reads all four. The table applies where the procedure writes elements (`visionary-tract`, `positional-construction`). In `small-situation`, `problematization` and `qualification-pass` see "When to use".

| Answer | Kind, board, field |
|---|---|
| Scale at which the group works and the one the target needs (Q1-Q4) | `situation` on `s`, half `small`, `label` begins "view of ourselves at scale N: ..."; `move: {op: rescale, from: [<big situation>], via: "scale: object \| ecosystem \| market (Khaprov)", status: candidate}`; relate to the earlier small situation with `refers` (as the visionary tract specifies) |
| What the target market requires at the next scale (Q2, Q3) | `gap` on `od`, `of` set to the nearest scheme block; or `place_for_others` on `od` for an ally or supplier the case does not have yet |
| Ontological object (Q5-Q7) | `ontology.object`: one sentence, the common object |
| Each position's answer to Q5 | `ontology.subjects`: `{position: <position id>, subject: "<that position's answer>"}`; each position must be in `valid_for` |
| Set of positions the picture is valid for (Q9) | `ontology.valid_for`: ids of `position` elements |
| What competes with what (Q8) | `ontology.competes`: the statement, in the group's words if it gave them |
| Competitor's claim (Q6) | `note` on `oo`, `seen_from` the competitor's position if the case has one, else `epistemic: unverified` and no `seen_from`; or a `place_for_others` for the competitor if the case holds one |
| Cooperation (Q10) | `cooperation` element on `oo`; `ontology.cooperation` points to its id |
| Realizability test (Q11) | a hypothesis `H` with `assumes`, `action`, `observe`, `revise_if`; `ontology.test` points to its id |
| The picture in use, as a concept (Q5, Q14) | `concept` on `oo`, `seen_from` the position whose concept it is |
| Not-knowing (Q12, Q13) | thesis with `kind: question` or `problem`, `belt: m`, `lens: khaprov-ontology`; the hypothesis behind it, if testable, as an `H` |
| What is not known and where (Q12, Q14) | `gap` with `of` set; or `note` with `epistemic: unverified` when no scheme block fits |
| The next step against not-knowing (Q15) | `goal` on `od`, `seen_from` the position that takes it |

Example for the invented bakeries case (`cases/example/`): the record `O1` there has object "shared production as an asset owned by the bakeries that use it", `valid_for` the owner and the organiser, one subject per position, a cooperation element, a `competes` statement and the test `H1`. Use it as the shape of a finished record.

## Limits

- The source gives no procedure for choosing, building or comparing ontologies. The four-step ontology test is read from two examples; the source does not list it as steps **(own formulation)**.
- The source treats ontology as the algorithm of the world a firm lives in, with a right and a wrong one. The engine records it as valid for chosen positions and tested for realizability (GP1981). Neither is quoted as the other's position.
- "Subjects" per position (предметы) come from the classic method (GP-OP), not from Khaprov. The lens maps his "what do we say we make" onto them **(own extrapolation)**.
- The three scales are Khaprov's. They are a different axis from his seven levels; the source relates them only by example. The lens does not give a scale-to-level table.
- Scale is read from the evidence the group brings. The lens gives no thresholds.
- Managing not-knowing is a title and a first question in the source, not a method. The questions in the third group above are the engine's way of using it **(own extrapolation)**.
- Figures and company data in the lecture come from an automatic transcript and are not to be quoted without the recording.
