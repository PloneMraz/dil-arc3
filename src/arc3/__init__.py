"""The ARC-AGI-3 host — the body the loop runs inside, and the mind it carries.

`dil/` is the operating mechanism. This ring is the body and the thinking organ,
kept apart:

  - **the body** — `frame.py` gates what arrives, `action.py` says what a legal
    move looks like, `host.py` holds the game and executes what the self
    committed, `observe.py` carries signals inward. It concludes nothing.
  - **the mind** — `perceive.py` finds the things in a signal, `interpret.py`
    reads what became of them, `mind.py` says what they will do next. It thinks;
    it never chooses, never sees the afforded set, and never reaches the
    emission.
  - **the self** — what occurs while the loop runs through them. It is what acts.

An earlier build had these inverted: the body handed the loop a finished
interpretation while the mind reached past the loop into the raw grid to pick
what to look at. Both are the other way round now.
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
from .interpret import REGION_ENTITY, ThingChange, change_value, region_status
from .mind import Mind, create_mind, predict_rule, situation_of
from .observe import (
    SELF_MOVE_CHANGE,
    STATUS_CHANNEL,
    VISION_CHANNEL,
    action_context,
    move_from_value,
    move_value,
    observe,
    transducers,
)
from .perceive import Region, background_of, segment, segment_grid
from .seeing import Scene, Seeing, Thing, create_seeing

__all__ = [
    "ACTIONS_ARE_PER_FRAME",
    "CELL_MAX",
    "CELL_MIN",
    "COMPLEX_ACTION",
    "COMPLEX_ACTION_COORD_MAX",
    "COMPLEX_ACTION_COORD_MIN",
    "ENTITY",
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
    "VISION_CHANNEL",
    "Frame",
    "FrameViolation",
    "Grid",
    "IllegalMove",
    "Mind",
    "Move",
    "Region",
    "Scene",
    "Seeing",
    "Thing",
    "ThingChange",
    "action_context",
    "background_of",
    "change_value",
    "check_afforded",
    "create_mind",
    "create_seeing",
    "move_from_value",
    "move_value",
    "observe",
    "predict_rule",
    "read_frame",
    "region_status",
    "segment",
    "segment_grid",
    "situation_of",
    "to_engine",
    "transducers",
]
