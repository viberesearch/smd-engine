# Deal mode: task packs for a sale or transfer

A task pack (see `task-packs.md`) serves a group that answers apart. Deal mode adds optional fields so that the same cycle serves counterparties: a seller, a buyer, brokers, and a neutral holder of one sealed number. Nothing here changes a group pack: a pack with none of the new fields validates, renders and diffs byte for byte as before (`tests/test_deal_golden.py`). Schema stays `0.1`; deal mode came with 0.7.0, 0.7.1 added signatures and per-position agendas, and 0.7.2 bound consents and answers to the pack and added `smd deal verify`. The invented example is `cases/example/deal/`. The decisions behind it are the case owner's, 2 November 2026 (dz02#l=43, dz02#l=47, and dz02#l=55 on the price: asking price first).

What deal mode is for: the parties read the same description of the business, find where they read it differently, and arrive at the table with one picture. They may then agree on everything except the price. That is a normal, successful result, so the price is never a stop. The seller states an asking price in the pack, and the price is bargained at an in-person meeting. Only if the seller switches it on does the engine also report a flag on whether his sealed floor and the buyer's sealed ceiling met.

## The cycle

The cycle of `task-packs.md` stands: pack, term check, blind answers, diff, replies, call, record. What changes is who sees what. The diff may be run again with `--ledger` after a verdict: the second diff replaces the first when it differs only in the verdict fields of the sealed points and the ledger extends the one the first was made from; a model pass written into the file, or a ledger cut short or swapped, still refuses it (`--force` overrides).

| Step | Group pack | Deal pack |
|---|---|---|
| 0. Pack | one file for all | a shared core and an annex per position; the seller states his asking price, and commits a sealed floor at day 0 only if he switches it on |
| 1-2. Answers | blind, each alone | the same; the buyer names no number, only (optionally) whether he is ready to discuss the price; a sealed ceiling exists only with the sealed floor |
| 3. Diff | anyone re-runs it | the shared part, anyone; the sealed part, only the holder program (see "Re-running") |
| 4. Reply | to the one diff | to the view of the member's position (`smd deal views`) |
| 5. Call | the points on `agenda.md` | the same, plus `call_by_pair`; red lines and the price go to the call or the meeting |

## Positions and the audience

`positions` lists `{id, label, kind}` with kind one of `seller`, `buyer`, `broker_sell`, `broker_buy`, `successor`, `family`, `adviser`, `verifier`, `stakeholder`, `other`. Each member has a `position`; a broker also names a `principal` (the member he acts for). An item or an ontology term with `audience: [position ids]` belongs to the annex of those positions; one with no `audience` is the shared core.

The sha256 of the core is what answers pin to (with `pack.annex: {position, sha256}` for the annex), so an annex can change without voiding the answers of the other positions. `smd task check` prints the core sha and each annex sha. `smd task render pack.yaml --position seller` writes the core and the seller's annex only. A pack with several buyers is one pack per buyer.

Krippendorff's alpha is computed on the core only, leaving out items with an audience and items of `nature` value or position (the parties are expected to differ on those). The diff says on how many items it was computed (`alpha.basis`).

## Item kinds

All kinds of `task-packs.md` stay. Deal mode adds these, each switched on by its own fields.

| Kind | Answer | Diff class and route |
|---|---|---|
| `fact` with a `claim` (`text`, `asserted_by`, `source`, `level` stated or checked) | `holds`, `does_not_hold`, `cannot_say`, optional `source_ids` | disagreement is `conflict: fact`, route `check`; a source with `sha256` and `date` is what can settle it |
| `line`: a red line in the shape of `red-lines.md` | `accept` or `reject` | any `reject` is `line_rejected`, route `blocking`: always on the call, a reply cannot accept it |
| `range`: `unit` on the item | `{min, max, unit, date?}` | identical = `agreement`; nested = `refinement`; a common stretch = `compatible` (route `accept_unless_objected`); none = `conflict: value` |
| `bound`: a sealed one-sided limit | a commitment, nothing else | class `sealed`, route `price_meeting`, no answers in the diff |

Two more fields sort the points. `nature` (`term`, `fact`, `value`, `position`) says what kind of disagreement the item can show; a `fit_of` item (does this reading fit what I want) whose reading item conflicts gets `after_reading` and goes to the call. A fact item is used only where a source or the verifier can settle it; two restatements of one fact are a term (procedures `task-pack` and `task-diff` 0.2.0).

A pack may also pin the map the members are asked to accept (`map: {id, version, sha256}`), with a `task_acceptance` record per member in three layers (vocabulary, elements, independent check). The engine records what the member wrote and never writes an acceptance; any edit of the board file voids it. Details: `task-packs.md`, section Deal mode.

## Views

`smd deal views pack.yaml diff.yaml -o out/views` writes `diff.<position>.yaml`, `.md` and `.html` for each position (`--position` limits it). **The full `diff.yaml` in deal mode is the holder's file only.** It holds every answer of every member, the points of every annex (audience), and a `labels` block that names every item. A party is never sent it, nor its `diff.md` or `diff.html`; each position is sent its own view. `smd task diff` prints a warning when it writes a deal diff that has annex points. A view leaves out the annex points not for the position and the entries of the `labels` block for them (`tests/test_deal_views.py` checks that no hidden item id or question is in a view's yaml, md or html). The agenda has its own rules: see "Agendas" below.

A view also leaves out:
- points not for the position (`audience`);
- a fact dispute over a claim of the buyer's side, unless the viewer is on that side;
- on a value point (`nature: value`, a `value` conflict, a range with no nature), the class, route, `sets`, `silent` and the other side's answers. The viewer sees only `open` or `settled`.

A side is sell (seller, sell-side broker), buy (buyer, buy-side broker) or the position alone. A broker is on the side of his principal's position and gets his principal's view of the other side. The summary, `by_pair`, labels and transcripts are cut the same way. A view has a `view` block (`position`, and the sha256 of the whole diff). A reply may carry `view`, the sha256 of the view it answers; `smd task check --replies` refuses another view's sha256. An agenda is built from the whole diff only (see "Agendas").

## Agendas

`smd task agenda` on a deal diff writes the **common agenda**, for every reader of the call. A point with an `audience` (an annex point, also an added point that is not shared) never shows its question, text, refs, options, claim, red line, answers or item id. If it is on the call it appears as `annex-1`, `annex-2`... under the item's `call_title` (a neutral title the pack author writes; `smd task check` warns when an item with an audience has none, or when a core item has one), else under the generic «Точка приложения» / "Annex point". It shows no class, route or reason: the members who chose discuss or did not reply would name its audience, and a rejected red line is not said to be one. It is not listed under a pair in `call_by_pair`, which would name its audience. The item numbers are counted again over the core items, as the core pack numbers them, so a number never skips a hidden item. A settled annex point is left out and the counts follow the lists. The sealed price points are the exception: their verdict is the shared state of the price, so they stay on the list, with class, verdict and who committed, but with no question or id. The `labels` block and `call_by_pair` keep the shown points only. The common agenda is read by both sides, so it follows the sell side's view: a fact dispute over a claim of the buyer's side (`buyer_claim: true` on the diff point, set by `smd task diff`) is left out of it, and a value point shows only `open` or `settled`, with no route and no replies. A diff made before 0.7.1 has no `buyer_claim`; make it again.

`smd deal views pack.yaml diff.yaml -o out/views --replies replies_*.yaml --members a,b,c` also writes `agenda.<position>.yaml` and `.md` for each position it writes views for. The agenda is cut by the rules of the position's view (no point outside the audience, no buyer-side fact dispute for the sell side, a value point shown as `open` or `settled` with the replies of the position's own side only, labels numbered over the items the position holds and `call_by_pair` cut to the points shown) and has a `view` block (`position`, sha256 of the whole diff). A point of the position's own annex keeps its question. A group agenda is unchanged.

`pairs: [{id, members: [a, b]}]` names the member pairs compared on their own. The diff then has `by_pair` (class and route per point from the two answers only) and the agenda has `call_by_pair`.

## Price: the asking price, then an optional sealed floor

The seller knows what he asks. The buyer is still studying the business and gives no number in the pack. The price is bargained at the in-person meeting (route `price_meeting`); the pack gives that meeting a shared starting point.

**Asking price (required).** `deal.asking_price: {value, unit, stage?}` is the seller's asking price, shared with every position. A deal pack with a seller and no asking price is a `smd task check` error, so is a `stage` that is not one of `deal.stages`. The seller chooses the stage at which the pack pages open it. The default is the stage after `nda`; with no `nda` stage, the second stage; with one stage, that one. `smd task render pack.yaml --stage <id> [--position <id>]` writes «запрашиваемая цена» / "asking price" on the pack pages from that stage on; for an earlier stage, or with no `--stage`, the pages say only at which stage it opens. The pack file itself holds the number, so before that stage send a party the page for his stage, not `pack.yaml`. The diff, its views and the agenda are made after the answers and always show the price. The asking price is in the shared core, so changing it voids the answers.

**The buyer's choice.** An optional item in the shared core, at the last stage (item field `stage`), asks "ready to discuss the price: at the level asked / below / not yet" (`cases/example/deal/`, item `price-talk`, `nature: position`). The answer is shown in the diff like any choice and carries no number.

**Sealed floor (optional, off by default).** `deal.sealed_floor: true` switches on the sealed branch below; with `false` or no field, a `bound` item is a `smd task check` error. The branch has two bounds:

| Bound | Who | When | Required |
|---|---|---|---|
| floor | the seller: his lowest acceptable value | day 0, before stage 1, so it cannot be tuned to what the buyer learns | optional; with no floor the verdict is `not_tested` |
| ceiling | the buyer: his highest | only at the last of `deal.stages`, after he has studied the business | optional; no ceiling gives `not_tested` and the price goes to the meeting |

Why it is off: a floor that anyone may test is probed one bit per check, and fake buyers multiply the checks under a per-pair cap. With the branch on, every run against the floor needs the seller's own consent in the ledger, naming the buyer (see "Run cap"), so a fake buyer gains nothing without it.

`smd task check` refuses a ceiling in an earlier stage, a bound without `holder`, `deal.id` and `deal.sealed_floor`, a bound whose `audience` is not the committer's position with exactly one member (a floor is the seller's, a ceiling the buyer's), a broker as `holder.operator`, and a sealed answer that contains anything but the commitment. An operator who is a seller or a buyer is a warning.

**Commit.** On his own machine each party runs `smd deal seal pack.yaml <item> -o <folder outside every repository>`. It asks for the number unseen (or takes `--value`) and writes `sealed_<member>_<item>.yaml` (record `task_sealed`: the number, the unit, and a 64-hex random salt; mode 0600; never overwritten). It prints the commitment:

```text
sha256("smd-seal-v1\n" + canonical JSON of deal, pack id, core sha, item, member, side, unit, value, salt)
```

The commitment goes into the party's answers file as the item's value and is shared like any answer. The salt defeats a guess at round prices; the binding to member, item and pack core ties the commitment to this deal. The page shows no input box. `smd task check` warns about a `sealed_*.yaml` beside the answers that sits in a git work tree and is not ignored.

**Compare.** The holder runs `smd deal verdict pack.yaml <topic> --answers ... --floor <sealed> [--ceiling <sealed>] --ledger verdicts.yaml`. It checks the run cap and the consents, then opens each sealed file, accepts it only if deal, pack core sha, member, item, side and unit are the pack's and the recomputed commitment equals the one in the member's answers, and compares the numbers in memory with the comparator named by `holder.method`. `local-v1` says met when the floor is at most the ceiling. The comparison sits behind a `Comparator` protocol (`src/smd_engine/deal/overlap.py`), so a two-party protocol can replace it without changing the files, the commitments, the ledger or the verdict.

**Result.** One of three flags, never a stop:

| Verdict | Meaning | Reason, when `not_tested` |
|---|---|---|
| `met` | the floor is at most the ceiling | |
| `not_met` | the floor is above the ceiling | |
| `not_tested` | no comparison was made | `no_floor`, `no_ceiling`, `bad_commitment`, `unit_mismatch`, `consent_missing`, `commitment_changed`, `cap_reached` |

The route is `price_meeting`: the parties meet in person and bargain, holding a close picture of the business from the pack. The pages read «цена: условия сошлись / не сошлись / не проверено — торг на личной встрече» (English: "price: terms met / not met / not tested - bargain at the in-person meeting"). A reply to a sealed point is keep or discuss, never accept. No file, page or message gives a number, a salt or the size of the gap.

**Ledger.** `verdicts.yaml` (record `task_verdicts`) is append-only and hash-chained: each entry has `prev_sha256` and its own `sha256`, so an edited entry breaks the chain. It contains verdicts, consents and the public commitments, and no number. `smd task diff --ledger verdicts.yaml` verifies the chain and writes each bound point's `verdict` and the `ledger_head` into `diff.yaml`; a ledger cut short later no longer matches an earlier diff, and `task diff` refuses to overwrite that file. If a party's commitment in the answers is not the one the latest counted run used, the point reads `not_tested` and carries `changed_since_run` (the members), so a verdict is never shown for a number nobody has compared. The first entry of a deal's ledger, the seller's consent to run 1 or a verdict, takes `--new` to start it; without it the file must exist, so a mistyped path cannot start a new ledger with a run count of zero.

**Run cap and the seller's consent.** One run per seller-buyer pair, topic and deal, and every run, the first included, needs the seller's consent entry naming the buyer. A second run needs a consent entry from each of the two parties. `smd deal consent pack.yaml <topic> --member <id> --evidence <file> --ledger verdicts.yaml` logs one; the first consent of a deal takes `--new`, which starts the ledger. The evidence is the party's `task_consent` file: `record`, `deal`, `pack: {id, sha256}`, `keys`, `topic`, `run`, `member`, `buyer` (the member who commits the ceiling) and `commitments: {floor, ceiling}`, the two commitments now in the answers files. The command refuses a file for another member, run, topic, deal or buyer, and a buyer's consent to the first run; the entry keeps the buyer, the file's sha256 and the commitments, and with the sealed floor the file's text (`signed`) and the signature. With a number missing the result is `no_floor` or `no_ceiling`, not `consent_missing`. A run whose commitments differ from those in both consents is `commitment_changed`; after a party changes his number both consent again, and see the new commitment. A file cannot be reused for another party or run. With the sealed floor the file is also signed (see "Signatures"), so the engine can tell who wrote it. A broker cannot consent. Two runs at most; a third is `cap_reached`. A run that returns `not_tested` gives nothing away and does not count. Each counted run gives each side at most one bit.

## Signatures

Without signatures the holder's operator could write both parties' consent files and sealed files (the trust step below). With `deal.sealed_floor: true` the parties sign with OpenSSH keys, and the engine adds no dependency: it calls `ssh-keygen -Y` (OpenSSH 8.0 or later; a sealed-floor command fails with a clear error where it is missing). The private key is never read by the engine.

- **Keys.** `members[].ssh_key` is one OpenSSH public key line (`ssh-ed25519 AAAA... name`). `smd task check` requires it for every member in a seller or buyer position (a broker needs none), refuses a malformed line and a key shared by two members. A member's key is in the core, so changing it voids the answers. Without `sealed_floor` the field is not asked for.
- **Namespace and signer.** Namespace `smd-deal`; the signer principal is the member id.
- **Sealed file.** `smd deal seal pack.yaml <item> -o dir --key <private key>` signs the sealed file after writing it (`ssh-keygen -Y sign`, signature `<file>.sig`). Without `--key`, or when signing fails (a wrong key path or passphrase), it prints the commitment and the command for the party to run; the file stays, since a second seal of the item is refused. The party sends the signature with the sealed file.
- **Consent.** The party signs his `task_consent` file, which names `pack.sha256` (the core sha256 of the pack he was sent) and `keys` (the sha256 of the pack's key list: the lines `<member> <type> <base64>` of every member with a key, comment dropped, sorted, joined by newlines; `key_list_sha` in `signing.py`). `smd deal consent` refuses a consent whose `pack.sha256` or `keys` differs from the pack it is given, and one that names neither (a 0.7.1 consent: the message says to write it again and sign it again); `smd deal consent` takes `--signature` (default `<evidence>.sig`), verifies the file against his key in the pack and refuses a missing or bad signature. The ledger entry also stores the exact text (`signed`, with `evidence` its sha256) and the armored `signature`, so anyone with the ledger can verify the consent again. A ledger from before signatures or before the bindings stays readable; its unsigned (0.7.0) or unbound (0.7.1) consent is replaced by a signed, bound consent naming the same commitments (`smd deal consent` takes it once), since a sealed-floor verdict refuses the old one. A consent whose text the YAML ledger cannot keep exactly (a control character such as U+0085 in a one-line flow-style file) is refused, so that the entry hash stays valid.
- **Answers files.** A member with an `ssh_key` signs his `answers_<member>.yaml` as it is (`ssh-keygen -Y sign -f <private key> -n smd-deal answers_<member>.yaml`, signature `answers_<member>.yaml.sig` beside it); a broker without a key signs nothing. The signature covers the whole file, so he signs again after every change, such as a new commitment. `smd task diff` on a sealed-floor pack only warns for each answers file of a key-holding member that has no valid signature (stderr; the diff is written as usual), since the group may diff before it signs; `smd deal verdict` refuses (see below).
- **Verdict.** In a sealed-floor pack `smd deal verdict` first re-verifies every consent entry it counts for the run (signature, `evidence` against `signed`, the entry's commitments and buyer against the signed text, and `pack.sha256` and `keys` against the pack; a consent that names neither is refused), then the answers file of every member with a key given with `--answers` (`<file>.sig`, signer the member id), then the floor file against the seller's key and the ceiling file, if given, against the buyer's (`--floor-sig`, `--ceiling-sig`, default `<file>.sig`). It refuses the run, and logs nothing, if one is unsigned or bad. A run past the cap counts and opens nothing, so nothing is checked. The verdict entry then records `answers: {member: sha256}`, the sha256 of each answers file it read, and, when the run is counted (`met` or `not_met`), `consents: [entry sha256, ...]`, the consent entries it counted (seller first, by entry number); the hash chain covers both, so a later audit can tie a verdict to its signed inputs. Entries of older ledgers have neither and still verify. A consent names the commitments, so an older answers file swapped back by the operator (its signature still valid) shows as `commitment_changed` and is not counted, and the entry records its sha256 for the party to compare with his own copy; no separate sha rule was added, since a second run already needs both parties' signed consents to the commitments now in the answers.

The operator can still read both numbers (see the threat model); what he can no longer do is consent or commit for a party, within the pack the party holds.

**Limits of the signatures.** In 0.7.1 three things were open; 0.7.2 closes the first two in part and narrows the third.

Closed in 0.7.2:

- A consent is bound to the pack: it names the core sha256 and the key list, so it cannot be carried to a fork of the pack with other text or other keys. An older signed answers file put back by the operator shows as `commitment_changed`, and the answers sha256 is on record in the verdict entry.
- A verdict entry names the consents it counted and the answers files it read, and `smd deal verify` (below) re-checks them against the signed consents, the answers files and, for the holder, the sealed files. A hand-written or replayed entry is a `FAIL`.
- Answers files of key holders are signed; `smd deal verdict` refuses an unsigned one.

Still open:

- A ledger of the old kind from its first entry (no signed, bound consent) passes `smd deal verify` with every line `unbound`, and so does a ledger whose first entries are old and whose later ones are signed: the old entries before the first 0.7.2 entry cannot be told from forged ones, since a 0.7.0 or 0.7.1 ledger is legitimately like that. The summary says "no check failed, but not fully verified" and counts them, and the exit code is 1: an `unbound` line is not proven. `--allow-unbound` gives exit 0 for a ledger known to come from 0.7.0 or 0.7.1. Entries from before 0.7.2 cannot be checked in full, and a consent made before 0.7.2 is refused by a new run.
- The comparison of the two numbers is re-run only by someone who has the sealed files, so the holder or a party who is shown them.
- A consistent forgery from the first entry is caught only by a party who kept an earlier diff or the ledger head. An operator who forks the pack with keys of his own gets a ledger whose consents the fork's parties would have to sign; a party compares the core sha256 of the pack he was sent with the one the holder used.
- A signature proves who wrote a file, not that it is the current one; it is the signed commitments in the consents that catch a replaced answers file, and only for runs that have a consent.

## Verifying the ledger

`smd deal verify pack.yaml --ledger verdicts.yaml [--answers answers_*.yaml] [--sealed <folder>] [--diff diff.yaml] [--json] [--allow-unbound]` is an audit any party or a third party can run. It reads only what it is given, changes nothing, and prints one line per check: `ok`, `FAIL`, `unbound (old entry)` or `skipped` (Russian packs: `ок`, `СБОЙ`, `не привязано (старая запись)`, `пропущено`). The exit code is 1 if any line is `FAIL` or `unbound`, else 0; with `--allow-unbound` an `unbound` line does not make it 1. The last line says `all checks passed` only when nothing failed and nothing is `unbound`; with `unbound` lines and no `FAIL` it says `no check failed, but not fully verified (old entries)`. `--json` prints the same as a machine-readable report: `ok`, `complete` (`ok` and no `unbound`), `counts`, `ledger_head` and the checks, each with `check` (code), `status`, `entry`, `detail` and `text`. A sealed-floor pack needs `ssh-keygen`.

- **Chain.** The entries are numbered in order, each follows the one before it and has the sha256 of its text; the head is printed.
- **Each consent entry.** The signed text hashes to `evidence`; its signature is the member's, made with the key the pack lists, namespace `smd-deal`; the text names this deal, pack id, topic, run, member and buyer, and the commitments of the entry; its `pack.sha256` and `keys` are the pack's. The member is a party to the topic, the buyer is the one who commits the ceiling, and the seller alone consents to the first run.
- **Each counted verdict entry.** The run is the next counted run of the topic and at most two (a `not_tested` entry is not counted). The consents it names (`consents`) are consent entries earlier in the chain, valid by the rule above, for the same topic, run and buyer, with the commitments the verdict recorded, each the latest of its member before the verdict; the seller consented, and for a second run the buyer too (a verdict that names no consents, `consents: []`, is `FAIL` for the same reason: the consents it needs are not among them). The answers sha256 it recorded (`answers`) is matched to the files given with `--answers`: each file is for this text of the pack and signed by its member, and the commitment in it is the one the run used. A recorded file that is not among those given is `FAIL` only for the latest run that read that member's answers, since an earlier run may have read a version nobody passed; for the rest it is `skipped`.
- **`--sealed`, the holder's check.** The folder holds the sealed files and their `.sig`. Each is found by its commitment, checked against the pack (deal, pack core sha256, member, item, side, unit) and its signature, and the comparison of the method the entry names is run again in memory; a result other than the logged one is `FAIL`. A run whose sealed file is not in the folder is `skipped`. No number, salt or gap is ever printed; the report says only `met` or `not_met`. Without `--sealed` the step is skipped and the report says so.
- **`--diff`.** The diff (or a position's view of it) is for this text of the pack. Every bound item it should show (all of them, or for a view those of the position's audience) is there as one sealed point of the item's topic and side; a point left out, shown twice or stripped of its `sealed` block is `FAIL`. Its sealed points name one `ledger_head`, an entry of the ledger, or none (a diff made without the ledger: `not_tested` points are `skipped`, any other verdict is `FAIL`); a mix is `FAIL`. Each sealed point's `verdict` is the one the ledger had at that entry. A point shown `not_tested` over a counted run must carry `changed_since_run`, and the claim is checked: each member it names commits a side of the topic; the answers file the diff read for him (`answers_files`) is not the one the run recorded; and when that file is given with `--answers`, its commitment differs from the one the run used. Without the file the line is `skipped`, not `ok`: give the answers files the diff names to check it; files of that member given, none of them the one the diff names, is `FAIL`. For a committer whose answers files are given, the file the diff names must be one of them (the diff's `answers_files` is the holder's word; the files are signed by the parties). A counted run logged after the diff's head (or at all, for a diff with no head) that read the same answers files of both committers as the diff is `FAIL`: the diff does not show a verdict on its own answers. Any other later counted run is `FAIL` as well unless a file given with `--answers` shows that the diff read other answers than the run did; so an old or removed head cannot hide a verdict, and a party who checks an older diff gives the answers files it names (with the later ones). A view must name a position of the pack, and the report says which. Otherwise a diff made earlier, before more entries were added, still passes. (0.7.3 and 0.7.4; before them a holder could show a logged verdict as `not_tested` with any `changed_since_run`, point the head before the run, or leave a sealed point out, and `--diff` passed.)
- **Entries from before 0.7.2** (an unsigned or unbound consent, a verdict that names no consents or answers) cannot be checked in full and are `unbound`; for a verdict the engine still looks for the earlier consent entries it needed. Once any entry has the 0.7.2 fields, a later entry without them is `FAIL`: the engine always writes them, so such an entry was written by hand. (A 0.7.1 holder program that keeps adding to a ledger a 0.7.2 program has begun is therefore also `FAIL`.)

What it cannot show: an operator who writes a whole ledger of the old kind, with no signed bound consent in it, or who rewrites the entries before the first 0.7.2 entry into the old kind, gets those lines `unbound`, the summary "not fully verified" and exit 1; only `--allow-unbound`, which a party gives for a ledger he knows to be old, turns that into exit 0. The comparison of two numbers is verified only by someone with the sealed files. A ledger that is a consistent forgery from its first entry is caught only by a party who kept a diff or the head. Code: `src/smd_engine/deal/verify.py`, `verify_extra.py`, `verify_diff.py`, `verify_report.py`, `verify_cmd.py`; tests: `tests/test_deal_verify.py`, `tests/test_deal_verify_forged.py`, `tests/test_deal_verify_diff.py`.

## Holder and model consent

`holder: {kind: program|organisation|person, name, operator?, program, method: local-v1}` and `deal: {id, stages?, model_consent?}`. The facilitator sends the pack. The holder is a program: it only does the arithmetic, and in pilots an organisation runs it (the `operator`). A broker never operates it.

`deal.model_consent` is false unless set. The diff then says `model_pass_allowed: false`, the pages say so, and the model pass of `procedures/task-diff.md` stops there; no transcript is read. A diff never takes a `task_sealed` file as input, and neither do `check`, `render` or `agenda`.

## Re-running

In a group pack anyone can re-run the diff from the pack and the raw answers and get the same bytes. A deal pack splits that rule in two.

| Part | Who may re-run | Needs |
|---|---|---|
| Shared part: the diff of the core, views, agenda, `check` | anyone with the pack and the answers | files every party already has |
| Sealed part: the verdict | only the holder program | the sealed files, which only their owners and the holder have |

Anyone can run `smd task diff --ledger verdicts.yaml` and check that the verdict in `diff.yaml` is the ledger's latest and that the chain is intact. Nobody else can repeat the comparison, because they have no sealed file; what they can check is that the commitment in the ledger is the one in the answers. A diff made without `--ledger` shows each bound point as `not_tested`; `task diff` will not overwrite a `diff.yaml` that differs from the new one (without `--force`), so a diff that carries a verdict is not replaced by one that does not.

## Trust step for pilots

In a pilot the sealed files reach an organisation that runs the holder program. This is a trust step in that organisation and its machine; `local-v1` does not remove it. Signatures (above) stop the operator from consenting or committing for a party, not from reading the numbers. No dependency is added for it; the transfer happens outside the engine (decision ДМ5 А).

1. The party encrypts the sealed file to the organisation's age key, on his own machine, and sends only the encrypted file.
2. The organisation decrypts into the run only, on a RAM disk, runs `smd deal verdict`, then unmounts the disk.
3. The party deletes his plaintext sealed file after the run, or keeps it offline.

```bash
age -r age1organisationpublickey -o sealed_vera_price-floor.yaml.age sealed_vera_price-floor.yaml   # the party
diskutil erasevolume HFS+ sealedram $(hdiutil attach -nomount ram://8192)   # macOS: a 4 MB RAM disk at /Volumes/sealedram
age -d -i organisation.key -o /Volumes/sealedram/sealed_vera_price-floor.yaml sealed_vera_price-floor.yaml.age   # the organisation
```

On Linux use a tmpfs such as `/dev/shm`. The hdiutil sector count is in 512-byte units.

## Threat model

| Who | What they are trusted with | What goes wrong if they fail |
|---|---|---|
| the holder's operator | to read both numbers once, in memory, and to log the verdict honestly | it learns both numbers; a dishonest ledger is caught by `smd deal verify` (hand-written or replayed entries, not the numbers) or by a party that kept a diff. With `sealed_floor` it cannot consent or commit for a party in the pack he holds: that needs the party's signature (limits: "Signatures") |
| the party's SSH key | to be kept by the party | whoever holds it can consent and seal in his name; the pack lists the public key, so a changed key voids the answers |
| the party's own machine | to keep his sealed file private | a copy of the file is the number |
| the other party | nothing | learns only what the flag and the shared files show |
| a broker | the shared core and his principal's view | no sealed file, no consent right, never the operator |

What the design guarantees: a party cannot change his number after he commits it without the change showing (the commitment is in the answers and the verdict recomputes it; each counted run records the commitments it used, the diff flags a later change, and a further run needs both parties to consent to the new commitments); the commitment does not reveal a round price (salt); the other party never receives the number or the gap; a cut or edited ledger is detectable against any earlier diff; with `sealed_floor` every counted consent, answers file of a key holder and sealed file carries the party's signature, which the verdict checks before it opens anything, and the consent is tied to the pack text and keys it was written for.

What it does not guarantee. Misstatement before the commitment is unavoidable, since no mechanism makes a party name his true limit (the Myerson-Satterthwaite result); the commitment only fixes it afterwards.

## What leaks

- **One bit per counted run.** A `met` or `not_met` tells the other side whether the floor is at most the ceiling. Run twice at different ceilings and the seller's floor is bracketed. The cap of two runs per pair and topic, the seller's consent to each run, and the consent of both parties for the second, limit this to a pair.
- **More pairs, more bits.** The cap is per seller-buyer pair. A buyer who is not serious could multiply the checks by multiplying packs; that is why a run needs the seller's own consent naming the buyer, and why the sealed floor is off unless he switches it on. The engine does not tell a serious buyer from a probe; the seller decides whom to send the pack to, whether to commit a floor at all, and which buyer to consent to.
- **The holder's operator** sees both numbers in memory at the run, and the plaintext on the RAM disk for its duration. Swap and core dumps on that machine are outside the engine.
- **`committed_by` and `silent`** in the diff show who committed and who did not. A buyer with no ceiling is visible as such; the verdict `not_tested` with `no_ceiling` adds nothing to it.
- **The signature files and the ledger.** A signed consent entry stores its exact text and signature, so anyone with the ledger can read the buyer named, the commitments and the date. The signatures carry the member id as signer and nothing about a number.
- **The ledger** shows the dates of runs and consents and the commitments, which are in the answers anyway.
- **The cap-reached and consent-missing reasons** show that a further run was asked for.
- **Views** keep the other side's value answers out, but a viewer still sees every shared-core point. The common agenda shows a value point as `open` or `settled` only, and who discussed or did not reply, but not their answers, and nothing of an annex point but a neutral title (see "Agendas"). The id of an added point in a deal pack is `add-<member>-<8 hex of the sha256 of its text>` (with `-2`, `-3` on a repeated shared text; a point the author kept to his position hashes its text with a prefix, so its id differs and no private copy is counted in the suffix of a shared one), so the id of a shared point does not tell how many unshared points its author has; it is the same for the same answers file. A group pack keeps `add-<member>-<n>`. A 0.7.1 diff has the old ids; make the diff again, and the replies that name them with it.

Sealed values and salts do not appear in `diff.yaml`, `diff.md`, `diff.html`, an agenda, a view, the ledger or an error message; tests grep those outputs for the test numbers and salts (`tests/test_deal_sealed.py`, `tests/test_deal_verdict.py`).

## Commands

`smd task check | render | diff | agenda` take the new fields (`render --stage`); the deal commands are `smd deal views | seal | verdict | consent | verify`. Examples: `commands.md`.

## Not yet built

- A two-party or split-trust comparison (a multiparty protocol instead of `local-v1`): the `Comparator` protocol is the place for it.
- Real use of the sealed branch in a deal, before one role-play and one consenting deal.
