"""DECIDE@IMPL declarations for the ARC-AGI-3 host (protocol §12).

The protocol leaves tags A, B, F and H open because they depend on the
environment. This file declares them for ARC-AGI-3, and every figure in it was
**read off real frames**, not copied from a type hint or a docs page — the shape
of an observation turned out to differ from what the documentation implied.

Ported nothing: this is the host's own declaration.
"""

from typing import Final

# ── Tag A — concrete representation of Signal, InfoUnit, ActivityEnvironment ──
#
# Measured on `ls20` and `vc33` over 42 frames, 2026-09-22.

# An observation is a STACK of grids, not one grid. `FrameData.frame` is typed
# `list[list[list[int]]]`, and real frames came back as (1, 64, 64) and
# (6, 64, 64) — one to N grids, each 64 rows by 64 columns. The docs say
# "maximum 64x64"; both games observed used the full 64×64 every time.
FRAME_IS_A_STACK: Final = True
GRID_ROWS: Final = 64
GRID_COLS: Final = 64

# Cell values are integers 0–15 by the schema. Across those 42 frames the values
# actually seen were 0,1,3,4,5,7,8,9,11,12 — ten of the sixteen. The range is the
# declaration; the observed subset is not, since another game may use the rest.
CELL_MIN: Final = 0
CELL_MAX: Final = 15

SIGNAL_PAYLOAD_REPR: Final = (
    "one ARC-AGI-3 frame: a stack of 1..N grids, each 64x64, cells integer "
    "0-15, plus the game state and the available_actions set"
)

# ── The action set, and a trap in it ──
#
# Seven actions exist: RESET, ACTION1-5 simple, ACTION6 taking x,y in 0-63,
# ACTION7 undo. But `available_actions` is PER FRAME and per game: `ls20`
# offered (1,2,3,4) and `vc33` offered only (6,). An agent that emits only the
# simple actions does literally nothing in a game that affords only ACTION6.
# Whatever produces a move MUST read available_actions from the frame it is
# answering, never from a fixed table.
ACTIONS_ARE_PER_FRAME: Final = True
COMPLEX_ACTION_COORD_MIN: Final = 0
COMPLEX_ACTION_COORD_MAX: Final = 63

# ── Tag B — thresholds ──
#
# NOT YET DECLARED for this environment. The loop ring carries dil-core's
# minimal-host values (MATCHING_WINDOW 8, STABILITY_THRESHOLD 3, BASELINE_WINDOW
# 16, SUFFICIENT_RECURRENCE 3). Whether they suit a 64x64 grid stack arriving
# every step is an empirical question, and inventing numbers before measuring is
# what §12 forbids. They stay inherited, and declared as inherited, until a run
# gives grounds to change them.
TAG_B_STATUS: Final = "inherited from dil-core's minimal host; not yet tuned on measurements"

# ── The entities — the Others the region says are there ──
#
# Two, one per channel the host carries in (`observe.py`): the frame the region
# returned, and the region itself speaking about its state. The mind predicts
# the first; the second holds the standing expectation. What an entity was
# before — an affordance, then a "thing" computed from the grid — is in LOG.md.
ENTITY: Final = "the frame and the region — one per signal the host carries in"

# ── Tag F — the open-tag registry beyond `domain`, and the store's index ──
#
# §9: a key MUST denote the same dimension wherever it appears, so the store is
# filterable by it; which keys exist is the implementation's to declare. These
# are the keys this host uses, each with the one dimension it names. T3 asks the
# store with an arrival's description on these keys (§6.4 query), and a datum
# answers when its open tags carry the same pairs — so a key used with two
# meanings would recall the wrong thing, and that is why they are fixed here.
OPEN_TAG_KEYS: Final[dict[str, str]] = {
    "domain": "the class of data the datum is (required by §9)",
    "kind": "what sort of datum it is within its domain",
    "source": "where the datum was read or produced",
    "object": "what the datum is about — the same on a stored datum and on an "
    "arrival, which is what lets the one recall the other",
    "sense": "which sense the datum concerns — the one an arrival came by, or "
    "the one a stored datum describes",
}

# ── Tag H — situation fit ──
#
# DECLARED: the frame's fit is exact equality, cell for cell, of the grid the
# mind's program predicted with the grid the region returned — the last of each
# stack, which is the mind's reading (`mind.transition_of`). Nothing looser: a
# program that is right on most cells is still wrong, and the mismatch is what
# the mind thinks from. The region's status fits when the region reports what it
# reported last; its `context`, the action just taken, is the agent's own act and is
# not expected back (`mind.Mind.on_status`). Never against a correct answer:
# none is revealed in a run.
# The earlier declaration (equality of an effect signature, `effect.py`) and its
# measurements are in LOG.md.
TAG_H_STATUS: Final = "declared — exact equality of the predicted and returned grid"
