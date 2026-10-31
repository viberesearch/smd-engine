# Golden run: transcript to board

An invented check for the pair `ingest-transcript` then `theses-to-board`. It tells whether a model produces a worse record than the reference one.

| File | What |
|---|---|
| `s3_transcript.txt` | Group session 2 of the invented bakeries case, 60 lines with timecodes. Source `s3` in `../sources.yaml`. |
| `bakeries-c2-expected.board.yaml` | The record the two procedures should make from it, with `../bakeries-c1.board.yaml` as the previous cycle. Valid; no sign-offs. |

The expected record is a hand-checked reference, not the only right answer. `smd eval` shows how far a run is from it; read the unmatched lines before you call a run worse.

It stops where the two procedures stop. The functional plan is drawn by `functional-plan`, so `smd validate --hints` on this record still reports the hints `function-flows`, `unlinked-functions` and `idle-positions`, which `../bakeries-c2.board.yaml` clears with `flow` relations. They are left here on purpose: `smd eval` compares elements, theses, K and H, not relations, and a record that carries a plan the transcript does not state would not be what the two procedures produce.

## Run it

1. Pack the two procedures with the transcript's manifest and the previous cycle:

```bash
uv run smd pack ingest-transcript cases/example/bakeries-c1.board.yaml --sources cases/example/sources.yaml -o out/pack-ingest.md
uv run smd pack theses-to-board cases/example/bakeries-c1.board.yaml --sources cases/example/sources.yaml -o out/pack-board.md
```

2. Give each pack and `s3_transcript.txt` to the model under test (in Claude Code, `/procedure ingest-transcript` and then `/procedure theses-to-board`). Save the record it writes as `out/run.board.yaml`. The procedures end by writing `run: {procedure, version, model, date}` into the record, which says which model made it. The optional fields `pack_sha256` (the hash `smd pack` printed), `inputs`, `temperature` and `sample` say what it ran on (`docs/data-model.md`, `run`).

3. Check that the record is valid, then compare it with the expected one:

```bash
uv run smd validate out/run.board.yaml cases/example/bakeries-c1.board.yaml --sources cases/example/sources.yaml
uv run smd eval out/run.board.yaml cases/example/golden/bakeries-c2-expected.board.yaml --min-agreement 10 --max-only-expected 3
```

4. To measure how stable a procedure is, run it N times on the same pack and transcript (three is the least that tells much), each time in a fresh session, and save the records as `out/run1.board.yaml`, `out/run2.board.yaml`, `out/run3.board.yaml`. Give each its own `run.sample` (1, 2, 3) and the same `run.pack_sha256` and `run.inputs`. Then:

```bash
uv run smd agree out/run1.board.yaml out/run2.board.yaml out/run3.board.yaml
```

`smd agree` prints Krippendorff's alpha for the labels the model chooses (`belt`, `kind`, `status`, `voice`, a move's `op`, a gap's `of`), and how many cite addresses every run found. It warns when the records do not share a procedure, a pack hash or inputs. Read it with `docs/commands.md`, `agree`.

## Reading the result

- The first line is the five counts of `smd compare`, with the run as A and the expected record as B: `only_a` is what the run added, `only_b` what it missed.
- Theses are paired by the address they cite: the same source id and, for `#t=` timecodes, a time within 30 s. Other addresses (`#p`, `#l`, `#u`, `#r`) must be equal. A thesis with no `cites` is never paired.
- `--min-agreement N` fails when fewer than N elements agree; `--max-only-expected M` fails when more than M elements of the expected record are missing from the run. Either failure exits 1. Thesis counts are printed and not thresholded.
- The expected record against itself gives 13 agreements and exits 0.

A real case keeps its own golden transcript and record outside this repository.
