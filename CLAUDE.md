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

## Unverified — do not treat as settled

- The Kaggle **runtime limit in hours** is not stated in the ARC Prize docs, and
  the Kaggle pages render client-side so they could not be read. Figures found by
  search ("P100, 12 hours") belong to ARC Prize 2024 and were discarded.
- The **number of games in the private evaluation set** is not published. A
  community repository mentions 25 public games; unverified.

## Dates

Code submission 2026-11-02. Paper 2026-11-08. Results 2026-12-04.
