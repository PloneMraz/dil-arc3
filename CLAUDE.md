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
next frame** over a stack of 64×64 grids with values 0–15 — a far smaller problem,
and a far better fit for the compute ceiling of a Kaggle session with no network.

## DECIDE@IMPL — what this implementation still has to declare

Protocol §12 leaves eight constants open and says a conforming implementation
"MUST fill each and MUST declare the value it chose. Fabricating a constant at
protocol level is non-conformant." `dil-core` declares all eight for its minimal
host. This repository has declared only the store's (F, G, H, carried over in
`store/decisions.py`). The rest are open, and two of them are not paperwork.

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
- **Tag E — settled: the reader is a peer agent.** §8.4 puts reflection outside
  the agent, and §10 makes it an obligation — "a private store … MUST carry the
  resistance-retrieval channel, otherwise drift is certain". A Kaggle session has
  neither network nor human, so the usual reader cannot exist. The reader here is
  **another agent running in the same session**, reading this agent's recorded
  collisions out of its log. Tag E's own wording already admits it: "WHO reads (a
  user, **another agent**, a critic service) stays deliberately deployment-open".

  This is the private-store branch done properly, not §10's shared-store branch:
  each agent keeps its own store and the retrieval channel is what crosses
  between them. The peer holds a read-only log view and no store handle, so
  §8.4's "Mode-B returns; it does not write" is kept by the type, and
  `form_reading` refuses a coordinate naming no real record, so a reflection
  cannot be fabricated about a collision that never happened.

  **The limit, which the paper must state rather than bury**: peers run the same
  implementation, with the same update law and thresholds. Peer reflection
  catches *accrued* drift and is blind to bias in the *mechanism*, which every
  peer shares equally. It is a real Mode-B channel and it is weaker than a
  genuinely foreign reader.
- **Tag H — situation fit.** Fit is measured between the frame the loop predicted
  and the frame the region returned. Not against a correct answer: no answer is
  ever revealed during a run.

**The diversity problem, and how the same move solves it.** Conformance criterion
7 (§11) fires a diversity-loss signal when the resistance-source set holds fewer
than MIN_DIVERSITY_SOURCES distinct sources over a window. An agent playing one
game has one resistance source, so §13.5 and §13.7 would render `partial`, as
they do in dil-core for the same reason.

Peer reflection fixes this as a side effect, because a peer's reading arrives
tagged ENV_PUSHED and can itself resist. Measured on a run of two agents on
different games:

| | resistance sources | §13.5 | §13.7 |
|---|---|---|---|
| agent alone | `e1` | partial | partial |
| agent with a peer reader | `agent-A`, `e2`, `region` | **pass** | **pass** |

The diversity is earned rather than arranged: the peer is a real source that
returns something this agent did not author.

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
  *An earlier draft of this file said "a 2D grid". That was read off the docs,
  not off a frame, and it was wrong.*
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

**The protocol document is not the paper.** `DIL-protocol-v0.3.4.md` is 60 KB of
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

## The host ring — what exists, 2026-09-22

`src/arc3/` is the body. Three files, 132 tests green.

- `decisions.py` — tag A, declared from 42 measured frames. Tag B recorded as
  **inherited from dil-core, not chosen**; tag H left open.
- `frame.py` — the boundary gate. It **refuses** a frame outside the
  declaration rather than coercing it, the same stance §5's tagging gate takes
  toward a datum without provenance. Verified against 52 live frames from
  `ls20` and `vc33`: 52 accepted, 0 refused.
- `action.py` — what a legal move looks like and how to hand one to the engine.
  It forms no move. Who forms one is unsettled.

### A third trap, this one in the engine's enum

`GameAction(1)` raises `ValueError: 1 is not a valid GameAction`. The members
are declared `ACTION1 = (1, SimpleAction)`, so `_value2member_map_` is keyed by
the **tuple**; `__init__` then rewrites `_value_` to the bare id, too late for
the lookup map. `GameAction.from_id(1)` works, which is why the classmethod
exists. Found by running it — reading `_value_ = action_id` suggests the
opposite.

## The entity is the affordance — settled with Plone, 2026-09-22

The loop holds an expectation about **what an action does**, not about what the
next frame looks like. A collision is the action doing something other than
expected.

Three reasons it was chosen over "the whole frame" and "the cell/region":

1. It matches what ARC-AGI-3 actually is — discovering the control scheme.
2. It matches RHAE: winning a level in few actions means learning the mechanics
   fast, which is exactly accruing confidence per affordance.
3. **It settles emission without breaking the four roles.** The model predicts
   an action's *effect* — it supplies the **expectation**, not the **choice**.
   The self picks which expectation is worth testing. The model still emits
   nothing. Exploration stops being an epsilon-greedy bolt-on and becomes a
   consequence of the mechanism.

It required **no change to the loop ring**: `T4`'s context resolver is already
DECIDE@IMPL and pluggable, so the entity id becomes the affordance, and `T5`'s
persistence rule then accrues a window of observed effects per affordance with
confidence ramping over recurrence.

### Tag H, declared and measured

Fit is equality of the **effect signature** in `src/arc3/effect.py`: a
translation-invariant description of what changed, so the same control used in
two places reads as the same event. A literal cell diff would have made every
use of a control look unrelated and the agent could never have learned its own
controls.

Measured on **316 real transitions**, not asserted:

- In `ls20` the signature **recovers the control scheme unaided** — values 9 and
  12 displace `(-5,0)` under ACTION1, `(+5,0)` under ACTION2, `(0,-5)` under
  ACTION3, `(0,+5)` under ACTION4, with 29–33 consistent observations each.
- One filter carries this. A displacement is claimed only when a value vanishes
  from as many cells as it appears in — a **rigid translation conserves cell
  count**, a spreading trail does not. Without it, one noisy value shattered the
  signature: 33 distinct signatures instead of 10, 8–11 per action instead of
  2–4, at the same 79% discrimination.
- A blocked move gives the same signature whichever direction was tried. Not a
  defect — walking into a wall is genuinely direction-blind.
- **Negative result, declared:** in `vc33` the signature carried no information.
  Across 157 transitions the click position never changed it. Whether the
  representation is failing there or those clicks genuinely do nothing is **not
  established**, and is not being guessed at.

Variants that scored worse are recorded rather than discarded: dropping the
transition counts and keeping only displacements gave a tidier 5 signatures for
`ls20` but went blind on any game whose effect is a colour change rather than a
movement, which is the `vc33` case.

## The bridge, and what running the real loop found

`src/arc3/observe.py` turns "I made move M and the region returned frame F" into
the `HostCycleInput` the cycle driver takes. It needed **no custom resolver**:
T4's declared default reads `content["value"]["entity"]`, so the transducer just
has to put the affordance there.

Two declarations it makes:

- **One affordance per action id.** ACTION6 carries `(x, y)`; treating each
  coordinate as its own affordance would create 4096 entities that each recur
  once, and nothing would accrue. Coordinates are context, not identity.
  Bucketing them would be tidier, but no measurement backs any particular
  bucketing, and §12 exists to stop that. Declared cost: `action:6`'s
  expectation cannot stabilise.
- **The agent authors moves, never frames.** T2 sees one self-written change —
  the move, observed back — and every frame change is environment-pushed. This
  is the architectural line stated in code, and it makes each affordance an
  Other under T6.

### Run on 159 real ls20 cycles

The loop runs end to end. All four affordances reached confidence 1.00 with
36–42 observations each. But **resistance never fell**: 93, 132, 129, 127 scars
per 40-cycle block.

The cause is measured, not guessed. **444 of the 481 scars were absences.** T7
registers an expected entity that did not return as a negative PredErr — but an
affordance is not a source that returns on its own. It returns only when the
agent uses it, and the agent uses one per cycle. So once N affordances are known,
N−1 absences are recorded every cycle, for ever.

`vc33` is the control that proves it: one affordance, **0 absences**, and the
scar rate was 0.58/cycle against a measured persistence ceiling of 42% — a
58% miss rate, matching exactly. **The mechanism is sound; the mapping is what
floods it.**

This is not patched around. Disabling T7 for affordance entities would be a
change to the skeleton, and it is Plone's call. Pinned by
`tests/test_arc3_observe.py::test_unexercised_affordances_register_as_absences`
so it cannot quietly stop being true.

### The other declared limit

Under the affordance reading the loop is handed **no coordinates**. It learns
what its controls do; it does not learn where anything is. Knowing the control
scheme is not the same as knowing how to win a level. In `ls20` the persistence
ceiling per affordance is 66–86%, so the residual error is largely the cases
where the effect depends on position — exactly the information withheld.

## The host, and the loop closing against a live game

### Correction to the earlier entry

What the previous section called "running the real loop" was `cycle.run()`
driven by a scratchpad script over pickled frames. **No daemon, no HostSource,
no live game — and no emission.** The actions in that replay were chosen by the
dump script's round-robin; the loop's `response` was computed and thrown away.
The loop was a passive observer of a scripted sequence. The absence measurement
stands, because it is about T7's bookkeeping and independent of who chose the
actions. The description did not.

### What plays the thinking role

**Nothing does. There is no model.** The prediction is T5's declared update law,
persistence, and it is one line:

```python
predicted = window[-1] if window else observed
```

"Predict that this control does what it did last time." That is the whole
thinking organ at present. **This is where a model goes** — it would supply the
expectation, predicting an action's effect from context, which is exactly the
role settled with Plone: the model supplies the expectation, never the choice.

### Two declared deviations from dil-core

Both are additive and defaulted, so dil-core's behaviour is unchanged when a
host declares neither.

1. **`HostCycleInput.afforded` → `T7Input.present`.** T7 registers an absence
   only against entities the region says are there. Silence presupposes the
   chance to speak.
2. **`Cycle(respond=...)`, a host-declared `RespondPolicy`.** dil-core hard-codes
   the terminal emission as `{kind: "respond", cycle, valence}` because its
   minimal host has no region to push into. A host with a real region must
   commit a real action or INV-1 never closes. The seam is at the close of the
   meaning-channel after appraisal, issuing layer T8 — **not in a layer**. A
   layer emitting the move would make the thinking organ the actor.

`src/arc3/respond.py` declares the policy: commit the afforded action whose
expectation is **least resolved**, ties on fewest observations then lowest id.
An affordance never met ranks at confidence 0, so the loop reaches for what it
does not know first. Exploration is not bolted on; it is what the loop's own
state recommends.

### `src/arc3/host.py` — the body

`Arc3Source` is a `HostSource` over a live game. `deliver` executes what the
self committed — *the agent acts through deliver* — and the following `next`
reports what the region did. Nothing here chooses; a move the frame does not
afford is refused, never substituted, because swapping in a legal action would
put the choice in the body.

Cycle 0 reports the opening RESET with a **null effect**: `reset()` makes the
first frame out of nothing and there is no earlier frame to difference it
against. It binds an `action:0` entity the game never affords, which is also the
live check that the presence filter works.

### Measured on live runs, 80 cycles each

| | `ls20` | `vc33` |
|---|---|---|
| precondition gate | Qualify | Qualify |
| cycles / actions | 80 / 80 | 80 / 80 |
| scars from the region (absences) | 225 | 1 |
| scars from an affordance | 4 | 45 |
| levels completed | 0 | 0 |

**The absence flood persists in `ls20` and the presence filter does not touch
it**, exactly as forecast when option (ii) was chosen: `ls20` affords all four
actions every cycle, so all four are genuinely present and three are genuinely
unused. The filter is live — it is what keeps `action:0` from being registered
absent, and `vc33` shows 1 absence rather than a flood — but it does not solve
`ls20`. The remaining question is whether an affordance that is present but
*unasked* should count as silent. Not decided here.

**Two engine behaviours found by running it**, neither documented:

- `reset()` returns a populated frame for `ls20` and an **empty** one for
  `vc33`, which needs RESET sent as an action before the game starts. The
  boundary gate refusing the empty frame is how this surfaced.
- `vc33` reaches `GAME_OVER` and **keeps reporting `available_actions == (6,)`**.
  Stepping that action in a terminal state returns an empty frame. So the
  policy reads the state, not the afforded list, and commits RESET from a
  terminal frame.

**Neither game completed a level.** The move distribution is 20/20/20/20 — with
all four affordances at confidence 1.0, ties break on fewest observations and
the policy round-robins. That is a systematic sweep, not learning-driven
behaviour, and it is the declared limit showing up in the numbers: the loop
knows what its controls do and does not know where anything is.

## The model — the thinking organ

`src/arc3/model.py`, plugged into T5's `PredictRule` seam (declared deviation
**#3**, same additive-and-defaulted shape as the other two; dil-core's
persistence stays the default). The model supplies the **expectation** and
nothing else: it never sees the afforded set and never reaches the emission, so
it cannot choose. The model thinks, the self acts.

### Why it is not a downloaded network

Three constraints, each on its own sufficient:

- The scored games are **unseen**, and their mechanics are the thing to be
  discovered. Weights trained on other games predict the wrong world.
- Kaggle's evaluation session has **no network**.
- **INV-5 forbids the alternative outright**: "refeeding the whole game history
  into a context window each step is a load, not an accrual". A large model
  re-reading its own history every step is exactly what the invariant names.

What is left, and what the protocol actually asks for, is a predictor that
**accrues within the episode**. It starts knowing nothing about the game it is
in.

### What it conditions on

Persistence predicts that a control does what it did last time; measured, that
is right 76% of the time in `ls20`. The residual is position — whether a move is
blocked depends on what is in the way. So the context is **what lies where the
move would land**: the values of the cells the mover would arrive on, as a
multiset, so the same obstruction met at two places reads as one situation.

The mover and each action's displacement are **learned from the agent's own
effects**, not configured. On real `ls20` frames the model recovered
`action:1 → (-5,0)`, `action:2 → (+5,0)`, `action:3 → (0,-5)`, `action:4 →
(0,+5)` and a mover of value 9 — the control scheme, from nothing.

### Measured, with the two gains separated

The model changed **two** things at once — majority vote over accrued evidence
instead of most-recent, and context conditioning. Reporting one number would
credit context with wins that majority alone produces.

| on 316 real transitions | `ls20` | `vc33` |
|---|---|---|
| most-recent (dil-core persistence) | 76% | 41% |
| majority, no context | 76% (**+0**) | **69%** (+28) |
| majority + context (the model) | **94%** (+18) | 69% (**+0**) |

**Two different mechanisms, each carrying one game.** In `ls20` the whole gain
is context; in `vc33` the whole gain is majority, because no mover is learnable
there — `vc33` produced no rigid displacement at all, so its context was empty
in every one of 157 cycles.

Live, 80 cycles each, scars sourced to an affordance fell from **4 → 2**
(`ls20`) and **45 → 23** (`vc33`).

### A defect the tests found, which the real frames had hidden

The background collected displacement votes it had not earned: when a thing
steps into empty space, the hole it leaves steps the other way, so the
background mirrors every move and can tie with — or beat — the thing that
actually moved. On real frames the rigidity filter already excluded it, so the
live numbers never showed it; a clean two-value frame exposed it immediately.
The model now votes for a background separately and excludes it, and keeps
displacement votes keyed by value so the mirrored vote cannot outrank the real
one. **The measured numbers are unchanged by the fix** — it buys robustness, not
score.

### What it does not do

Neither game completed a level. The model improves **prediction**, not
**winning**. Knowing what a control does, and knowing it 94% of the time, is
still not knowing where to go.

## Attention, and the absence flood dying

Ported from dil-core, where the gap actually was. T7 now carries two gates, both
additive and defaulted: `present` (the region's word — an entity it says is not
there is not silent) and `attentionSpan` scaled by the field's `attentionGain`
(the field's word — an entity the loop is no longer oriented toward is not being
waited on).

**Measured live on `ls20`, 80 cycles per run:**

| `attentionSpan` | scars | absences | real resistance |
|---|---|---|---|
| ∞ (the old behaviour) | 227 | **225** | 2 |
| 3 | 221 | 219 | 2 |
| 2 | 149 | 147 | 2 |
| 1 | 76 | 74 | 2 |
| 0.5 | 2 | **0** | 2 |

**The right-hand column never moves.** Attention removed 225 false absences and
not one real collision. That is §8.2's line holding in live data rather than in
a promise: attention lowers what is demanded back, never what is registered.

`span = 0.5` reaches zero, and is not the answer: §8.1 **C3** requires a
missing-InfoUnit when an expected event fails to occur, and a loop that expects
nothing fails C3 by construction. `span = 1` keeps C3 alive while cutting
225 → 74.

### The loop sets its own attention width

The span no longer has to be hand-tuned per game. T6 — the layer that *accrues*
Others — contributes `attentionGain = 1/N` upward into the field through the new
INV-7 up-channel, and T7 reads it at N+1. The host declares a span meaning "how
long I would wait if I had one thing to watch"; the loop divides by how many
things it is actually holding.

Measured live on `ls20`, where T6 accrues five entities (`action:0` plus the
four affordances), so the gain settles at 0.2:

| declared span | effective | absences | real resistance |
|---|---|---|---|
| ∞ | ∞ | 225 | 2 |
| 8 | 1.6 | 76 | 2 |
| **4** | **0.8** | **3** | **2** |
| 2 | 0.4 | 1 | 2 |

**225 → 3 at a declared span of 4**, with C3 still alive, and the real-resistance
column still untouched.

### The resistance-retrieval channel, and a negative result

§10 requires a private store to carry the resistance-retrieval channel. It now
exists here: `dil/loop/recollection.py` reads `[event]` and answers with an
expectation — what the region gave, last time, in this same situation — and
nothing else. `scar → running` fires for every scar it returns, so the store is
genuinely being read for the first time.

Two sources of expectation then exist: the model, which says what it has
learned, and the record, which says what the region actually did. §6.4 already
settles what to do when two internal sources disagree — "the opposition is not
resolved by an internal rule but collided against the region" — so nothing
arbitrates on the merits: where the record speaks, it is what gets TESTED.

**Measured, 200 cycles per game. It does not work.**

| | `ls20` OFF | `ls20` ON | `vc33` OFF | `vc33` ON |
|---|---|---|---|---|
| prediction errors | 9 | **16** | 58 | **113** |

And the contests themselves, across both games — **66 disagreements**:

| the region sided with | count |
|---|---|
| the model | 62 |
| the record | **1** |
| neither | 3 |

The record lost 62 of 66 and roughly doubled the error rate in both games.

### Why — a sampling bias, and no verdict anywhere

An earlier draft of this section said the store holds "the occasions on which the
agent was wrong". That was wrong, and it imported a verdict the protocol
explicitly refuses. §9: the tag "carries no claim of correctness", and "judging
correctness is the work of Mode-B and of an external third party reading the
scar, **never of the store**"; a datum that has met no resistance "is not wrong,
only not yet tested". §3 defines the unit exactly: a ResistEvent is **a
registered mismatch between the agent's expectation and what the region
returned** — divergence, not error.

The real mechanism is a **sampling bias**, and it is sharper than the
correctness story. A scar's `received` field is a genuine return from the
region; nothing about it is mistaken. But a scar exists *only where the return
diverged from what was expected*. So conditional on a predictor that mostly
works, the recalled set is exactly the subset of returns that **surprised** the
loop — which are the rare ones. The record recites the region's exceptions, and
recites them faithfully. The model answers with the distribution. Asked "what
will happen", the exception loses; that is arithmetic, not a defect in either.

`vc33` shows it plainly: the record disagreed with the outcome 54 times while
*agreeing with the model*. Both named the same thing and the region did something
else — the record was not contradicting the model, it was reporting an old
surprise.

This is the quantitative form of a worry raised before the design was chosen,
now stated correctly: if only mismatches enter the store, **the better the
predictor gets, the rarer and more exceptional the store's contents become**. In
`ls20` the model is right 94% of the time, so what the store holds is the 6%
that surprised it.

### What the record is actually for

Which is not nothing. §9's chain is mismatch → memory → learning → change: a
ResistEvent is where the region pushed back, and that is what the loop is
supposed to change *from*. A faithful record of every point where the region
resisted is exactly right for driving change, and exactly wrong for answering
"what happens next". The measurement here says only the second thing.

### What is kept, and what is declared

The channel stays, wired and tested, and **off by default** (`recollection=None`
keeps the reference behaviour exactly). It is not recommended as a *predictor*
on this evidence. What it might still be good for — a signal that a situation is
unstable, rather than a claim about what will happen — is not settled, and is
not being guessed at here.

## The fit floor, and what bounds its reach

Ported from dil-core: the field can raise the floor a situation's fit must clear
before the loop builds forward from it — attention over *situations*, under the
`H_COUNT` ceiling. Measured live on `ls20`, 60 cycles:

| `fitFloor` | forward-builds | scars | real resistance |
|---|---|---|---|
| 0 (the old behaviour) | 55 | 5 | 2 |
| 0.5 | 51 | 5 | 2 |
| 0.99 | 47 | 5 | 2 |

The scar column does not move at any setting: the floor selects what is **built
forward from**, never what is **registered**. That is the §8.2 line again, held
in live data.

**Its reach is bounded, and by tag B.** `SUFFICIENT_RECURRENCE` is 3, so
confidence saturates after three observations of an entity and clears any floor
below 1 from then on. The floor bites only while confidence is still ramping,
which in a 60-cycle run is a short window. That is not a flaw in the floor — it
is the untuned tag B showing through, the one still declared here as inherited
from dil-core rather than measured.

### A design error the measurement caught

The contribution was put on T8 first, and it did nothing: the gain sat at 1.0
for all 80 cycles. T8 ranks the Others *present this cycle*, and in this host one
affordance returns per cycle, so T8 saw N = 1 every time. How many Others the
loop holds is **accrued** knowledge, and T6 is the layer that accrues it. Fixed
upstream in dil-core first, with a test pinning it there.

### What this corrects in the earlier entry

The absence flood was reported here as a consequence of the affordance mapping,
and the open question was whether an affordance that is present but unasked
counts as silent. That framing was too narrow. The flood is the signature of a
loop with **no attention at all**: every entity ever seen expected back every
cycle, for ever. With one entity it is invisible; with N entities of which one
returns per cycle it is N−1 false absences per cycle, in any host, for any
domain. The affordance mapping only made it visible.

## What a third party can read of the prior, 2026-09-23

Measured by reading a live run's `[event]` log directly, not through this code:
the five T3 queries were there and `prior:directive` moved `prior → running` at
cycle 1 — but **960 of 960 layer-exit lines were the cycle datum's**. The
recalled datums ran T1→T8 and left no path; their floor-tags stayed at 1; their
tags lived only in mutable `[data]`. So a reader could see that *something named
`prior:directive` began to run*, and not what class of data it was, nor that it
came through the gate — which §13.6 asks a third party to confirm from traces.

Re-reading §9 settled the fix and ruled out the first proposal. Writing each
prior's CONTENT into `[event]` at admission would put uncontested information
into the agent's memory — the log is also what recollection reads — and §9 keeps
the trail complete "without letting uncontested information into the agent's
memory". Admission is not an edge of the provenance graph, so the protocol does
not ask for it to be logged. What it does ask: "every layer a datum exits MUST
be recorded", no pass-through layers, and an open layer that makes the log
"auditable by data class". Plone chose (b): the path, and the tag set, never the
content.

Fixed in dil-core (`d358902`), ported: a recalled datum's exits are recorded
under its own id, its floor-tag is stamped as it passes, and the cycle's activity
record carries its full tag set (fixed and open). A cycle that recalls nothing
writes exactly what it wrote before. The checker gained two trace claims — a
recalled datum's path covers T1→T8 (C3), and every datum leaving `prior` shows a
gate-admissible tag set in that cycle's record (C6, §13.6) — and a test pins that
a datum appearing from `prior` with no tags in the trace fails.

Live, 120 cycles each, read from the JSONL:

| | `ls20` | `vc33` |
|---|---|---|
| layer-exit lines | 960 cycle + 8 × 6 recalled | same |
| recalled tag sets in the cycle-1 record | 6, floor-tag 8 | 6 |
| directive text anywhere in the log | 0 | 0 |
| hash chain | ok, 4 082 records | ok, 3 284 |
| conformance | 5 pass, 1 partial (C4, by design), 1 unverifiable (C2) | same |

C2 is unverifiable only because the gate result was not handed to the checker;
the run itself qualified. C4's partial is §7: continuity is attributable only by
a third party.

## The prior — what the character may know before it lives, 2026-09-23

Settled with Plone. The zero levels are not a defect: the character was put in
the maze with no problem to solve. A creature put in a box arrives with a very
long history (genes, and what Others taught it); this one arrives with none, at
the level of a zygote with a wide range of action. So the least it must be given
is **a directive**, tagged `prior`, and everything after that is its own thinking
and interpretation. Plone: "Đừng tự làm khó mình và làm khó nhân vật" — give it
what the rules allow it to know.

### What the rules allow it to know, verified

Read in full on 2026-09-23: the ARC-AGI-3 Technical Report, the docs pages
game-schema, actions, methodology and competition_mode, and the Kaggle rules
(rendered through a headless browser, since the page needs JavaScript).

- The directive: the official leaderboard gives every model the same system
  prompt, "You are playing a game. Your goal is to win." (report, §4.3.1).
- `WIN` = "The objective was completed successfully", `GAME_OVER` = "The run
  ended without a win" (game-schema).
- Structure, cost, body and the world's core-knowledge priors (objectness,
  geometry and topology, basic physics, agentness; no language or cultural
  symbols).
- The Kaggle rules permit external data that is "publicly available and equally
  accessible to use by all Participants" (§6.a) and forbid "information from hand
  labeling or human prediction of the validation dataset or test data records".
  Public documentation is the first and none of the second.

What the report warns against is a different thing: a harness carrying
"ARC-AGI-3 specific strategies". The rules of the place are not a strategy;
nothing here says how to win any game.

### `src/arc3/prior.py`

Five items (`directive`, `levels`, `cost`, `body`, `world`), 31 sentences, each
quoted verbatim with the document it was read in. All 31 were checked
programmatically against the downloaded sources. The host declares them as
`StoreDeclaration.preexisting`; the runtime's requisition admits each through
the tagging-gate as `prior`, cycle-mark null. A test pins that an item carrying
a verdict tag is refused and reported, not admitted.

Declared: admission happens only with a real substrate (`store_root`). The
in-memory fixture the live measurement scripts ran on has no requisition step.

### How the prior is recalled — settled with Plone, same day

First found: **nothing read the prior once it was admitted.** It sat in `[data]`
stamped `prior` and never made the `prior → running` move §9 defines — a sixth
instance of a channel present in the topology that nothing drew on.

Plone settled how it enters, correcting both options put to him. Data does not
flow in by itself — the store is the character's memory, and memory pouring in
unasked is overload, a disease in a living thing. So the character asks. But
what it retrieves then enters the loop and runs every layer, and that is when
its tag changes from `prior` to `running`. `prior` is only a state tag: it tells
the character that the datum is not its own, has not been through its own
experience, and needs to be tested. (§9 agrees: "Running many cycles does not
wash a prior to tested status; only collision-and-hold does.")

The protocol already had every piece; the first proposal here invented an
`about` tag the open layer already covers, and Plone sent it back to be re-read.
What is used:

- **§6.4, T3 query** — "opens or calls a channel to ingest actively". The
  channel called is the store.
- **§6, link 1** — query returns are an input channel, so the return arrives at
  T1 the next cycle and runs T1→T8.
- **§9 open layer, tag F** — a key denotes the same dimension wherever it
  appears. That is the index: an arrival's description and a datum's open tags
  are matched on the same keys. This host declares its keys in
  `decisions.OPEN_TAG_KEYS`; the one doing the recalling is `object`.

Fixed in dil-core first (`5bb031a`), then ported. T3 asks once per description
it has not asked about. T7 no longer registers a recalled datum absent on cycles
it was not asked for — measured before that fix, with no presence reported, it
was registered absent every cycle from the second on.

The status transducer describes its reports as `object: region-status`; the
directive carries the same tag. The other four items are about other things
(`level-structure`, `action-cost`, `body`, `things`) and nothing arriving
describes those yet, so they wait.

**The signs left the code.** `region_valence` now reads the region's answer
against the recalled directive; with none recalled every answer reads 0. What
stays in the mind is the interpretation — what an objective and a run ended
without it mean. Which states those are, and what the region counts on the way,
comes from the directive.

### Live, 120 cycles, with a real substrate

| | `ls20` | `vc33` |
|---|---|---|
| admitted through the gate / rejected | 5 / 0 | 5 / 0 |
| store queries from T3 | 1 (`object: region-status`) | 1 |
| `prior:directive` → `running` | cycle 1 | cycle 1 |
| directive in the mind from | cycle 1 | cycle 1 |
| other priors | still `prior`, no cycle-mark | same |
| moves committed | `4:38 1:28 3:28 2:26` | ACTION6 swept |
| levels | 0 | 0 |

Behaviour is identical to the run before, and that is what should happen: the
directive carries exactly the content the hard-coded signs had. What changed is
where it comes from and that an auditor can see it arrive. It does not, by
itself, get the character through a level; nothing about how to win was ever in
it.

### The three limits that run left, worked through

**1. Four items were never recalled.** Because no arrival described what they
were about. The descriptions were made honest rather than the items forced:
a status report carries the region's state, the change in its level count and
the actions it affords, so it is about all three (`object`: `region-status`,
`levels`, `actions`); a thing's change is about a thing and came by sight
(`object: things`, `sense: vision`). dil-core now lets one arrival carry several
descriptions. The old `body` item mixed what the body sees with what it can do;
it is split into `seeing` (`object: frames`, `sense: vision`) and `actions`
(`object: actions`). `sense` is declared in `OPEN_TAG_KEYS`. All 31 quotes
re-verified against the sources after the split.

**2. The query's return was never read back by T2.** §6.4 rule 3 wants every
emission readable by T2 next cycle; T2 only saw the committed response. Fixed in
dil-core (`9b0bbdf`), ported: T2 also reads last cycle's lateral emissions, and
each return arrives as an observed change whose value is the query that asked,
so T2 tags it SELF_WRITTEN. The content stays not-its-own; agency and
provenance are different questions.

**3. T3 asks each description once — kept, and why.** Re-asking returns the
same data, already `running` and in use. Nothing added to `[data]` later carries
these tags, so there is nothing new a second ask could find. Asking every cycle
would put three to five queries a cycle into T2's matching window of 8, crowding
out the moves it has to recognise. It would bite if a datum carrying a cue's
tags entered `[data]` after that cue was asked; none does here. Declared, and
put to Plone.

Live, 120 cycles, 6 items admitted, 0 rejected:

| | `ls20` | `vc33` |
|---|---|---|
| queries | 5 (things, vision, region-status, levels, actions) | same 5 |
| items `prior → running` | all 6, cycle 1 | all 6, cycle 1 |
| `self:move` SELF_WRITTEN | 118 / 120 (2 before T2 is stable) | 118 / 120 |
| store returns | 6, all UNDECIDED | 6, all UNDECIDED |
| moves | `4:38 1:28 3:28 2:26` | ACTION6 swept |
| levels | 0 | 0 |

**Read the UNDECIDED row correctly.** Every return arrives at cycle 1, and T2
classifies nothing before `STABILITY_THRESHOLD = 3` cycles have run — its own
move is UNDECIDED then too. The path is closed and tested (with a threshold of
1 the return is SELF_WRITTEN); in a live run it simply never has a return to
close on after cycle 2. The threshold is tag B, inherited, untuned.

**What is still true:** the mind reads one of the six — the directive, whose
payload is structured. The other five are sentences. They run the layers and are
in use as data, but nothing in this mind can read English, so they change no
expectation.

## Individuals, and curiosity that follows progress

Two changes, both approved by Plone, both measured before they were wired.

### (a) Tracked individuals, grouped by common fate

The contact reading proposed to fix curiosity's stickiness helped overall
prediction (93 → 97%) and did nothing for the moving object (70 → 66%). The data
said why: under ACTION1, "thing:9" moved (−2,0) 29 times and held (0,0) 12 times —
a clean blocked-or-not outcome — but value 9 is **five pieces**, one of which
moves, and any reading of the stuff was the union over all five. The declared
limit ("a kind of stuff, not an individual") was exactly what blocked the fix.

`seeing.py` follows each piece across frames (nearest centroid within its value),
groups pieces that repeatedly move together by the same displacement
(`MIN_COMOVEMENTS = 2`, vetoed outright by any occasion of moving apart), and
reads for each thing what it faces first on every side. Measured on the 316 saved
transitions:

| identity | churn | ls20 | vc33 |
|---|---|---|---|
| value (stuff) | 1.0× | 93% | 85% |
| tracked piece + what lies ahead | 1.5× | 98% | 94% |
| **tracked, grouped by common fate** | **1.7×** | **99%** | **93%** |

Without grouping the moving object's front part was predicted 100% and its back
part 67%: it is drawn in two colours, segmentation splits it, and a ray from the
back stopped at its own front and never saw the wall. With grouping the object is
`thing:9+12`, and its blocked-or-not outcome is predicted **100%** (35 of 35).

**Order is INV-8.** Grouping learns from how pieces moved, and the situation a
thing is read in predicts how it will move. The scene is read with the groups
the past formed; this cycle's co-movement is accrued afterwards. A test pins that
the group appears in the look *after* the one that supplied the deciding
evidence.

The stuff-level readers in `interpret.py` (`changes_of`, `contacts`,
`interactions_of`) and `Region.kind` were removed once nothing in production
called them. Churn rose partly because a thing is renamed when its parts are
first grouped (`thing:12#8` → `thing:9+12#8`); that is declared, not hidden.

### (b) Curiosity follows learning progress

Least-resolved-first is greedy toward irreducible noise: whatever the mind can
never predict stays least resolved for ever, and curiosity never leaves it. The
mind now reports `progress:action:N` — the absolute change in accuracy between
the last `PROGRESS_WINDOW = 4` uses of an action and the four before — and the
policy composes it with want as `−(progress + valence)`. Unlearnable noise shows
no progress; an action whose accuracy starts falling counts again; an action with
fewer than eight uses counts as still being learned, which is also what puts an
untried action first.

This replaces the policy's base rather than modulating it, which went beyond the
earlier approval ("modulate, not replace"); Plone approved it explicitly.

### Live, 120 cycles

| | `ls20` before | `ls20` after | `vc33` after |
|---|---|---|---|
| moves committed | `1:103 2:9 3:4 4:4` | `4:38 1:28 3:28 2:26` | ACTION6 swept |
| `resolved:action:*` | 0.91–0.94 | 0.97–0.99 | `6`: 0.93 |
| things per cycle | 9 | 19 | 12 |
| situations the mind has met | 45 | 176 | 56 |
| `SocialEdge` | 5 | 28 | 20 |
| moving object's distinct positions | not measured | **19** | — |
| levels completed | 0 | **0** | **0** |

It does not oscillate in place: the last twelve positions of the run walk a
straight line leftward across the grid, following the one action still showing
progress (`progress:action:3` = 0.12, all others 0). It did spend five cycles
pressing into the right-hand wall before that.

**Still 0 levels, and the reason is unchanged: want can only avoid.** Every
`valence` in `ls20` is 0 because the region has never answered anything with a
level or a win.

## A regression in the rebuild, and the technical items closed

### The regression

The respond policy ranked actions by T5's confidence in an entity named
`action:N`. The rebuild made entities things, so no entity carried that name,
every action ranked `(0, 0, id)`, and the lowest id won every cycle. Measured on
a live `ls20` run: **ACTION1, 40 times out of 40.** The rebuild's first
behaviour figures — 44 scars, 1 absence, 8 resistance sources — came from an
agent pressing up into a wall. Its perception figures (9 Others per cycle,
`RelValue` in the hundreds) were sound; its behaviour figures were not, and they
were reported without the move distribution that would have shown it. `vc33` was
unaffected, affording only ACTION6.

### What the policy reads now

Only the field. The mind accrues, per situation (per action, here), how well it
predicts what follows and how the region has answered — and reports both upward
as `resolved:action:N` and `valence:action:N`. The field's blend keeps no memory
of its own (a key contributed this cycle takes this cycle's average), so the
memory is the mind's and the field carries the current reading. The policy
composes the two as `resolved − valence`, lower first: curiosity is the base and
want shifts it. Ties break on the self's own record of what it has committed.

`region_valence` is the one place a sign is put on an outcome: +1 for a
completed level or a win, −1 for game over, 0 otherwise. Declared, named, and
not a goal — it reads how the region answered; want is what the composition does
with that.

### Other-to-Other interactions

The mind reads contacts *made or broken* between two kinds of stuff, and the host
carries them in as T8's `interactions`. Standing contacts were measured at ~10
per frame and nearly constant, so they would have said nothing; made-or-broken
came to about five per eighty transitions — sparse and real. `SocialEdge` went
from 0 to 5 (`ls20`) and 14 (`vc33`) over 120 cycles.

### T8 was a sink

Nothing read T8's output. INV-1 forbids dead branches and §6.2 says "T8 closes
back into the loop, not into a sink". T8 now contributes `interactions` and
`resistanceConcentration` to the field. Fixed in dil-core first (`a1914f3`).

### Live, 120 cycles

| | `ls20` | `vc33` |
|---|---|---|
| moves committed | `1:103 2:9 3:4 4:4` | ACTION6 only, swept |
| `SocialEdge` | 5 | 14 |
| scars / absences | 90 / 1 | 119 / 4 |
| `resolved:action:*` | 0.91–0.94 | `6`: 0.86 |
| `valence:action:*` | all 0 | `6`: −0.02 |
| levels completed | 0 | 0 |

### What is still wrong, diagnosed

**Curiosity sticks.** ACTION1 took 103 of 120 moves in `ls20` because it is the
least resolved action (0.91), and it is least resolved because its outcome
depends on position — blocked or not — while the context is the action alone.
The mind can never resolve it, so curiosity never leaves it. This is the "noisy
TV" failure of curiosity-driven exploration, and its cause here is specific: the
situation the mind reads against is too coarse. The hand-coded landing patch had
supplied exactly the missing piece; removing it was right, but nothing has yet
replaced what it carried.

**Want can only avoid.** `valence` is 0 for every action in `ls20` because the
region never answered anything with a level or a win. In `vc33` a single game
over registered as −0.02 on ACTION6, and with one afforded action it can change
nothing. Want exists and is wired; it has never had anything to want.

## The rebuild, measured end to end

`entity = thing`, `context = action`, and the two rings swapped back:

| ring | files | job |
|---|---|---|
| **body** | `frame.py`, `action.py`, `host.py`, `observe.py` | receives, gates, carries, executes. **Concludes nothing.** |
| **mind** | `perceive.py`, `interpret.py`, `mind.py` | finds things, reads what became of them, says what they will do. **Chooses nothing.** |

`effect.py` and the old `model.py` are gone. Nothing in production referenced
them once `perceive.py` and `interpret.py` existed — segmenting first makes the
frame-level signature unnecessary, because a thing's displacement is just where
it was against where it is, with no rigidity filter and no translation
invariance to engineer.

### Prediction, on the same 316 transitions the old mapping was measured on

| | old (affordance + hand-coded landing patch) | new (things) |
|---|---|---|
| `ls20` | 94% | **93%** |
| `vc33` | 69% | **85%** |

One point given up where the hand-coded feature was doing the work, **sixteen
gained** where it was blind — and the feature is gone.

### Live runs, 60 cycles each

| | `ls20` before | `ls20` after | `vc33` after |
|---|---|---|---|
| Others per cycle | 1 | **9** | **7** |
| T8 `RelValue` | **0** | **540** | **420** |
| T8 `SocialEdge` | 0 | 0 | 0 |
| total scars | 227 | 44 | 61 |
| of which absences | **225** | **1** | **2** |
| distinct resistance sources | 2 | **8** | 3 |
| `channelActivity` in the field | 1.0 constant | **9.0** | **7.0** |

**T8 produced nothing at all before and produces hundreds of `RelValue`s now** —
the top of the meaning-channel has work for the first time.

**The absence flood is gone structurally, not patched.** 225 → 1. Attention was
holding it down; the real cause was that an affordance cannot be absent, and a
thing can: it either is in the frame or it is not. §13.7's source diversity also
stops being nominal — resistance now arrives from eight distinct Others instead
of one.

### Still zero, and declared

`SocialEdge` is **0**. It needs Other↔Other interactions, which the host never
supplies — `HostCycleInput.interactions` is left empty. Under the old mapping the
idea was meaningless (two buttons cannot interact without the agent); under this
one it is perfectly meaningful — `thing:9` touching `thing:5` is exactly that —
and it is simply not implemented.

`levels_completed` is **0** on both games. Nothing reads the goal; that is
unchanged and is not a consequence of this rebuild.

## Entity was the wrong thing, and T8 said so

`entity = affordance` was settled early and it was wrong. §8.4 defines an entity
as "an other-entity the agent does not control", and §6.3 puts the layers that
live off it above T4: T6 builds an `OtherModel` of it, T8 builds `RelValue` and
`SocialEdge` — the latter being "an Other↔Other interaction with **no self
present**". An entity is an *Other*. It is not the self, which T2 already
separated, and it is not an action the agent can take.

An affordance passes T4 and T5 and starves everything above. Measured over a
real run:

```
T8 over the run:  RelValue = 0   SocialEdge = 0   others/cycle = [1]
```

**The top layer of the meaning-channel produced nothing, ever.** `RelValue`
needs N ≥ 2 and there was never more than one Other present; `SocialEdge` needs
two Others interacting without the agent, and two buttons cannot do that. The
absence flood was the first symptom of the same error: an affordance does not
return on its own, so asking whether it fell silent was the wrong question from
the start. Attention patched the symptom.

### Roles were inverted, both of them

The host handed the loop a finished interpretation — "the thing of value 9 moved
up five" — while the model reached past the loop into the raw grid to decide what
was worth looking at. The body was concluding and the mind was sensing. Under the
biological reading Plone set out — host is the body that receives signals, model
is the thinking and interpreting part, DIL is how information moves, `store/` is
memory — both belong the other way round.

### `perceive.py`: the model reads the signal

Things are connected runs of one value, four-connected, excluding whatever the
grid is mostly made of. The background is *read* rather than assumed, so a world
on a non-zero background still parses.

**Identity was chosen by measurement, over 60 real frames per game.** The score is
churn: how many identities exist overall against how many are present in any one
frame. An identity that changes when the thing changes is not an identity.

| identity | overall | per frame | churn | ever moves |
|---|---|---|---|---|
| value + bbox | 101 | 16.3 | 6.2× | 5 |
| value + size | 101 | 16.3 | 6.2× | 4 |
| **value** | **8** | **8.0** | **1.0×** | **4** |
| value + channel | 16 | 8.0 | 2.0× | 3 |

Value alone holds at **1.0× in both games** — every identity present in every
frame. Extent and cell count fail hard: a thing that changes shape becomes a
different thing six to ten times over. Channel was rejected on the same
evidence, because `ls20`'s stack depth varies.

**Declared limit:** this is a kind of *stuff*, not an individual. Every cell of
value 9 is one Other however many separate pieces they form. Telling individuals
apart needs matching across frames, which is a further interpretation and is not
done. What it does buy is what affordances never could — **six to eight Others
present at once**, so T8 has the N ≥ 2 it has never had.

Segmentation costs ~5.7 ms per frame pair, measured; ~0.6 s over a hundred-cycle
run.

## What GLOB-MOD actually holds, read off a live run

Attention is a composition now, not one layer's formula. Each layer contributes
the fact it can see and no other layer can, at weight 1, and decides nothing
about what follows: T3 `channelActivity`, T4 `strangeness`, T5 `surprise`, T6
`otherCount`, T7 `silence`. T7 reads the width off the composition —
`(1 + strangeness) / max(1, otherCount)` — and `RespondContext` now carries the
field, so it can reach behaviour.

Traced on `ls20`, 40 live cycles:

```
cyc channelAc strangene  surprise otherCoun   silence  ->width  ->span
  1     1.000     0.000     0.000     1.000     0.000    1.000   4.000
  2     1.000     0.000     0.000     2.000     0.000    0.500   2.000
  4     1.000     0.000     0.000     3.000     1.000    0.333   1.333
  6     1.000     0.000     0.000     4.000     1.000    0.250   1.000
  8     1.000     0.000     0.000     5.000     1.000    0.200   0.800
 20     1.000     0.000     0.000     5.000     0.000    0.200   0.800
 40     1.000     0.000     0.000     5.000     0.000    0.200   0.800
```

**Two of the five facts are constants in this host, and the rest go flat after
cycle 8.**

- `channelActivity` is 1.000 for ever: the host sends exactly one signal per
  cycle, so the number carries nothing.
- `strangeness` is 0.000 for ever: T4's resolver always finds the entity,
  because the host always knows which affordance it just used. There is no
  entity novelty in this host to measure.
- `otherCount` climbs 1 → 5 and then freezes: five affordances, all met by
  cycle 8.
- `surprise` and `silence` do move, and they are the only two that do.

So the composition machinery is right and **the host is not feeding it anything
that varies**. The field is legible now, and what it legibly says is that it has
almost no context to compose from.

### The model's interpretation now reaches the field — and the field goes static anyway

`PredictRule` gained `contribute`, so the model reports what only it can read:
`contextNovelty` (is this situation one I have met?) and `contextsKnown`. Both
land in the field, bound to T5, and `attentionWidth` composes novelty as a third
fact. Traced live on `ls20`, 48 cycles:

```
cyc contextNo contextsK  surprise otherCoun   silence strangene  ->span
  1     1.000     0.000     0.000     1.000     0.000     0.000   4.000
  3     0.000     2.000     0.000     2.000     0.000     0.000   2.000
  6     1.000     4.000     0.000     4.000     1.000     0.000   1.000
 10     1.000     8.000     0.000     5.000     0.000     0.000   0.800
 16     0.000     9.000     0.000     5.000     0.000     0.000   0.800
 48     0.000     9.000     0.000     5.000     0.000     0.000   0.800
```

`contextNovelty` **does** vary, for about fifteen cycles. Then it is 0 for ever,
and `contextsKnown` freezes at **9**.

**That is the finding, and it is about the model rather than the field.** The
landing-patch context collapses a 64×64 world into **nine** distinct situations.
Five affordances across nine situations is a space the agent exhausts in fifteen
cycles — after which nothing in the field moves again, there is nothing left to
be curious about, and no want exists to take over. The environment stops being
open because the model stopped being able to tell it apart.

So the field being static was never only the field's problem. `strangeness` is
structurally 0 here because the host always knows which affordance it used, and
`contextNovelty` saturates because the model's situation space is nine states
wide. A richer reading of the situation would give the loop an environment it
does not finish mapping in fifteen moves.

### Where the missing context is

`strangeness` measures **entity** novelty, and this host has none. The novelty
that exists here is **context** novelty — is this landing-situation one the agent
has met before? The model knows exactly that: it is whether `(entity, context)`
is already a key in its table. That is an interpretation of context, which is
what the field is missing, and it is one the model is already computing and
throwing away.

It cannot get in yet. The model lives behind T5's `PredictRule`, and a rule is
not a layer: it receives `(entity, window, observed)` and has no `contribute`.
Letting the model's reading of its own situation reach the field means widening
that seam, which is a skeleton decision and is not taken here.

## Nothing reads the goal

Traced through the code, the chain §9 describes — mismatch → memory → learning →
change — is complete, and its last link is one rule wide:

| what | which component |
|---|---|
| interacts with the region | `Arc3Source.deliver` → `env.step` |
| perceives | `read_frame` → `diff` → the effect signature |
| **knows where anything is** | **nothing** — only "what is on the square I would land on" |
| collects mismatch | T5 (value-mismatch), T7 (absence) → driver → `[event]` |
| learns | the model's table, T5's windows, T6's counters, T7's expectations |
| changes behaviour | `LeastResolved`: take the least-resolved afforded action |
| **pursues a goal** | **nothing** |

`levels_delta` is the score channel — the only thing RHAE counts, the only
definition of winning. Grepped: it appears exactly twice, both in
`observe.py`, writing it into the payload and reading it back out when
rebuilding an `Effect`. **No component uses it to decide anything.** The
`stateTo` channel has one reader, `respond.py`, and only to RESET after a
terminal frame — never to seek a WIN.

So the agent cannot pursue the goal, because nothing reads the goal. It carries
the goal inward and drops it.

That accounts fully for zero levels completed. It is not a tuning problem. Two
limits declared earlier — "the loop is handed no coordinates" and "`vc33`
learns nothing from context" — were written up as limits of the *context*
representation. They are the same single hole, and the hole is that **nothing in
this repository represents a want**.

Where such a thing could live is not obvious and is not being guessed at:
§6 link 4 assigns direction and value, but INV-8 forbids the appraisal step from
drawing its criteria from the state the agent is editing, and `levels_completed`
is part of that state. Naming a goal is therefore a skeleton decision, not an
implementation detail.

## How far this travels beyond ARC-AGI-3

Layered, and the layers were checked rather than assumed. `grep` over `src/dil/`
finds no ARC-AGI-3 knowledge in code at all — only the word "frame" inside
"reference frame", and two comments.

| ring | what it assumes | portability |
|---|---|---|
| `dil/` | nothing about any world | travels intact |
| `frame.py` | 64×64, values 0–15 | shape is general, constants are not |
| `effect.py` | a grid of discrete values | any grid world; `transitions` survive off-grid |
| `model.py` | something moves rigidly on a grid | **the most specific piece** |
| `respond.py`, `host.py` | action ids plus coordinates | general in shape |

**`vc33` is the empirical test of this**, not a hypothetical: there the model
found no rigid mover, context was empty in all 157 cycles, and it degraded
gracefully to majority-over-effects — 41% → 69%. It keeps working and loses its
best feature.

Porting to another world means re-declaring exactly the seams §12 already
enumerates: T3's transducer, T4's resolver, T5's predict rule, the boundary gate
and the effect signature. The DECIDE@IMPL list *is* the portability surface.

## Two bugs in the starter kit on Windows

Both are upstream's, both block a Windows user at the first step, and both are
worth a pull request to `arcprize/ARC-AGI-3-Kaggle-Starter`:

1. `scripts/slim_framework.py` calls `INIT.write_text(SLIM)` with no encoding, so
   on Windows it writes cp1252. The text contains an em dash, which lands as byte
   0x97, and Python then refuses to read the generated `.py` as UTF-8. Fixed
   locally with `encoding="utf-8"`.
2. `scripts/play_local.py` prints `→` to a cp1252 stdout and raises
   `UnicodeEncodeError`. Worked around with `PYTHONIOENCODING=utf-8` rather than
   by editing their file.

## What the Paper Track forum gives

- **A 1,500-word limit is referred to as a known constraint** by two competitors
  ("does the bibliography fit within the 1500-word limit?", "does the 1,500-word
  limit also apply if you upload a PDF through the Public Project Link instead of
  writing it in the Kaggle Writeup"). No host ever replied to either. If it holds,
  it reshapes the paper completely: 1,500 words against a 55 KB specification.
  **Confirm this on the competition's own Overview page before writing anything.**
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

If the 4.5 is a mean of the six criteria — the natural reading, and the one a
search summary asserts, though the page itself leaves the aggregation unstated
and one cited source was a third-party blog — then the pool needs better than
27 of 30 points. An Accuracy of 0 costs 5 and makes it unreachable; an Accuracy
of 2 requires a perfect 5 on all five remaining criteria.

**So aim at the Top Paper prizes.** They are ranked, not gated, against a field
of 198. Accuracy then contributes to a ranking rather than standing as a gate
that forecloses everything, and the paper's quality is what decides the outcome.
Treat the pool as upside, never as the plan.

## Direction C: can an open model write the world model? First measurements, 2026-09-24

Settled with Plone: the mind's thinking can be done by an open model that writes
an **executable world model** — a program `predict(grid, action) -> grid` — which
DIL then tests against the region, as data in the store, expectation → mismatch →
scar → rewrite. The model thinks; it does not choose. Before any architecture,
the question measured is whether a model that can run offline writes such a
program at all. Probe: `scripts/wm_probe.py`, on the 159 recorded `ls20`
transitions (80 train, 79 held out), scored by **exact** match of the whole 64×64
grid. Baseline "nothing changes": 0/159 — every step changes at least two cells.

| where | model | mode | runs | best program, train / held out |
|---|---|---|---|---|
| this machine, CPU + GTX 1050 Ti | Qwen3.6-35B-A3B, IQ4_XS | no thinking | 1st | **64/80 / 60/79 (76%)** |
| this machine | same | no thinking | 2nd | 1/80 / 0/79 |
| Kaggle RTX Pro 6000, vLLM | Qwen3.6-27B-FP8 | no thinking | 2 | 0/80 / 0/79 both |
| Kaggle RTX Pro 6000, vLLM | Qwen3.6-27B-FP8 | thinking | 2 | no program: every round hit the 16,384-token cap inside its reasoning |

What the numbers say, and do not:

- **The capability exists and is not reliable.** One run wrote a program exact on
  76% of transitions it had never seen; its 35 misses were almost all movement,
  the step counter being right. The next run with the same model and data wrote
  one right once in 80. Two runs cannot give a rate.
- **The 27B dense model did worse here than the 35B-A3B MoE**: six programs, all
  loading and running, none exact once. Four runs are not enough to rank models
  either.
- **Thinking needs a far larger budget.** 26–44k characters of reasoning per round
  never reached code within 16,384 tokens.
- The first local run's two failed rounds were the probe's fault — a 4,096-token
  cap, and each revision seeing the whole transcript. Fixed before the next runs:
  the probe keeps the best program and shows only it and its failures.

The pipeline itself is proven: the notebook checked all 80 model files (30.9 GB)
against Hugging Face's published hashes, installed vLLM 0.19 offline, served
65k-token contexts with a 199k-token KV cache (≈11 full-length requests at
once), and generated about 33 tokens/s per stream with four streams. The run used
0.48 h of the 30 h weekly GPU quota; the RTX machine was not charged at more than
wall-clock time. Locally the same probe costs 25–45 minutes a run.

### Run 2 on Kaggle: the 35B-A3B MoE, FP8, 2026-09-24

Same probe, same data, `Qwen3.6-35B-A3B-FP8` (the official release, mirrored,
all 56 files checked against Hugging Face before serving — the check asserts, and
the server that runs after it did start). Eight runs at once, four without
thinking and four with, three rounds each, up to 45,000 output tokens a round.

| run | best program, train / held out | note |
|---|---|---|
| no thinking 0 | 7/80 / 3/79 | |
| no thinking 1 | **78/80 / 75/79 (95%)** | round 0 already 63/80 / 58/79 |
| no thinking 2 | **78/80 / 75/79 (95%)** | round 0 63/80 / 58/79; round 1 fell to 0, round 2 recovered |
| no thinking 3 | 0/80 after round 0 | then refused: 20,537 prompt + 45,000 output = 65,537 tokens, one over the 65,536 context |
| thinking 0 | 12/80 / 0/79 | 33–40k chars of reasoning a round |
| thinking 1 | 2/80 / 0/79 | |
| thinking 2 | 0/80 / 0/79 | one round hit the 45,000 cap |
| thinking 3 | 0/80 / 0/79 | one round hit the cap after 100,141 chars of reasoning |

What this adds to run 1:

- **Two independent runs reached the same 95% held out with different code.**
  Both programs are rules, not lookup tables, and state the same two: the 5×5
  object (two rows of 12 over three of 9) moves five cells in the action's
  direction only if every target cell is 3, and the bar on rows 61–62 advances one
  column per action. Why the last 4 held-out transitions miss has not been looked
  at.
- **Still not reliable**: of the three no-thinking runs that finished, two reached
  95% and one 4%. Across both machines, 3 of 6 no-thinking runs of this model
  wrote a program above 75% held out. That is a count, not a rate.
- **Thinking made it worse, not slower-but-better**, with the budget nearly
  three times run 1's: 0–2 of 79 held out in every thinking run. The reasoning
  produced code, and the code was wrong.
- The refused run was the builder's fault: the context was fixed at 65,536 while
  the output cap was raised. It now sizes the context as
  `max(65536, max tokens + 24,576)` unless told otherwise.

Cost: 0.33 h of GPU quota (0.49 h used before, 0.82 h after, of 30 h a week).
Downloading the outputs was cut off by the local 600 s timeout; every probe's log
is present, but the notebook's own log was not downloaded.

### What the thinking runs got wrong, read off their programs

The reasoning itself cannot be read: the probe kept only its length, not its
text, so whether the model tried to run the grid by hand in its reasoning is
unknown. Fixed for later runs — the log now keeps the reasoning whole, and the
temperature used. What can be read is every program, and
`scripts/compare_programs.py` re-scores each one and says where its wrong cells
are:

| log | round | train | held | wrong cells per miss | misses only in the bar |
|---|---|---|---|---|---|
| thinking 0 | 1 | 12 | 0 | 49.2 | 7 |
| thinking 3 | 1 | 0 | 0 | **17.1** | **64 of 80** |
| no thinking 1 | 0 | 63 | 58 | 52.4 | 1 |
| no thinking 1 | 2 | 78 | 75 | 70.0 | 1 |

- **Most thinking programs fitted the examples literally.** Coordinates copied from
  them — a start at (40, 34), the bar at column `13 + step`, fixed tracks at
  columns 34–38 and rows 45–49, clamps at rows 20–40; one kept its own position in
  state across calls instead of reading it from the grid; three described the
  10×5 region that changes (old place plus new) as a "wave" to paint, not as an
  object that moves. None checked whether the target cells were free — the rule
  the 95% programs have.
- **One came within a line of the no-thinking result.** Thinking 3, round 1, found
  the 5×5 object by its pattern and moved it five cells; 64 of its 80 train misses
  are only in the bar, because it took the first column where rows 61 and 62 are
  equal and not 3 to be the marker — column 0, value 4, not the 11s. Its other 16
  misses are as many as the no-thinking round-0 programs have without the
  blocked-move check. The round that should have fixed it hit the 45,000 cap
  after 100,141 characters of reasoning and wrote no code.
- **The comparison was not run as Qwen recommends, for either mode.** Every run
  sent temperature 0.2 and nothing else, and the server was started with
  `--generation-config vllm`, which by vLLM's engine-argument documentation loads
  no generation config and uses vLLM's defaults instead of the model's. The
  Qwen3.6-35B-A3B-FP8 model card recommends, for thinking on precise coding tasks,
  `temperature=0.6, top_p=0.95, top_k=20, presence_penalty=0.0`; for non-thinking,
  `temperature=0.7, top_p=0.80, top_k=20, presence_penalty=1.5`; and an output
  length of 32,768 tokens for most queries, 81,920 for competition-level
  problems. "Thinking made it worse" holds for these settings only.

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

### Direction C, placed in the loop (Plone, same day)

The world-model probe (`scripts/wm_probe.py`) ran **entirely outside dil-arc3**:
it imports nothing from `src/`, its transitions came from a scripted agent in
`dump_frames.py`, and its score-and-rewrite loop was the probe's own. It recorded
no mismatch, no ResistEvent, no scar and no `[event]` line, so it is evidence
only that an open model *can* write such a program — not evidence about this
agent, and nothing the paper's claim can rest on. It also poured 80 transitions
into one prompt, the load INV-5 names. Its measurements stay as a feasibility
result; the next ones run inside the loop.

- **A program the model writes is `running` data** — the character's own, from
  running — not `prior`.
- **There is no trigger for rewriting it, and no constant to declare.** The model
  sits at the **mind**: it is the thinking. When its expectation meets the region
  and does not hold, the loop registers the mismatch, the ResistEvent and, where
  it holds, the scar; adjusting is what thinking does with that. If it does not
  adjust, the mismatch recurs. Rewriting is the consequence of mismatch, not a
  step scheduled by the host.
- **The mind reads by asking; nothing is poured into it.** It has the right to
  read anything in the store, and it chooses what: meeting a problem, it goes to
  memory for what bears on that problem. Only T3 could query the store, and only
  about what had just arrived, so this was a gap — fixed in dil-core first
  (`1e2d826`) and ported: T5 hands its rule `ask(cue)`, which emits a store query
  and nothing else, traced to T5 with register ↔, answered at T1 next cycle. The
  settled line narrows from "the mind does not emit" to **"the mind does not
  act"**: the one thing it sends out is a question to its own memory, and that
  question is in `[event]`.
- **What the region returns is data, and the scar is on it** (Plone, same day;
  cost accepted). dil-core kept no return as data: its one datum per cycle was
  the driver's cycle datum (payload a signal count, `domain: cycle`), which went
  to `scar` on any collision, so the tag sat on a counter and the mismatch did
  not say what it was a mismatch with (§3: "A `scar` has collided with resistance
  and held"). First built here as a host option, then, at Plone's direction,
  fixed in dil-core as a gap of the mechanism (`276f30a`) and ported back: each
  return enters `[data]` through the tagging-gate as `signal-<cycle>-<i>`, runs
  as `running`, leaves a line at every layer it exits, its tags (never its
  content) go into the cycle's activity record under `admitted`, and when the
  expectation about it fails **that datum** moves `running → scar`, the scar
  record embedding and naming it (`datumId`). The cycle datum still stands for
  the cycle, and for an absence, where nothing returned. The host declares the
  tags (`AdmitPolicy`; the reference `admit_return` tags `domain: region`,
  `source`, `format`); `arc3.observe.admit` uses this host's vocabulary —
  `domain: observation`, `kind`, `source`, and the channel's own `object` and
  `sense` values. The checker covers the returns' paths (C3) and gate entry
  (C6), and reads the flow mode from the cycle seal, since it is the cycle's.
- **Memory is what the store held before the cycle that asks** (Plone, option
  (a)). T3 asks after the cycle's returns are admitted, so at first 19 of cycle
  0's own arrivals came back as "recalled" — the character recalling what it is
  seeing. A query is now answered without the data admitted in the cycle that
  raised it. In dil-core too (`276f30a`), with a mutation check.

  Live, `ls20`, 60 cycles (`scripts/run_prior.py ls20 60 [admit]`): moves,
  positions and scars identical to a run before any of this; 1,142 returns kept
  (1,122 `running`, 20 `scar`); 20 of 20 scar records name their datum; 0
  returns recalled as their own memory; the 6 priors still recalled at cycle 1;
  12,364 `[event]` records; conformance unchanged (C1, C3, C5, C6, C7 pass, C4
  partial, C2 unverifiable). `run_prior.py` had counted absences as scars
  sourced `region`, which is the status entity's name too; it now counts them by
  `mismatch_kind` (0 here) — earlier absence counts from that script need
  re-checking.

### Protocol v0.3.3: `nascent`, entries by origin, `write`, revision (Plone, same day)

Discussed and settled with Plone, then written into the law in dil-core
(`f8230de`, protocol v0.3.3 and specification v7, copied into `spec/`), migrated
there (`44309b7`) and ported here:

- **`prior` is what its definition says**: host data existing before the loop
  ran. Region returns and the cycle datum are not that; they pass the
  tagging-gate at `running`, told apart by `domain`, their entry being their
  tag set in the cycle's record. The first port had admitted them as `prior`
  and moved them at once — a mislabel of this session's own making.
- **`nascent`** — the name chosen to keep clear of "self" and of T2's
  SELF_WRITTEN — is the second one-way entry: a datum the agent writes anew,
  bearing the cycle-mark of the cycle that wrote it. It arrives at T1 the next
  cycle, is SELF_WRITTEN at T2, runs every layer, and moves `nascent → running`.
- **A revision is not an entry**: the content of a held datum changes, its
  provenance does not, T2 reads it SELF_WRITTEN the next cycle, and `[event]`
  gets a bare `revision` line with no content. The content is read from the
  commit snapshot. This is what a rewritten world-model program is.
- The predict rule has **`write`** (anew, or with `datum_id` to revise), and a
  **cue may carry `provenance`**, so the mind can ask what collided.
- DEVIATION from dil-core, declared (Plone: too costly for a full agent, right
  for this one): **dil-arc3 also commits at the close of every cycle in which
  the agent wrote a datum**, so every version of the program is in a snapshot
  tied by its marker to its place in `[event]` (`COMMIT_CADENCE`; tested).
  `CycleResult.written` carries the count for the daemon.
- A bug the commit test caught on the way: a written datum's arrival carried its
  fixed tags as a dataclass, which the snapshot could not store; it now takes
  the store-return form.
- **A pre-existing gap, fixed the same day (`f1b4491`)**: the Python daemon's
  snapshot payload kept only the driver's `cycle` and `lastEmission`, not
  pending returns, `recalled`, `last_lateral` or `pending_writes`, so a recovery
  from a commit dropped whatever was on its way to T1. It now keeps the whole
  driver state, as dil-core does; snapshots in the old form still restore. A
  recovery test failed before the change and passes after.

Live, `ls20`, 60 cycles after the port: moves, positions, scars and recall
identical to before; `[event]` 11,162 records, 1,202 fewer than before — exactly
the 1,142 region returns' and 60 cycle datums' `prior → running` lines v0.3.3
drops; conformance unchanged. 267 tests.

### When the cycle datum scars, and which datum a recalled scar is (Plone, same day)

The deferred item from dil-core's README, settled with Plone and fixed there
first (`6c74f0c`, `dc7a9a7`), then ported:

- **The cycle datum goes to `scar` only when what it carries collides**: an
  outcome it cast (`projected → scar`), or a collision with no return of its own
  to hold the scar — an absence, a return the host kept out, a store arrival —
  for which it stands. A cast that did not collide returns to use
  (`projected → running`) even when another return collided; with no cast it
  stays `running`. ResistEvents and scar records are unchanged.
- **A recalled scar is the datum its record names**: since the return holds the
  scar, recollection now reports that datum (`cycle-N` only for an absence), and
  the driver moves it `scar → running` once, while it is a scar, with `[data]`
  following the line. Before, it recorded the move for `cycle-N` on every
  recall and never touched `[data]` — a gap opened when the scar moved onto the
  return.
- Left open, in both repositories: a store arrival that mismatches (a revised
  datum arriving against persistence's "nothing changed") is not tied to its
  own datum; the cycle datum stands for it. This mind returns store arrivals as
  they are, so it does not arise here.

Live, `ls20`, 60 cycles: behaviour identical; 12 cycles had a collision and in
none did the cycle datum go to `scar` — every one of its 59 casts ended
`projected → running`. The three situations it casts (`H_COUNT = 3`, the most
confident) never collided; every collision was on another thing's return, which
holds the scar (20 of 20 records name it). 275 tests.

### Every record takes the clock when it happens (Plone, same day)

Found by reading back the first live run with the model in the loop: dil-core
read the clock once per cycle and stamped every record and datum in it with
that reading. Seventeen minutes of thinking inside T5 showed nowhere in
`[event]` — every line of the cycle bore its start — and the program the model
wrote bore that time too, though written at the end. §9 asks for "each
transition as it occurs" and a timestamp "when the datum is first stamped".
Fixed in dil-core (`9073ddf`) and ported: every record takes the clock when it
is appended, region returns and written data when they enter, the cycle datum
keeps its cycle's start, and the seal adds `closedAt`. Tests with a ticking
clock, two mutations caught in dil-core. 283 tests.

Still not in the log, by the law as it stands: a thought the mind does not keep
changes no datum, so it leaves no line beyond the query it asked with; the time
it took shows only as the gap between T4 and T5.

### First live run with the model in the loop, this machine (2026-09-24)

`scripts/run_world_model.py ls20 10`, Qwen3.6-35B-A3B IQ4_XS on llama.cpp
(CPU + GTX 1050 Ti), no thinking, temperature 0.2. Store:
`scripts/data/wm-ls20-cobmhzp2/` (git-ignored). Code as of `949883e` — the run
started before the per-record clock, so its `[event]` still stamps each cycle
with one time.

- **The loop worked end to end, and the log shows it.** The frame's expectation
  failed in 9 of 10 cycles (cycle 0 is the RESET, which changes nothing); each
  failed frame is the datum that went to `scar`, named by its record. The mind
  asked the store 9 times, `{"kind": "frame", "provenance": "scar"}`, from T5.
  The first program entered at `nascent` (`written-1-0`) and moved to `running`
  the next cycle; 2 commits; 2,319 `[event]` records; conformance as before
  (C1, C3, C5, C6, C7 pass, C4 partial, C2 unverifiable).
- **The thinking did not find the game.** 9 thoughts; the first program was kept
  because there was none, though it explained 0 of the 1 transition it had; the
  8 after it explained 0 of 1–7 and were not kept, so no revision. 5,971 s for
  10 cycles, almost all of it the model (262–1,057 s a thought).
- **The scoring is not the cause**: the program that reached 95% on Kaggle
  scores 153/159 on the recorded `ls20` transitions through the mind's own
  `score()`.
- **Why so little evidence**: memory answers what the store held before the
  cycle that asks, the answer arrives the next cycle, and it reaches T5 after the
  frame has been predicted; so a transition seen at cycle k is evidence from
  about k+3. After 10 cycles the model had seen at most 7, against the 24 the
  probe showed at once. The local model is also the weaker one: the same model
  and quantisation wrote 1/80 in the probe's second local run.
- Open, for Plone: shortening that lag touches the driver's signal order or has
  the mind hold what it has just seen until memory can answer — both near the
  line "memory is the store".

### What a written datum was built from, and the mind's short-term perception (Plone, same day)

Plone rejected reordering the driver so memory answers before the region
returns ("why would the mind read memory before anything has come back?") and
chose (b) with the trace closed:

- **Short-term perception is T5's window**, already in the law (§6.1
  `Expectation.built_from: history_window`; the baseline window is
  `BASELINE_WINDOW = 16`). The world-model mind had ignored the `window` its rule
  receives; it now thinks from what the store answered, what the window holds of
  the frame, and the transition in front of it. No new mechanism, no new constant.
- **A written datum records what it was built from** — protocol v0.3.4, written
  with Plone and fixed in dil-core first (`c2c0cd2`), ported here. Every write
  carries `built_from` (units or ids; `()` for nothing held), the driver maps
  units to their data across cycles (a weakref-keyed map; `InfoUnit` now has a
  weakref slot) and records ids only in the cycle's `written` entries; an
  unknown id, a unit from no datum, or a write that says nothing is refused; the
  checker fails a written datum naming data with no recorded entry. The mind's
  `built_from` is exactly the evidence the model was shown. With it a reader
  follows data → program version → expectations → scars → revision.

287 tests.

## Still unverified

- **Whether the 1,500-word limit also binds a PDF** submitted through the Public
  Project Link. The Overview states the limit for the Writeup and does not say
  either way for the PDF.
- The two official sources disagree on the Milestone 1 split: arcprize.org says
  $25K/$10K/$2.5K, Kaggle says $25,000/$7,500/$5,000. Both total $37,500. Which
  is authoritative is unknown; it does not affect this plan, but it is a reason
  to read both sites rather than trust one.
