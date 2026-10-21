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
game returns a frame, the host's senses take it in, the protocol's layers carry
it, the mind compares it with what it expected and commands, and the host's body
carries the command out.

Contributions:

1. An agent whose beliefs, refutations and choices are data with provenance, in a
   hash-chained log that a verifier and a conformance checker read.
2. A learning mind that names no task, with a replaceable model.
3. What the log shows of the agent's play, and why changes before its first
   success did not carry from the public games to the hidden ones.
4. A ledger of the ideas that failed, each measured.

*Figure 1: region → host (senses) → layers T1–T8 → mind → host (body) → region.* [[to draw]]
