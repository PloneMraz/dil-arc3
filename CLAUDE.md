# dil-arc3 — working rules

An ARC-AGI-3 agent host built on the DIL protocol, for ARC Prize 2026.

## Hard constraints

- **Never modify `dil-core`.** This repo *imports* it. If something in dil-core
  blocks the work, report it and stop; do not edit that repository to make this
  one easier.
- **MIT-0 from the first commit.** ARC Prize requires every file authored by the
  submitter to carry a permissive public-domain licence. Nothing enters this repo
  under a licence that keeps an attribution clause.
- **No network at evaluation.** Kaggle disables the internet on every accelerated
  session, so nothing may reach for a hosted model, an API key, or a download at
  run time. Anything the agent needs ships with it.
- **DIL does not act.** The loop supplies the condition; the agent acts. Whatever
  chooses a move lives in this repo, not inside DIL.

## Architecture — settled with Plone, 2026-09-22

`dil-core` is a preparation, not an organism: a brain on a bench, wired to
electrodes and stimulated to show the mechanism runs. It has no region to meet,
which is why its terminal emission is a fixed marker —
`{ kind: "respond", cycle, valence }` — and never a move.

This repository is a whole body, built as one from the start. Four roles, and
they are not interchangeable:

| | |
|---|---|
| **DIL** | the operating mechanism of the whole. Not a part beside other parts — how the body runs. Present everywhere, located nowhere. |
| **host** | the container and the sense organs. It declares its faculties; DIL threads through. |
| **model** | the thinking organ. An organ, not a subject. |
| **the self** | what occurs while the loop runs. **The self acts.** |

### The line that must not be crossed

**The model emits no action.** It supplies predictions and models into the loop —
material for T5 expectation, T6 other-model synthesis, T8 abstraction. What the
region returns then *collides* with that prediction, and the collision — the place
the model was wrong — is the information that accrues. The move is emitted by the
agent under DIL, through the host: by the self, after appraisal, on criteria that
lie outside the state being edited.

A model that picks the move rebuilds the design this replaced — DIL as a wrapper
around a policy — and breaks four invariants outright:

- **INV-4** — no layer assigns meaning to a signal in isolation; meaning is a
  function of (signal, lower-layer context). A model reading a frame and naming a
  move is meaning assigned in isolation.
- **INV-5** — temporal state forms only by sequential accrual, never loaded. Refeeding
  the whole game history into a context window each step is a load, not an accrual:
  the guard's own note calls it "a reloaded context masquerading as a self".
- **INV-6** — every change is classified self-written or environment-pushed before
  interpretation. Model output is self-written; the returned grid is
  environment-pushed. Conflating them destroys the only signal that matters.
- **INV-8** — appraisal may not draw its criteria from the state being edited,
  "otherwise it is self-scoring and hackable". A model that both proposes and
  justifies the move is scoring itself.

### What this settles about model choice

The requirement is not a strong decision-maker. It is something that **predicts the
next frame** over a grid of at most 64×64 with values 0–15 — a far smaller problem,
and a far better fit for the compute ceiling of a Kaggle session with no network.

## What the benchmark actually measures

The score is **RHAE — Relative Human Action Efficiency**, not a solve rate:

```
level_score = (human_baseline_actions / ai_actions) ^ 2      capped at 1.15x human
```

Per game, level scores are averaged with the 1-indexed level number as weight;
the total is the mean across games, 0–100%.

Two consequences fix the design:

1. **Wasted actions are punished quadratically.** Spending three times a human's
   actions leaves one ninth of the score. An agent that flails and eventually wins
   scores near zero.
2. **Thinking is free.** Only actions that change game state count — "internal
   operations that do not alter the environment (tool calls, reasoning steps,
   retries) are not counted". A heavy deliberation loop costs nothing, provided it
   removes actions from the environment.

So the target is not the strongest model. It is the architecture that wastes the
fewest moves.

## The environment

- Observation: a 2D grid, at most **64×64**, cells are integers **0–15**, origin
  `(0,0)` top-left, `(x, y)` order. It is a grid of numbers, not an image.
- Game state is one of `NOT_PLAYED`, `NOT_FINISHED`, `WIN`, `GAME_OVER`.
- Actions: `RESET`; `ACTION1`–`ACTION4` (up/down/left/right); `ACTION5` (varies by
  game); `ACTION6` taking `x, y` in 0–63; `ACTION7` (undo). Each response carries
  `available_actions`, and only that subset may be used.
- Agent surface: `is_done(frames, latest_frame) -> bool` and
  `choose_action(frames, latest_frame) -> GameAction`.
- Competition mode allows one `make` per environment and one scorecard.

## What this repository is for

The goal is the **Paper Track**, not winning ARC-AGI-3. A paper is only eligible
when it is linked to a Kaggle code submission, so this agent is the ticket — but
the rule names what kind of ticket: "a Kaggle code submission **that demonstrates
the approach detailed in the paper**." A throwaway agent would not qualify. This
one has to run the protocol honestly: the eight invariants enforced, the layers
threaded, an `[event]` log a third party can verify.

The bar for a *valid submission* is low, and worth knowing: "as long as the agent
takes action on any of the games, a submission file for all of the games is
created." One action secures the entry. Everything above that serves the paper's
Accuracy criterion, not the entry itself.

**The protocol document is not the paper.** `DIL-protocol-v0.3.2.md` is 55 KB of
normative specification, written for someone implementing it. The paper is a
separate artifact still to be written, in the shape ARC Prize asks for —
abstract, introduction, prior work, approach, results, conclusion — and their
instruction is "shorter and clearer is always better. No filler, no unnecessary
equations."

## Dates — the entry deadline is the one that bites

- **2026-10-26 — ENTRY DEADLINE.** The competition rules must be accepted before
  this date or there is no way to compete at all, and the paper loses the
  submission it has to be linked to. Accepting them is a binding agreement on
  Plone's account: he does it, not the agent.
- 2026-10-26 — team merger deadline.
- 2026-11-02 — final submission.
- 2026-11-08 — paper.
- 2026-12-04 — results.

All deadlines are 23:59 UTC.

## Limits, verified from the Kaggle competition page

- Submissions are **Notebooks**. CPU notebook ≤ **9 hours**, GPU notebook ≤
  **9 hours**.
- **Internet access disabled.**
- "Freely & publicly available external data is allowed, **including pre-trained
  models**" — so shipping a local model is explicitly permitted, not a grey area.
- RTX 6000 (`g4-standard-48`) is in the hardware pool for this competition only;
  using it for anything else risks account moderation, and RTX sessions must have
  internet disabled.

## What the Kaggle rules add

- **Licence, and a conflict between two official sources.** arcprize.org asks for
  "a permissive public domain license (eg. CC0 or MIT-0)"; the Kaggle rules (§1.6,
  §2.5) name **CC-BY 4.0**, which keeps an attribution condition and is not a
  public-domain licence. MIT-0 grants strictly more than CC-BY 4.0 does, so it
  satisfies either reading and nothing needs changing — but the relicence was
  argued from arcprize.org alone, and under the Kaggle rules plain MIT would
  likely have sufficed. Read both sites before relying on either.
- **The model constraint is tighter than "open weights"** (§2.5.a): a submission
  must have "open source system, open source model, and open source
  weights/parameters, as defined in the checklist from the Open Source AI
  definition by the Open Source Initiative". OSAID asks for training-data
  information too, which many downloadable-weight models do not provide. The very
  next paragraph cuts the other way — a pretrained model "with an incompatible
  license" need not be relicensed — and the whole section binds winners only.
  **Settle this with the organisers before choosing a model**; choosing first and
  asking later risks a wasted month.
- **One Kaggle account** (§3.5.a). Submitting from more than one is
  disqualification, not a warning.
- **Public code sharing has a required channel** (§3.6): sharing Competition Code
  publicly obliges sharing it "on Kaggle.com on the discussion forum or notebooks
  associated specifically with the Competition". Publishing this repository on
  GitHub is not forbidden, but it does not discharge that obligation, and §3.6.a
  treats private sharing as a breach.
- Submission limits (§2.2): one per day, at most two final submissions.
- Open-source code used in the submission must be under an OSI-approved licence
  that does not limit commercial use (§3.6.c). MIT-0 is OSI-approved.
- Entry itself constitutes acceptance of the rules, which are a binding agreement
  under California law (§2.9). Plone accepts them; the agent does not.

## Still unverified

- **How the Paper Track's 4.5 threshold is computed** — a mean across the six
  criteria, or something else. It is not on the paper page, and it decides
  whether a low Accuracy forecloses the $375K pool. Only the organisers can
  answer this.
- Whether the three Top Paper prizes use that same threshold.
- **The number of games in the private evaluation set.** A community repository
  mentions 25 public games; unverified.
- The two official sources disagree on the Milestone 1 split: arcprize.org says
  $25K/$10K/$2.5K, Kaggle says $25,000/$7,500/$5,000. Both total $37,500. Which
  is authoritative is unknown; it does not affect this plan, but it is a reason
  to read both sites rather than trust one.
