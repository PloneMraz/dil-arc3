"""DECIDE@IMPL declarations for the ARC-AGI-3 host (protocol §12).

The protocol leaves tags A, B and H open because they depend on the environment.
This file declares them for ARC-AGI-3, and every figure in it was **read off real
frames**, not copied from a type hint or a docs page — the shape of an
observation turned out to differ from what the documentation implied.

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

# ── Tag H — situation fit ──
#
# NOT YET DECLARED. Fit is measured between the frame the loop predicted and the
# frame the region returned — never against a correct answer, because no answer
# is revealed during a run. What "closer" means over a stack of grids (cell
# agreement, region agreement, something else) is open and depends on what an
# entity turns out to be.
TAG_H_STATUS: Final = "open — depends on the entity decision, which is Plone's"
