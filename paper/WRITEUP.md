# Expect, Collide, Revise: Learning Without a Reward Function, Every Step on the Record

*The DIL protocol on ARC-AGI-3 — submission 57470744*

<!-- Draft. Budget: 1,500 words in all (OUTLINE.md). Every number is checked against
LOG.md and paper/TABLES.md before submission. [[...]] marks what is still open. -->

## Abstract

We built an agent that learns each ARC-AGI-3 game with no reward function. It
expects what each action will bring back; where the return differs, the mismatch
is recorded as a collision, and the collision turns what it does next. Every
expectation, collision, thought and choice is a datum naming what it was built
from, in a hash-chained event log, following the DIL protocol. On the 25 public
games, the submitted code's logs hold 1,130 chains a reader can follow from a
collision to the thought and the choice it turned; all 1,742 turned choices name
the collision behind them, and all 25 logs verify under the protocol's reference
verifier. The submission scores 0.25 on the leaderboard, against 0.02 and
0.06 for a random agent.

## 1. Introduction

ARC-AGI-3 scores an agent by how few actions it needs against a human, on games
it has never seen: what it knows of a game, it must learn while playing. The usual
way to learn by acting is to maximise a reward. We take another: the agent
expects, the game answers, and where the answer differs, the difference is what it
learns from — not a score to raise, but data that changes what it does next.

Our question is whether a third party can read back, from the agent's record
alone, what it knew at each step and why it acted. Figure 1 shows the loop: the
game returns a frame, the host's sensory organs take it in, the protocol's layers
carry it, the mind compares it with what it expected and commands, and the host's
effectors carry the command out.

Contributions:

1. An agent whose beliefs, refutations and choices are data with provenance, in a
   hash-chained log that a verifier and a conformance checker read.
2. A learning mind that names no task, with a replaceable model.
3. What the log shows of the agent's play, and why changes before its first
   success did not carry from the public games to the hidden ones.
4. A ledger of the ideas that failed, each measured.

*Figure 1: region → host (sensory organs) → layers T1–T8 → mind → host (effectors) → region.* [[to draw]]

## 2. Approach

**DIL** is a protocol for a loop that learns from collision and can be audited:
eight layers (T1–T8) every datum passes, eight invariants that halt the loop when
broken, and a store of two parts — `[data]`, which may be revised, and `[event]`,
an append-only, hash-chained log. DIL itself acts on nothing. The **host** is the
container: its sensory organs take in what the game returns, its effectors carry
out commands, and it computes nothing. The **mind** expects, is curious, wants and
commands; the **model** computes for it and can be replaced. *The mind acts on
nothing; it commands, and the host carries the command out through its
effectors* — and the game's return, never the mind, judges a command.

**Learning.** Each step is kept as an experience: from this state, this act gave
that. What an experience suggests beyond itself, the model (here a grid inducer)
states as a hypothesis — a cell rewritten, nothing changed, later a thing moved —
written as a datum built from the step it came from. Before each act the mind
expects, from the experience or hypothesis right at the highest rate,
(right + 1) / (tried + 2); where nothing it knows applies, it expects the game to
change, so that silence too can collide. When the return differs, the mismatch is
recorded: the return, and every datum the expectation rested on, move to `scar`.
The mind then thinks on what collided, writes the thought, and the thought turns
its next choice — away from a kind of act that changed nothing, toward where an
answer differed, away from what ended the game. A mismatch is never a penalty: no
count of collisions is kept or sought.

**Choosing.** The mind is curious for acts that have reached states not met
before; it goes where a hypothesis says the level's aim lies once it holds one;
and a modulatory field — trust, alertness, exploration, voted by every layer and
carried across cycles — sets how sure it must be before it expects, how long a
turn lasts, and how far it looks ahead.

**An Other.** An onlooker in the world remarks when the agent repeats itself or
stands still; its word reaches the mind as a collision, not an instruction.

## 3. A chain the reader can check

Each cycle leaves in `[event]` the path of every datum through the layers, what
entered, what was scarred, what the mind read, and each datum it wrote with the ids
it was built from. Kaggle shows no log of a scored run, so the evidence is the
submitted code's Save & Run on the 25 public games; its stores are published with
the notebook.

Figure 2 is one chain from lp85, where the agent finishes the first level in its
human baseline's 17 actions. A click at (37, 20), expected to change the game,
returns it unchanged: the return `signal-9-0` is scarred. The thought `written-9-0`
records the silence and turns the mind from that kind of act; the next choice,
`written-9-3`, clicks elsewhere and says so in its reason, naming the return and the
thought. The experience `written-9-2` now holds that the click there changes
nothing; when the agent meets that click again at cycle 22, the game answers as now
expected, and nothing collides.

Across the 25 games: 2,757 frame collisions; 1,130 such chains, each a scar, the
thought it set off and the choice it turned, all built from the same return; in 717
the next return came as expected. All 1,742 turned choices name the return behind
them. All 25 logs verify under the protocol's reference verifier, and its
conformance checker passes four criteria in every store (invariants, loop,
resistance, store); continuity of the self it leaves to a third party, as the
protocol requires.

Two individuals of the same agent, born in different fields, part in tu93 at step
72: a silence turns both, but the turn lasts one choice longer in one of them. With
and without the onlooker, the agent parts in all eleven games tried; in m0r0 the
onlooker's earlier remarks had moved its field, and with it the agent scored 0.80
on the game against 0.19 alone. `scripts/chains.py`,
`thoughts.py` and `differ.py` find all of this in the stores alone.

*Figure 2: the lp85 chain, each record by its id.* [[to draw]]

## 4. Results

| | Leaderboard |
|---|---|
| Random agent (starter kit, twice) | 0.02, 0.06 |
| A language model in the learning's place | 0.00 |
| The learning mind, first form | 0.05 |
| Grid inducer, versions 18, 23, 28, 35, 37 | 0.25–0.26 |
| … with "suspects" (version 26) | 0.02 |
| **This submission (version 41)** | **0.25** |

On the 25 public games the submitted code finishes 15 of 183 levels (0.489). An
earlier version's log (23) showed where the actions go: 29% changed nothing and 17%
walked back to where something was left to try; three levels came near the human
baseline, the rest at 3 to 20 times it.

## 5. What did not work, and why

Nineteen ideas were measured and not kept (the PDF's Table 3): a law ordering
foreseen acts (13 levels against 15), a ladder of looser aim hypotheses (one refuted
195 times), an object-centred inducer (0.457 in its first form; later 0.500 and 0.486 against
the grid's 0.491, with fewer levels), commands chosen
as tests of the least sure expectation (0.379 and 0.255 against 0.513), and a
language model writing predictive programs, right about one step in eleven.

The lesson is one of Theory. Before its first success in a level, a change only
moves where the agent explores, and the public games did not foretell the hidden
ones: "suspects" reached the most levels in public (15, 0.515) and scored 0.02
hidden, against 0.25 for the version it changed. Since then, the inducer's laws of
things — moves, blocks — apply only once a level's aim has come, so that what
earned the first levels is not moved.

## 6. Limits and conclusion

The score is low, and said so. Where the agent never looks stuck, the onlooker has
no reason to speak, and the checker's diversity criterion fails (six games of 25).
Writing what the mind learns is itself data that returns to the loop: naming each
thought in its choice moved nine games of eleven a little. The verifier is the
protocol's own reference implementation, not an independent one.

What holds is the record: every belief, refutation and choice the agent made can be
read back, and checked, by someone who does not trust it. The mind names no task;
another model, or another environment, plugs into the same loop.
