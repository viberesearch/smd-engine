# Roles and actors on the boards

Adopted 27.10.2026 after a pilot case, where places for others mixed roles (a sponsor) with actors (state institutions, guarantee funds) on one board.

## Rule

The org-activity and object boards hold roles: positions, places for others, gaps of `of: position`, functions. A role says what is done, and in which cooperation, without naming who does it.

Actors are not elements of their own. An actor is a form that can occupy a role: the state, a region, a fund, a bank, a type of company or person. Actors are listed in the `fillers` of the role they can occupy.
- One actor may occupy several roles. The state can be the regulator of deals and also a sponsor.
- One role may have several fillers.

The situation board is different: facts, signals and series of events describe the world in its own forms, so actors appear there by name.

## Grounds

- Positions are places in cooperation, each with its own means, knowledge, tasks and view of the object. A positioner is the carrier who occupies a position [V GP-OP, GP1981]; see `smd-classic.md` 2.5.
- An empty place is a place in a scheme, not a missing person [V GP-PP].
- A job title, a profession or an agent doing one operation is not a position [Schukin].

## Test

Read the label as "what is done, for whom, in this cooperation", without saying who does it.
- If the label reads that way, it is a role.
- If the label names an organisation type, a person type or a list of them, it is an actor. Name the role it occupies and move the actor to `fillers`.
- A function's `performed_by` points to a role, never to an actor.

Examples from the invented bakeries case (`cases/example/`), as a group might first write them:

| On the board | Role | `fillers` |
|---|---|---|
| «мельницы и оптовики: поставляют муку» | поставщик муки: поставляет сырьё цеху по договору | мельницы, оптовики |
| «банк, региональный фонд, регион — оплачивают часть лизинга оборудования…» | финансирующая сторона: платит за оборудование цеха в обмен на свои условия возврата | банк, региональный фонд, регион |
| «гарантийные фонды» | гарант лизинга цеха | гарантийные фонды |

## Terms

- **Stakeholder** (стейкхолдер, заинтересованная сторона) names the role of whoever has an interest in the object of thinking and in what continues after the change.
- A stakeholder may set a red line, and then pays for its slice of the map, log and verification. Relief counts as payment.
- Avoid «бенефициар» in Russian labels: it reads as «бенефициарный владелец» (the beneficial owner under 115-ФЗ).

## A role with structure

When one role has inner structure, the board shows one element with a `short` label, and its `detail` table holds the structure. Example: stakeholders on each of the six tiers of OST (Organizational Schema Theory), from the owner's intent to the organisation. In English the six are tiers and L0–L5 are the levels of the OST projection cascade; in Russian records «уровень» means a tier only.
- Columns of that table: tier, stakeholder, `fillers`, example of a line, data to check it by.
- The table appears in the frames panel on click, in the HTML tables and in the Markdown digest. It is never drawn on the board.
- Split the role into separate board elements only when the session works each part on its own.

## Where the rule is applied

- `theses-to-board`, step 2: an actor in a thesis becomes a filler of a role.
- `positional-construction`: the positional set is a set of roles.
- `stakeholder-ontology`, section 0: the position whose ontology is elicited is a role; the person who occupies it is its filler.
- `qualification-pass` 3.3, check "Role, not actor": a К, or a label fix by whoever wrote the record.
- `smd validate` checks the form only: `fillers` sits on roles, and `detail` rows match their columns.
