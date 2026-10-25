# The paper — outline

The Writeup, at most 1,500 words and standing on its own, and beside it the
paper as a PDF in the Public Project Link (`PLAN.md`), against the six criteria.
The Writeup's sections below; the paper widens each, and adds what the Writeup
has no room for (the full tables, the trace, the theory, the ideas that failed
one by one). Every
number below is from `LOG.md` and is checked again against it before the draft.
Words in brackets are a budget, not a target.

## What the winning papers of 2024 and 2025 share (read 2026-10-11)

Read: 2025 — 1st, Jolicoeur-Martineau, "Less is More: Recursive Reasoning with
Tiny Networks"; 3rd, Liao & Gu, "ARC-AGI Without Pretraining". 2024 — 1st, Li
et al., "Combining Induction and Transduction for Abstract Reasoning"; 2nd,
Akyürek et al., "The Surprising Effectiveness of Test-Time Training for Few-Shot
Learning"; 3rd, Bonnet & Macfarlane, "Searching Latent Program Spaces". (2025's
2nd, Pourcel, Colas & Oudeyer, on OpenReview: the page refused the download; not
read.) PDFs in the workspace's `Downloads/papers/`.

- **The title is the finding**, not the system's name: "Less is More", "Without
  Pretraining", "Surprising Effectiveness", "Combining … ".
- **The abstract** goes question → what was done → one number → what it means.
- **The introduction** poses one question, shows a figure early (tasks, or the
  method), and ends in a numbered list of contributions.
- **Each choice is shown by a measurement**: ablations one change at a time
  (TRM's tables), a study of what each part solves (Li et al.'s complementarity).
- **The limits and what failed are stated**: TRM's "Ideas that failed",
  Liao & Gu's counterpoint to "conventional wisdom".
- They are research papers of 10–47 pages; the sample writeup holds the
  abstract and links the paper. Ours: a Writeup of at most 1,500 words that
  stands alone, each of these in one or two sentences and the tables carrying
  the numbers; the paper behind the link, in full.

## Title (Plone, 2026-10-11)

**"Expect, Collide, Revise: Learning Without a Reward Function, Every Step on
the Record"** — DIL's two contributions: behaviour that changes from its own
collisions with what it expected, not from a reward set beforehand; and every
step of it auditable. No competition name in the title (not required; most
winning titles have none; it serves Universality). Subtitle: the DIL protocol on
ARC-AGI-3, and the submission it describes.

## The evidence is a trace, not a claim (Plone, 2026-10-11)

The paper does not assert "DIL learns from its own experience". It shows a
stretch of trace the reader can check for themself: **a ResistEvent occurs →
the behaviour changes → the expectation is revised → the next ResistEvent is
otherwise.** One such chain, checkable from `[event]` (hash-chained, with the
tool to read it), is worth more than ten pages of argument. So:

- the chain is the paper's centre (Figure 2, and section 3), the rest serves it;
- every link is a record in `[event]`: the scar (which datum, which
  expectation), the thought it set off and the choice it turned (each naming
  what it was built from), the revision of what was expected (a hypothesis's
  or an experience's datum revised, a refutation), the next scar;
- the evidence script finds such chains in the run's `[event]` itself, counts
  them, and prints one in full; the reader runs it on the published stores;
- mismatch is never written as a penalty or reward, nor collisions as a score.

The agent must first produce such chains plainly (Plone: develop dil-arc3
before the paper; `PLAN.md`).

## Sections

**Abstract** [120] — An agent that learns ARC-AGI-3 games with no reward
function: it expects, its expectation collides with what comes back (a
ResistEvent), and the collision turns what it does next. Every expectation,
collision, thought and choice is a datum naming what it was built from, in a
hash-chained `[event]` log. We show chains a reader can check — collision →
changed behaviour → revised expectation → a different collision — and the
submission's score, against the random agent's.

**1. Introduction** [200] — RHAE rewards few actions; an agent that learns in the
game must explore. The question: can what it knew and why it acted be read back
by a third party? Figure 1 (the loop: region → host (senses) → DIL layers →
mind → host (effectors) → region: one host, its sensory organs and its effectors).
Contributions:
1. an agent whose beliefs, refutations and choices are all data with provenance,
   in a hash-chained log, checked by a conformance checker (C1–C7);
2. a learning mind neutral about its environment, with a replaceable model (the
   inducer) — the same loop for another task;
3. what the log measured: where the actions go, and why changes before the
   first success do not carry from the public games to the hidden ones;
4. a ledger of the ideas that failed, each with its numbers.

**2. Approach** [350] — The four roles (DIL, host, model, the self as a law).
"The mind acts on nothing; it commands, and the host carries the command out
through its effectors" (T5's test).
The learning: experience → hypothesis (data) → expectation (the one right at the
highest rate; where nothing it knows says, that the region will be otherwise, or
what the same kind of act did where it stood alike) → the region's return →
scar → a thought that turns the next choice (silence, an answer otherwise, an
end); curiosity for somewhere new (S2b; T1, testing the expectation that least
says what will come, measured beside it); reaching the aim as an experience
(S4). The field: every layer's votes and the mind's (trust, exploration),
carried over cycles (DEVIATION 9), read by the mind in counts that follow it
(B2). The inducer (grid): still, rewrite, aim; once the aim has come, moves,
blocks and an aim of no one act (version 28's addition). The invariants it keeps (INV-4, -5, -6, -8) and the declared
deviations, in one line each or by reference.

**3. A chain the reader can check** [300] — What `[event]` holds (each cycle's
layers, admissions, scars, reads, writes with `built_from`). One chain in full
(Figure 2): the ResistEvent, the thought and the turned choice, the revised
expectation, the next ResistEvent — each record's id, so the reader finds it in
the published stores; how many such chains the run holds, and that every choice a
collision turned names the return and, once its id came back, the thought
(`scripts/thoughts.py`). Two individuals of
the same DIL parting (`scripts/differ.py`): with the Other and without it (the
remark said again, the objection, the choice replaced), and born in fields
apart (what it counted by, thirty steps on). dil-core's own verifier on every
store, and its conformance checker's verdicts (§13.4 partial by design: continuity
is a third party's to say; §13.7 failing where the onlooker had no reason to
object). Stated: the scored run's own logs are not shown; the evidence is the
same code on the public games.

**4. Results** [250] — Table 1: scores, hidden and public — random agent;
versions 18 to 41. Table 2: changes one at a time (from the 10- and
25-game runs). Where the actions went (version 23, 25 games): 29% changed
nothing, 17% walked back to something left to try; the score is three levels
near the human baseline.

**5. What did not work, and why** [200] — Table 3: the ideas that failed (B1,
L2, P1, WAY_LAW, objects, suspects, ends, near at a step's scale, the cap, the
two level-2 laws, likeness, into-alone, mirrored moves, moves per thing, T1's
five versions and the noisy TV; the objects inducer, steps 1–4, and the language
inducer — a served model's programs right about one step in eleven), one line and
one number each. Why (Theory): every change before the first success
reshuffles exploration; the public 25 did not foretell the hidden games
(suspects: 0.515 public, 0.02 hidden); hence version 28's rule — change nothing
before the first aim — kept the hidden 0.25.

**6. Limits and conclusion** [130] — Accuracy is low and said so; the field's
axes keep narrow bands, and trust stands high wherever what memory names is
mostly right, so it tells regions apart little; what an individual is born as
reaches a choice only through the counts it reads; the inducer lacks objects
that move together, mirrors, hidden state. What holds: the
audit, and a loop that another model or another task can plug into. Also
stated: a run that stops at its cycle budget leaves its last choice awaiting the
ids it was built from; writing what the mind learns is itself data that comes back
into the loop, so how it is written can move what it does (the relinking moved
nine games of eleven a little, LOG.md, 2026-10-21).

## Figures and tables

- Cover image (required) — our own; no screenshots of others' work.
- Figure 1: the loop. Figure 2: a trace excerpt.
- Table 1: scores. Table 2: one change at a time. Table 3: ideas that failed.

## To settle before drafting

- The submission described: version 41 (`57470744`, 0.25), settled with Plone
  2026-10-25; version 35 set aside, its stores not verifying under dil-core
  (`PLAN.md`).
- The game Figure 2's chain is from — chosen from version 41's stores when the
  chains are found.
