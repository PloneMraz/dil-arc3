# dil-arc3 — working rules

An ARC-AGI-3 agent host built on the DIL protocol, for ARC Prize 2026.

This file keeps what is in force; its history — the measurements, the designs
replaced, the corrections — is in [LOG.md](LOG.md).

## Hard constraints

- **dil-core is changed only at Plone's direction.** This repo does not import
  it: `src/dil/` is a Python port of it. A gap in the mechanism is fixed in
  dil-core first, when Plone directs it, and then ported here. Otherwise, if
  something in dil-core blocks the work, report it and stop; do not edit that
  repository to make this one easier.
- **History goes in `LOG.md`.** A measurement, a run's result, a design replaced,
  a correction — anything that says what happened — is written in `LOG.md`,
  under its date. `README.md` and `CLAUDE.md` say only what holds now: when
  something changes, they are edited to the new state, and how it changed is
  logged.
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
| **model** | the thinking organ's engine: replaceable. The **mind** is the design — it reads, expects, is curious, wants, and constructs behaviour; another model changes how well it thinks, not what it is. |
| **the self** | what the loop produces when it runs (§7): a law, not a part, **located in no file** — "host, self, and agent are one motion at three descriptive levels, not three entities" (§2). Its behaviour is the body's motion under the mind's command. The word is not used in the code (Plone, 2026-09-25). |

### The line that must not be crossed

**The mind acts on nothing; it commands, and the body carries out.** The body
takes in what the region returns; the mind reads it, forms expectations, is
curious and wants — in its thinking, not in a formula — and constructs the next
action toward getting through the level; it commands it; the body carries it
out; mismatch comes back; the loop goes on (Plone, 2026-09-25). The command is
T5's **test** (§6.4: "an action that pushes to the region to see whether the
return matches the Expectation just built"), recorded from T5 in `[event]` and
carried out by the body at link 5 in the same cycle. The mind sees what the
region offers — it reads everything — and a command the region does not afford
is not carried out: the body waits.

What judges a command is the region, never the mind: the move's return is
compared with what the program predicted, and when it does not hold, the
program is scarred and the mind thinks again. That is what keeps the invariants:

- **INV-4** — no layer assigns meaning to a signal in isolation. The program is
  built from the store and the window, and tested against the region.
- **INV-5** — temporal state forms only by sequential accrual, never loaded. The
  model is shown what the mind asked for and its short-term perception, bounded;
  never the whole history.
- **INV-6** — model output is self-written; the returned grid is
  environment-pushed. The command is the mind's; what comes back is the
  region's.
- **INV-8** — appraisal may not draw its criteria from the state being edited.
  The mind commands; it does not score its command — the region's return does,
  and the scar lands on the program.

### What this settles about model choice

The requirement is not a strong decision-maker. It is something that **predicts the
next frame** over a stack of 64×64 grids with values 0–15 — a far smaller problem,
and a far better fit for the compute ceiling of a Kaggle session with no network.

## The mind, the store and the log — settled with Plone, 2026-09-24

What the one mind is and how its work reaches `[event]`. Each rule below was
settled with Plone; where and why is in `LOG.md`, under 2026-09-24.

- **One mind, and it is the model.** The thinking organ is Qwen3.6-35B-A3B and
  the program it writes, `predict(grid, action, x, y)` (`src/arc3/mind.py`).
  Nothing else computes over the grid: a second computation is a second mind, and
  the self would have no one mind to crystallize from. Plone: "Dùng Qwen thì
  dùng Qwen, đừng nhập nhằng."
- **Seeing is the eye's, computing is the brain's.** The host takes the signal in
  and computes nothing from it: two signals a cycle, the frame (both grid stacks
  and the move, as the engine returned them) and the region's status. Never name
  a computation of the mind with a verb of the senses.
- **The mind commands; the body carries out.** From its program's
  `propose(grid, steps)`, run on where the game stands and the steps it has
  just seen (short-term perception, each with the state and levels the region
  reported) once the region has said all it says in a cycle, the mind pushes
  the next action as T5's `test` — if the body can carry it out: RESET always,
  any other action the region offers unless the game has ended.
  `src/arc3/command.py` carries it out and weighs nothing. With no such
  command the mind thinks again while the body waits (`MAX_WAIT_THOUGHTS = 2`,
  declared, not measured); then the body stands
  still, and in an informational region the run ends — no action is made up in
  the mind's place (Plone: "Cơ thể có thể đơ để đợi"). Cycle 0's RESET is the
  host's start-up (§4). What else the mind sends out is a question to its own
  memory: `ask(cue)`, a store query, traced to T5 with register ↔.
- **Curiosity, want and expectation are the mind's, arising in its thinking.**
  Nothing in code computes or weighs them: the per-action `resolved`,
  `progress` and `valence` readings and the formula that composed them are gone
  (Plone, 2026-09-25).
- **What the mind is told is a `prior`** (`prior:mind-task`, `src/arc3/task.py`):
  this project's own words (`source: dil-arc3`), neutral — the aim is to get
  through the levels; no kind of game, mechanic or strategy is named. It enters
  through the tagging-gate, the mind recalls it at its first arrival (a thought
  before it waits for it), and every program names it in `built_from`.
- **The mind reads by asking; nothing is poured into it.** It may read anything
  in the store, and the model chooses what: `ASK {...}` lines in its answer, a
  cue by any tag key and `provenance` — frames, statuses, the onlooker's remarks,
  the rules it was told, scars or not. No cue is written into the code; until
  the model asks, it thinks from what it has seen. **What T3 recalls is not
  shown to it** (Plone, 2026-09-27): T3 asks the store by the description of each
  arrival — the protocol's recall, traced as `prior → running` — but only a
  return that answers a cue the model asked reaches its prompt or `built_from`.
  Until then the competition's rules, "Your goal is to win" among them, reached
  every prompt unasked.
- **What the body can carry out is one rule** (`command.can_carry_out`), which the
  mind asks before it counts a proposal as a command. Written twice, it parted
  twice: after `GAME_OVER`, and for ACTION6 with no cell.
- **Memory is what the store held before the cycle that asks.** A query is
  answered without the data admitted in the cycle that raised it.
- **Short-term perception is as long as T5's window** (`BASELINE_WINDOW = 16`):
  the steps just seen, each with what the region reported of itself that cycle.
  The mind thinks from what the store answered, those steps, and what the
  onlooker says now — bounded, never the whole history.
- **The program predicts what the region returns**: the next grid and, when it
  says so, the region's status (`{"grid": ..., "status": {...}}`); status fields
  it leaves out stay as they were. Where it says nothing, the standing
  expectation holds: the region reports what it reported last.
- **A mismatch on any channel sets the mind thinking** — the frame, the status,
  or the onlooker's change of stance — at most once a cycle; a change of the
  onlooker's stance is thought on even in a cycle already thought in.
- **The mind always holds an expectation of reaching an aim** (Plone,
  2026-09-25): whatever aim the task it receives has — stated, or worked out and
  said to be its inference. The words are the mind's own prior
  (`prior:mind-aim`, `src/arc3/aim.py`), apart from the environment's task; they
  name no environment. The program writes `GOAL = {aim, source, reached_when,
  within}`: `reached_when` is what will come back when the aim is reached, and
  when the aim falls due it joins the program's expectation of that step. Not
  reached then, or reached sooner: the mind thinks on `goal`, and a program that
  predicts as well and acts otherwise is kept; the aim is then held again from
  that step. **The aim is the mind's, not the program's**: a program that states
  one replaces it, one that states none leaves the mind the aim it held. With no
  aim held at all, the mind commands nothing and thinks again while the body
  waits. Why a `GOAL` was not taken (`goal_check`), or why the last answer did
  not load, is said to the model in the last message, where it reads what to do.
- **Where a regress stops.** (1) The mind thinks only on what comes from outside
  — a return, the onlooker — or while the body waits; one thought never sets off
  another. (2) An aim must ground out in what comes back: an aim nothing coming
  back could show is not taken. (3) Standing still is said by the onlooker each
  moment, and standing costs the run's budget, which ends it.
- **What a command is for is an expectation too** (Plone, 2026-09-25). `propose`
  may return `(action, x, y, want)`, `want` being cells of the next grid and
  fields of the region's next report. It joins the program's expectation of the
  step the command makes, and meets the region there: when only it fails, the
  mind thinks on `want`. The aim stays in the prior; what the program wants of
  each move is its own, and the region can refute it.
- **Every answer the model gives is kept whole** as the mind's datum
  (`domain: mind`, `kind: thought`: the text, and the reasoning when the model
  gives one), built from what it was shown. It is evidence for a later thought
  only when the model asks for it.
- **A program the model writes is `running` data**, not `prior`. It enters at
  `nascent` bearing the cycle that wrote it, arrives at T1 the next cycle, is
  SELF_WRITTEN at T2, runs every layer and moves `nascent → running`. A rewrite
  is a **revision**: the content changes, the provenance does not, and `[event]`
  gets a bare `revision` line with no content; the content is read from the
  commit snapshot. The mind keeps a new program only if it explains the evidence
  better; the first is kept because there was none. It also keeps one that
  explains as much and can command, when the body is waiting for a command, or
  when what set it thinking was how it acts — the onlooker's objection, or a
  command that did not bring about what it was for — which is met by acting
  otherwise (Plone, 2026-09-25). For those reasons (onlooker, want, goal) such a
  program must **act otherwise**: its `propose`, from where the game stands,
  gives another action than the held program's. The same action again is not
  kept, and the model is told so (Plone, 2026-09-27).
- **There is no trigger for rewriting, and no constant to declare.** Rewriting is
  the consequence of mismatch: if the mind does not adjust, the mismatch recurs.
- **Every written datum records what it was built from** (protocol v0.3.4): ids
  only, never content; `()` for nothing held. The mind's `built_from` is exactly
  the evidence the model was shown.
- **What the region returns is data, and the scar is on it.** Each return enters
  through the tagging-gate as `signal-<cycle>-<i>` at `running`, its tags (never
  its content) in the cycle's record under `admitted`; when the expectation
  about it fails, that datum moves `running → scar` and the scar record names it.
  `arc3.observe.admit` tags returns `domain: observation`, `kind`, `source`, and
  the channel's `object` or `sense`.
- **Every datum that meets a mismatch is scarred** (protocol v0.3.5, Plone): the
  return, and each datum the expectation is (`held_by`) — the program, for an
  expectation it made; the observation repeated, for a standing one — each with
  its own scar record of the same ResistEvent. A scar used again returns to
  `running`, so the program circulates between the two as its expectations meet
  the region. This is how the mind turns behaviour: what enters appraisal
  changes (§6.4). A mismatch with the agent's own revision coming back from the
  store scars no expecting side.
- **The cycle datum goes to `scar` only when what it carries collides**: an
  outcome it cast (`projected → scar`), or a collision with no return of its own
  — an absence, a return the host kept out, a store arrival. Otherwise a cast
  returns `projected → running`. **A recalled scar is the datum its record
  names**, moved `scar → running` once.
- **Every record takes the clock when it happens**; the cycle datum keeps its
  cycle's start and the seal adds `closedAt`.

### Open in the current design

- A store arrival that mismatches is not tied to its own datum; the cycle datum
  stands for it. This mind returns store arrivals as they are, so it does not
  arise here. Open in dil-core too.
- A thought the mind does not keep changes no datum, so it leaves no line beyond
  the query it asked with; the time it took shows only as the gap between T4 and
  T5.
- Nothing that arrives is about "things" now, so the prior item about the
  world's things is never recalled; the one about seeing is, on the first frame.
- **C7 is `fail` wherever the agent does not look stuck.** The onlooker speaks
  only when it judges the agent stuck, so an agent that keeps varying its moves
  meets one resistance source, the frame, and C7 establishes diversity-loss.
  Declared, not arranged: the diversity C7 asks for is only as real as the
  onlooker's reasons to object.
- **The onlooker's remark reaches behaviour only through the mind.** A change of
  its stance sets the mind thinking and the model is shown what it says; a
  program that acts otherwise and predicts as well is kept. It scars only when
  its stance changes, not at every repeat, so it sets the mind thinking only
  then — except standing still, which it says anew each moment.
- **A cycle the body stood still in is a cycle.** The region returns nothing, the
  host reports only what it hears, and T7 counts no absence of the region
  (nothing was done to it). The mind commands after the onlooker; the body goes
  by the frame it stands on. Such cycles count against the run's budget and cost
  no action. Without an onlooker nothing arrives in them, so the mind is never
  asked, and the run spends its budget standing.
- **The aim's time is the model's.** `within` is how many actions the model
  expects; a large one means the aim is not met by the region within a run. Not
  bounded by the host's budget, which would put an environment's constant in the
  mind (declared).
- **One expectation a run is not attributed**: the cycle the program first
  comes back, T5 meets the frame before the store arrival that tells the mind
  its datum's id. Every later one is the program's.

## DECIDE@IMPL — what this implementation declares

Protocol §12 leaves eight constants open and says a conforming implementation
"MUST fill each and MUST declare the value it chose. Fabricating a constant at
protocol level is non-conformant." `dil-core` declares all eight for its minimal
host. The store's (F, G, H) are carried over in `store/decisions.py`; this host's
are below.

- **Tag A — concrete representation of Signal, InfoUnit, ActivityEnvironment.**
  **Declared** in `src/arc3/decisions.py`, from measured frames — and it was not
  straightforward. See "The environment" below: an observation is a *stack* of
  grids, not one grid. Note 0–15, sixteen values — 0–9 is ARC-AGI-1/2, a
  different benchmark.
- **Tag B — numeric thresholds** (matching window, stability, recurrence).
  Still undeclared. The loop ring carries dil-core's minimal-host values and
  `arc3/decisions.py` records them **as inherited, not as chosen**. Tuning them
  before a run has produced measurements would be inventing numbers, which §12
  exists to prevent.
- **Tag C / Tag D — the Mode-A anchor and the live Mode-B source.** Satisfiable.
  `dil-core` declares tag D as "host-source (live external input the agent does
  not control) … any region that returns and can resist", and an ARC-AGI-3 game
  is exactly that: it returns frames, the agent does not control it, and it
  resists prediction. The game is the Mode-B source.
- **Tag E — the reader is an onlooker: an Other outside the agent, judging how
  it behaves** (Plone, 2026-09-25). §8.4 puts reflection outside the agent — "a
  collision read into coordinates by a third party ('you drifted at this point')"
  — and a Kaggle session has no person to be that party. An Other is a position,
  not a kind (§2: "any entity occupying the relational position not-Self"), and
  a B-source may be "a hard third party … so long as it can resist" (spec,
  DECIDE@IMPL-D). So the reader is **a separate piece of code, not an agent and
  not a mind**: `src/world/onlooker.py`.

  - **Where it stands: in the world, not in the host** (Plone, 2026-09-25).
    `src/world/` is what lies outside the agent: the region it acts on, and the
    Others who see it act. The host's body touches the region and, when it does
    not act, lets a moment pass (`World.idle`); the Others see each act or its
    lack. The host hears what they say on its own channel (`onlooker`, declared
    by `declaration(onlooker=True)`); it does not hold, wrap or call them, and
    does not know what they are.
  - **It judges the agent's behaviour, not the region, and knows no game.** It
    sees acts, opaque (two are the same or not), and moments without one; not
    the grid, not the region's report, not the agent's store, `[event]` or
    program. No levels, no RESET: every act is an act.
  - **Its stance**, neutral about any environment: "standing still" (no act since
    a moment, `for` how many — said again each moment it lasts, a new nudge),
    "repeating" (the same act `REPEAT_AT = 4` times running — **not measured**,
    declared as chosen) and "back-and-forth" (x y x y). Each points at the moment
    it began. It has no claim of being right: a repetition that is getting
    somewhere is remarked on too.
  - **The mismatch is between the agent and the onlooker.** The agent's standing
    expectation is that the onlooker says what it said; a change of stance
    collides, and the scar is on the remark's datum (`domain: reflection`,
    `kind: remark`). While it keeps its stance, nothing collides — except that
    standing still is said anew each moment.
  - It returns and does not write; it holds no handle on the agent.
  - `scripts/run_game.py` puts it in the world; `--alone` leaves it out.

  **Not the peer.** A peer agent relaying this agent's recorded collisions only
  retells what the agent already wrote — a compliant source, re-authorable by the
  agent (§8.3, §8.4) — and two peers echo each other. It was removed.

  `src/dil/runtime/reflection.py` is **kept as ported from dil-core (`3a186b4`)
  and not used here**: it points a reader's view at a cycle of the trace, and to
  check the cycle it reads the agent's log, which the onlooker never sees. The
  onlooker's remark enters through the host's transducer on its own channel.

- **Tag H — situation fit.** The frame fits when the grid the mind's program
  predicted equals, cell for cell, the grid the region returned (the last of each
  stack); the region's status, when the region reports what it reported last —
  its `context`, the action just taken, is the agent's own and is not expected back.
  Not against a correct answer: no answer is ever revealed during a run.
- **Tag F — open-tag keys.** Declared in `src/arc3/decisions.py`
  (`OPEN_TAG_KEYS`): `domain`, `kind`, `source`, `object`, `sense`, each naming
  one dimension wherever it appears, which is what lets an arrival's description
  recall a stored datum.

### Declared deviations from dil-core

Each is marked `DEVIATION` in the code, additive and defaulted, so dil-core's
behaviour holds when a host declares none. dil-core has since taken the first
two in its own form (a `present` set, a `predict` rule for T5).

1. **`HostCycleInput.afforded` → `T7Input.present`.** T7 registers an absence
   only against entities the region says are there.
2. **T5's `PredictRule`** — the seam the mind plugs into. It supplies the
   expectation; it may `ask`, `write` and `test` (dil-core `a8ef7ce`).
3. **`Cycle(respond=...)`, a host-declared `RespondPolicy`**, at the close of the
   meaning-channel after appraisal, issuing layer T8, with the cycle's T5 tests in
   `RespondContext.tests`. `src/arc3/command.py` is the body carrying out the
   mind's command: the last T5 test, if the region affords it; RESET at cycle 0;
   otherwise it waits. dil-core has no body and hands the tests over after the
   cycle (`CycleResult.tests`).
4. **`COMMIT_CADENCE`** (Plone: too costly for a full agent, right for this one):
   dil-arc3 also commits at the close of every cycle in which the agent wrote a
   datum, so every version of the program is in a snapshot tied to its place in
   `[event]`.

Declared by the run (`scripts/run_game.py`): T7's `attention_span = 4.0`, scaled
by the field; the resistance-retrieval channel (`recollection`) is not wired —
the channel exists, off by default, and is not recommended as a predictor. T3
asks the store once per description: re-asking returns the same data, and asking
every cycle would crowd T2's matching window of 8.

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

- Observation: a **stack of grids** — `FrameData.frame` is
  `list[list[list[int]]]`, three levels deep. Measured on 42 real frames
  (2026-09-22): shapes `(1, 64, 64)` and `(6, 64, 64)`. So a frame is 1..N grids,
  each 64 rows × 64 columns; both games observed used the full 64×64 every time,
  though the docs say "maximum". Cells are integers **0–15** (values actually
  seen across those frames: 0,1,3,4,5,7,8,9,11,12 — ten of sixteen). Origin
  `(0,0)` top-left, `(x, y)` order. It is numbers, not an image.
- Game state is one of `NOT_PLAYED`, `NOT_FINISHED`, `WIN`, `GAME_OVER`.
- Actions: `RESET`; `ACTION1`–`ACTION4` (up/down/left/right); `ACTION5` (varies by
  game); `ACTION6` taking `x, y` in 0–63; `ACTION7` (undo). Each response carries
  `available_actions`, and only that subset may be used.
- **`available_actions` varies by game, and can be a single action.** Measured:
  `ls20` offered `(1,2,3,4)`; `vc33` offered only `(6,)`. An agent that emits
  only the simple actions does literally nothing in `vc33`. Whatever produces a
  move must read `available_actions` off the frame it is answering.
- Agent surface: `is_done(frames, latest_frame) -> bool` and
  `choose_action(frames, latest_frame) -> GameAction`.
- Competition mode allows one `make` per environment and one scorecard.

### What the engine does that its docs do not say

- **`GameAction(1)` raises `ValueError: 1 is not a valid GameAction`.** The
  members are declared `ACTION1 = (1, SimpleAction)`, so `_value2member_map_` is
  keyed by the **tuple**; `__init__` then rewrites `_value_` to the bare id, too
  late for the lookup map. Use `GameAction.from_id(1)`.
- `reset()` returns a populated frame for `ls20` and an **empty** one for
  `vc33`, which needs RESET sent as an action before the game starts. The
  boundary gate (`frame.py`) refuses a frame outside the declaration rather
  than coercing it; that is how this surfaced.
- `vc33` reaches `GAME_OVER` and **keeps reporting `available_actions == (6,)`**.
  Stepping that action in a terminal state returns an empty frame. So the
  policy reads the state, not the afforded list, and commits RESET from a
  terminal frame.

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

**What the agent is a proof of — Plone, 2026-09-23.** "If the aim were a high
ARC-AGI-3 score, a micromouse would do, and dil-core would not be needed. What we
are building is a proof of dil-core, for the Paper Track. dil-core's contribution
is the loop that gathers, processes, learns by itself and enriches data — and,
most important, that it can be audited: the event log." So the test for any
change is not whether it raises a score but whether what the loop did can be
read back, by a third party, from `[event]` alone. A game-specific strategy that
scored better would work against the paper, not for it.

**The protocol document is not the paper.** `DIL-protocol-v0.3.5.md` is 60 KB of
normative specification, written for someone implementing it. The paper is a
separate artifact still to be written, in the shape ARC Prize asks for —
abstract, introduction, prior work, approach, results, conclusion — and their
instruction is "shorter and clearer is always better. No filler, no unnecessary
equations."

## Dates — the entry deadline is the one that bites

- **2026-10-26 — ARC-AGI-3 entry deadline. DONE.** Plone accepted those rules on
  2026-09-22; `kaggle competitions list` reports `userHasEntered True` for
  arc-prize-2026-arc-agi-3, so the submission the paper must link to can exist.
- **Paper Track entry. DONE**, 2026-09-22. It is a separate Kaggle competition,
  `arc-prize-2026-paper-track`, with its own rules: entering ARC-AGI-3 did not
  enter it, and before Plone accepted them the listing reported
  `userHasEntered False` and even its 150-byte NOTE.md returned 403. Worth
  remembering that nothing in the ARC-AGI-3 work would have revealed this.
- **The paper is submitted as a Kaggle Writeup**, not as an uploaded file. The
  competition page says "You haven't created a writeup yet." A Writeup is the
  Kaggle object that links to the notebooks, datasets and models behind it —
  which is almost certainly the mechanism behind the rule that a paper "must be
  linked to a Kaggle code submission". None exists yet.
- 2026-09-30 — Milestone 2. Optional, skipped deliberately: it is judged on
  leaderboard score at that date, there is no running agent, and RHAE squares the
  action ratio, so a barely-working agent would score near zero. Missing it costs
  nothing downstream.
- 2026-10-26 — team merger deadline.
- 2026-11-02 — final submission (ARC-AGI-3).
- **2026-11-09 23:59 UTC — paper.** Settled: the competition page states
  "All submissions are due by Nov 10, 2026 at 6:59 AM GMT+7", which is that
  instant. arcprize.org's 2026-11-08 is the one that is wrong.
- 2026-12-04 — results.

Field sizes, read from the Kaggle listing on 2026-09-22: ARC-AGI-3 has **3,230
teams**, the Paper Track **198**. The track this plan aims at is the far less
crowded one, which is a reason the aim is sound — not a reason to relax.

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
- **The model constraint, resolved by reading the two paragraphs together.**
  §2.5.a requires "open source system, open source model, and open source
  weights/parameters, as defined in the checklist from the Open Source AI
  definition by the Open Source Initiative". The next paragraph exempts pretrained
  models "with an incompatible license" — and scopes that exemption precisely:
  "you do not need to grant an open source license in the preceding Section **for
  that data and/or model(s)**". The exemption covers the borrowed model, not the
  work built on it.

  So: **a downloaded pretrained model whose licence fails OSAID is fine; anything
  this project writes or trains is not exempt.** The architecture already puts the
  model in as a prediction organ that is used, not retrained, so nothing here is
  blocked. The line to remember is that fine-tuning would change this — trained
  weights would have to meet OSAID, which asks for training-data information.

  On whether open-sourcing binds a submission not chasing a leaderboard prize:
  §2.5 is headed "Winner License" and conditions on "if you are a Competition
  winner", but arcprize.org states separately that "participants must open source
  their solutions before receiving official private evaluation scores **across all
  three competition tracks**". The obligation holds either way; it just does not
  come from §2.5.
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

## The submission pipeline, verified end to end on 2026-09-22

Run against the starter kit's baseline random agent, well before the deadline,
because a code competition allows **one submission per day**: a pipeline fault
found on 1 November leaves one attempt to fix it.

```
kaggle kernels push -p notebooks/
kaggle kernels status  <user>/<kernel>          # wait for COMPLETE
kaggle competitions submit arc-prize-2026-arc-agi-3 \
    -k <user>/<kernel> -v <version> -f submission.parquet -m "<message>"
```

What the run proved: the notebook executes on Kaggle with **internet disabled**,
installing `arc-agi` from wheels the competition ships offline at
`/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels`, and emits
`submission.parquet` with columns `row_id, game_id, end_of_game, score`.

Three traps, each of which would have cost a day at the deadline:

1. **Pushing a kernel is not submitting.** After a successful push and a COMPLETE
   run, `competitions submissions` still said "No submissions found" and the
   daily quota was untouched. The submit call is separate.
2. **`submit` needs `-f` as well as `-k` and `-v`.** Without the output file name
   it returns `400 Bad Request` with no explanation.
3. **Kaggle runs Python 3.12**, and the starter kit asks for 3.12. This machine
   has 3.13 and 3.14. Nothing has broken yet, but the local run and the graded
   run are not on the same interpreter.

**The submission scored 0.02, and that number matters more than its size.**
Grading runs in two phases. Phase A is the commit run, which emits a dummy
parquet — "1 row: row_id=1_0, game_id=1, score=1", exactly what appeared in our
kernel output, so it is not a fault. Phase B is the real evaluation: a sidecar
resolves `gateway:8001` and the agent plays the hidden games server-side.

Several competitors report submissions that finish in ~30 seconds, never reach
Phase B, and score 0.00 — including one who submitted an exact copy of the
official random-agent sample. Ours scored 0.02, so Phase B ran and the agent
played. The pipeline clears the step that is currently blocking other people.

**Baseline calibration: a uniformly random agent scores 0.02.** That is the floor
any DIL agent has to beat for Accuracy to mean anything.

## dil-arc3's scored run — built 2026-09-25, not yet submitted

The notebook (`scripts/kaggle/build_dil_run.py`) has two branches in one cell:

- **Scored rerun** (`KAGGLE_IS_COMPETITION_RERUN`): it waits for the gateway
  (`http://gateway:8001/api/games`), then `scripts/run_competition.py --mode
  competition` plays every game the gateway offers. The gateway records each
  action and writes the submission; the notebook writes none.
- **Save & Run**: the same runner plays the chosen games offline, from the
  competition's `environment_files`, and writes the placeholder
  `submission.parquet` a commit needs.

How it plays, following the official harness (`ARC-AGI-3-Agents/agents/swarm.py`):
one arcade, **one scorecard, each game made on it once**, the scorecard closed at
the end. Where it differs: each game runs in a process of its own
(`run_game.py --remote`), because the mind bounds the programs it runs with
SIGALRM, which needs a main thread. The arcade and its games stay in the one
process, and each game's process reaches its game through `world/remote.py`, as
plain data both ways; `GameAction` does not survive a pickle. `CONCURRENCY`
games at once (4) share one model server. A deadline at 9 h less 20 min from the
notebook's start: no game starts after it, and a game still running is stopped.

Not verified, because only a scored rerun has a gateway: that the gateway takes
one scorecard driven from several processes' requests through one arcade; that
4 games at once finish ~110 games inside the deadline (from v9, one game of 60
cycles took 201–750 s alone); and whether a rerun's GPU time counts against the
weekly quota.

## How scoring works — settled

**110 environments, not 100.** Kaggle staff (inversion): "Submissions run on all
110 tasks." A top-3 competitor gave the split — 55 for the public leaderboard, 55
for the hidden score that decides the final ranking — and separately wrote "100
games in test data", which does not sum. 55 + 55 = 110 and the staff figure is
110, so the 100 was the slip.

**Submissions are graded when made, not re-run at the end.** "There are no rerun
at end of competition. Your final score is already computed but will stay hidden
till end of competition." With one submission a day and two selectable finals, a
submission is a commitment: there is no submitting something rough on 2 November
and improving on it afterwards. This is the strongest argument for having tested
the pipeline six weeks early.

Environment seeds are stable per task (Greg Kamradt), with one noted exception —
the black-noise animation in `lf52-271a04aa`. Whether seeds are identical across
two scored runs of the same notebook was asked and never answered.

## What the Paper Track forum gives

- There is apparently a **Public Project Link** through which a PDF can be
  uploaded, as an alternative to writing the Writeup inline.
- **A unified paper covering both ARC-AGI-2 and ARC-AGI-3 is allowed** — Greg
  Kamradt, President of the ARC Prize Foundation: "A unified paper is allowed —
  it will be judged according to the rubric as normal." Irrelevant here, since
  only ARC-AGI-3 is entered, but it fixes that the rubric is what judges papers.
- For what a winning paper looks like, Kamradt points to the previous winners at
  arcprize.org/competitions/2025 and /2024. Worth reading before drafting.

## The Paper Track's own rules

Read on 2026-09-22. Four things in them that the ARC-AGI-3 rules and
arcprize.org do not say:

- **The $375K pool is discretionary.** §1.5: "Client **may choose** to award up to
  $375,000 for papers that score above 4.5/5 on the paper rubric. If multiple
  papers score above 4.5/5, the total prize pool will be **divided equally among
  all**." Clearing 4.5 neither guarantees payment nor a fixed amount. The section
  is headed "TOTAL PRIZES AVAILABLE: $75,000"; the $450K on the Kaggle listing is
  that $75K plus the discretionary pool.
- **One submission only.** §2.2 contains a single clause — "For Hackathons, each
  Team may submit one (1) Submission only" — and no per-day limit at all. The
  Paper Track is judged by a rubric with no leaderboard, which §3.7.a says is the
  hackathon shape. So the writeup is one shot, not an iterated leaderboard entry.
  The rules never state in so many words that this competition is a hackathon, so
  treat this as a strong inference; a competitor on the forum read it the same way.
- **The team must match.** §2.1.b: "Team must match the team making a submission
  to either ARC-AGI-2 or ARC-AGI-3." Automatic for a solo entrant, but it shows
  the link to a code submission is structural.
- **There is no OSAID clause here.** The requirement for "open source system,
  open source model, and open source weights/parameters, as defined in the
  checklist from the Open Source AI definition" appears in the ARC-AGI-3 rules and
  **not** in the Paper Track's. The practical conclusion is unchanged — both
  competitions exempt a pretrained model with an incompatible licence — but the
  OSAID obligation belongs to ARC-AGI-3 alone.

Licence is CC-BY 4.0 here too (§1.6), which MIT-0 over-satisfies. No competition
data is provided at all (§1.7, §2.4.a).

## Which prize this aims at

The Paper Track pays through two mechanisms, and they are not the same shape.
From arcprize.org's paper page, read directly:

- **Top Paper — $50K / $20K / $5K.** Three prizes, awarded by **rank**. No
  threshold is stated for them.
- **Outstanding Papers Pool — $375K**, "awarded to submissions scoring above
  4.5", and "multiple parties may win from this pool". Gated by a **threshold**.

The Overview page settles the aggregation as the mean of the six criteria
(below), so the pool needs better than 27 of 30 points: an Accuracy of 0 costs 5
and makes it unreachable; an Accuracy of 2 requires a perfect 5 on all five
remaining criteria.

**So aim at the Top Paper prizes.** They are ranked, not gated, against a field
of 198. Accuracy then contributes to a ranking rather than standing as a gate
that forecloses everything, and the paper's quality is what decides the outcome.
Treat the pool as upside, never as the plan.

## Settled from the Paper Track's Overview page, 2026-09-24

Read in full from the competition's own Overview page (rendered through a
headless browser; the text is kept in `Downloads/pages/` in the workspace).

- **The 1,500-word limit is real.** "Your Writeup should not exceed 1,500
  words. Submissions over this limit may be subject to penalty." So the paper is
  1,500 words set against a 55 KB specification: it states the claim, the
  evidence and the limits, and points to the repository for the rest.
- **The score is a mean.** "Each criterion is scored on a scale from 0 (lowest)
  to 5 (highest), with the final score calculated as the average of all six."
  The bonus pool therefore needs a mean above 4.5, which confirms the reading in
  "Which prize this aims at": aim at the three ranked prizes.
- **A valid submission is four things**: the Writeup, a **Media Gallery with a
  required cover image**, an **attached public Notebook** ("If you use a private
  Kaggle Notebook, it will automatically be made public after the deadline"),
  and optionally a public project link.
- **Accuracy is tied to one submission**: "you will be asked to provide your
  submission ID to match your notebook to your submission". The notebook the
  paper describes must be the one that scored.
- **A PDF may replace the Writeup text** through the Public Project Link: "It
  should be publicly accessible and not require a login or paywall."

## Settled with Plone, 2026-09-24

- **The paper is a report on this submission, not a rewrite of the protocol and
  not a paper about DIL in the abstract.** The rules ask for "a detailed analysis
  of your submission", and Accuracy and Completeness are judged against the one
  submission it names. Shape: one claim (every thing the loop knows and every
  change in what it does can be read back by a third party from `[event]`), the
  evidence for it, and the limits, stated plainly. The protocol stays as it is
  and is linked, not condensed.
- **This repository stays private until ARC-AGI-3 ends, then goes public.** The
  paper's required public Notebook carries the code in the meantime.
- **Follow the rules as written**: keep the Writeup within 1,500 words rather
  than relying on the PDF route to go past it.

## Still unverified

- **Whether the 1,500-word limit also binds a PDF** submitted through the Public
  Project Link. The Overview states the limit for the Writeup and does not say
  either way for the PDF.
- The two official sources disagree on the Milestone 1 split: arcprize.org says
  $25K/$10K/$2.5K, Kaggle says $25,000/$7,500/$5,000. Both total $37,500. Which
  is authoritative is unknown; it does not affect this plan, but it is a reason
  to read both sites rather than trust one.
