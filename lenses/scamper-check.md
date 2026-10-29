---
id: scamper-check
title: SCAMPER as a cross-check of the four structural moves
version: 0.1.1
source: Eberle (1971), SCAMPER, from Osborn's idea-spurring checklist (Applied Imagination, 1953); the four moves from Zharnikov (2026), doi:10.5281/zenodo.21653102 (docs/method/structural-moves.md); the mapping between them is the engine's
route: smd
offered_by: [visionary-tract]
---

# SCAMPER as a cross-check of the four structural moves

Marks as in `docs/method/triz-systems.md`: **[V]** read in the primary text, **[ANALYSIS]** the engine's reading, **[UNVERIFIED]** not checked against a primary text. Examples use the invented bakeries case.

SCAMPER is a checklist of seven prompts for generating variants of a product or idea. The four structural moves (`adjoin`, `rescale`, `respecify`, `glue`) are a small set of operations on a representation. This lens runs the seven prompts after the visionary tract to find candidates that the four-move pass did not produce. The mapping from prompts to moves below is the engine's interpretation, not a claim by Eberle, Osborn or Zharnikov. The method note on Zharnikov's paper (`structural-moves.md`) records no mention of SCAMPER **[UNVERIFIED]**; the paper itself was not searched for it here.

The route is `smd`: the moves act inside the classic chain of schematization and idealization (`reconciliation.md` section 9), and the check serves that chain.

## When to use

- After the visionary tract (`visionary-tract`, after step 6 and before the hand-over of section 10), when the human has selected at each step and the record holds accepted and rejected move candidates.
- When the four-move pass gave few candidates, or all of one move type, or when the human feels the options are narrow.
- Not before the tract: the check needs candidates to compare against, and a position and small situation to work from.

The check adds candidates only. It does not rank, does not test whether the four moves are complete, and does not replace the tract's steps. The paper's closure claim is made only where compatibility is decidable; a board is not such a domain, so the four moves are a menu there (`structural-moves.md`, limits).

## The mapping (engine interpretation)

Operators as listed in a local digest of an invention-method catalog (not in the repo): Substitute, Combine, Adapt, Modify (Magnify, Minify), Put to other use, Eliminate, Reverse (Rearrange). Eberle's own wording and the content of Osborn's list were not checked against the primary texts [UNVERIFIED].

| SCAMPER | Prompt | Counterpart | Reasoning [ANALYSIS] |
|---|---|---|---|
| Combine | what can be joined with what? | `glue` | A move only if a shared substructure can be named. The paper's glue is a pullback over a shared substructure, not a mixture, so "put A next to B" without the substructure is not a candidate. |
| Adapt | what else is like this; what can be borrowed from elsewhere? | `glue` | It starts from our object and looks for another domain, which is how the tract's step 3 works. The two operators differ in direction, not in kind of move. |
| Modify: Magnify, Minify | make it larger, smaller, more or less frequent | `rescale` | Change of size, frequency or grain maps to rescale. "Modify" in the sense of changing form, colour or meaning has no counterpart. |
| Reverse, Rearrange | do the opposite; change the order, the roles, the direction | `respecify` | Changing who depends on whom, or in what order, changes the admissible links. Reordering along a time axis may instead be `adjoin` if time was not on the picture. |
| Put to other use | other users, other purpose | `respecify` | The paper lists exaptation, a thing taking new admissible links, as an example of re-specifying [V, structural-moves.md]. |
| Substitute | what can be replaced: a participant, material, rule, place? | none as such | A substitution fills the same slot with another filler inside the same representation. It counts as `respecify` only if the replacement changes which links are admissible. |
| Eliminate | what can be removed or simplified? | none as such | The four moves construct; none deletes. The nearest case is `respecify` that identifies two elements kept apart, which removes one. Compare the "no new elements" demand of `triz-contradictions`. |
| (no operator) | what axis does the picture hold fixed? | `adjoin` | No SCAMPER prompt asks for a new axis (time, observer, scale). Osborn-style "Magnify" also asks what to add, which may produce an axis by accident [UNVERIFIED wording]. |

Summary: five of seven operators have a counterpart (Combine and Adapt to `glue`; Modify to `rescale`; Reverse and Put to other use to `respecify`); Substitute and Eliminate have none; `adjoin` has no operator. The check therefore tests `glue`, `rescale` and `respecify` well, and cannot test `adjoin`: candidates of that move come only from the four-move pass.

## Questions

Ask them of the AI visionary's material, with the human. Each question is answered from the record and the session.

1. List the candidates of the tract by move, accepted, rejected and still candidate. Which of the four moves were used, and how many times each?
2. Combine: which two things on the boards (two functions, two positions, two models) could be joined? What substructure do they share? If none can be named, drop it.
3. Adapt: what else, in another field, is like the garland or the model? Is it a domain already tried at the tract's step 3? If so, what does a second domain add?
4. Modify: what if the object were much larger, much smaller, or much more or less frequent: one bakery, a street, a region; once a week, every night?
5. Reverse or Rearrange: what if the roles were exchanged, the direction of a dependence reversed, or the steps put in another order? Who would then depend on whom?
6. Put to other use: who else could use this arrangement, or for what else could its parts be used?
7. Substitute: what could stand in place of one participant, material or rule? Does the substitution change which links are admissible, or only who fills a slot?
8. Eliminate: what could be removed with the purpose kept? Does the removal merge two elements, or only drop one?
9. For each answer to questions 2 to 8: is it already on the record? If yes, drop it. If no, name the nearest of the four moves and the `via` it would need. If none fits, mark it unplaced.
10. Which move got no candidate from SCAMPER (always `adjoin`, possibly others)? Say so plainly, so the human knows the check could not test it.

Limits on volume: at most two new candidates per operator, and none for an operator that has nothing new. Do not pad.

## Output slots

Every element carries `lens: scamper-check`, `voice: ai`, `epistemic: hypothesis`, and `seen_from` the owner of the vision (the position the tract was drawn for). Put the operator's name at the start of `via`, since the record has no field for it.

| Answer | Element kind | Board | Fields |
|---|---|---|---|
| New `glue` candidate (Combine, Adapt) | `model` | `oo` | label begins "model from another domain: ..."; `move: {op: glue, from: [...], via: "SCAMPER Combine; shared substructure: ...", status: candidate}` |
| New `respecify` candidate (Reverse, Rearrange, Put to other use, Substitute, Eliminate when they change links) | `situation` | `s`, `half: big` | label begins "big situation with new quality: ..."; `move: {op: respecify, ..., via: "SCAMPER Reverse; links changed: ...", status: candidate}` |
| New `rescale` candidate (Modify) | `situation` | `s`, `half: small` | label as in the tract's step 5; `move: {op: rescale, ..., via: "SCAMPER Magnify; grain: ...", status: candidate}` |
| Unplaced result (Substitute or Eliminate that fits none of the four) | `note` | the board where it belongs | label begins "unplaced by the four moves: <operator>: ..."; no `move` |

The kinds and boards repeat those of the tract's steps 3 to 5 so that a candidate from this check is read like one from the tract. `from` names the earlier accepted elements the move acts on, as in the tract. Run the gate of `visionary-tract` section 1 (`uv run smd validate <draft> <previous> --sources <manifest> --hints`) and drop what still fails after two repairs.

The human selects. A candidate with a move is accepted by an `accept_move` sign-off by a person or the group; the model does not write it. An unplaced `note` has no sign-off function; the human either restates it in their own words or removes it. All unplaced notes go to the methodologist as a list, since they are the nearest the engine has to evidence about where the four moves stop; one such note proves nothing about closure.

Example (invented): after the tract the bakeries record has a `glue` model (a cooperative owning a shared asset) and a `respecify` situation, and no `rescale` candidate. Minify gives "view of oneself: one night of dough for one street, tested before a regional plant" with `rescale`. Reverse gives "the mills deliver dough, not flour, so the first step of baking moves from the bakery to the mill" with `respecify`, `via: SCAMPER Reverse; links changed: who performs the first step`.

## Limits

- The seven operators and the bibliographic details (Eberle, 1971; Osborn, 1953) come from a local digest of an invention-method catalog and from general knowledge, not from the primary texts [UNVERIFIED]. Check them before quoting.
- The mapping is a reading. Other readings are possible: Adapt could be placed beside `respecify`, and Put to other use beside `glue`. Where the mapping is doubtful, the `via` text carries the reason, not the operator name.
- SCAMPER was devised for products and teaching imagination **[UNVERIFIED]**. That its prompts help with positions, frames and big situations is [ANALYSIS], not shown.
- Zharnikov's paper is about representations in science and ontology, not group talk in the Shchedrovitsky tradition (`structural-moves.md`). Reading a SCAMPER prompt as a move on a board is the engine's interpretation, to be checked with methodologists.
- The check cannot test `adjoin`, and finding nothing new from an operator does not show that the four-move pass was complete.
