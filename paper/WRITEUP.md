# Expect, Collide, Revise: Learning Without a Reward Function, Every Step on the Record

*The DIL protocol on ARC-AGI-3 — submission [[57470744, to be settled]]*

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
verifier. The submission scores [[score]] on the leaderboard, against 0.02 and
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
