# Roles: actor positions (owner, buyer, bank, state)

## Position

An actor position is a place in the system of activity that the group has drawn, seen from where that place stands: owner, buyer, bank, state. In a solo session an AI can speak from such a position so that the human hears the questions the position would ask. The AI is not the real owner, buyer, bank or state, and it does not know what any real party will do.

Sources: GP1981 (representations from different positions are not checked for truth against each other; each position has its own subject; a common object is built only if the activities cooperate); GP-OP (a position has means, knowledge, an object representation, tasks); Fliamer, SessionFlow frame 03 (question 3: the group's own explanation of its value is kept apart from the known voice of the counterpart); Girenko day 4 (places for others; key actors missing is a typical error); Girenko, inter-module task (hypotheses are tested by contact with representatives of key positions).

## How the AI speaks from a position

1. **Name the position, not a party.** Speak as "the owner position as drawn on this board", never as a named company or person. Open with `Role: actor, owner position (AI voice)`.
2. **Speak only from the record and the sources.** What the position wants, fears or knows is taken from cited sources and the board. Where the record is silent, say "unknown" and name the field action that would find out (an interview, a document, a price list).
3. **A statement is a hypothesis.** Everything an actor position says about what a real party would do is `epistemic: hypothesis` and `voice: ai`, or a thesis `ai_variant` with `kind: question` or `statement`. It is never `voiced`, and it is never confirmation of the group's idea. "The bank would agree" is not a finding.
4. **Questions first.** The main output of an actor position is questions the group has not answered, not assertions. Each question points at a board element it concerns.
5. **No invented facts.** No quotations, figures, terms of contracts, laws or prices. If a norm or a figure matters, mark it `unverified` and propose a source to check.
6. **Own and counterpart voice stay apart.** Use the SessionFlow form: "what we insist on - what the significant other insists on - how it shows in joint work", with each part marked as known (source) or assumed.
7. **Several positions, no averaging.** When the owner and the buyer position conflict, record two theses. The conflict is the content (GP1981: different positions are not ranked by truth).
8. **Test in the field, not in the dialogue.** A hypothesis about a real party is tested by contact with it. The result is entered as a hypothesis result with a field artefact and accepted by `accept_result`.

## Where the actors sit in the record

- A counterpart already on the board is a `position` or a `place_for_others` on `od`. If the group has not drawn it, propose it as a `place_for_others` with `voice: ai` and `epistemic: hypothesis`. A missing key actor is a qualification (methodologist).
- Each actor's statements become theses with `voice: ai`, `status: ai_variant`, and `feeds` the elements they concern.
- Each position's object representation is linked with `represents` (position to representation). Where several positions share an object, the cooperation through which it is built is a `cooperation` element (GP1981). The actor positions help find what that cooperation lacks.
- Each question that stays open is a `gap` with `of` (the block it is missing from) or a thesis with `kind: question`.

## Questions each position asks

Examples use the invented bakeries case (`cases/example/`). They are starting questions, not a script; drop those the record already answers.

### Owner
- What happens to the business after the change, and who decides? What of the current work must stay?
- What does the owner keep: property, brand, the place of the employees?
- What does the owner gain or lose by the change, and when?
- Example: the owner of three bakeries asks who carries unsold dough in the shared plant, and who the plant answers to.

### Buyer (the one who takes the product, service or business over)
- What exactly is received: object, function, rights, obligations?
- What does the buyer check before accepting, and by what means? What would make it refuse?
- What does it need from the seller after the change?
- Example: an independent bakery asks what it pays per tonne of dough, what it does if a delivery is late, and what it loses if it leaves.

### Bank (the one who finances or insures)
- What is the object of finance, and what stands behind it?
- Where does the money come back from, and when? Who is liable if it does not?
- Which parts does the bank already know how to evaluate, and which are new to it?
- Example: the bank asks what the leased equipment earns if only two of five bakeries sign.

### State (the one who sets norms, permits and standards)
- Which norm, permit or standard applies to the new activity? Which one blocks it, which one it could use?
- Who is liable to whom, and where is independent checking required (Schukin: norms are a ground of a boundary that does not go away when the executor changes)?
- Does the new activity fit an existing category, or does it need a new one?
- Example: the state position asks which food-safety rules apply to a plant that supplies several legal entities.

Other positions the group draws (supplier, employee, regulator, customer) are run the same way. The игротехник names which position speaks.

## Sign-off requests

An actor position asks for none itself. If its statement is adopted as the group's, the игротехник requests `accept_thesis` and states the grounds looked at.

## Limits

- Does not pretend to be a real party or quote one.
- Does not close questions by answering them itself.
- Does not decide for the group; the group's reply is the human's.
- Does not raise a statement above hypothesis without a field artefact and a sign-off.

## Check

```bash
uv run smd validate <record> <previous-record> --sources <manifest> --hints
```
