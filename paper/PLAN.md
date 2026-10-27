# The paper — plan

What the Paper Track writeup is to be, what is settled, and the order of work.
Kept here so that a new session starts from it, not from memory. History goes in
`LOG.md`; this file says what holds now, and is edited as it changes.

## Settled with Plone (2026-10-11)

0. **dil-arc3 first, the paper after.** Plone: dil-arc3 does not yet show
   DIL's main contribution — learning and changing behaviour from its own
   collisions with what it expected, not from a reward set beforehand. It is
   developed until it does (silence as a collision; a collision turning what the
   mind does next; scars and the field reaching how it builds behaviour), and the
   paper describes the notebook that shows it. The dates below move with it.
   The title is settled: "Expect, Collide, Revise: Learning From Mismatch, Every
   Step on the Record" (Plone, 2026-10-26; before: "Learning Without a Reward
   Function"). The evidence is a checkable chain, not a
   claim (`OUTLINE.md`).
   **The work on dil-arc3, in order (Plone, 2026-10-11): 3 → 2 → 1 → 4 —
   done** (LOG.md, 2026-10-11 to 2026-10-19): (3) a collision of the region's
   report is thought on and an end turns the mind; (2) what an act did where
   the mind stood alike is expected again; (1) T1, each command a test of the
   expectation that least says what will come, measured in five versions and
   kept as an option (`--curiosity test`), S2b staying the default as it
   reached the most levels; (4) individuals of the same DIL differ, read back
   from their stores (`scripts/differ.py`): the Other present or not, and the
   field — once it carries its history (B1, DEVIATION 9) and the mind's counts
   follow it (B2) — set otherwise at birth.
1. **The submission the paper describes: `57623232`** (settled with Plone
   2026-10-26, once it scored 0.25, as version 41 had): notebook
   `plonemraz/dil-arc3-history` version 1, code `e04c515` — grid, S2b with
   attention, 600 cycles a game, four at once; as version 41, with the mind
   reading its own history (protocol v0.3.9); all 25 stores of its Save & Run
   verify under dil-core's verifier. Version 41 (`57470744`, 0.25) scored the
   same, without reading its history; version 37 (`57443352`, 0.25) without the
   thoughts named. **Version 35 (`57371259`, 0.26) is set aside**: its
   stores do not verify under dil-core's verifier (the hash of floats changed
   after it, LOG.md, 2026-10-19), and the paper's claim is that a third party
   checks the log. The notebook attached is the version described; a private
   one is made public after the deadline.
2. **Data**: version 41's Save & Run on the 25 public games, stores unpacked in
   `scripts/data/kaggle/dil-run/submit-963b7fb-v41/stores/` (the commit
   snapshots left packed), for `[event]` logs to read the evidence from. The
   individuals of point 4 are to be run again with version 41's code: their
   stores were removed with the old measurements' on 2026-10-20 (their reports
   and scorecards kept). The scored run's own logs are not shown by Kaggle, so
   the evidence is from the same code on the public games, and the paper says
   so.
3. **Form: both** (Plone, 2026-10-11, after first choosing the Writeup alone:
   "1,500 words cannot set out the whole work"). **The Writeup**, at most 1,500
   words, standing on its own — the claim, the evidence, the results, the
   limits — so no penalty is risked. **The paper**, a longer PDF (about 8–12
   pages) in the Public Project Link, as the sample writeup does: the theory,
   the full tables, the `[event]` trace, the ideas that failed. The Project
   Links then hold two: the notebook and the PDF.
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
| Accuracy | performance on the leaderboard (submission ID) | version 35's score, stated plainly (version 28: 0.25); against the random agent on the same road |
| Universality | does it translate beyond the competition | the mind and its learning name no task; host and model replace; the audit holds anywhere |
| Progress | does it raise anyone's chance of a top score | a loop a third party can check from `[event]`; what did not work, measured |
| Theory | *why* it works, not only how | expectation → collision → the mind turned → the next collision otherwise; why the same DIL makes different individuals (the Other, the field); why scores barely moved: changes reshuffle exploration, the public 25 do not foretell the hidden games |
| Completeness | covers the submission thoroughly | layers, invariants, deviations, how it plays on Kaggle |
| Novelty | against public research | the DIL protocol; a hash-chained event log; "the mind commands, the host carries the command out through its effectors" |

## Shape (after the winning papers of 2024 and 2025 and the sample writeup)

Title and subtitle; abstract; introduction (the claim); approach (DIL, the four
roles, the mind and its learning, the inducer); evidence (reading `[event]`
back); results (scores, and one change at a time); ideas that failed; limits;
conclusion. The claim, from CLAUDE.md: every thing the loop knows and every
change in what it does can be read back by a third party from `[event]`.

## Order of work (settled with Plone, 2026-10-19)

| When | What |
|---|---|
| 2026-10-11 → 19 | done: the outline; dil-arc3 developed (3 → 2 → 1 → 4); the evidence scripts (`scripts/chains.py`, `scripts/differ.py`); version 35 submitted |
| 2026-10-20 → 23 | evidence from version 35's stores: the chains a reader can check (a collision → the turned choice → what is expected of that act from then on → the next return), one in full for Figure 2; the individuals of point 4 (the Other; the field), one chain each; the conformance checks C1–C7; tables of scores (random agent, versions 18 to 35 — hidden and public), of changes one at a time, of ideas that failed (T1's five versions among them); figures (the loop, a trace excerpt) and the cover image |
| 2026-10-23 → 28 | the Writeup's draft, section by section, each sent to Plone as it is done |
| 2026-10-26 → 11-01 | the paper (PDF), from the Writeup and the evidence: each section widened, the full tables, the trace |
| 2026-11-01 → 04 | review against each criterion; the Writeup's word count; every number in both checked against LOG.md; outbound disclosure (no session link, no personal data, no metadata in the PDF or the images) |
| 2026-11-04 → 07 | the PDF published where it needs no login; the Writeup made, notebook, PDF, cover image and submission ID attached, **submitted**; the margin to 2026-11-09 kept |

The stores' archive (`submit-e04c515-history1/stores.tar.gz`, 410,049,466 bytes,
sha256 `1b8920d5a3e47702337e78d9b967a61ac0220703ea25141d5c26cbfe554b5dc1`) is published
after 2026-11-02 (Plone, 2026-10-26, option (b): this repository stays private until
ARC-AGI-3 ends), as a release of dil-core (tag `dil-arc3-57623232-stores`, not marked
latest), at `https://github.com/PloneMraz/dil-core/releases/tag/dil-arc3-57623232-stores`
— the URL the Writeup and the PDF already give (Plone, 2026-10-27). dil-arc3 itself
goes public after 2026-11-02. The PDF's home is the workspace's `Plone's documents`
folder (`pdfs/ExpectCollideRevise.pdf`; `markdowns/` in its local history, never uploaded), kept on Hugging Face
alone as the dataset `plonemraz/Plones_documents` (Plone, 2026-10-27: no GitHub, no
Zenodo), updated with `hf upload`; private until 2026-11-02, then public and **not
gated** (a gated dataset asks for a login), checked without one, and then given a DOI
of its own — the archive's, not the paper's. The Public Project Link is
`https://huggingface.co/datasets/plonemraz/Plones_documents/resolve/main/pdfs/ExpectCollideRevise.pdf`,
which serves the PDF itself; the Writeup's last line gives it.

**After 2026-11-02, before the Writeup is submitted — two links to open without a
login** (Plone, 2026-10-27), each named before it serves anything (the first in the
Writeup and the PDF, the second in the Writeup):
1. the stores' release, `…/dil-core/releases/tag/dil-arc3-57623232-stores`: the
   page opens and `stores.tar.gz` downloads, its sha256 as above;
2. the PDF, `…/Plones_documents/resolve/main/pdfs/ExpectCollideRevise.pdf`: served
   as a PDF once the dataset is public and not gated.
Only then the DOI for `Plones_documents`, and the Writeup submitted.

Settled with Plone (2026-10-19): the dates above, moved for the work on
dil-arc3. Alongside: choose the two final ARC-AGI-3 submissions by 2026-11-02
(`57623232` and version 41's `57470744`, approved by Plone 2026-10-26 in place of
versions 41 and 37; he settles them on the last day).

## Where things are

- Scores and what each run did: `LOG.md` (versions 28 to 35: 2026-10-09 to
  2026-10-19; the ideas that failed: 2026-10-05 to 2026-10-18; point 4:
  2026-10-18).
- The described submission's Save & Run output (25 games):
  `scripts/data/kaggle/dil-run/submit-e04c515-history1/` (git-ignored), its stores
  unpacked — the evidence is read from them; `evidence/chains-summary.txt`.
  Version 41's: `submit-963b7fb-v41/` (`stores.tar.gz`; what the scripts found, in
  its `evidence/`, `chains-summary-corrected.txt` with the corrected count). Version 37's: `submit-9fcaafc-v36/`; version 35's:
  `submit-b4d7d5a-v35/` (their `stores.tar.gz`).
- Point 4's individuals: reports and scorecards in `scripts/data/t1/` (git-ignored);
  their stores to be made again.
- The rubric, rules and sample writeup: the workspace's `Downloads/pages/`; the
  2025 first-place paper: `Downloads/papers/2510.04871v1.pdf`.
