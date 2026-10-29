# Structural moves: the preprint behind the `move` field

Part of the method notes, compiled 2026-10-25 from the paper's text. `docs/stages.md` says where the moves enter the engine; this note says what the paper claims and where it stops.

## Citation

Zharnikov D. (2026). *Invention as a Structural Operation: Why the Abductive Jump Is a Re-Coordinatization of the Space of Description, Not a Sensory Leap.* Working Paper v1.0.0, Zenodo, CC-BY-4.0, published 2026-07-28.
- Concept DOI (all versions): doi:10.5281/zenodo.21653102; v1: doi:10.5281/zenodo.21653103.
- Public repository: https://github.com/spectralbranding/meaningfulness-papers/tree/main/invention-as-structure

## Thesis

The common position (cited to Zahavy 2026, "LLMs can't jump") holds that generative models have mastered induction and are conquering deduction, but cannot make the abductive jump to new axioms, because that needs embodied simulation. The paper replies that the jump is misdescribed:
- A representation is a typed structure in which a domain's regularities are stated.
- An invention is a morphism that changes the representation, not a new datum found inside a fixed one.
- Such operations form a small closed set of four types, and a selection functional chooses among candidates.
- Where compatibility is decidable, generating the move is mechanizable.

The paper names its precedents (Kuhn, Spivak's ologs, Friedman, Boden, Gärdenfors, Fauconnier-Turner). Its stated contribution is the combination: the closed four-move calculus, the selection functional and a running adjudicator.

## The four operations

| Engine `op` | Paper | Symbol | Definition | Paper's examples |
|---|---|---|---|---|
| `adjoin` | adjoin a dimension | α | make a latent degree of freedom explicit as an independent axis | observer-indexed time in special relativity; gene duplication; a new demand axis in a market |
| `rescale` | rescale or requantize | ρ | change the unit or grain, quantize the continuous, move to a log or renormalized scale | dimensional analysis in symbolic regression; polyploidy |
| `respecify` | re-topologize or re-specify | τ | change the connectivity or the admissible morphisms; promote a measured equality to a structural identity by a quotient | inertial and gravitational mass in general relativity (τ with α); exaptation |
| `glue` | glue (pull back) across domains | γ | find a shared substructure S of R1 and R2 and form R1 x_S R2 | conceptual blending; symbiogenesis |

- Gluing is a pullback over a shared substructure, not a mixture.
- New primitives (the imaginary unit, entropy) are a special case of adjunction: "structural completions under a consistency demand".
- The closure claim is falsifiable: an invention whose minimal description needs a fifth operation refutes it.
- Beyond prose and the pullback notation, the paper gives no formal definitions.

## Selection functional

S(R') = a1·DL(A_R') − a2·Sym(R') − a3·Clo(R') + a4·E(R'), minimized:
- DL is the description length of the axioms, not of the data;
- Sym rewards symmetry, Clo closure or consistency;
- E is empirical inadequacy against whatever evidence exists;
- the weights a_i are non-negative and have not been robustness-checked.

Generation and validation are one process in empirical science. The Zurich notebook (Janssen 2007) shows Einstein dropping the correct curvature structure for about three years because it failed the Newtonian limit.

## What it claims about machines

- In formalized or specification domains, enumerating, scoring and selecting moves is computable. This is a claim about a mechanism. The paper does not claim that a current language model has produced a paradigm-scale invention.
- Embodiment may explain how a human found a move, but the operation is substrate-neutral (Langley's rediscovery programs, AI Feynman).

## Limits

- Mechanizability and closure are asserted only where compatibility is decidable. In open empirical domains the four types describe observed moves, with no claim of enumerability or completeness (Kauffman's adjacent possible; Fodor on global relevance).
- The existence proof is one demonstration in one specification domain. More move compositions and a robustness check of the weights are owed.
- Grounding is relocated, not removed: it constrains which hypothesis is true, not whether a well-typed one can be generated.
- No new empirical data.

## The running demonstration

`code/four_moves_demo.py` (deterministic, Python 3.12 and PyYAML) feeds two authors' specification module sets to a negotiator and checks predicted classes:

| Move | Ontology operation | Class |
|---|---|---|
| adjoin a dimension | a module owns a new term | no cross-interaction |
| glue across domains | imports the other author's term | CROSS_IMPORT |
| re-specify or rescale | refines the other's term | CROSS_REFINE |
| admissible adjunction | same key, identical definition | AGREEMENT |
| inadmissible adjunction | same key, incompatible definition | CONFLICT |

The compatibility predicate is a finite check: unique ownership, no dangling import, compatible refinement, acyclicity. The negotiator proposes reconciliation by lock, fork, rebase or merge. Step 5 of the engine reuses this classification for comparing two board sets.

## Consequences for the engine

- A board is not a formal domain, so the four moves are a menu of options, not a complete set.
- The validator gates the form of a candidate before the group sees it; deciding which candidate is meaningful stays with the participants.
- Any ranking by S is shown as a hint, with its weights logged.
- The paper is about representations in science and ontology, not group talk in the Shchedrovitsky tradition. Reading a position as a representation is the engine's interpretation, to be checked with methodologists.
