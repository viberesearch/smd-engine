# Data model (schema v0.3)

Two record types, `board_set` and `source_manifest` (schema 0.3), a taxonomy file (`taxonomies`, schema 0.1) and a patch (`board_patch`, schema 0.1). YAML is the authoring format; the JSON Schemas are in `src/smd_engine/schemas/`, one file per record type.

The validator accepts only the current schema version. A record with another `schema_version` is reported as one error, `schema 0.2: run smd migrate`, and its fields are not checked (see Migration below).

## board_set: one cycle of a three-board screen

Top level: `id`, `case`, `title`, `date`, `cycle` (1, 2, ...), `revises` (id of the previous cycle), `reflected_from`, `status` (`draft` | `extracted` | `verified`, the last needs `checked_by`), `sources` (manifest ids), `lineage`, `profile`, `run`, `applied`, `boards`, `elements`, `relations`, `transitions`, `qualifications`, `theses`, `hypotheses`, `ontology`, `signoffs`, `state`.

- `profile`: the method profile the record follows, a string; `program-three-boards` when absent. The profile sets the boards, kinds, relation kinds and hints (see Profiles below); an unknown profile is an error.
- `run`: the procedure run that produced the record: `{procedure, version, model, date}`; `procedure` (a procedure id) is required. `model` is free text, what the runner reports about itself. Each procedure writes it at hand-over and replaces an earlier one; `smd eval` compares two records (`cases/example/golden/README.md`).
- `applied`: the ids of the patches applied to the record, in order (`smd apply`, see Patches below).

`reflected_from` is the position element a new cycle was made from. A cycle is a reflexive exit, not a time slice: the group leaves the actor's position, describes the past cycle and projects the next one (GP1975; `docs/method/reconciliation.md` section 4).

### Boards

The boards of the default profile, `program-three-boards`; `classic-two-boards` has `od` and `oo` only; `management-four-boards` has `od`, `ot`, `ap` and `us` (`docs/profiles.md`, The management profile).

| `board` | Board | Content |
|---|---|---|
| `od` | org-activity (оргдеятельностная) | positions and their links, places for others, goals |
| `oo` | object (объектная) | frames, functions, models, concepts, standards |
| `s` | situation (ситуационная), `half: small \| big` | the group's own practice; the wider system of activity |

### Record boards

A profile may declare a board template (`per_record: true`, `docs/profiles.md`); a record then makes any number of boards of it, listed once in `boards`, and its elements name such a board in `board` like any other. In `management-four-boards` the template is `process`: each working process idealised «на отдельной доске» (GP-T5 p. 245).

```yaml
boards:
  - {id: pb-dough, template: process, label: "ночной замес теста", seen_from: p-organiser, unfolds: wp-dough}
elements:
  - {id: fn-mix, board: pb-dough, kind: function, label: "замес"}
```

Fields: `id` (no dot, since a dot separates a board from its half), `template`, `label` (drawn as "<template label>: <label>", e.g. «Доска процесса: ночной замес теста»), and optional `seen_from` (a position), `unfolds` (the element the board unfolds, of a kind among the template's `unfolds` when it lists any: a `work_process` for a process board) and `cites`. The ids `records` and `sources` are refused (layers of `smd graph`). Every part of the engine handles a record board as a board: the screen draws it below the profile's boards, the frames read it in a step of its own (`process-pb-dough`) and cut a zoomed step to it, `smd graph` gives it a plane, `smd vault` a folder, `smd index` a table of record boards, `smd compare` matches record boards by id, `smd revise` carries them into the next cycle and a patch may add, change and remove them (see Patches). A record without `boards`, or on a profile without templates, is handled exactly as before; `boards` is optional, so the schema stays 0.3.

### Elements

`id`, `board`, `kind`, `label` (as said or written, verbatim) and optional fields:

| Field | Meaning |
|---|---|
| `short` | screen label, about 40 characters; the screen draws it, the full `label` stays in frame texts, tables and the details panel. Without it, a label over 60 characters is cut on the screen with «…» |
| `fillers` | roles only (`position`, `place_for_others`, `gap`): the actors that can occupy the role, e.g. `[государство, регион, фонд]`. Roles go on the boards, actors in `fillers` (`docs/method/roles-and-actors.md`) |
| `detail` | a table behind the element: `title`, `columns`, `rows` (each row as long as `columns`), `keys`. Shown in the frames panel, the HTML tables and the Markdown digest, never on the boards; for a role with inner structure, e.g. stakeholders by tier. `keys` binds a column to a taxonomy, `{tier: tier}`: each cell of the column holds values of that taxonomy, several separated by `;` |
| `half` | small or big; required on a board with halves (the situation board) and only there |
| `frame_state` | `old` or `new` (frames only; new frames are drawn dashed) |
| `of` | gaps only: the block of a named scheme the gap is missing from: `product`, `material`, `means`, `method`, `function`, `position` (GP-PP) |
| `scheme` | gaps only: a free id of the named scheme that `of` refers to, e.g. `gp-pp-activity` |
| `route` | `smd` or `triz`: the line of work the item came from; theses carry it too |
| `tags` | taxonomy id to the values the item takes in it, `{tier: [t1, t2]}`; checked against the taxonomy file. Theses, hypotheses and ontology records carry it too |
| `seen_from` | element id of the position the item is seen from |
| `stance` | kinds the profile flags `stance` only (`position`; the classic `reflexive_position` too): `inside` (внутренняя, a place in the structure), `reflexive` (рефлексивная), `external` (внешняя: outside the structure, drawing it as an object) (GP-Guide11 ¶35-36). `smd revise` carries it with the element |
| `acts_as` | positions only: the place the position takes: `organiser` (организатор), `leader` (руководитель), `manager` (управляющий), `politician` (политик, a fourth level above управление, GP-T5 pp. 242-243), `functionary` (функционер) (GP-Guide10 ¶7) |
| `goal_source` | goals only: `breakdown` (set at a прокол, GP-Guide11 ¶43), `assigned` (passed down under руководство, GP-Guide4 ¶12), `own` (собственная цель of the `seen_from` position) |
| `arises_from` | goals only: what broke: ids of gaps, facts (a kind the profile flags `factual`, `fact` in the default profile, or `modality: fact`), and `difficulty`, `problem` or factual (`modality: fact`) theses |
| `assigned_by` | goals only: the position or place for others that passed the goal down |
| `pace` | years, a number > 0: the characteristic period of change of what the element stands for (a tier, a technology); any element. The hint `ontology-outlives-pace` compares it with an ontology's `horizon` |
| `modality` | `fact` or `ought` (модальность фактического и должного, GP-Guide11 ¶7); theses carry it too |
| `nature` | elements of an object board only: `natural`, `artificial` or `both` (естественное, искусственное; GP-STS; GP-T5 p. 252) |
| `performed_by` | functions only: the position or place for others that performs the function; the viewpoint stays in `seen_from` |
| `in` | containers, e.g. a function inside a frame |
| `epistemic` | `stated`, `hypothesis`, `unverified`, `checked` |
| `voice` | who introduced it, from the thesis voices: `group`, `participant`, `moderator`, `expert`, `organisers`, `ai` |
| `voice_note` | the old voice text that `smd migrate` replaced with `participant`, kept as written |
| `lineage` | origin tags, e.g. `earlier-concept`; used by the clean room and highlighted |
| `cites` | `source-id`, or with an address: `#t=hh:mm:ss` (time), `#p=page`, `#u=n` (turn n of a dialogue log with no timecodes), `#s=section`, `#l=line` (plain-text sources), `#r=n&t=hh:mm:ss` (recording n of a file that holds several recordings, each with its own timecodes; recordings counted from 1 in file order) |
| `move` | the structural move that produced the element (below) |
| `lens` | id of the lens (`lenses/<id>.md`) whose questions produced the element; theses carry it too |
| `geom` | `[x, y, w, h]` as fractions of the screen; overrides automatic layout |

Kinds of the default profile (`classic-two-boards` has `position`, `reflexive_position`, `place_for_others`, `goal`, `frame`, `function`, `model`, `concept`, `standard`, `norm`, `cooperation`, `gap`, `note`, `other`):
- `entry`, `position`, `place_for_others`, `goal`;
- `frame`, `function`, `model`, `concept`, `standard`, `cooperation` (the construction through which several positions build one common object, GP1981);
- `normality_boundary`, `signal`, `garland`, `fact`, `situation`; `vision`: an orienting picture from a visionary's published work (an outside author), on the big half, citing that work (Girenko, inter-module task 4: "your visionary");
- `gap`, `note`, `other`.

The `seen_from` rule follows the organisers' criterion that nothing lies on the boards without a position. It also records the per-position subjects (предметы) of one object.

### Moves

```yaml
move: {op: glue, from: [f-new], via: "accounting: method, standards, professions", status: candidate}
```

A thesis can carry a move too; there `from` may name theses as well as elements.

`op` is one of the four structural operations of Zharnikov (2026), *Invention as a Structural Operation*, doi:10.5281/zenodo.21653102:

| op | Operation | On a board |
|---|---|---|
| `adjoin` | adjoin a dimension (α) | add an axis the picture held fixed: time, observer, scale |
| `rescale` | rescale or requantize (ρ) | change grain: one deal, a flow of deals, rules of the field |
| `respecify` | re-topologize or re-specify (τ) | change admissible links, or identify two elements kept apart |
| `glue` | glue across domains (γ) | build on a shared substructure with another domain |

`status` is `candidate`, `accepted` or `rejected`. Candidates are listed as hints until the group decides.

### Relations, transitions, qualifications, state

- **Relations** (`shift`, `flow`, `produces`, `uses`, `belongs`, `opposes`, `refers`, `represents`, `other`, the `relations` of every profile; a profile may add its own, as the management profile does) link elements, normally within a board. `shift` links two positions; `represents` goes from a position to its representation of an object. Relations and transitions take an optional `voice` (e.g. AI), so links an AI drew stay visible as such.
- **Transitions** are numbered 1..n and move between boards. They draw the trajectory of the group's thinking.
- **Qualifications** `K1..Kn`: `targets`, `text`, `short` (the legend's text when given), `by`, `voice` (who wrote it, e.g. AI drafting for the methodologist), `status` (`open` | `partly` | `closed`), `raised_in`, `closed_in` (cycle numbers).
- **State** is the one-line state after a cycle: `version`, `difficulty` (what failed in the previous cycle), `accepted`, `open`, `next_move`.

### Theses (ingestion, step 2)

A thesis is a SessionFlow thesis card (frame 03) with the belt and kind of the classic method. Ingestion turns a transcript into theses, and theses into board updates.

```yaml
- {id: T3, claim: "Nobody on the board carries the risk of unsold dough.", voice: ai,
   status: ai_variant, belt: m, kind: problem, feeds: [gap-risk],
   move: {op: adjoin, from: [f-new], via: "time: day-to-day demand", status: candidate}}
```

| Field | Meaning |
|---|---|
| `id` | `T1..Tn` |
| `claim`, `grounds`, `illustration`, `consequence`, `next_move` | the card: Утверждение, Обоснование, Иллюстрация, Следствие, Следующий ход |
| `voice` | `group`, `participant`, `moderator`, `expert`, `organisers`, `ai`; no speaker names |
| `status` | the six SessionFlow labels, below |
| `belt` | `md` thought-action (мД), `mk` thought-communication (М-К), `m` pure thinking (М) (GP1987) |
| `kind` | `statement`, `difficulty`, `task`, `problem`, `question` (GP-PP, GP-Guide9) |
| `feeds` | board elements the thesis produced or changed |
| `of` | for a problem: the scheme block it is tied to, as for gaps |
| `scheme` | for a problem: the named scheme `of` refers to, as for gaps |
| `route`, `tags` | as on elements |
| `raises` | K ids the thesis raised, e.g. an organisers' remark that became a qualification |
| `about` | board elements the thesis reads or comments on without changing them (`feeds` is for elements it produced or changed) |
| `modality` | `fact` or `ought`, as on elements |
| `move` | the structural move the group made in its talk (`accepted`) or the model's reading of it (`candidate`) |
| `cites` | source address, `s3#t=00:08:10` (Источник) |

| `status` | SessionFlow label | Fits voice |
|---|---|---|
| `voiced` | Прозвучало в группе | group, participant |
| `assumption` | Предположение участников | group, participant |
| `proposal` | Предложение модератора / эксперта | moderator, expert, organisers |
| `ai_variant` | Вариант формулировки от ИИ | ai |
| `refined` | Уточнено группой после записи | any; needs an `accept_thesis` sign-off |
| `open` | Оставляем открытым | any |

Only the group's decision raises a status: an AI variant becomes `refined` through a sign-off, never by editing the label.

### Hypotheses (field tests)

The inter-module form: what we assume, how we test it, what we got, what it changes. The field gives the result; the group accepts it by a sign-off.

| Field | Meaning |
|---|---|
| `id` | `H1..Hn` |
| `assumes`, `action`, `observe`, `revise_if` | что предполагаем, каким действием проверяем, что будем наблюдать, какой результат заставит пересмотреть |
| `status` | `untested`, `testing`, `confirmed`, `refuted` |
| `result`, `changes` | what the test gave; what it changes on the boards |
| `targets`, `qualifications` | element ids and K ids it is about |
| `artefacts` | the field artefacts the result rests on: manifest ids of kind `field_artefact` |
| `raised_in`, `resolved_in` | cycle numbers |
| `voice` | who formulated it; AI-drafted K and H are listed as a hint until a human keeps or drops them |
| `lens` | the lens behind it, as on elements; ontology records take `lens` too |
| `tags` | as on elements; ontology records take `tags` too |

A result (`confirmed` or `refuted`) needs `result`, `artefacts`, `resolved_in` and an `accept_result` sign-off.

### Ontology (step 3)

An ontological picture is valid for a chosen set of positions, and is checked for realizability in activity, not for truth (GP1981; `docs/method/reconciliation.md` section 2).

| Field | Meaning |
|---|---|
| `id` | `O1..On` |
| `object` | the ontological object |
| `valid_for` | the positions the picture is valid for; places for others (positions not yet taken) may be named |
| `subjects` | per-position subjects (предметы): `{position, subject}` |
| `cooperation` | the `cooperation` element through which the common object is built |
| `competes` | what competes with what (Khaprov's ontology test) |
| `aspects` | the object taken apart, aspect name to text; the usual ones are `activity`, `carrier`, `ownership`, `management` and `separation` (how they come apart), others may be added |
| `test` | the hypothesis that tests realizability |
| `lives_in` | what the system lives in and must fit into, no entry twice: `{id: <element id>}` (must exist) or `{text: "..."}` |
| `tempos` | the tempos the ontology assumes: `{id, years}` or `{text, years}`, e.g. `{text: "business models", years: 5}` |
| `horizon` | years the ontology is expected to hold; with `pace` and `tempos`, the space-time continuum of the record (Khaprov, podcast 28.10.2026, `lenses/khaprov-ontology.md`) |
| `covers` | element ids the picture covers besides those in `lives_in`, no id twice; the hint `ontology-outlives-pace` reads both |

### Sign-offs (interface tax)

A human sign-off point must state its function (Schukin, interface tax: a touchpoint with no function is old paper-forwarding; one with a function cannot be removed without losing verifiability).

```yaml
signoffs:
  - {function: close_k, target: K2, by: group, cycle: 2, date: "2026-01-17", note: "..."}
```

| `function` | `target` | Licenses |
|---|---|---|
| `close_k` | a qualification | `status: closed` |
| `partly_k` | a qualification | `status: partly` (part of its request is answered; say which in `note`) |
| `reopen_k` | a qualification | `status: open` again, after it was closed (the group lifts a closing) |
| `accept_move` | an element or thesis with a move | `move.status: accepted` |
| `reject_move` | an element or thesis with a move | `move.status: rejected` |
| `accept_thesis` | a thesis | `status: refined` |
| `accept_result` | a hypothesis | `status: confirmed` or `refuted` |
| `verify_record` | none | record `status: verified` |

`by` is a person or the group, never an AI voice. Optional: `date`, `cycle`, `note` (the grounds looked at), `cites`.

## source_manifest: raw materials, listed not copied

`case`, `location`, `sources[]` with `id`, `title`, `kind` (`transcript`, `slides`, `handout`, `analysis`, `prompt`, `correspondence`, `team_doc`, `external`, `field_artefact`, `decision_log`: the owner's or group's written decisions, cited by theses and sign-offs that rest on them), `origin` (`program` | `team` | `external`), `author`, `date`, `file` or `url`, `sha256`, `lines` (the line count the `sha256` covers), `lineage`, `clean_room` (`allow` | `deny`), `personal_data`, `note`.

`smd sources --clean-room --deny-lineage <tags>` splits sources into allowed and denied for a run that must not see a given lineage.

`smd sources <manifest> --folder F --refresh [ids]` recomputes `sha256` (and `lines`, for a source that carries it) for the named sources (default: every `decision_log`) from the files in F and edits only those `sha256:` and `lines:` lines in the manifest text (comments and formatting stay; a source with a `file:` line and no `sha256:` gets one); file names are matched after Unicode NFC normalisation.

## taxonomies: the values of tags

```yaml
record: taxonomies
schema_version: "0.1"
case: mipt-transfer
taxonomies:
  tier:
    - {id: t1, ru: "владелец и семья", en: "owner and family"}
    - {id: t2, ru: "сотрудники", en: "employees"}
```

`smd validate --taxonomies <file>` checks every `tags` value and every cell of a column bound by `detail.keys` against the file: an unknown taxonomy or value is an error naming the item and the value. In a bound cell, values are separated by `;` and spaces around them are trimmed; an empty cell is allowed. Without the file, a record that uses `tags` or `detail.keys` gets one warning. `smd publish --taxonomies <file>` validates with it; `smd pack --taxonomies <file>` carries it in the pack.

## Patches: a decision as a record

A change to the current cycle is a patch; a new cycle is `smd revise`. A patch (`*.patch.yaml`, `record: board_patch`) names the board it applies to and lists what the decision changes:

```yaml
record: board_patch
schema_version: "0.1"
id: bakeries-c2-1
applies_to: bakeries-c2
version: "0.2.1"
add:
  elements:
    - {id: fact-pledges, board: s, half: small, kind: fact, label: "...", seen_from: p-organiser, cites: [s4]}
  sources: [s4]
set:
  - {id: place-mills, label: "...", label_note: "regional mills"}
remove:
  - {id: gap-risk, reason: "answered by the pledges (H1, s4)"}
state:
  accepted: ["pledged members carry unsold dough"]
```

Top level: `id`, `case`, `applies_to` (the board's id), `version` (the board's new `state.version`, kept as text; an unquoted `5.8` is read as `"5.8"`, but quote it, since YAML reads `5.10` as `5.1`), `date`, `cites`, `notes` (the patch's own note), `title` (replaces the board's title), `board_notes` (see below), and:
- `add`: items appended to `boards` (record boards, placed before `elements` when the board had none), `elements`, `relations`, `transitions`, `qualifications`, `theses`, `hypotheses`, `ontology`, `signoffs`, in the board's shapes; `sources`: manifest ids added to the board's `sources`. The added items are checked by the board schema after application, not in the patch.
- `set`: `{id, <field>: value}` merged into the record board, element, K, thesis, hypothesis or ontology record of that id; `null` deletes the field. `{n, <field>: value}` does the same for the transition numbered `n` (`n` itself is not changed). When both the old and the new value are mappings (`detail`, `move`, `tags`, `aspects`), they merge one level deep, key by key, and `null` deletes that key; lists and scalars replace. So `{id: x, detail: {keys: {tier: tier}}}` keeps the table's `columns` and `rows`, and `{id: m, move: {from: [a, b]}}` keeps the move's `op`.
- `board_notes`: text appended to the board's `notes`, before the lines for removals.
- `remove`: `{id, reason}` or `{n, reason}`. `n` drops that transition (later ones renumbered 1..n) and notes `<patch id>: removed transition <n>: <reason>`. The item is dropped with every link that names it; each id and reason is appended to the board's `notes` as `<patch id>: removed <id>: <reason>`, followed by `; dropped sign-off <function> <id> (<by>, <date>)` for each sign-off dropped with it. A record board is removed with the elements on it, noted as `; with <ids>`. Links dropped: relations and transitions from or to it (the remaining transitions are renumbered 1..n), `reflected_from`, record board `seen_from` and `unfolds`, element `seen_from`, `performed_by` and `in`, qualification `targets`, thesis `feeds`, `about` and `raises`, hypothesis `targets` and `qualifications`, goal `arises_from` and `assigned_by`, ontology `valid_for`, `covers` and the `{id}` entries of `lives_in` and `tempos`, `subjects` of that position, `cooperation` and `test`, sign-offs on it, and its entry in `state.open`. A list left empty is deleted, except `valid_for` and a move's `from`, which stay empty so that the validator reports them.
- `state`: `accepted` and `open` entries are appended, `remove_open` entries dropped from `open`, `next_move` and `difficulty` replaced.

`smd apply <board> <patch> -o <out> [--sources <manifest>] [--taxonomies <file>]` applies `add`, `set`, `board_notes`, `remove`, `sources`, `state` and `title` in that order, sets `state.version`, appends the patch id to `applied`, and validates the result, with the manifest and the taxonomy file when given; an error in an item names the item's id. A patch for another board, a `set` or `remove` naming an unknown id or transition number, or, with `--sources`, a patch `cites` entry that is not in the manifest exits 2. A transition `n` in `set` and `remove` is its number after `add`, before this patch renumbers; so `add` may give a transition and `set` may change it. The notes get `board_notes` (trailing whitespace dropped), then one line per removal, each joined to the notes by one newline. A patch already in `applied` exits 1: a patch applies once. A result with errors is not written and the command exits 1; `--force` writes it and still exits 1. The output is in the engine's YAML layout (`dump_record`), so a board written by the engine changes only in the patched lines; comments of a hand-written board are not kept. `smd revise` does not carry `applied` into the next cycle.

## Profiles

A profile is a YAML file in `profiles/` of the install: the repository folder in a checkout, `smd_engine/assets/profiles` in the wheel. A record names its profile by id in `profile`; there is no per-case profile path, so a new profile is added to `profiles/` of the install. The schema leaves `board`, `kind` and the relation `kind` as strings; the validator checks them against the record's profile, and an unknown board or kind is an error naming the element and the value. Three profiles ship:
- `program-three-boards` (default): the program's screen (`screen: triangles`), boards `od`, `oo` and `s` (halves `small`, `big`), the 19 kinds above, every hint;
- `classic-two-boards`: boards `od` and `oo` side by side (`screen: regions`); no `entry` and no situation kinds, plus `reflexive_position` and `norm`; no `entry` or situation hints; no SessionFlow export. Example: `cases/example/two-boards-c1.board.yaml`.
- `management-four-boards`: G.P.'s scheme of ОРУ (gates Ш13 В, Ш15 В): `od` and the upper system `ot` on top, the apparatus `ap` and the managed polysystem `us` below (`screen: regions`); its kinds, relations and hints are in `docs/profiles.md`, The management profile. Example: `cases/example_ru/pekarni-oru-c1.board.yaml`.

The file format, the layout of boards by their regions and the checks of a profile file are in `docs/profiles.md`. Two sets of ids are fixed by the engine:
- **Kinds every profile defines:** `position`, `place_for_others`, `function`, `cooperation`, `gap`, `note`; also `entry` when the profile enables the hint `entry`, and `goal` when it enables `goal-without-breakdown`. The checks, the frames switches and the fold counter name these ids; other meanings come from kind attributes (`shape: frame`, `light_off`, `stance`, `factual`) and the board flag `object`. No board id is fixed; `records` and `sources` are refused (layers of `smd graph`).
- **Reading step ids:** `entry`, `positions`, `places`, `small`, `big`, `old-frame`, `new-frame`, `object`, `upper`, `process`, `apparatus`, `managed`, each at most once: the steps `smd frames` has titles and texts for. A step on a template is read once per record board, as `<step>-<board id>`.

`smd pack` reads `profile` in a procedure's front matter (`any` or a profile id). A procedure for another profile than the records' is refused (exit 2, "procedure is for profile ..."); a procedure it names is left out. `smd compare`, `smd frames --by cycle` and the cycle frames of `smd publish` take records of one profile; records of two profiles exit 2 with a message naming both.

## Migration

`smd migrate <paths> [--write]` rewrites board sets and manifests (files or folders) to the current schema, one step per version (`src/smd_engine/migrate.py`). It prints what each file changes; without `--write` it only reports. A current record, of any type, is left as it is; an unquoted version (`schema_version: 0.2`) is read as text. The changes are made in the file's text, line by line, so comments and layout stay; the edited text is loaded back and compared with the migrated data. When they differ, the file is rewritten in the engine's YAML layout (JSON for a `.json` file) and the report says so ("rewritten, about N comment line(s) not kept"; the count is approximate).

From 0.2 to 0.3: `schema_version` becomes `"0.3"`; an element `voice` outside the enum is set to its lowercase form when that is in the enum (`AI` to `ai`; `ИИ` also becomes `ai`), otherwise to `participant`, with the old text kept in `voice_note`. Nothing else in 0.3 is stricter than 0.2. The profile checks came later within 0.3 and need no migration: the default profile holds exactly the boards, kinds and relation kinds of the 0.3 enums.

## Checks

The checks are in `src/smd_engine/validate/`, one module per subject, run in the order of its `REGISTRY`; hints run only when the record's profile enables them. An unknown profile, or a board, kind or relation kind outside the profile, is an error reported with the schema errors, and like them it stops the checks:
- **Errors:** duplicate ids; `fillers` on an element that is not a role; a `detail` row whose length differs from `columns`; dangling references in `seen_from`, `in`, relations, transitions, qualification targets, move sources and thesis `feeds`; `seen_from` or `reflected_from` that is not a position; `half` rules; containment cycles; transition numbering; a closed K without `closed_in`; a K raised after the record's cycle; a record revising itself; `verified` without a checker; unknown source ids when a manifest is given.
- **Errors (ingestion):** `of` on an element that is not a gap; `performed_by` on a non-function or not naming a position or place for others; a thesis that `raises` an unknown K; a hypothesis result without its text, field artefact or `resolved_in`; dangling hypothesis targets or K; a thesis status that does not fit its voice; an accepted move from an AI voice with no `accept_move` sign-off; a sign-off by an AI voice, without a target, or aimed at the wrong kind of target.
- **Warnings:** a screen label (`short`, or `label` when there is no `short`) over 60 characters, which the screen cuts; a kind off its usual board; a content item without a position; a transition inside one board; a `shift` between non-positions; a manifest entry with no file or url, or no clean-room decision.
- **Warnings (ingestion):** a revising cycle with no `reflected_from`; a thesis with no source address (except AI voice); an accepted move with neither a source nor a sign-off; a closed K, a `refined` thesis, a hypothesis result or a `verified` record with no matching sign-off; a hypothesis `testing` with no action; a sign-off that changes nothing, because its target is not in the state it licenses (only the latest K or move sign-off on a target is checked: `reopen_k` supersedes an earlier `close_k`).
- **Hints** (Girenko's criteria for a group screen, 17.10.2026): no entry; an empty board, or an empty half of a halved board (the program's small or big situation not laid out); one position and no places for others; a new frame without functions or with functions no one performs; open gaps; open qualifications; candidate moves, on elements and theses; AI variants awaiting the group.
- **Warnings (step 3):** subject-object talk ("we must", "our task", "мы должны", "наша задача") in a label on a board the profile flags `object` (the object board); `represents` not starting from a position; an ontology subject for a position outside `valid_for`.
- **Errors (step 3):** ontology `valid_for` that is not a position, `cooperation` that is not a cooperation element, `test` that is not a hypothesis, an id in `lives_in`, `covers` or `tempos` that is not an element.
- **Hints (classic method):** an ontology with no realizability test, or valid for several positions with no cooperation; an ontology whose `horizon` is longer than the `pace` of an element in `lives_in` or `covers`, or than a `tempos` entry: the continuum is exhausted before the horizon (`ontology-outlives-pace`, Khaprov, podcast 28.10.2026, l.154-172; no hint without `horizon`); a gap or a problem thesis with no scheme block; a new cycle with no `difficulty`; a hypothesis with no `revise_if`; degenerate belts (GP1987): mostly М-К theses and none in М ("play with words"), or М theses with none in мД (thinking cut off from the situation).
- **Errors (G.P.'s «Программа действий»):** `stance` or `acts_as` on an element that is not a position, `goal_source`, `arises_from` or `assigned_by` on one that is not a goal, `nature` off an object board; an `arises_from` id that is neither a gap, a fact, nor a `difficulty`, `problem` or factual thesis; `assigned_by` that is not a position or place for others.
- **Warnings (G.P.'s «Программа действий»):** `reflected_from` naming a position with `stance: inside`.
- **Hints (G.P.'s «Программа действий», GP-Guide11, read against GP-T5):** an object-board element seen from a position with `stance: inside` (`object-from-inside`, ¶36); a new cycle whose object board is seen from an `external` position with no `reflected_from` (`external-without-reflection`, ¶35, ¶47); a goal with no breakdown: no `goal_source`, `arises_from`, gap linked by a relation, `difficulty` or `problem` thesis naming it, or `state.difficulty` (`goal-without-breakdown`, ¶43; also an `assigned` goal with no `assigned_by` and a `breakdown` goal with no `arises_from`); a position with `acts_as` (not `functionary`) and no `represents` relation (`position-without-object`, GP-Guide10 ¶7, ¶19); an object-board element with `modality: ought` and no fact linked by a relation, `in`, or a factual thesis (`ought-without-fact`, GP-T5 p. 252); `ought` on a `natural` element (`design-the-natural`, GP-STS); theses, other than `open`, with neither `feeds` nor `about` (`information-without-cell`, ¶5). Where the 1981 and 1988 texts disagree the 1988 lectures win: GP-Guide5 ¶7 required a forecast ("Управлять без прогноза в принципе невозможно"); GP-T5 p. 251 calls forecasting in оргуправление a substitution by scientistic principles, so `ought-without-fact` asks for the natural processes, not a forecast.
- **Hints (G.P.'s management scheme, `management-four-boards`, GP-T5):** a `leads` relation to someone with goals `goal_source: own` (seen from the target or from a position that `belongs` to it) (`lead-vs-manage`, pp. 169-170); a `manages` relation with no element the source `produces` and the target `uses` (`manage-via-organizedness`, pp. 222-223); a position that `manages` with no retrospective or no projective knowledge seen from it or linked to it (`manage-without-knowledge`, p. 241); a `leads` relation whose ends hold no post (itself, or one it `belongs` to), or with no line of `subordinates` from the leader's post down to the other (`leads-outside-organisation`, pp. 242, 254); a `represents` target outside the kinds expected for the position's `acts_as`: organiser to `post`, `functional_place`, `mission`, `monosystem`; leader to `post` (not `group`: the informal group is outside the administrative structure, pp. 224-225, 254); manager to `work_process`, `trajectory`, `self_motion`; politician to `club`, `position`; functionary to none (`representation-fit`; the table is the engine's reading of GP-T5 pp. 170-175, 213, 223, 242-244, 253-254, not a table of G.P.'s); an upper board with content but no past of the object (a `factual` kind, `knowledge_retro`, or `modality: fact` on the managed board), no `ideal_state`, or no `captures` from the upper board to the managed one (`development-step`, «шаг развития», «минимальная единица», pp. 229, 232, 238); a managed board with fewer than two monosystems, or monosystems with no `parasitic`, `symbiotic` or `mechanism_of` relation (`polysystem`, pp. 206-213).
- **Errors (record boards):** reported with the schema errors: a record board of an unknown template, with an id of a profile board or template or `records`/`sources`, or twice; an element of a known kind its record board's template does not take. Later: a record board id that is also an element id, a `seen_from` that is not a position, an unknown `unfolds` or one of a kind outside the template's `unfolds`. **Warnings:** a record board with no `seen_from` when its template sets `needs_position`; a kind whose `home` is a template, on another board ("usually lies on a board of template 'process'").
- **Errors (v0.3):** `scheme` on an element that is not a gap or on a thesis that is not a problem; a `detail.keys` column that is not among `columns`; with a taxonomy file, an unknown taxonomy or value in `tags` or in a bound column.
- **Warnings (v0.3):** `tags` or `detail.keys` used and no taxonomy file given.
- **Across cycles:** when the revised record is among the files validated, a new cycle with no new or changed frame, function, model, concept, standard or cooperation gets the hint "reflection without a new scheme". A cycle run by `ingest-transcript` or `theses-to-board` whose new theses feed only elements the previous cycle did not have gets `cells-from-information`: the cells were drawn from the information, not before it (GP-Guide11 ¶5).
