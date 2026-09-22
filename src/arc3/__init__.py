"""The ARC-AGI-3 host — the body the loop runs inside.

`dil/` is the operating mechanism; this ring is the container and the sense
organs. It declares what the protocol left open for this environment
(`decisions.py`) and reads the environment's frames at the boundary
(`frame.py`).

Nothing here decides a move. What produces action is the self — the loop running
through this host — and where that emission is formed is not settled yet.
"""

from .decisions import (
    ACTIONS_ARE_PER_FRAME,
    CELL_MAX,
    CELL_MIN,
    COMPLEX_ACTION_COORD_MAX,
    COMPLEX_ACTION_COORD_MIN,
    FRAME_IS_A_STACK,
    GRID_COLS,
    GRID_ROWS,
    SIGNAL_PAYLOAD_REPR,
    TAG_B_STATUS,
    TAG_H_STATUS,
)
from .model import EffectModel, create_model, predict_rule
from .observe import (
    EFFECT_INFO_TYPE,
    GAME_CHANNEL,
    SELF_MOVE_CHANGE,
    affordance_key,
    game_transducer,
    observe,
)
from .action import (
    COMPLEX_ACTION,
    RESET,
    SIMPLE_ACTIONS,
    IllegalMove,
    Move,
    check_afforded,
    to_engine,
)
from .effect import Effect, diff
from .frame import (
    LIVE_STATES,
    TERMINAL_STATES,
    Frame,
    FrameViolation,
    Grid,
    read_frame,
)

__all__ = [
    "ACTIONS_ARE_PER_FRAME",
    "COMPLEX_ACTION",
    "CELL_MAX",
    "CELL_MIN",
    "COMPLEX_ACTION_COORD_MAX",
    "COMPLEX_ACTION_COORD_MIN",
    "FRAME_IS_A_STACK",
    "GRID_COLS",
    "GAME_CHANNEL",
    "GRID_ROWS",
    "LIVE_STATES",
    "RESET",
    "SIGNAL_PAYLOAD_REPR",
    "SELF_MOVE_CHANGE",
    "SIMPLE_ACTIONS",
    "TAG_B_STATUS",
    "TAG_H_STATUS",
    "TERMINAL_STATES",
    "Frame",
    "EFFECT_INFO_TYPE",
    "Effect",
    "EffectModel",
    "FrameViolation",
    "Grid",
    "IllegalMove",
    "Move",
    "affordance_key",
    "check_afforded",
    "create_model",
    "diff",
    "game_transducer",
    "observe",
    "predict_rule",
    "read_frame",
    "to_engine",
]
