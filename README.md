# dil-arc3

An [ARC-AGI-3](https://arcprize.org/arc-agi/3/) agent whose whole operation is
the DIL protocol.

Not a solver with a protocol wrapped around it. The protocol *is* the mechanism:
there is no decision procedure underneath that DIL decorates, and no step where
the agent leaves the loop to think.

## Status, plainly

It runs. It learns what the things in a game do. **It completes no levels.**

That is not a tuning problem, and the reason is recorded rather than glossed:
nothing in this repository reads the goal. `levels_completed` — the only thing
the scorer counts — travels inward with every observation and no component uses
it to decide anything. The agent carries the goal and drops it. What it has
instead is curiosity: it acts on whatever it is least certain about.

Everything below is measured on live games, not asserted. Where a claim has no
measurement behind it, it says so.

## The four roles

Settled deliberately, because getting them the wrong way round was the first
real mistake this project made.

| role | what it is | in this repo |
|---|---|---|
| **DIL** | the operating mechanism of the whole — how information moves | `src/dil/` |
| **host** | the body: receives signals, carries them, executes what was committed. **Concludes nothing.** | `src/arc3/frame.py`, `action.py`, `host.py`, `observe.py` |
| **mind** | the thinking organ: finds the things in a signal, reads what became of them, says what they will do. **Chooses nothing.** | `src/arc3/perceive.py`, `interpret.py`, `mind.py` |
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

It works in three steps, all of them cheap:

1. **Perceive** — things are connected runs of one value, four-connected,
   excluding whatever the grid is mostly made of. The background is *read*, not
   assumed, so a world on a non-zero background still parses.
2. **Interpret** — what became of each thing between two frames: did it move, by
   how much, did it grow, split, appear, vanish. Never *where* it is, because
   position does not repeat and what a thing did does.
3. **Predict** — associate (thing, action) with what the thing then did, and
   answer by majority.

### Identity was chosen by measurement

A thing has to stay the same thing while it persists, or expectation can never
match. Four readings were scored against 60 real frames per game by *churn* —
how many identities exist overall against how many are present in one frame:

| identity | overall | per frame | churn |
|---|---|---|---|
| value + bounding box | 101 | 16.3 | 6.2× |
| value + cell count | 101 | 16.3 | 6.2× |
| **value** | **8** | **8.0** | **1.0×** |
| value + channel | 16 | 8.0 | 2.0× |

Value alone holds at 1.0× in both games. Keying on extent or cell count makes a
thing that changes shape become a *different thing* six to ten times over.

**Declared limit:** this is a kind of *stuff*, not an individual. Every cell of
value 9 is one Other however many separate pieces they form. Telling individuals
apart needs tracking across frames, and is not done.

## Measurements

Prediction accuracy, over the same 316 real transitions from two games.

What the mind does, against the cheaper rule it replaces:

| | `ls20` | `vc33` |
|---|---|---|
| predict whatever happened last time | 92% | 80% |
| **majority over accrued evidence** (what it does) | **93%** | **85%** |

And against the architecture this replaced — which made an *action* the unit of
experience and read the situation through a hand-written feature:

| | `ls20` | `vc33` |
|---|---|---|
| actions as entities, hand-coded feature | 94% | 69% |
| **things as entities, no hand-coded feature** | **93%** | **85%** |

One point given up where the hand-written feature was doing the work, sixteen
gained where it was blind, and the feature is gone.

Live runs, 60 cycles each:

| | `ls20` | `vc33` |
|---|---|---|
| Others perceived per cycle | 9 | 7 |
| distinct sources of resistance | 8 | 3 |
| scars recorded | 44 | 61 |
| of which absences | 1 | 2 |
| **levels completed** | **0** | **0** |

## Findings

Porting DIL from [dil-core](https://github.com/PloneMraz/dil-core) and running it
against a live environment turned up more about the protocol than about
ARC-AGI-3. These are the substance of the work rather than a side effect of it,
and they fall into three kinds — which is worth keeping straight.

### Gaps between the protocol and its reference implementation

Each was verified by measurement, then fixed in `dil-core` first and ported back.
All three have the same shape: a channel present in the topology that nothing
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

### A property of the protocol's own design

4. **The experience store is a biased sample, by construction.** §9 admits only
   registered mismatches, so what it holds are the region's *surprises*. Asked to
   predict, it lost 62 of 66 contests against the model — not because it is
   wrong, but because an exception loses to a distribution. No verdict is
   involved anywhere: §9 is explicit that a scar "carries no claim of
   correctness". This is not a defect to fix; it is what an experience store of
   collisions *is*, and it means the store is right for driving change and wrong
   for answering what happens next.

### A gap in this agent

5. **Nothing reads the goal**, as the status section says. This one is local to
   this repository and is not upstream's.

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
