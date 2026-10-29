# Golden run: transcript to board

An invented check for the pair `ingest-transcript` then `theses-to-board`. It tells whether a model produces a worse record than the reference one.

| File | What |
|---|---|
| `s3_transcript.txt` | Group session 2 of the invented bakeries case, 60 lines with timecodes. Source `s3` in `../sources.yaml`. |
| `bakeries-c2-expected.board.yaml` | The record the two procedures should make from it, with `../bakeries-c1.board.yaml` as the previous cycle. Valid; no sign-offs. |

The expected record is a hand-checked reference, not the only right answer. `smd eval` shows how far a run is from it; read the unmatched lines before you call a run worse.

## Run it

1. Pack the two procedures with the transcript's manifest and the previous cycle:

```bash
uv run smd pack ingest-transcript cases/example/bakeries-c1.board.yaml --sources cases/example/sources.yaml -o out/pack-ingest.md
uv run smd pack theses-to-board cases/example/bakeries-c1.board.yaml --sources cases/example/sources.yaml -o out/pack-board.md
```

2. Give each pack and `s3_transcript.txt` to the model under test (in Claude Code, `/procedure ingest-transcript` and then `/procedure theses-to-board`). Save the record it writes as `out/run.board.yaml`. The procedures end by writing `run: {procedure, version, model, date}` into the record, which says which model made it.

3. Check that the record is valid, then compare it with the expected one:

```bash
uv run smd validate out/run.board.yaml cases/example/bakeries-c1.board.yaml --sources cases/example/sources.yaml
uv run smd eval out/run.board.yaml cases/example/golden/bakeries-c2-expected.board.yaml --min-agreement 10 --max-only-expected 3
```

## Reading the result

- The first line is the five counts of `smd compare`, with the run as A and the expected record as B: `only_a` is what the run added, `only_b` what it missed.
- Theses are paired by the address they cite: the same source id and, for `#t=` timecodes, a time within 30 s. Other addresses (`#p`, `#l`, `#u`, `#r`) must be equal. A thesis with no `cites` is never paired.
- `--min-agreement N` fails when fewer than N elements agree; `--max-only-expected M` fails when more than M elements of the expected record are missing from the run. Either failure exits 1. Thesis counts are printed and not thresholded.
- The expected record against itself gives 13 agreements and exits 0.

A real case keeps its own golden transcript and record outside this repository.
