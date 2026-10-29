# Profiles: boards, kinds and the screen as data

A profile is one YAML file that sets what a record may hold and how the engine draws it: the boards and where they stand on the screen, the kinds of elements, the relation kinds, the hints, the groups `smd compare` matches, the reading order of `smd frames` and the SessionFlow picks. `src/smd_engine/profile.py` loads it. What a record does with its profile (the `profile` key, the two shipped profiles, the fixed ids) is in `docs/data-model.md`, section Profiles.

## Where profile files live

Profiles are files in `profiles/` of the install: the repository folder in a checkout, `smd_engine/assets/profiles` in the wheel (`profiles_dir()` takes the packaged folder when it exists). A record names a profile by its id, the file name without `.yaml`; there is no per-case profile path. A new profile is a new file in `profiles/` and, for a wheel, a rebuild.

## Format

| Key | Meaning |
|---|---|
| `id`, `title` | the file name; `{ru, en}` |
| `screen` | `regions` (default) or `triangles`; see Screen and layout |
| `boards` | in screen order: `id`, `label: {ru, en}`, `halves` (`[small, big]`, one of them, or `none`; each half at most once), `region: [x0, y0, x1, y1]` (screen units, width 1600), `colour: [background, ink]` (`#rrggbb`), `split` (only for a board with two halves: the x where they meet; the middle of the region by default), `object` (`true`: a board of objects, where subject-object talk is warned) |
| `kinds` | in layout order: `id`, `label: {ru, en}` (plural, for counters and tables), `home` (the board it usually lies on, a warning otherwise), `shape`, and the flags `needs_position`, `container`, `role` (takes `fillers`), `scheme` (counts for "reflection without a new scheme"), `skeleton` (kept by the folded overview), `light_off` (left off the lighter screen, `--light`) |
| `relations` | relation kinds, each once |
| `hints` | ids of the hints enabled, each once, among the hints the engine has (`src/smd_engine/validate/hints.py`). `situation-halves` reports an empty half as "small situation not laid out" or "big situation not laid out", the method's names for the halves, so a profile that halves a board without situations leaves it off |
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

Limit: a screen shape other than rectangles around regions or the program's triangles needs a new `screen` value, drawn in `render/svg.py` and `render/frames_page.py`.

## Ids every profile defines

The engine names a few kinds by id; the parser refuses a profile without them ("missing kinds the engine names"):

| Kind | Where the engine names it |
|---|---|
| `position` | `seen_from`, `reflected_from`, `performed_by`, `shift` and `represents` links, ontology `valid_for` and `subjects`, the hint on positions, `seen_from` kept by a `smd compare` merge |
| `place_for_others` | `performed_by` and ontology `valid_for` may name it; the hint on positions; the frames switch "places" |
| `function` | `performed_by`; the hint on new frames; the frames switch "functions"; the performer line of SessionFlow |
| `cooperation` | ontology `cooperation` |
| `gap` | `of` and `scheme`; the hint on gaps; the frames switch "places"; a board holding only gaps and notes counts as empty |
| `note` | the counter a folded region becomes (`smd frames --zoom`) |
| `entry` | only when the profile enables the hint `entry` |

Other meanings come from attributes, so a profile can name these kinds as it likes: a kind drawn as `frame` takes `frame_state`, holds function chips, is found by the `old-frames` and `new-frames` picks and by the hint on new frames; `heading` draws the bold paragraph; `light_off` kinds leave the lighter screen; a board flagged `object` gets the subject-object warning, which names the home boards of the `role` kinds as the place for such talk. No board id is fixed. The halves are `small` and `big` (the schema's enum for `half`).

## Reading steps

`reading` lists the steps of `smd frames --by reading`, each `{step, board, pick}`:
- `step`: one of `entry`, `positions`, `places`, `small`, `big`, `old-frame`, `new-frame`, `object`, each at most once (the steps `smd frames` has titles and texts for, `render/frames_text.py`);
- `board`: the board, or the half (`s.small`), a zoomed step is cut to;
- `pick`: what the step adds, either a filter or `old-frames` / `new-frames` (frames and their contents, by `frame_state`).

A filter is a mapping of at least one of `kinds` (a list of kind ids), `board`, `half` (a half of that board; of any board when `board` is absent) and `frame_state` (`old` or `new`). An element passes when it matches every key given. A step adds only what earlier steps did not show; an empty step is skipped. The SessionFlow picks are filters of the same form.

## Checks of a profile file

A malformed profile is an error of every record that names it (`error: profile: <id>: ...`), and like a schema error it stops the checks of that record:
- a section of the wrong type, a key outside the tables above (at the top, in a board, kind, reading step or filter), a flag other than `true` or `false`, `relations` or `hints` other than a list of strings;
- a duplicate board, kind or reading step id; a missing kind of the table above;
- no boards; `halves` other than `none` or a list of distinct halves; a board off the screen or overlapping another as drawn, a row whose boards do not overlap vertically, a `split` on a board without two halves or outside its region, a colour other than `#rrggbb`, a `screen` other than `regions` or `triangles`, a `triangles` screen with other than its three boards or with a board outside its part;
- a duplicate relation kind or hint id, a hint id the engine does not have;
- a `home` that is not a board; a `shape` outside the list; a kind in `compare_groups` or `compare_skip` that is not in `kinds`;
- a reading step other than the ids above, a step `board` that is neither a board nor a half of one, a filter with an unknown kind, board or half, `kinds` written as a string;
- a SessionFlow block other than `who`, `where`, `what_for`, or a pick that is not a valid filter; an empty filter `{}`, which would match every element.
