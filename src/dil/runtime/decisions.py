"""Declared DECIDE@IMPL choices for the runtime / requisition ring (protocol §12).

This is the outermost ring — where DIL meets the host. It declares the live
Mode-B source (tag D), the reflection mechanism (tag E), and the diversity-loss
thresholds (§11, conformance criterion 7).

**Tag E is settled for this host, and differently from dil-core's deployment.**
Reflection needs a third party, and a Kaggle evaluation session has neither a
network nor a human. The reader here is **another agent in the same run**, which
tag E's own wording already admits: "WHO reads (a user, another agent, a critic
service) stays deliberately deployment-open". See `peer.py` for the mechanism and
for what it does not reach.

Ported from dil-core against DIL protocol v0.3.3.
"""

from typing import Final

# DECIDE@IMPL tag D — the identity of the live Mode-B source (protocol §8.4).
MODE_B_SOURCE: Final = "host-source (live external input the agent does not control)"
# Rationale: the live Mode-B source is the HostSource the daemon requisitions — a
# user, another agent, or any region that returns and can resist. This replaces
# the static appraisal anchor (loop tag C) as the real brake: resistance enters
# from outside the loop, not self-generated. A compliant source that never
# resists is useless however much it supplies (the B-source rule, §8.4); the
# diversity monitor below flags its loss.
#
# For an ARC-AGI-3 host this is satisfiable: the game returns frames, the agent
# does not control it, and it resists prediction.

# DECIDE@IMPL tag E — the read-collision-into-coordinates mechanism (§8.4).
REFLECTION_MECHANISM: str = (
    "an onlooker: an Other outside the agent, a separate piece of code and not an "
    "agent, that watches the moves the agent commits and whether the level moved, "
    "and says when it judges the agent stuck — 'repeating' (the same move 4 times, "
    "the level unchanged; not measured) or 'back-and-forth' (x y x y), each pointing "
    "at the cycle the pattern began (arc3/onlooker.py). Its remark enters on the "
    "declared T3 channel `onlooker`, is kept as data (domain reflection), and "
    "collides when the onlooker changes its stance: a mismatch between the agent and "
    "the onlooker, never a retelling of a collision the agent already recorded. It "
    "returns and does not write. LIMIT, declared: its stance is two written rules, "
    "so it objects only to what they name"
)
# Rationale: §8.4's reader is a third party with a view of its own, and an Other
# is a position, not a kind — a hard third party may fill it so long as it can
# resist. The onlooker's coordinate is the cycle in the agent's behaviour it
# points at. The declaration it replaces — a peer agent relaying this agent's
# recorded collisions — only retold them, and two peers echoed each other
# (LOG.md, 2026-09-25). No internal self-reflection faculty exists, per §8.4. Typed `str` rather than a
# frozen literal so the conformance checker's "is it still deferred?" comparison
# stays a genuine runtime read.

# DECIDE@IMPL — diversity-loss monitor window and minimum source count (§11).
DIVERSITY_WINDOW: Final = 8
MIN_DIVERSITY_SOURCES: Final = 2
# Rationale (tunable, not derived): over the last DIVERSITY_WINDOW cycles, if the
# resistance-source set holds fewer than MIN_DIVERSITY_SOURCES distinct sources,
# the daemon emits the diversity-loss signal (conformance criterion 7). This
# catches both single-source domination — a Sybil-ish flood, §11 — and resistance
# depletion, the Mode-A collapse risk. The cure, admission control and
# source-diversity enforcement, lives outside the loop; the protocol carries only
# the signal.
