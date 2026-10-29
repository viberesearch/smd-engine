# Profiles: boards, kinds and the screen as data

A profile is one YAML file that sets what a record may hold and how the engine draws it: the boards and where they stand on the screen, the kinds of elements, the relation kinds, the hints, the groups `smd compare` matches, the reading order of `smd frames` and the SessionFlow picks. `src/smd_engine/profile.py` loads it. What a record does with its profile (the `profile` key, the two shipped profiles, the fixed ids) is in `docs/data-model.md`, section Profiles.

## Where profile files live

Profiles are files in `profiles/` of the install: the repository folder in a checkout, `smd_engine/assets/profiles` in the wheel (`profiles_dir()` takes the packaged folder when it exists). A record names a profile by its id, the file name without `.yaml`; there is no per-case profile path. A new profile is a new file in `profiles/` and, for a wheel, a rebuild.

## Format

| Key | Meaning |
|---|---|
| `id`, `title` | the file name; `{ru, en}` |
| `screen` | `regions` (default) or `triangles`; see Screen and layout |
| `boards` | a board template among them: see Board templates. Otherwise in screen order: `id`, `label: {ru, en}`, `halves` (`[small, big]`, one of them, or `none`; each half at most once), `region: [x0, y0, x1, y1]` (screen units, width 1600), `colour: [background, ink]` (`#rrggbb`), `split` (only for a board with two halves: the x where they meet; the middle of the region by default), `object` (`true`: a board of objects, where subject-object talk is warned) |
| `kinds` | in layout order: `id`, `label: {ru, en}` (plural, for counters and tables), `home` (the board it usually lies on, a warning otherwise; or a template, see Board templates), `shape`, and the flags `needs_position`, `container`, `role` (takes `fillers`), `scheme` (counts for "reflection without a new scheme"), `skeleton` (kept by the folded overview; listed by `smd pack` as the cells a reading fills), `light_off` (left off the lighter screen, `--light`), `stance` (takes the element field `stance`: the positions, GP-Guide11 ¶35), `factual` (records a fact: a breakdown a goal may arise from, and the fact the hint `ought-without-fact` looks for), `vsm` (takes the element field `vsm_system`: Beer's systems 1-5, BEER1972), `of_whole` (takes the element field `of_whole`: a model of the whole, BEER1972 Гл. 13). Flags left out are false |
| `relations` | relation kinds, each once, in order: an id of the engine's own (`shift`, `flow`, `produces`, `uses`, `belongs`, `opposes`, `refers`, `represents`, `other`), or a mapping `{id, label: {ru, en}}` for any other kind (an engine id takes no label). `smd graph` and `smd vault` name and filter links by these labels; a kind the engine does not colour is drawn grey |
| `hints` | ids of the hints enabled, each once, among the hints the engine has (`src/smd_engine/validate/hints.py`, `src/smd_engine/validate/management.py`). `situation-halves` reports an empty half as "small situation not laid out" or "big situation not laid out", the method's names for the halves, so a profile that halves a board without situations leaves it off |
| `compare_groups` | name to kinds matched against each other by `smd compare`; a kind in no group is matched in `other` |
| `compare_skip` | kinds `smd compare` leaves out (the program's: `entry`, `note`) |
| `reading` | reading steps of `smd frames`; see Reading steps |
| `sessionflow` | optional: the picks behind the first three SessionFlow questions (`who`, `where`, `what_for`); without it `--format sessionflow` is refused |

Flags are `true` or `false` and default to `false`.

`shape` is how the screen draws a kind: `marker` (entry), `figure` (position), `ellipse` (dashed, place for others), `question` (gap), `frame` (holds function chips; dashed when new), `heading` (bold text across the region on a board with halves, a box elsewhere; the program's situation), `paragraph` (text across the region on a board with halves, a box elsewhere), `box`.

The board colours are used everywhere a board is coloured: the screen (background and ink), the map of `smd frames --zoom`, the planes and points of `smd graph` and the folders and canvas cards of `smd vault` (ink), so the three agree.

## Screen and layout

Automatic layout places each element in the region of its board, or of its half, kind by kind in the order of `kinds`. The halves of a board are two regions, 10 units to each side of `split`.

Boards whose regions overlap vertically form a row. When a region's content runs past its bottom, the whole row grows downwards by the same amount, and every row below moves down by it. A region keeps its width: a dense board grows, it does not spread sideways.

`screen: regions` draws each board as a rectangle around its region (20 to each side, 50 above for the board's name, 10 below; `src/smd_engine/screen.py`), with its name at the top left. A board with two halves gets a dashed line at `split` and the names of its halves above it. A profile has at least one board. Any number of boards, with or without halves, can stand anywhere on the screen, within these rules:
- a board as drawn lies on the screen: `20 <= x0 < x1 <= 1580`, `150 <= y0 < y1`;
- no two boards overlap as drawn: regions side by side are at least 40 apart, one above the other at least 60 (touching rectangles are allowed, as the classic profile's at x 800);
- the boards of a row overlap vertically pairwise: a tall board beside two stacked boards would join them into one row, where the upper one could not push the lower one down, so the profile is refused;
- `split` lies inside the region, more than 10 from each edge (`x0 + 10 < split < x1 - 10`).

`screen: triangles` is the program's screen (Girenko, day 4, 17.10.2026): the first two boards without halves on top, the third below them, drawn as three triangles that meet at the apex (800, 440). It takes exactly three boards in that order, each drawn within its part of the screen: the first left of the apex and above it (`60 <= x0 < x1 <= 780`, `150 <= y0 < y1 <= 430`), the second right of it (`820 <= x0 < x1 <= 1540`, the same y), the third between the apex and the lower corners (`60 <= x0 < x1 <= 1540`, `490 <= y0 < y1 <= 850`). The top two parts lie inside their shapes; the third reaches past the slanted edges at its top corners, as the program's region does (its items start at y 625, under the names of the halves). The triangles are the screen's fixed geometry, and the regions place the items inside them. The top row grows as in `regions` and moves the apex down with it; the board below does not grow: when it overflows, it extends below its triangle into a band as wide as the screen, each half to its side of `split`. The program profile sets `split: 800`, so its halves meet under the apex (regions to 790 and from 810).

The map beside a step of `smd frames --zoom` follows the screen: the three triangles for `triangles`, the rectangles of the regions for `regions`. A board's count of elements in the step stands in its outline: centred in a rectangle, at a fixed point inside a triangle. A step cut to a board takes that board's rectangle, or to a half the part up to 10 past `split`.

## Board templates

A board with `per_record: true` is a template: it is not drawn itself, and each record makes its own boards of it (`boards` in the record, `docs/data-model.md`, Record boards). Keys: `id`, `label: {ru, en}`, `colour`, `kinds` (the kinds its boards take; an element of another kind on such a board is an error), `unfolds` (optional: the kinds of the element a record board of it may `unfold`; any kind when absent), and the flags `object` and `needs_position` (a record board with no `seen_from` is warned). It takes no `region`, `halves` or `split`. A kind whose `home` is the template must be among its `kinds`; on a record board the template's kinds are never warned off their home. The `triangles` screen takes no templates.

The record's boards stand below the profile's boards, in the record's order: rows of as many boards as the widest row of the profile, across the span of its boards, as close as the drawing margins allow (40 side by side, 60 one above the other), each region 300 tall (`screen.record_regions`). They grow like any row. A reading step whose `board` is the template (`{step: process, board: process, pick: {board: process}}`) is repeated for each record board of it, its filter narrowed to that board; the frame takes the id `<step>-<board id>` and the board's label as its title.

Limit: a screen shape other than rectangles around regions or the program's triangles needs a new `screen` value, drawn in `render/svg.py` and `render/frames_page.py`.

## Ids every profile defines

The engine names a few kinds by id; the parser refuses a profile without them ("missing kinds the engine names"):

| Kind | Where the engine names it |
|---|---|
| `position` | `seen_from` (also a `reflexive_position` where a profile has that kind), `reflected_from`, `performed_by`, `shift` and `represents` links, ontology `valid_for` and `subjects`, the hint on positions, `seen_from` kept by a `smd compare` merge; `acts_as` and the hint `position-without-object`; `assigned_by` |
| `place_for_others` | `performed_by` and ontology `valid_for` may name it; the hint on positions; the frames switch "places" |
| `function` | `performed_by`; the hint on new frames; the frames switch "functions"; the performer line of SessionFlow |
| `cooperation` | ontology `cooperation` |
| `gap` | `of` and `scheme`; a breakdown in `arises_from` and for the hint `goal-without-breakdown`; the hint on gaps; the frames switch "places"; a board holding only gaps and notes counts as empty |
| `note` | the counter a folded region becomes (`smd frames --zoom`) |
| `entry` | only when the profile enables the hint `entry` |
| `goal` | only when the profile enables the hint `goal-without-breakdown`; takes `goal_source`, `arises_from` and `assigned_by` |
| others | a hint of one profile's scheme (`src/smd_engine/validate/management.py`) registers the kinds and relation kinds it names; a profile that enables it must define them ("missing kinds the engine names", "missing relation kinds the hints name") |

Other meanings come from attributes, so a profile can name these kinds as it likes: a kind drawn as `frame` takes `frame_state`, holds function chips, is found by the `old-frames` and `new-frames` picks and by the hint on new frames; `heading` draws the bold paragraph; `light_off` kinds leave the lighter screen; `stance` kinds take the field `stance`, `vsm` kinds the field `vsm_system`, `of_whole` kinds the field `of_whole`, and `factual` kinds count as facts for `arises_from` and `ought-without-fact`; a board flagged `object` gets the subject-object warning, which names the home boards of the `role` kinds as the place for such talk. No board id is fixed, but `records` and `sources` are refused for any board, template or record board: they are the layers `smd graph` draws above and below the board planes. The halves are `small` and `big` (the schema's enum for `half`).

## The management profile

`management-four-boards` is G.P. Shchedrovitsky's scheme of organisation, leadership and management (ОРУ), gates Ш13 В and Ш15 В: the org-activity board `od` and the upper system of ОРУ `ot` on top, the apparatus of leadership `ap` and the managed polysystem `us` below, `ot` above `us` (GP-T5 p. 239: «Внизу идет естественный процесс изменения объекта, а вверху — процесс преобразования»). `ot` and `us` are flagged `object`. Example: `cases/example_ru/pekarni-oru-c1.board.yaml`. GP-T5 is т. 5 of the Archive (lectures of 1988); where G.P.'s texts of different periods disagree the latest wins, and the earlier view stays as a comment in the profile file, not as a kind or hint.

| Board | Kinds (G.P.'s terms; GP-T5 pages unless marked) |
|---|---|
| `od` org-activity | `position` (`acts_as`: организатор, руководитель, управляющий, политик, функционер; `stance`), `reflexive_position`, `goal`, `place_for_others` |
| `ot` system of ОРУ, upper | `knowledge_retro`, `knowledge_projective` («службы по организации знаний — как ретроспективных, так и прожективных», p. 241), `ideal_state` (the second state, the future, pp. 229, 238), `programme` (pp. 216, 245-246), `means` (рычаги, каналы; организованности, pp. 199, 222-223), `functional_place` (GP-Guide2004 pdf 138), `model` (конфигуратор, p. 151), `concept`, `cooperation` |
| `process` template: a process board per working process | `function` (its `home`), `cooperation`, `gap`, `note`; `unfolds: [work_process]`; flagged `object` and `needs_position` |
| `ap` apparatus of leadership | `post` (место; `fillers` = наполнение, pp. 177, 192-193; a role), `group` (неформальная группа, pp. 153-154, 224-225), `club` (where politics is done, p. 254) |
| `us` managed polysystem | `monosystem` (a container: «реально мы имеем дело с полисистемами», pp. 206-213), `mission` (p. 211, set by `organises`, p. 213), `self_motion` (p. 170), `trajectory` (with `modality`: the natural and the artificial-natural course, pp. 231, 244), `work_process` (рабочий процесс, the object of управление, p. 244), the five planes of the system (p. 201; four in GP-T4, five from p. 205): `work_process` for the processes, `functional_structure`, `link_structure`, `morphology` (организованности материала), `material`; `fact` (flagged `factual`) |

Relations: the engine's, plus `organises`, `leads`, `manages` (pp. 169-175, 241-244), `subordinates` (from the superior place to the subordinate one, pp. 169, 242), `personal` (pp. 166, 224-225), `captures` («захват», pp. 226-227, 236), `knows` (retrospective and projective knowledge of the lower system, p. 241; not «отражение», which p. 181 drops), `contends` (politics: rival systems of ОРУ in a struggle for the capture of the object, an activity built over управление, pp. 225-229, 253), and between monosystems `parasitic`, `symbiotic`, `mechanism_of` (p. 208). A position fills a post by `belongs`.

Hints: the classic set and those of gates Ш8-Ш12, plus the hints of this scheme (`docs/checks.md`). There is no `forecast` kind and no hint on management without a forecast: GP-Guide5 ¶7 (1981) has «Управлять без прогноза в принципе невозможно», but GP-T5 p. 251 calls forecasting in оргуправление a substitution by scientistic principles. «Управлять вообще можно только развитием» is G.P.'s own «очень смелая гипотеза» (p. 174); the profile states it here as a hypothesis and checks nothing by it.

**Beer layer** (gate Бир3 В). Items from Stafford Beer, «Мозг фирмы» (1972; М., 1993; BEER1972 in `docs/method/sources.md`), marked "Beer layer" in the profile file with the chapter each rests on. Beer's viable system model is a model source for the profile, not a reading of G.P.; the profile carries both and does not merge them. The book has no System 3\*, so there is no kind for it. Example: `cases/example_ru/pekarnya-holding-c1.board.yaml`, an owner-run bakery sold to a holding.

| Item | What it is | Beer |
|---|---|---|
| flag `vsm` on `position` and `post`; field `vsm_system` | the systems 1-5 a position or place fills, a list | Гл. 9-15; one person can be the firm, Гл. 9 |
| kind `algedonic_channel` on `ot`, fields `threshold`, `recovery_time` (days) | an alarm path that bypasses the filters; a stakeholder's red line is recorded as one | Гл. 17 |
| relation `escalates` | from an algedonic channel to the place that must act once the recovery time has run out | Гл. 17 |
| relation `filters` | what a place passes up to the place above | Гл. 7 |
| hint `single-node-metasystem` | one filler fills systems 3, 4 and 5: the transfer will remove the metasystem with the person | Гл. 9, 13 |
| hint `line-without-recovery` | a red line with a threshold and no recovery time or no escalation address | Гл. 17 |
| hint `absorbed-into-system-1` | a place filling system 5 captures (`captures`) systems 4 and 5 of the business: it becomes part of the buyer's system 1, its name and identity at risk | Гл. 15 |
| flag `of_whole` on `model`; field `of_whole` (gate Г2 В) | `true`: the firm's model of itself and its environment, the model system 4 keeps. The post or position that holds it `uses` it | Гл. 13 |
| hint `no-model-of-whole` | a post or position filling system 4 holds no model of the whole: no model with `of_whole: true` on the boards, or none that it, a position belonging to it, the post it belongs to or another position of that post `uses` | Гл. 13 |
| hint `model-of-whole-one-filler` | a model of the whole held by one named filler: it leaves with the person at transfer | Гл. 13 |

The lens `beer-viable-system` asks the questions whose answers fill these items.

G.P. asks that each working process be idealised «на отдельной доске» (GP-T5 p. 245). The template `process` gives each record as many process boards as it has working processes, each a board of its own below the four, labelled «Доска процесса: <label>», naming the `work_process` it `unfolds` and the position it is seen from; its functions lie on it. The reading step `process` follows `upper`, once per process board.

## Reading steps

`reading` lists the steps of `smd frames --by reading`, each `{step, board, pick}`:
- `step`: one of `entry`, `positions`, `places`, `small`, `big`, `old-frame`, `new-frame`, `object`, `upper`, `process`, `apparatus`, `managed` (the last four for the boards of G.P.'s management scheme), each at most once (the steps `smd frames` has titles and texts for, `render/frames_text.py`);
- `board`: the board, or the half (`s.small`), a zoomed step is cut to; or a template, for a step read once per record board of it;
- `pick`: what the step adds, either a filter or `old-frames` / `new-frames` (frames and their contents, by `frame_state`).

A filter is a mapping of at least one of `kinds` (a list of kind ids), `board`, `half` (a half of that board; of any board when `board` is absent) and `frame_state` (`old` or `new`). An element passes when it matches every key given. A step adds only what earlier steps did not show; an empty step is skipped. The SessionFlow picks are filters of the same form.

## Checks of a profile file

A malformed profile is an error of every record that names it (`error: profile: <id>: ...`), and like a schema error it stops the checks of that record:
- a section of the wrong type, a key outside the tables above (at the top, in a board, kind, reading step or filter), a flag other than `true` or `false`, `hints` other than a list of strings, `relations` other than a list of ids and `{id, label}` mappings;
- a duplicate board, kind or reading step id; a missing kind of the table above;
- no boards; `halves` other than `none` or a list of distinct halves; a board off the screen or overlapping another as drawn, a row whose boards do not overlap vertically, a `split` on a board without two halves or outside its region, a colour other than `#rrggbb`, a `screen` other than `regions` or `triangles`, a `triangles` screen with other than its three boards or with a board outside its part;
- a duplicate relation kind or hint id, a hint id the engine does not have, a relation kind outside the engine's without a label, a relation kind an enabled hint names and the profile lacks;
- a `home` that is neither a board nor a template; a `shape` outside the list;
- a template with a key outside its list (`region`, `halves`), `per_record` other than `true`, no kinds or an unknown kind in `kinds` or `unfolds`, a kind homed on it but not among its `kinds`, or on the `triangles` screen; a reading step on a template whose filter has `half` or another `board`; a board or template id `records` or `sources`; a kind in `compare_groups` or `compare_skip` that is not in `kinds`;
- a reading step other than the ids above, a step `board` that is neither a board nor a half of one, a filter with an unknown kind, board or half, `kinds` written as a string;
- a SessionFlow block other than `who`, `where`, `what_for`, or a pick that is not a valid filter; an empty filter `{}`, which would match every element.
