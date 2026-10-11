# The paper — plan

What the Paper Track writeup is to be, what is settled, and the order of work.
Kept here so that a new session starts from it, not from memory. History goes in
`LOG.md`; this file says what holds now, and is edited as it changes.

## Settled with Plone (2026-10-11)

1. **The submission the paper describes is version 28**: `56983446`, notebook
   `plonemraz/dil-arc3-learning` version 28, code `9e69156` — grid with moves,
   blocks and into aims once the aim has come; S2b curiosity; attention; 600
   cycles a game, four at once. Scored 0.25 (as version 23). The notebook
   attached to the writeup is that version; a private one is made public after
   the deadline.
2. **More data**: a Save & Run of the same code (notebook version 29, pushed
   2026-10-11) for `[event]` logs to read the evidence from. The scored run's
   own logs are not shown by Kaggle, so the evidence is from the same code on the
   25 public games, and the paper says so.
3. **Form: (a), the Writeup itself, at most 1,500 words** — the rules as written
   (CLAUDE.md, "Follow the rules as written"). Not the PDF route.
4. **Drafts live in `paper/`**, in English.

## What the rules ask (read 2026-10-11; texts in the workspace's `Downloads/pages/`)

- A valid submission: the **Kaggle Writeup** (title, subtitle, "a detailed
  analysis of your submission"; a Track selected — Main Track, the only one), a
  **Media Gallery** with a **cover image** (required), the **public Notebook**
  in the Project Links field, and optionally a public project link.
- "Your Writeup should not exceed 1,500 words. Submissions over this limit may
  be subject to penalty."
- **Submitted, not draft**: "Any un-submitted or draft Writeups by the
  competition deadline will not be considered by the Judges." A Writeup can be
  edited until the deadline.
- **One submission** (§2.2.a; the page calls the competition a "Featured
  Hackathon"). Team must match the ARC-AGI-3 team (§2.1.b).
- **Deadline**: 2026-11-09 23:59 UTC (Nov 10, 6:59 AM GMT+7).
- **Judges**: Mike Knoop, François Chollet.
- **Licence**: CC-BY 4.0 for a winning submission (§1.6); the sample writeup is
  released under CC BY 4.0. A winner may be asked for a reproducible description
  and a code repository with instructions (§2.5.b), and a recorded call.
- **Original work** (§3.14.a): nothing in the writeup infringes others' rights —
  figures are our own.

## The rubric — six criteria, 0 to 5 each, the score their mean

| Criterion | What it asks | What this paper brings |
|---|---|---|
| Accuracy | performance on the leaderboard (submission ID) | 0.25, stated plainly; against the random agent on the same road |
| Universality | does it translate beyond the competition | the mind and its learning name no task; host and model replace; the audit holds anywhere |
| Progress | does it raise anyone's chance of a top score | a loop a third party can check from `[event]`; what did not work, measured |
| Theory | *why* it works, not only how | expectation → test → scar; why scores barely moved: changes reshuffle exploration, the public 25 do not foretell the hidden games |
| Completeness | covers the submission thoroughly | layers, invariants, deviations, how it plays on Kaggle |
| Novelty | against public research | the DIL protocol; a hash-chained event log; "the mind commands, the body carries out" |

## Shape (after the 2025 first-place paper and the sample writeup)

Title and subtitle; abstract; introduction (the claim); approach (DIL, the four
roles, the mind and its learning, the inducer); evidence (reading `[event]`
back); results (scores, and one change at a time); ideas that failed; limits;
conclusion. The claim, from CLAUDE.md: every thing the loop knows and every
change in what it does can be read back by a third party from `[event]`.

## Order of work

| When | What |
|---|---|
| 2026-10-11 → 12 | outline against the rubric; version 29's data in |
| 2026-10-12 → 17 | evidence: a script that rebuilds, from one game's `[event]` alone, what the mind knew, what it changed and why, where it was scarred; the conformance checks C1–C7; tables of scores (random agent, versions 18, 23, 26, 28 — hidden and public), of changes one at a time (the ten- and 25-game runs in LOG.md), of ideas that failed; figures (the loop, a trace excerpt) and the cover image |
| 2026-10-18 → 25 | the draft, section by section, each sent to Plone as it is done |
| 2026-10-26 → 11-01 | review against each criterion; word count; every number checked against LOG.md; outbound disclosure (no session link, no personal data, no image metadata) |
| 2026-11-02 → 06 | the Writeup made, notebook, cover image and submission ID attached, **submitted**; the margin to 2026-11-09 kept |

Alongside: read the 2024 and 2025 winning papers (arcprize.org; the 2025
writeups on Kaggle), as the Overview suggests; choose the two final ARC-AGI-3
submissions by 2026-11-02 (proposed: versions 28 and 23).

## Where things are

- Scores and what each run did: `LOG.md` (version 28: 2026-10-09; its score:
  2026-10-11; the ideas that failed: 2026-10-05 to 2026-10-11).
- Version 28's Save & Run output (25 games, stores): `scripts/data/kaggle/dil-run/submit-9e69156-moves/`
  (git-ignored); version 29's when it comes.
- The rubric, rules and sample writeup: the workspace's `Downloads/pages/`; the
  2025 first-place paper: `Downloads/papers/2510.04871v1.pdf`.
