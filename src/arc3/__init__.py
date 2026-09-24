"""The ARC-AGI-3 host — the body the loop runs inside, and the mind it carries.

`dil/` is the operating mechanism. This ring is the body and the thinking organ,
kept apart:

  - **the body** — `frame.py` gates what the engine returns, `action.py` says
    what a legal move looks like, `host.py` holds the game and executes what the
    self committed, `observe.py` carries the frame and the region's status
    inward. It takes in; it computes nothing from what it takes in.
  - **the mind** — `mind.py`: one mind, the model and the program it writes.
    It predicts, thinks when a prediction fails, and reports how its
    understanding stands; it never chooses, never sees the afforded set, and
    never reaches the committed action.
  - **the self** — what occurs while the loop runs through them. It is what acts
    (`respond.py` is the policy by which the committed action is formed).

Until 2026-09-24 a computation of the grid (`perceive.py`, `seeing.py`,
`interpret.py`) and a counting mind ran beside the model: two minds. They are
gone; see `mind.py` and `observe.py`.
"""

from .action import (
    COMPLEX_ACTION,
    RESET,
    SIMPLE_ACTIONS,
    IllegalMove,
    Move,
    check_afforded,
    to_engine,
)
from .decisions import (
    ACTIONS_ARE_PER_FRAME,
    CELL_MAX,
    CELL_MIN,
    COMPLEX_ACTION_COORD_MAX,
    COMPLEX_ACTION_COORD_MIN,
    ENTITY,
    FRAME_IS_A_STACK,
    GRID_COLS,
    GRID_ROWS,
    SIGNAL_PAYLOAD_REPR,
    TAG_B_STATUS,
    TAG_H_STATUS,
)
from .frame import (
    LIVE_STATES,
    TERMINAL_STATES,
    Frame,
    FrameViolation,
    Grid,
    read_frame,
)
from .mind import Mind, ModelEndpoint, create_mind, mind_rule, region_valence
from .observe import (
    FRAME_CHANNEL,
    REGION_ENTITY,
    SELF_MOVE_CHANGE,
    STATUS_CHANNEL,
    action_context,
    admit,
    move_from_value,
    move_value,
    observe,
    region_status,
    transducers,
)

__all__ = [
    "ACTIONS_ARE_PER_FRAME",
    "CELL_MAX",
    "CELL_MIN",
    "COMPLEX_ACTION",
    "COMPLEX_ACTION_COORD_MAX",
    "COMPLEX_ACTION_COORD_MIN",
    "ENTITY",
    "FRAME_CHANNEL",
    "FRAME_IS_A_STACK",
    "GRID_COLS",
    "GRID_ROWS",
    "LIVE_STATES",
    "REGION_ENTITY",
    "RESET",
    "SELF_MOVE_CHANGE",
    "SIGNAL_PAYLOAD_REPR",
    "SIMPLE_ACTIONS",
    "STATUS_CHANNEL",
    "TAG_B_STATUS",
    "TAG_H_STATUS",
    "TERMINAL_STATES",
    "Frame",
    "FrameViolation",
    "Grid",
    "IllegalMove",
    "Mind",
    "ModelEndpoint",
    "Move",
    "action_context",
    "admit",
    "check_afforded",
    "create_mind",
    "mind_rule",
    "move_from_value",
    "move_value",
    "observe",
    "read_frame",
    "region_valence",
    "region_status",
    "to_engine",
    "transducers",
]
