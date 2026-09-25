"""The ARC-AGI-3 host — the body the loop runs inside, and the mind it carries.

`dil/` is the operating mechanism. This ring is the body and the thinking organ,
kept apart:

  - **the body** — `frame.py` gates what the engine returns, `action.py` says
    what a legal move looks like, `host.py` holds the game and carries out what
    was committed, `observe.py` carries the frame and the region's status
    inward, `command.py` carries out the mind's command at link 5. It takes in
    and carries out; it computes nothing and weighs nothing.
  - **the mind** — `mind.py`: one mind, the model and the program it writes.
    It reads, expects, is curious and wants — in its thinking, not in a formula
    — and constructs the next action, commanding it as T5's test (§6.4). It
    acts on nothing.

Nothing here is the agent's first person: that is what the loop produces when it
runs (§7), located in no file.

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
from .command import WAIT, carry_out
from .mind import Mind, ModelEndpoint, create_mind, mind_rule
from .observe import (
    FRAME_CHANNEL,
    REGION_ENTITY,
    AGENT_MOVE_CHANGE,
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
    "AGENT_MOVE_CHANGE",
    "WAIT",
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
    "carry_out",
    "check_afforded",
    "create_mind",
    "mind_rule",
    "move_from_value",
    "move_value",
    "observe",
    "read_frame",
    "region_status",
    "to_engine",
    "transducers",
]
