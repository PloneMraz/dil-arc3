# dil-arc3

An [ARC-AGI-3](https://arcprize.org/arc-agi/3/) agent whose whole operation is
the DIL protocol.

Not a solver with a protocol wrapped around it. The protocol *is* the mechanism:
there is no decision procedure underneath that DIL decorates, and no step where
the agent leaves the loop to think.

## Status, plainly

It runs. It learns what the things in a game do. **It completes no levels.**

It explores: over 120 cycles of `ls20` it spreads its moves across all four
directions and reaches 19 distinct positions, walking in lines toward whatever it
is still learning about. What it lacks is a reason to go anywhere in particular.

**Want can only avoid.** How the region answers each action is read, accrued, and
carried to where behaviour is decided. But the only good answer the region gives
is a completed level, and none has ever happened, so the want that exists has
only ever learned what to steer away from. That is measured, not guessed, and it
is the open problem.

**What it is told.** It arrives with no history — nothing like what a creature
carries in its genes or learned from others — so the least it is given is a
directive: the one sentence the competition gives every model on its official
leaderboard, "You are playing a game. Your goal is to win.", with the published
rules of the place. Nothing about any particular game, and nothing about how to
win one. It enters as host data stamped `prior` — not the character's own, not
yet tested — and stays in the store until the character recalls it: the first
report of the region's status brings the directive to mind, and the first thing
seen brings what it was told about things and about seeing. The good-or-bad reading of the
region's answers used to be written into the code; it is now read from that
recalled directive, and with no directive every answer is neutral.

An earlier version also stuck: it acted on whatever it understood least, and took
one action 103 times in 120 because that action's outcome depended on something
the mind could not see. That is fixed — see below — and the fix is recorded
rather than hidden.

Everything below is measured on live games, not asserted. Where a claim has no
measurement behind it, it says so.

## The four roles

Settled deliberately, because getting them the wrong way round was the first
real mistake this project made.

| role | what it is | in this repo |
|---|---|---|
| **DIL** | the operating mechanism of the whole — how information moves | `src/dil/` |
| **host** | the body: receives signals, carries them, executes what was committed. **Concludes nothing.** | `src/arc3/frame.py`, `action.py`, `host.py`, `observe.py` |
| **store** | memory: what the character recalls on a cue, including what it was told before it lived (`prior`) | `src/dil/store/`, `src/arc3/prior.py` |
| **mind** | the thinking organ: finds the things in a signal, follows them across frames, reads what became of them, says what they will do. **Chooses nothing.** | `src/arc3/perceive.py`, `seeing.py`, `interpret.py`, `mind.py` |
| **self** | what occurs while the loop runs through them. **It is what acts.** | not a file |

The line that matters: **the mind does not emit.** It supplies an expectation and
nothing else — it never sees which actions are available and never reaches the
emission. An earlier build had these inverted, with the body handing the loop a
finished interpretation while the mind reached past the loop into the raw grid to
pick what to look at. Both are the other way round now.

## What the mind is, and is not

It is **not a downloaded network**, for three reasons each sufficient alone:

- the scored games are unseen, and their mechanics are the thing to be
  discovered, so weights trained on other games predict the wrong world;
- Kaggle's evaluation session has no network;
- INV-5 rules out the alternative in so many words — "refeeding the whole game
  history into a context window each step is a load, not an accrual".

What is left, and what the protocol actually asks for, is a predictor that
**accrues within the episode**. It starts each game knowing nothing about it.
There are no weights, no gradients, and no third-party dependencies at all —
`dependencies = []` is a requirement, not a boast, because an accelerated Kaggle
session has no network to install from.

It works in four steps, all of them cheap:

1. **Perceive** — pieces are connected runs of one value, four-connected,
   excluding whatever the grid is mostly made of. The background is *read*, not
   assumed, so a world on a non-zero background still parses.
2. **See individuals** — each piece is followed from frame to frame, and pieces
   that keep moving together, by the same displacement, are learned to be one
   thing. Nothing is configured: a two-colour object is recognised as one object
   because its parts always move as one.
3. **Read the situation** — for each thing, what it faces first on every side, at
   any distance: another thing, or the edge of the grid. No distance constant, and
   nothing about what any action does.
4. **Predict** — associate (thing, action, situation) with what the thing then
   did, and answer by majority. Report upward, per action, how fast that is being
   learned and how the region has answered it.

### Identity was chosen by measurement

A thing has to stay the same thing while it persists, or expectation can never
match. Four readings were scored against 60 real frames per game by *churn* —
how many identities exist overall against how many are present in one frame:

| identity | churn | prediction `ls20` / `vc33` |
|---|---|---|
| value + bounding box | 6.2× | — |
| value + cell count | 6.2× | — |
| value — a kind of stuff | 1.0× | 93% / 85% |
| **tracked piece, grouped by common fate, read with what lies ahead** | **1.7×** | **99% / 93%** |

Stuff held identity perfectly and hid the thing that mattered. In `ls20`, value 9
is five separate pieces, one of which moves; every reading of "the 9s" was
swamped by the four that never move. Tracking individuals costs some churn —
partly because a thing is renamed when its parts are first grouped — and buys
this: the moving object's blocked-or-not outcome, predicted **100%**.

The grouping step is there because of a second measurement. Before it, the
object's front part was predicted 100% and its back part only 67%: the object is
drawn in two colours, segmentation splits it, and a ray cast from the back part
stopped at its own front part and never saw the wall.

## Measurements

Prediction accuracy, over the same 316 real transitions from two games.

| | `ls20` | `vc33` |
|---|---|---|
| actions as entities, one hand-written feature | 94% | 69% |
| kinds of stuff as entities, context = action | 93% | 85% |
| **tracked things, context = action + what lies ahead** | **99%** | **93%** |

The first row is the architecture this replaced, which made an *action* the unit
of experience. Its one strong number came from a feature written by hand for
this game; the feature is gone, and nothing is given up for it.

Live runs, 120 cycles each:

| | `ls20` | `vc33` |
|---|---|---|
| things perceived per cycle | 19 | 12 |
| Other-to-Other interactions (`SocialEdge`) | 28 | 20 |
| scars recorded | 54 | 101 |
| of which absences | 4 | 4 |
| moves committed | `4:38 1:28 3:28 2:26` | ACTION6 only, swept |
| distinct positions the moving object reached | 19 | — |
| **levels completed** | **0** | **0** |

Two earlier versions of this table are gone, and why is worth keeping. One came
from runs where the agent pressed a single key every cycle — a regression in how
it chose moves. The next came from an agent that acted on whatever it understood
least and took one action 103 times in 120. Their perception figures were sound;
their behaviour figures described an agent stuck, and they were replaced rather
than footnoted.

### How curiosity chooses

It follows **learning progress**, not ignorance. Going for whatever is least
understood sticks to irreducible noise — the "noisy TV" failure of
curiosity-driven exploration — because noise never becomes understood.
Following how fast understanding is *changing* instead, noise that cannot be
learned shows no progress, and curiosity leaves it on its own. Measured, one
action's share of moves fell from 103/120 to 38/120.

## Findings

Porting DIL from [dil-core](https://github.com/PloneMraz/dil-core) and running it
against a live environment turned up more about the protocol than about
ARC-AGI-3. These are the substance of the work rather than a side effect of it,
and they fall into three kinds — which is worth keeping straight.

### Gaps between the protocol and its reference implementation

Each was verified by measurement, then fixed in `dil-core` first and ported back.
All five have the same shape: a channel present in the topology that nothing
drew on.

1. **The store was write-only.** §9 says "the self accrues from scars" and defines
   three provenance edges by which a scar returns. On a real run all three fired
   **zero** times: the loop called `data.put` once per cycle and never read
   anything back, so §10's resistance-retrieval channel was satisfied nowhere.
2. **The modulatory field was inert downward.** INV-7 has it reaching every layer
   as background — "same data plus a different field yields different meaning".
   No layer read it. Two of the eight did not even declare the parameter, and its
   only consumer was a single gain at the appraisal step.
3. **And inert upward.** "Every layer contributes to it as one competing
   parameter; contributions blend, never last-write-wins." No layer *could*
   contribute; the only caller was the driver, once per cycle, with one
   hard-coded key. With one contributor, blending is last-write.
4. **The top layer was a sink.** Nothing read T8's output: its relative values
   and its Other-to-Other interactions were produced every cycle and dropped.
   INV-1 forbids dead branches, and §6.2 says in as many words that "T8 closes
   back into the loop, not into a sink". The meaning-channel cannot carry T8's
   output back down, so it now returns through the field.
5. **Admitted, and never asked for.** Host data enters through the tagging-gate
   stamped `prior`, and §9 has it move to `running` "once it has run". Nothing
   ever asked for it, so it never ran. §6.4 already names the mechanism — "T3
   emits a *query*: it opens or calls a channel to ingest actively" — and the
   index is the open-tag layer §9 already requires to be consistent by key. T3
   now asks the store with the description of what just arrived; the answer
   comes back through T1 and runs every layer. Recalled on a cue, never poured
   in.

### A property of the protocol's own design

6. **The experience store is a biased sample, by construction.** §9 admits only
   registered mismatches, so what it holds are the region's *surprises*. Asked to
   predict, it lost 62 of 66 contests against the model — not because it is
   wrong, but because an exception loses to a distribution. No verdict is
   involved anywhere: §9 is explicit that a scar "carries no claim of
   correctness". This is not a defect to fix; it is what an experience store of
   collisions *is*, and it means the store is right for driving change and wrong
   for answering what happens next.

### A gap in this agent

7. **Want has nothing to seek**, as the status section says. The directive now
   tells it what counts as reaching the goal, but not how to get there, and no
   level has ever been completed to learn from. Local to this repository, not
   upstream's.

## Running it

Requires Python 3.12+. No dependencies.

```sh
# tests
uv run --with pytest python -m pytest tests/ -q
```

Playing a game needs the ARC-AGI-3 environment, which is not vendored here:
point the host at an environment exposing `reset()` and `step(action, data)` and
hand it the engine's action class.

```python
from arc3 import transducers
from arc3.host import create_source, declaration
from arc3.mind import create_mind, predict_rule
from arc3.respond import least_resolved
```

`src/arc3/host.py` shows the whole wiring; `src/arc3/decisions.py` records what
this host declares for the protocol's deferred constants.

## Layout

```
src/dil/          the protocol — invariants, the eight-layer loop, the store,
                  the runtime, the conformance checker. Knows nothing about
                  ARC-AGI-3.
src/arc3/         the body and the mind, kept apart.
CLAUDE.md         the decision record: every declared choice, every measurement,
                  every limit, and the corrections made along the way.
```

`CLAUDE.md` is the honest version of this README. It is longer, it is written for
whoever has to maintain this, and it keeps the mistakes in.

## Licence

[MIT-0](LICENSE). No attribution required.
