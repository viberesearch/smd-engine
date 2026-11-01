# Spectra Coffee: an invented business map with checked stories

**Everything here is invented.** "Spectra Coffee" is an invented coffee shop, its founder, head barista, buyer and bank are invented, and so are their words, figures and dates. The one thing not invented here is a list of what the public demonstration specification of that shop describes (6 menu items, 5 critical control points, 14 allergens, 3 roles, prices and margins); the shop it describes is itself invented (`sources.yaml`, source `s-spec`). No person in these files is real: people appear as roles. Every title says so, every element carries `lineage: [fictional]` and `voice: ai`, and the stories are marked «черновик ИИ». Nothing here was checked by a human.

The case is a sample of what a map of one business needs before a story can be told from it, and of what such a story looks like. It answers "what is required from us" with an example, so that a group or a broker does not start from an empty page.

## Files

| File | Content |
|---|---|
| `spectra-coffee-c1.board.yaml` | the board set (default profile, Russian labels): 39 elements, 52 relations, 5 hypotheses, 2 K, 1 ontology record |
| `sources.yaml`, `taxonomies.yaml` | the invented sources; the six values of the `tier` tag |
| `owner.story.yaml` | SCQA for the founder: red line broken in August 2026 while the founder was away |
| `buyer.story.yaml` | SCQA for the buyer, a regional roaster chain: the trial month without the founder inside the series of handover events; the walk goes from the buyer through the journal and the training to the trial month and the cooperation of the transfer |
| `bank.story.yaml` | SCQA for the buyer's bank: the coverage red line (not below 1.3) and the 92 days between two measurements |
| `successor-premortem.story.yaml` | premortem for the future manager: a series of linked events that stops, with the causes and an early sign for each |

The invented situation: a founder aged 61 wants to hand over two cafes within 3 years and keep the taste of the drinks. Candidates: the head barista as manager (the place `place-successor`), a regional roaster chain as buyer, a bank that finances the buyer. The business depends on the founder in one place that the board can show: his own tuning of the grinder every morning, and the record of it (a red line `rl-dialin`, observed breach of 14 days).

## What the board holds

- Positions, places for others, one goal, two frames (old and new), six functions with `performed_by`, 27 flows that carry money, material, information or product, `uses`, `produces`, `belongs` and `opposes` relations, and seven weak `refers` that are not yet typed.
- Two red lines with `red_line: true`, `line` and `observed`: `rl-dialin` is a yes/no (`expect: true`, `recovery_days: 3`) and `rl-cover` is a corridor (`min: 1.3`, `recovery_days: 60`); both are breached by the rule of `docs/red-lines.md`.
- A normality boundary `nb-qual` opposed by a signal `sig-august`; a series of linked events `gl-handover` with three events that `belongs` to it.
- Five hypotheses with typed rules: H1 is `testing` with `observed` (4 of 56 shifts, the engine's verdict is "inconclusive"), H2 and H3 are untested estimates, H4 is `confirmed` with a (invented) sign-off, H5 is a probe.
- Tier tags on elements for all six tiers (`tags: {tier: [...]}`), checked against `taxonomies.yaml`. The founder's own ontology has a shareable record `O1`; its private part is not on the board, as the engine never holds it.

```bash
uv run smd validate cases/spectra_coffee --sources cases/spectra_coffee/sources.yaml --taxonomies cases/spectra_coffee/taxonomies.yaml --hints
uv run smd story paths cases/spectra_coffee/spectra-coffee-c1.board.yaml --audience place-bank --limit 3
uv run smd story check cases/spectra_coffee/bank.story.yaml --boards cases/spectra_coffee/spectra-coffee-c1.board.yaml
```

## How the six tiers and the public specification fit

The six tiers of the OST ontology (owner intent, business model, business entity and rights, product, process, organisation) and the levels L0-L5 of the public specification are **not the same axis**. The levels are the order in which one shop's specification is derived, from the customer experience it must create (L0) down to sourcing (L5). The tiers decompose a firm for a transfer. The levels map to tiers many to many:

| Tier | What the specification has | What this case adds |
|---|---|---|
| 1 owner intent | nothing. The mission and values in the identity file are the shop's declared mission, not the owner's programme | the goal `goal-handover`, the founder's red line, the shareable ontology `O1` |
| 2 business model | L0 (target cohort, desired perception), prices and margins of L3 | `m-model`, an unchecked revenue estimate |
| 3 entity and rights | nothing about the legal person. Supplier and sourcing requirements (L4, L5) touch contracts | trademark held by the founder, lease with a change-of-control consent, the buyer and the bank |
| 4 product | L3 product specifications (6 items, cost, price) | `fn-shot`, `fact-spec`, `fact-price` |
| 5 process | L2 process contracts (quality control, opening and closing, maintenance, HACCP, allergens). L1 signal requirements spread over tiers 2 and 5 | `fn-dialin`, `fn-journal`, `nb-qual`, `sig-august` |
| 6 organisation | the roles (barista, shift lead, manager) | the head barista, the place of the manager, staff, `fn-train` |

Tiers 1 and 3 are where the specification is silent. A real business map has the same two holes until someone fills them, and a story that crosses them has nothing to rest on: that is what the stories here show by what they do not say.

## How the stories were made, and how they stay checked

1. `smd story paths` listed the walks from each protagonist (`procedures/story.md`, section 1). The four walks used are among its default top five (`tests/test_story_paths.py` keeps it so), and each story's `conflict` and `resolution` come from the walk.
2. The sentences were written for each audience, each on board ids; the allow-lists were cut by hand (the buyer and the bank do not see the founder's private estimate of his own share of mornings).
3. Each story is stamped with the board version and the sha256 of the board file. `tests/test_story_case.py` runs `smd story check` on all four in CI. If the board changes in any way, the stories fail rule G7 until they are written again: that is the rule, not a defect.
4. The stories are a view. They are not signed, and a correction goes to the board.
