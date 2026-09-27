# dil-arc3

An [ARC-AGI-3](https://arcprize.org/arc-agi/3/) agent whose whole operation is
the DIL protocol.

Not a solver with a protocol wrapped around it. The protocol *is* the mechanism:
there is no decision procedure underneath that DIL decorates, and no step where
the agent leaves the loop to think.

## Status, plainly

It runs, and it is being rebuilt around one mind. **It completes no levels.**

**The mind is a language model** — served offline; Qwen3.8-Flash-Next NVFP4 in
the latest runs, Qwen3.6-35B-A3B before — and the program it writes:
`predict(grid, action, x, y)`, the next grid and what the region will report of
itself; `propose(grid, steps)`, the next action from where the game stands and
the steps just seen; and `GOAL`, the aim it holds itself to. All kept as data in
the store, the prediction tested against the region every cycle. When an
expectation meets a mismatch — the frame, the region's status, what the program
said a command or its aim would bring about, or an onlooker's objection to how
the agent behaves — the program is scarred with it, and the mind has the model
write a better one from what it has, keeps it only if it explains that evidence
better (or as well, when the body waits for a command, the onlooker objected, or
a command or the aim did not bring about what was said), and writes it as a
revision; the model also chooses what to ask its memory for, and reads only
that, and each answer it gives is kept whole in the store. Every step of
that — each question, the program entering at `nascent`, each revision, what
each version was built from, each scar it met and each return to use — is in
`[event]`, and a checker reads it back.

**What is measured of the one mind so far**: one scored run submitted (notebook
version 12, code `3b31806`), its score not yet returned. In every offline run of
four games (60 cycles each, on Kaggle), no level. The program predicts much of
what the region returns — 55 of 60 frames in one `ls20` run — and the mind holds
an aim it inferred and meets it when it falls due. Behaviour turns, but reaches
no level. Before `3b31806` each game kept to one action. The submitted code
changed action in the one game its notebook played offline (`ls20`: RESET,
ACTION1, then ACTION2). The code after it (`af72f78`, offline run v14, not
submitted) changed action in every game, and refused 26 rewritten programs that
proposed the same action again. Every run is in `LOG.md`.

**What it is told.** Its store holds, before it lives, three things, each as host
data stamped `prior`: what its mind is told its thinking is for
(`prior:mind-task`, this project's own words, neutral — the aim is to get
through the levels, and no kind of game, mechanic or strategy is named; it is told
that its `propose` may run its own `predict` ahead toward its aim, and the seconds
each run has); what the
mind does with any aim (`prior:mind-aim`); and the competition's published
rules, quoted. The mind recalls the first two itself, and the model reads them.
The rules are recalled by T3 on a cue, as the protocol does, and the model reads
them only if it asks.

## The four roles

Settled deliberately, with Plone.

| role | what it is | in this repo |
|---|---|---|
| **DIL** | the operating mechanism of the whole — how information moves; its store is the agent's memory: what it had before it lived (`prior`), what it met, and what its mind wrote | `src/dil/` |
| **host** | the body: takes in what the region returns and carries it inward, carries out the mind's command. **Computes nothing and weighs nothing.** | `src/arc3/frame.py`, `action.py`, `host.py`, `observe.py`, `command.py`, `prior.py` |
| **model** | the thinking organ's engine, replaceable. The **mind** is the design: **one**, the model and the program it writes. It reads, expects, is curious and wants — in its thinking, not in a formula — holds an aim, and constructs the next action; commands it as T5's test. **Acts on nothing.** | `src/arc3/mind.py`, `task.py`, `aim.py` |
| **self** | what the loop produces when it runs (§7) — a law, located in no file. Its behaviour is the body's motion under the mind's command. | none: the word is not used in the code |

Outside all four is the **world** (`src/world/`): the region the agent acts on,
and an onlooker, an Other who sees it act and says what it sees (tag E). The host
touches the region and hears the onlooker; it holds neither.

The line that matters: **the mind acts on nothing; it commands, and the body
carries out.** The mind constructs the next action toward getting through the
level and commands it as T5's test (§6.4); the body carries it out, or, with no
command it can carry out, waits. What judges a command is the region's return,
which scars the program when it does not hold. What else the mind sends out is a
question to its own memory: a store query, by cue, that it chooses itself
(§6.4). The query is traced like any emission, so what the
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
  load, not an accrual" — the model is shown what it asked the store for and
  what T5's window holds, bounded, never the whole history; and it is asked to
  think only when something comes from outside — a mismatch, the onlooker — or
  while the body waits for a command.

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

7. **Behaviour turns, but reaches no level.** The mind holds an aim (`GOAL`,
   inferred when the task names none) and meets it when it falls due; the
   mismatch reaches the model, which rewrites its program. Until `3b31806` the
   rewritten program proposed the same action. Since then, a rewrite made on
   how the agent acts — the onlooker, a want, an aim — is kept only if it acts
   otherwise, and in the offline runs since, every game changes action. No
   level has been completed to learn from. Local to this repository, not
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
from arc3.command import carry_out
```

`scripts/run_game.py` shows the whole wiring; `src/arc3/decisions.py`
records what this host declares for the protocol's deferred constants.

## Layout

```
src/dil/          the protocol — invariants, the eight-layer loop, the store,
                  the runtime, the conformance checker. Knows nothing about
                  ARC-AGI-3.
src/arc3/         the body and the mind, kept apart.
src/world/        what lies outside the agent: the region it acts on, served to
                  a game's own process in a scored run, and the onlooker.
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
