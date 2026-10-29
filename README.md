# smd-engine

[Русская версия: README_ru.md](https://github.com/viberesearch/smd-engine/blob/main/README_ru.md)

`smd` is a command-line tool for thinking sessions in the SMD tradition (system-thought-activity, the Shchedrovitsky school). It does five things:

1. Keeps the state of a session as a YAML record: boards, positions, frames, functions, gaps, qualifications, numbered transitions, theses from the transcript, hypotheses, human sign-offs.
2. Checks the record against the schema, the conventions of the method and, across cycles, against the previous cycle.
3. Draws the record as an SVG screen, step-by-step frames, a 3D graph, an index with YAML lines, Markdown, Mermaid or an Obsidian vault. Drawings are generated, never edited by hand.
4. Applies decisions as records: a patch to the current cycle, or the next cycle with the human's sign-offs.
5. Packs a thinking procedure, its roles and lenses into one Markdown file that any model can run, and compares what a run produced with a reference record.

The default screen is the three-board screen of the MIPT program "Третья ступень" (org-activity, object and situation boards). A profile can lay out other boards: `classic-two-boards` is the classic org-activity and object-ontological pair. Terms that belong to the program and not to the classic method are marked as such in `roles/README.md`.

Version 0.3.6, schema 0.3. Python 3.14. The engine proposes and checks; a human decides, by sign-offs that each state a function.

## Install

Run without installing, from the repository:

```bash
uvx --from git+https://github.com/viberesearch/smd-engine smd validate path/to/case
```

Or install from PyPI:

```bash
pip install smd-engine
smd --help
```

From a checkout, for development (`uv` only):

```bash
uv sync
uv run smd --help
```

The package carries the procedures, roles, lenses, profiles and the data model, so `smd pack` works from an installed copy.

## Try it

The repository has invented teaching cases in two folders. In the main case three bakeries consider shared production for independent bakeries of a region. `cases/example` (English labels) holds its two cycles (`bakeries-c1`, `bakeries-c2`), the same case on the classic two boards (`two-boards-c1`), a patch and a golden run. `cases/example_ru` (Russian labels) holds the same two cycles (`pekarni-c1`, `pekarni-c2`) and two records on the profile `management-four-boards` that the English folder does not have: the bakeries on G.P.'s scheme of organisation, leadership and management (`pekarni-oru-c1`), and a regional holding that buys one of the bakeries, on the Beer layer (`pekarnya-holding-c1`).

```bash
uv run smd validate cases/example_ru --sources cases/example_ru/sources.yaml --hints
uv run smd render cases/example_ru/pekarni-c2.board.yaml -o out/screen.svg
uv run smd frames cases/example_ru/pekarni-c2.board.yaml -o out/frames.html
```

## Commands

Examples with options are in `docs/commands.md`; `smd <command> --help` lists the options.

| Command | What it does |
|---|---|
| `validate` | Schema, errors, warnings and (with `--hints`) methodological hints for records or folders; exit 1 on errors |
| `migrate` | Moves records from schema 0.2 to 0.3; reports by default, `--write` edits the changed lines in place |
| `render` | One board set as SVG, HTML, Markdown, Mermaid or SessionFlow text |
| `frames` | Step-by-step frames in one HTML page, in reading order or one per cycle, with texts per frame |
| `graph` | The boards as stacked planes in 3D, records above, sources below; one self-contained page |
| `index` | Every K, thesis, hypothesis, O, sign-off and element with its YAML line and source link |
| `publish` | Validates, then writes frames, cycle frames, index, graph and page as one bundle |
| `vault` | An Obsidian vault: a note per element, thesis, hypothesis, K and source |
| `sources` | Lists a source manifest, checks files and sha256, splits sources for a clean-room run |
| `compare` | Matches the elements of two board sets and classifies agreement, refinement, conflict; `--merge` drafts a cycle |
| `eval` | Compares a procedure run with an expected record; exit 1 below the thresholds |
| `revise` | Opens the next cycle of a board set and applies the human's sign-offs |
| `apply` | Applies a patch (add, set and remove by id or by transition number `n`, `board_notes`, state) to a board set as its next sub-version, then validates |
| `pack` | One Markdown file with a procedure, its roles, lenses, the data model, the cells to fill and the records, for any model |

## Data model on one screen

Full format: `docs/data-model.md`. Records are YAML; JSON Schemas are in `src/smd_engine/schemas/`.

| Record | What it is |
|---|---|
| `board_set` | One cycle of a screen. Top level: `id`, `case`, `cycle`, `revises`, `status`, `sources`, `profile`, `run`, `applied`, `state` |
| `source_manifest` | The case's raw materials, listed and not copied: `id`, `kind`, `origin`, `file` or `url`, `sha256`, `lineage`, `clean_room` |
| `taxonomies` | Values that `tags` and bound `detail` columns may take |
| `board_patch` | A decision on the current cycle: `add`, `set`, `remove`, `state` |

Inside a `board_set`:

| Part | Content |
|---|---|
| `elements` | `id`, `board`, `kind`, `label`; optional `seen_from` (the position it is seen from), `in`, `performed_by`, `fillers`, `detail`, `cites`, `voice`, `epistemic`, `move`, `lens` |
| `relations`, `transitions` | Links between elements; numbered moves between boards |
| `qualifications` | `K1..Kn`: remarks of the methodologist, `open`, `partly` or `closed` |
| `theses` | Cards from a transcript: `claim`, `voice`, `status`, `belt`, `kind`, `feeds`, `cites` |
| `hypotheses`, `ontology` | Field tests with results; pictures valid for named positions, with a realizability test |
| `signoffs` | Human decisions, each with a function: `close_k`, `accept_move`, `accept_thesis`, `accept_result`, `verify_record` and others |
| `state` | The one-line state after a cycle: `version`, `difficulty`, `accepted`, `open`, `next_move` |

Rules the validator enforces: nothing lies on a board without a position it is seen from; an AI voice never signs off; an AI variant stays a variant until a human sign-off raises it; every closed K, refined thesis and confirmed result needs its sign-off. Addresses in `cites` point into sources by id and time, page, turn or line: `s3#t=00:08:10`.

## Profiles

A profile (`profiles/*.yaml`) holds the boards, the element kinds, the relation kinds, the hints in force and the reading steps of `smd frames`. A record names its profile in `profile`; without it, `program-three-boards` applies. The profile format, with the layout of boards by their regions, is in `docs/profiles.md`.

| Profile | Boards |
|---|---|
| `program-three-boards` (default) | org-activity `od`, object `oo`, situation `s` with a small and a big half |
| `classic-two-boards` | org-activity `od` and object-ontological `oo` side by side; no situation board |
| `management-four-boards` | G.P.'s scheme of organisation, leadership and management: org-activity `od` and the upper system `ot` on top, the apparatus of leadership `ap` and the managed polysystem `us` below; a labelled layer from Beer's viable system model (systems 1-5, red lines as algedonic channels) |

An unknown profile, board or kind is an error naming the element. Format and the keys of a profile: `docs/data-model.md`, section Profiles.

## How a case repository uses the engine

A real case lives in the repository of its object of thinking; this repository holds invented examples only. A case repository keeps:
- board sets, one file per cycle (`<case>-c1.board.yaml`, `-c2`, ...) and patches (`*.patch.yaml`);
- one `sources.yaml` manifest: ids, checksums and the clean-room decision for each source. Raw materials stay where they are and records cite them by id;
- optionally a `taxonomies.yaml`.

It runs the engine without a local copy, pinned to a release, for example in CI:

```bash
uvx --from git+https://github.com/viberesearch/smd-engine@v0.3.6 smd validate . --sources sources.yaml --strict
```

Generated drawings (`smd publish`) are build output and are not committed. Records of an older schema are moved with `smd migrate`.

## Run a procedure with any model

A procedure (`procedures/*.md`) is a model-agnostic prompt. The roles and lenses it uses, and the data model, are packed with it:

```bash
smd pack small-situation cases/example/bakeries-c1.board.yaml --sources cases/example/sources.yaml -o pack.md
```

1. Attach `pack.md` and the source files the procedure names to any model, and say "run this procedure".
2. The model returns a record. It proposes; it does not sign off. Decisions it cannot take go to `state.open`.
3. Save the record and run `smd validate` on it. Fix what it reports.
4. For a reference run, `smd eval run.board.yaml expected.board.yaml --min-agreement N` shows whether the run got worse (`cases/example/golden/README.md`).
5. Record the human's decisions as sign-offs or as a patch (`smd apply`), and open the next cycle with `smd revise`.

In Claude Code, inside this repository, `/procedure <id> <inputs>` runs a procedure directly; role subagents are in `.claude/agents/`. `smd pack --help` lists the options. The procedures are listed in `procedures/README.md`, the lenses in `lenses/README.md`.

## Repository contents

| Path | What |
|---|---|
| `src/smd_engine/` | the package: schemas, validator with a check registry, renderers, profile loader, `apply`, `migrate`, `eval`, `pack` |
| `profiles/`, `procedures/`, `roles/`, `lenses/` | method files as data; shipped in the wheel under `smd_engine/assets/` |
| `cases/example/`, `cases/example_ru/` | invented teaching cases |
| `docs/` | data model, commands, method notes; index in `docs/README.md` |
| `CONTRIBUTING.md`, `CHANGELOG.md` | how to change the engine; what each release added |

## Licence

Code is under the MIT licence (`LICENSE`). Method notes, procedures, roles, lenses, profiles and the example cases (`docs/`, `procedures/`, `roles/`, `lenses/`, `profiles/`, `cases/`) are under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): reuse them with attribution. Copyright (c) 2026 viberesearch.

The method notes summarise published work of G. P. Shchedrovitsky and others and cite it (`docs/method/sources.md`); the original texts keep their own rights.
