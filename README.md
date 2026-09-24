# dil-arc3

An [ARC-AGI-3](https://arcprize.org/arc-agi/3/) agent whose whole operation is
the DIL protocol.

Not a solver with a protocol wrapped around it. The protocol *is* the mechanism:
there is no decision procedure underneath that DIL decorates, and no step where
the agent leaves the loop to think.

## Status, plainly

It runs, and it is being rebuilt around one mind. **It completes no levels.**

**The mind is a language model** — Qwen3.6-35B-A3B, served offline — and the
program it writes: `predict(grid, action) -> grid`, kept as data in the store and
tested against the region every cycle. When the program's expectation of the
frame fails, the mind asks its store for the frames that collided, has the model
write a better program from what it has, keeps it only if it explains that
evidence better, and writes it as a revision. Every step of that — the query,
the program entering at `nascent`, each revision, what each version was built
from, the frames it failed on — is in `[event]`, and a checker reads it back.

**What is measured of the one mind so far**: nothing on a scored run yet. Of the
model alone, outside the loop: it wrote an `ls20` program exact on 95% of held-out
transitions in two runs of four. Inside the loop, 60 cycles of `ls20` on Kaggle:
six versions of its program; the last, from cycle 35, held the frame on 16 of
the 24 cycles after it, all of the final 9, while naming fixed blocks by
coordinate rather than finding the object. No level (`LOG.md`, 2026-09-24).

**What it is told.** It arrives with no history, so the least it is given is a
directive: the one sentence the competition gives every model on its official
leaderboard, "You are playing a game. Your goal is to win.", with the published
rules of the place. It enters as host data stamped `prior` and stays in the
store until the character recalls it on a cue; how the region answers each action
is read against it.

## The four roles

Settled deliberately, with Plone.

| role | what it is | in this repo |
|---|---|---|
| **DIL** | the operating mechanism of the whole — how information moves | `src/dil/` |
| **host** | the body: takes in what the region returns and carries it inward, executes what was committed. **Computes nothing from what it takes in.** | `src/arc3/frame.py`, `action.py`, `host.py`, `observe.py` |
| **store** | memory: what the character recalls on a cue, including what it was told before it lived (`prior`) and the programs its mind wrote (`nascent`, then `running`) | `src/dil/store/`, `src/arc3/prior.py` |
| **mind** | the thinking organ — **one**: the model and the program it writes. Predicts, thinks when a prediction fails, reports how its understanding stands. **Chooses nothing.** | `src/arc3/mind.py` |
| **self** | what occurs while the loop runs through them. **It is what acts.** | not a file (`respond.py` is the policy the committed action is formed by) |

The line that matters: **the mind does not act.** It supplies an expectation —
it never sees which actions are available and never reaches the committed action.
The one thing it sends out is a question to its own memory: a store query, by cue,
that it chooses itself (§6.4). The query is traced like any emission, so what the
mind read is in `[event]`. What it writes, it writes as data (§9 `nascent`), with
what it was built from.

**Seeing is the body's; computing is the mind's.** The host takes the grid in as
the engine returns it; working out what is in it is the mind's program.

## What the mind is

**A pretrained language model, used as it is, and the program it writes.** The
model is not trained here and does not hold the game: what it knows of a game is
what the mind shows it — evidence the mind chose from its store and its window —
and what it produces is a program, which the loop then tests against the region
like any expectation. Three constraints shape that, and each is met:

- the scored games are unseen, so foreign weights would predict the wrong world
  — the model does not predict the world; it writes a program from this game's
  own evidence, and the program is what is tested;
- Kaggle's evaluation session has no network — the model is served offline, from
  a Kaggle Models mirror checked file by file against Hugging Face's hashes;
- INV-5: "refeeding the whole game history into a context window each step is a
  load, not an accrual" — the model is shown what the mind asked the store for
  and what T5's window holds, bounded, never the whole history, and only when an
  expectation failed.

`dependencies = []` holds: the model is reached over HTTP with the
standard library.

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

# a live game, with the model served at an OpenAI-compatible endpoint
PY=../ARC-AGI-3-Kaggle-Starter/.venv/bin/python
$PY scripts/run_game.py ls20 10 --endpoint http://127.0.0.1:8080/v1
```

Playing a game needs the ARC-AGI-3 environment, which is not vendored here: point
the host at an environment exposing `reset()` and `step(action, data)` and hand
it the engine's action class. `scripts/kaggle/build_dil_run.py` builds the Kaggle
notebook that runs it with the model on a GPU.

```python
from arc3 import admit, transducers
from arc3.host import create_source, declaration
from arc3.mind import ModelEndpoint, create_mind, mind_rule
from arc3.respond import least_resolved
```

`scripts/run_game.py` shows the whole wiring; `src/arc3/decisions.py`
records what this host declares for the protocol's deferred constants.

## Layout

```
src/dil/          the protocol — invariants, the eight-layer loop, the store,
                  the runtime, the conformance checker. Knows nothing about
                  ARC-AGI-3.
src/arc3/         the body and the mind, kept apart.
spec/             the DIL protocol and the specification it derives from,
                  copied from dil-core with their provenance.
scripts/          the measurement and run scripts behind every figure here.
CLAUDE.md         the working rules: the roles, declarations and constraints in
                  force, and the competition's rules.
LOG.md            the history: every measurement, the designs replaced, the
                  corrections made along the way.
```

History — the measurements behind this README, the designs it replaced and the
mistakes made on the way — is in [LOG.md](LOG.md).

## Licence

[MIT-0](LICENSE). No attribution required.
