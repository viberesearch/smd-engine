# Your first board

From an empty folder to a validated, drawn board, and then the first procedure to run. The example is invented: a family bakery whose owner wants to hand the daily running to a hired manager. Terms are in `glossary.md`.

`smd` below stands for however you run the engine: an installed `smd`, `uv run smd` in a checkout, or `uvx --from git+https://github.com/viberesearch/smd-engine smd` (README, Install). Every command here was run as shown, in an empty folder.

## 1. Choose a profile

A profile sets the boards and the kinds of elements a record may hold. Choose it at the first record; a record without `profile` uses the default.

| Profile | Choose it when | Boards |
|---|---|---|
| `program-three-boards` (default) | A person or a group works out its own activity: who we are, in what situation, what for. The first board of almost every case | org-activity `od`, object `oo`, situation `s` (small and big halves) |
| `classic-two-boards` | You work on an object and the activity around it, and the situation is not the question | `od`, `oo` |
| `management-four-boards` | The question is how an organisation is run: leadership, apparatus, the managed system (G.P.'s scheme of ОРУ) | `od`, `ot`, `ap`, `us` |

The bakery starts on the default profile. Three procedures (`small-situation`, `visionary-tract`, `qualification-pass`) are written for it, and `smd pack` refuses them on another profile.

## 2. What a record must have

A record is one YAML file. These top-level fields are required:

| Field | Value |
|---|---|
| `record` | `board_set` |
| `schema_version` | `"0.3"` (in quotes) |
| `id` | lowercase letters, digits, `.`, `_`, `-` |
| `title` | one line |
| `cycle` | `1` for the first record |
| `status` | `draft`, `extracted` or `verified` |
| `elements` | at least one, each with `id`, `board`, `kind`, `label` |

`smd new` (section 3) writes all of them. Leave out `title` or `status` and the validator says so:

```text
FAIL broken.board.yaml
  error: (root): 'title' is a required property
  error: (root): 'status' is a required property
1 record(s), 2 error(s), 0 warning(s)
```

## 3. The first record

`smd new` writes a folder that validates at once: the first record with these fields, the manifest of section 5 and a short README with the next steps. Run it with the profile, the language of the labels and a title:

```bash
smd new bakery --profile program-three-boards --lang en --title "Family bakery, handover to a manager, screen after session 1"
cd bakery
```

```text
bakery/bakery-c1.board.yaml
bakery/sources.yaml
bakery/README.md
next: smd validate bakery --sources bakery/sources.yaml --hints
```

The case id comes from the folder name (`--case` sets it); `smd new` refuses to overwrite a file that is there. The record, `bakery-c1.board.yaml`, ends with empty lists for what the procedures fill and a `state` naming the first procedure. Its two elements are the whole content:

```yaml
elements:
  - {id: entry, board: od, kind: entry, label: "entry"}
  - {id: p-start, board: od, kind: position, label: "the position the work starts from (rename it)"}
```

The `entry` is where the session starts; a `position` is a place in the activity. The board is `od`, the org-activity board. The kinds a profile allows are listed in its file, `profiles/program-three-boards.yaml`. Rename the position in the file, with an id of your own:

```yaml
  - {id: p-owner, board: od, kind: position, label: "owner, who has run the bakery for 30 years"}
```

```bash
smd validate bakery-c1.board.yaml --hints
```

```text
ok bakery-c1.board.yaml
  hint: oo: object board is empty
  hint: s/small: small situation not laid out
  hint: s/big: big situation not laid out
  hint: od: 1 position(s) and no places for others: positional set looks incomplete
1 record(s), 0 error(s), 0 warning(s)
```

No errors, so the record is valid; `--strict` would also pass, since there is no warning. The hints say what the board still lacks. Most of it is the work of the procedures in section 6. The last one you can fix by hand: add two places for others (those the activity gives to or takes from) to `elements`:

```yaml
  - {id: place-staff, board: od, kind: place_for_others, label: "the baking staff",
     seen_from: p-owner}
  - {id: place-regulars, board: od, kind: place_for_others, label: "regular buyers",
     seen_from: p-owner}
```

`smd validate bakery-c1.board.yaml --hints` now prints the first three hints only. An error would exit with 1 and name the element; a warning breaks a convention of the method (`--strict` fails on warnings).

## 4. Draw it

```bash
smd render bakery-c1.board.yaml --lang en -o out/screen.svg
smd render bakery-c1.board.yaml --lang en --format md
```

The first writes the screen as SVG (`--format html` gives a page with tables); the second prints a Markdown digest, one line per element. Drawings are generated from the record and are never edited by hand. Labels over 60 characters are cut on the screen with a warning; give the element a `short`.

## 5. Register what you bring

Procedures read sources, and records cite them by id. `smd new` wrote `sources.yaml` with one entry, `s1`, that points to `notes.txt`; the record already lists `s1` under `sources`. Save the owner's notes as `notes.txt` in the folder, then record their checksum:

```bash
smd sources sources.yaml --folder . --refresh s1
```

```text
s1: sha256 updated, 5 lines
```

`--refresh` writes the checksum into the manifest (the line count is that of your file); `smd sources sources.yaml --folder .` checks it later. Edit the entry's `title` to say what the file is, and list further files as further entries (the fields of an entry are in `docs/data-model.md`). Then:

```bash
smd validate . --sources sources.yaml --hints
```

A folder is validated record by record, each cycle against the one it revises.

Bring material for the four questions the first procedure asks: who we are and what we do; where we are, in what system of activity; what we are for there; what our activity rests on. Notes, a dialogue log or a transcript will do.

## 6. The first procedure

With the default profile the first step is `small-situation` (`procedures/solo-session.md`, section 3). It lays out the small situation, the positions and places for others, and the first hypotheses from the answers. With a recorded group talk, start with `ingest-transcript` and then `theses-to-board`; they work on any profile, and so does `stakeholder-ontology`.

```bash
smd pack small-situation bakery-c1.board.yaml --sources sources.yaml -o pack.md
```

```text
pack sha256: dfff1746f208cecc0a4f50cf7ba6a91776abd3f60cf0dd0e256eb5b90f05ded6
```

The hash goes to stderr; it names this exact pack. The hash above is of this walkthrough's files, yours will differ.

1. Attach `pack.md` and `notes.txt` to a model and say "run this procedure". In Claude Code, inside this repository, `/procedure small-situation <full path>/bakery-c1.board.yaml` does the same.
2. The model proposes the next cycle. Save its record as `bakery-c2.board.yaml`. It cannot sign anything off; what it leaves for you is in `state.open`.
3. Run `smd validate . --sources sources.yaml --hints` and fix what it reports. The record should carry a `run` stamp; give the model the pack hash for `pack_sha256` (`docs/data-model.md`, `run`).
4. Decide: record your sign-offs in the next cycle with `smd revise`, or as a patch with `smd apply` (`commands.md`).

## 7. What comes next

`solo-session` runs the steps in this order, stopping for your decision after each; each procedure names its follower in `next`.

| # | Procedure | What it adds |
|---|---|---|
| 1 | `small-situation` | the small situation, positions, places for others, hypotheses |
| 2 | `visionary-tract` | the big situation: boundary of normality, a series of linked events, a model from another domain |
| 3 | `positional-construction` | the positions in which the move becomes possible |
| 4 | `functional-plan` | functions with who performs, pays and receives |
| 5 | `problematization` | gaps and problems on a named scheme |
| 6 | `qualification-pass` | K remarks against the criteria |
| 7 | `reflexive-protocol` | closes the cycle and opens the next |

At any point, `smd next bakery-c2.board.yaml` names the procedure to run next with a line why, and `smd status bakery-c2.board.yaml --lang en` prints the open K, the hypotheses and the sign-offs waiting on one page (`commands.md`). The index of procedures is `procedures/README.md`; the build steps and where each method enters are in `stages.md`.
