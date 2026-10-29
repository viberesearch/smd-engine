---
id: theses-to-board
title: Theses to board updates and a state line
step: 2
version: 0.3.4
role: игротехник
profile: any
inputs:
  - theses from ingest-transcript
  - the previous board set of the case, if any
  - the case's source manifest
outputs:
  - a board-set record for the new cycle (status draft or extracted)
  - a state line
  - the list of sign-offs to request
next: field-result, or a step-3 thinking procedure
sources: [Girenko day 4 (three boards, transitions, K), GP1975 (reflexive exit), SessionFlow frame 03 (state line), Schukin (interface tax)]
---

# Theses to board updates and a state line

The board set is the record; drawings are generated from it. You turn theses into board elements and keep every element traceable to the talk.

## 1. The cycle

- No previous record: `cycle: 1`, no `revises`.
- A previous record: copy its elements, relations, qualifications, hypotheses, ontology and sign-offs forward. Set `cycle` to n+1, `revises` to its id, and a new `id`. Transitions belong to one cycle: number this cycle's transitions afresh from 1. A participant's name in a copied item becomes the position the person holds, recorded in the record's `notes` (`reflexive-protocol`, section 8, step 2, which also says where the boundary of "we" goes when a position is copied). Change nothing else in a copied item.
- A change to the current cycle, such as a decision taken after the record was written, is a patch applied with `smd apply` (`docs/data-model.md`, Patches); a new cycle is `smd revise`.
- A carried element that the talk describes differently stays one element when it is the same thing: keep its id, update `label`, put the previous label in `label_note`. When the talk moves it to another board or half, move it and say so in the reply; the change is material for the group, not a silent edit. When the talk contradicts the previous record outright, keep both readings as two theses and raise a K.
- `reflected_from`: the position the group took when it looked back at the previous cycle. It must be a `position` element on `od`. If the talk shows the group reflecting, from organisers' qualification or from its own review, add or reuse that position and cite it. If the talk does not show it, leave the field out; the validator will warn, which is the honest result.
- In a thinking session the same rule applies as in `solo-session`, section 2: with a human, gate 0 is the reflexive answers (`reflexive-protocol`, sections 2 and 3) and the record has `reflected_from` and `state.difficulty`. In proposal mode (`solo-session`, section 11, "Proposal mode"), open the record without `reflected_from` and `difficulty`, with the reflexive questions first in `state.open`. Do not invent a position or a difficulty to silence the warning.
- `state.difficulty`: what failed in the previous cycle, in the group's words, if the talk says it.
- `state.version`: set by `reflexive-protocol` when it opens the record. When the record is opened without it, the opener sets `n.0` for cycle n.

## 2. Elements from theses

For each thesis, decide whether it adds an element, changes one, or stays off the boards.

| The thesis is about | Element kind | Board |
|---|---|---|
| who acts, in which role; a role the group leaves room for (the actors that could take it go in `fillers`) | `position`, `place_for_others` | `od` |
| the old or new frame of the object, its functions, models, standards | `frame`, `function`, `model`, `concept`, `standard` | `oo` |
| the group's own practice; the wider system of activity | `situation`, `fact`, `signal`, `normality_boundary`, `garland` | `s`, `small` or `big` |
| what is missing in a scheme | `gap` with `of` (the scheme block) | where it is missing |

Rules:
- `label` is verbatim or near-verbatim from the thesis; do not improve it.
- `seen_from`: the position the item is seen from. Nothing lies on the boards without a position.
- `performed_by` (functions only): the position or place for others that performs the function. Leave it out when the talk does not say who performs it, so that the hint shows the gap; do not fill it from `seen_from`.
- `cites`: the thesis's source address, with the address form of the source: `#t=hh:mm:ss` (time), `#u=n` (turn of a dialogue log without timecodes), `#p=page`, `#s=section` or `#l=line`.
- `epistemic`: `hypothesis` for an assumption, `unverified` for a figure no one has checked, `stated` otherwise.
- `voice`: who introduced the element, taken from the thesis (`group`, `participant`, `moderator`, `expert`, `organisers`), and `voice: ai` on any element whose wording is yours. Names of speakers are never written.
- Subject-object talk ("we must", "our task", "мы должны", "наша задача") goes on `od`, not on `oo`.
- Fill the thesis's `feeds` with the ids of the elements it produced or changed. Move a thesis's `move` onto the element it produced (see `ingest-transcript`, step 4).
- Fill the thesis's `about` with the ids of the elements it reads or comments on without changing them. A thesis that only reads an element has `about`, not `feeds`.

A thesis that stays off the boards keeps an empty `feeds` and an empty `about`. Say why in the reply.

## 3. Relations, transitions, qualifications, hypotheses

- Relations link elements within a board (`shift` between two positions, `flow`, `produces`, `uses`, ...). A relation you drew carries `voice: ai`.
- Transitions are numbered 1..n in the order the talk moved between boards, each citing its time. In a thinking session, record each move between boards of the session in order, whoever made it; moves you made carry `voice: ai`. Numbering starts from 1 in each cycle.
- Qualifications: each critical remark by organisers or a methodologist becomes `K` with `targets`, `text`, `by`, `status: open`, `raised_in`, and the thesis that carried it gets `raises: [K..]`. A K you drafted yourself carries `voice: ai`. Never close a K yourself. When the talk partly answers a K, keep it `open`, note what answered it, and propose `partly` in the reply; a human sets `partly`, which closes nothing and needs no sign-off.
- Hypotheses: an assumption becomes `H` only when the group marks it as to be checked, or a planned action depends on it. Other assumptions stay theses with status `assumption`. An H you drafted carries `voice: ai`. Fill `assumes` and, where said, `action`, `observe`, `revise_if`, `status: untested` or `testing`. If no test is named, say "предположение высказано; способ проверки пока не определен" in the reply.

## 4. State line

`state`: `version`, `difficulty`, `accepted` (only the group's decisions in response to others or explicit acceptances, not the content of its own report), `open` (K, H and theses still open), `next_move` (one concrete move). In proposal mode, decisions that wait for a human go into `open`, never into `accepted`.

## 5. Sign-offs: request, never write them

The group or a named person licenses each of these by a sign-off. List them in the reply as requests, each with its function:
- `close_k`: a K the talk shows as resolved;
- `accept_move`: a candidate move the group took up;
- `reject_move`: a candidate move the group declined;
- `accept_thesis`: an AI variant the group refined;
- `accept_result`: a hypothesis result (see `field-result`);
- `verify_record`: a checker has compared the record with the source.

A human touchpoint with no function is paper-forwarding (Schukin). Do not ask for sign-offs that change nothing. In proposal mode, list the requests in the reply and in `state.open`, and write none.

## 6. Check and render

```bash
uv run smd validate <record> <previous-record> --sources <manifest> --hints
uv run smd render <record> --format html -o out/<id>.html
```

Fix every error. Report the warnings and hints you leave, with a reason. Coverage check: every element cites a source, and every thesis feeds an element, raises a K, reads an element (`about`), or is reported as off the boards.

Record the run: set `run: {procedure: theses-to-board, version: <this procedure's front-matter version>, model: <what your runner reports about the model, free text>, date: <today>}` in the record. A later procedure on the same record replaces it; `smd eval` compares two such runs.
