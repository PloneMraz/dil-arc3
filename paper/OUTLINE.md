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

## Title (to choose)

The finding is two-sided: the loop can be read back, and what it learned shows
why the score barely moved. Candidates:

- "Every Belief on the Record: An Auditable Learning Agent for ARC-AGI-3"
- "An ARC-AGI-3 Agent You Can Audit — and What Its Log Says About Exploration"
- "What an Event Log Shows: Auditing a Self-Learning Agent on ARC-AGI-3"

Subtitle: the DIL protocol; one submission (`56983446`, 0.25).

## Sections

**Abstract** [120] — Can an agent that learns ARC-AGI-3 from nothing be audited
by someone else, from its log alone? DIL (the loop) and a neutral learning mind
whose every expectation, hypothesis, refutation and choice is a datum with what
it was built from, in a hash-chained `[event]` log. Submission `56983446`: 0.25
(the random agent: 0.02 and 0.06). The log shows where the actions go and why
changes to exploration reshuffle which levels are won.

**1. Introduction** [200] — RHAE rewards few actions; an agent that learns in the
game must explore. The question: can what it knew and why it acted be read back
by a third party? Figure 1 (the loop: region → host → DIL layers → mind →
command → body). Contributions:
1. an agent whose beliefs, refutations and choices are all data with provenance,
   in a hash-chained log, checked by a conformance checker (C1–C7);
2. a learning mind neutral about its environment, with a replaceable model (the
   inducer) — the same loop for another task;
3. what the log measured: where the actions go, and why changes before the
   first success do not carry from the public games to the hidden ones;
4. a ledger of the ideas that failed, each with its numbers.

**2. Approach** [350] — The four roles (DIL, host, model, the self as a law).
"The mind acts on nothing; it commands, the body carries out" (T5's test).
The learning: experience → hypothesis (data) → expectation (the one right at the
highest rate) → the region's return → scar; curiosity for somewhere new (S2b);
reaching the aim as an experience (S4). The inducer (grid): still, rewrite,
aim; once the aim has come, moves, blocks and an aim of no one act (version 28's
addition). The invariants it keeps (INV-4, -5, -6, -8) and the declared
deviations, in one line each or by reference.

**3. Reading the loop back** [250] — What `[event]` holds (each cycle's layers,
admissions, scars, reads, writes with `built_from`). Shown on one game of the
Save & Run (version 29, the submitted code): rebuilt from `[event]` alone — what
it knew, each change, why it chose, which hypothesis a scar fell on. Figure 2: a
trace excerpt. The checker's verdicts. Stated: the scored run's logs are not
shown; the evidence is the same code on the public games.

**4. Results** [250] — Table 1: scores, hidden and public — random agent;
versions 18, 23, 26, 28. Table 2: changes one at a time (from the 10- and
25-game runs). Where the actions went (version 23, 25 games): 29% changed
nothing, 17% walked back to something left to try; the score is three levels
near the human baseline.

**5. What did not work, and why** [200] — Table 3: the ideas that failed (B1,
L2, P1, WAY_LAW, objects, suspects, ends, near at a step's scale, the cap, the
two level-2 laws, likeness, into-alone, mirrored moves, moves per thing), one
line and one number each. Why (Theory): every change before the first success
reshuffles exploration; the public 25 did not foretell the hidden games
(suspects: 0.515 public, 0.02 hidden); hence version 28's rule — change nothing
before the first aim — kept the hidden 0.25.

**6. Limits and conclusion** [130] — Accuracy is low and said so; a scar of an
experience is mostly the clock's; the act is not yet opaque to the mind; the
inducer lacks objects that move together, mirrors, hidden state. What holds: the
audit, and a loop that another model or another task can plug into.

## Figures and tables

- Cover image (required) — our own; no screenshots of others' work.
- Figure 1: the loop. Figure 2: a trace excerpt.
- Table 1: scores. Table 2: one change at a time. Table 3: ideas that failed.

## To settle before drafting

- The title.
- Whether the trace in Figure 2 is from tu93 (two levels, an aim of no one act)
  or a shorter game.
