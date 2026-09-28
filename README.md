# dil-arc3

An [ARC-AGI-3](https://arcprize.org/arc-agi/3/) agent whose whole operation is
the DIL protocol.

Not a solver with a protocol wrapped around it. The protocol *is* the mechanism:
there is no decision procedure underneath that DIL decorates, and no step where
the agent leaves the loop to think.

## Status, plainly

It runs, with one mind, which thinks with a language model, or learns from
nothing with an inducer (below). What it has done — the scored
submission, and every run — is in `LOG.md`, with the code each ran; this file
says only what the agent is.

**With the language model** — served offline; Qwen3.8-Flash-Next NVFP4, which
submission `56588469` used — the mind has the model write a program:
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
| **host** | the body: takes in what the region returns and carries it inward, carries out the mind's command; declares its eye and body to the mind. **Computes nothing and weighs nothing.** | `src/arc3/frame.py`, `action.py`, `host.py`, `observe.py`, `command.py`, `organs.py`, `prior.py` |
| **model** | the mind's computing, inside it — not a second mind — and replaceable: a language model and the program it writes, or an inducer the mind learns with. The **mind** is **one** and neutral about its region: it reads, expects, is curious and wants, holds an aim, and constructs the next action; commands it as T5's test. **Acts on nothing.** | `src/mind/` (`mind.py`, `models/`), seated by `src/arc3/mind.py`; `task.py`, `aim.py` |
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

One mind, neutral about its region (`src/mind/mind.py`), thinking with a model:
the part of it that computes (Plone, 2026-09-27). It can think with a language
model — below; submission `56588469` used it — or learn from nothing, with no
weights and no text, which submission `56623380` did (LOG.md, 2026-09-28).

**Learning is the mind's; an inducer computes for it** (Plone, 2026-09-28).
The loop is the mind's and names no task (`src/mind/learning.py`): it keeps
every step as experience, holds what an experience suggests as a hypothesis,
written as data built from the step, expects from the hypothesis that fits the
store best, which holds that expectation and is scarred when the region returns
otherwise, weighs each hypothesis by how often the region bore it out (held
while right more often than wrong), and chooses by the paths it knows and by
curiosity — what it knows least. The inducer is replaceable and only computes:
what a state is to it, what can be done in one, what an experience suggests and
what a hypothesis predicts. The one there is, the exact inducer
(`src/mind/models/exact.py`), suggests one hypothesis per experience — this act
from this situation gives that — applying nowhere else; it generalises nothing,
and is the reference others are measured against. It finds the clock a region
keeps whatever is done.

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
and they fall into three kinds — which is worth keeping straight. Each says what
holds now; how it was found, and the measurements, are in `LOG.md`.

### Channels the protocol requires, which an implementation can leave undrawn

The topology has channels an implementation can build and never draw on, and
nothing in running it shows one is dead until it is traced. Five are drawn on
now, in dil-core first and then here.

1. **The store is read back.** §9 has the self accrue from scars. A scar
   returns to `running` when it is used again — an expectation it is, or a
   recall — and `[event]` records each `scar → running`. §10's
   resistance-retrieval channel exists and is off by default: as a predictor it
   loses (6).
2. **The field reaches every layer, and every layer reads it.** INV-7 has it
   reach every layer as background — "same data plus a different field yields
   different meaning". It carries dispositions, never what was read (DIL-en-v7
   §2: "how to read, never what is read"): three axes, the specification's own
   examples — `trust`, `alertness`, `exploration`. Each layer reads the one that
   bears on its operation and shifts a declared threshold or gain by ½ to 1½:
   the declared value when the field has not leaned, never nothing, so the
   field biases and never annuls. Appraisal and forward-building read it too.
   Confidence it never touches, since §13.4 reads a confidence that fails to
   rise as a reloaded self. Which layer reads what is declared
   (`dil/loop/decisions.py`, `FIELD_WIRING`).
3. **Contributions blend.** "Every layer contributes to it as one competing
   parameter; contributions blend, never last-write-wins." Every layer votes on
   an axis from what it alone sees — whether the region spoke, how much it
   pushed, how much was new, how much mismatched or fell silent; each axis is a
   convex blend of the cycle's votes, taking effect the next cycle, and one no
   layer voted on carries over.
4. **T8 closes back into the loop through the field.** §6.2: "T8 closes back
   into the loop, not into a sink"; the meaning-channel cannot carry its output
   down, so T8 votes on the dispositions the layers below it read — `trust`,
   which T4 and T6 read, as the parent specification routes its feedback, and
   `exploration`. Every scar's context anchor records the field it was met under.
5. **What is admitted is asked for.** Host data enters through the tagging-gate
   stamped `prior`, and §9 has it move to `running` "once it has run". T3 asks
   the store, once, with the description of each kind of arrival on the
   open-tag keys (§6.4: "T3 emits a *query*"); the answer comes back through T1,
   runs every layer, and moves `prior → running`. Recalled on a cue, never
   poured in.

### A property of the protocol's own design

6. **The scars are a biased sample, by construction.** §9 moves to `scar` only
   what met a mismatch, so the scars are the region's *surprises*. Asked to
   predict, they lose to a model of what usually happens — an exception loses to
   a distribution. No verdict is involved anywhere: §9 is explicit that a scar
   "carries no claim of correctness". This is not a defect to fix; it is what a
   record of collisions *is*: right for driving change, wrong for answering what
   happens next.

### Gaps in this agent

7. **With the language model, what is kept is not what gets through a level.** A
   rewritten program is kept for predicting better; or for predicting as well
   and giving a command, when the body waits for one; or for predicting as well
   and acting otherwise, when the onlooker objected or a command or the aim did
   not bring about what it was for; or for stating an aim when the mind holds
   none. A missed aim sets the mind thinking, but nothing in what is kept
   favours a program whose acts reach the aim.
8. **What the onlooker says reaches no further than the acts it names.** It
   strikes the mind as a collision, and the mind answers there and then — it
   objects to the named acts where they were taken and commands again before
   the body moves. It learns nothing wider from being told: an objection is
   held while the onlooker says it and lifted when it stops.
9. **The language model's prompt does not show the field.** The field reaches
   the mind at T5 and conditions it whatever its model: its alertness sets how
   often the mind thinks in a cycle, for either model. The learning mind reads
   it further (how far an objection reaches); the language model is not shown
   it, so what it writes is not conditioned by the loop's disposition.

Local to this repository, not upstream's.

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
src/mind/         the one mind, neutral about its region; its learning
                  (learning.py); the models it thinks or learns with (language,
                  exact). Imports nothing from arc3.
src/arc3/         the body, its declared organs, what the mind is told, and
                  where this host seats the mind.
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
