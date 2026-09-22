"""What a move IS in this environment — the vocabulary, not the decider.

Tag A asks for the concrete `ActivityEnvironment`: the space the agent can act
into. That space is declared here. **Nothing in this module produces a move.**
Which layer forms an emission, and what the model's part in it is, is a
skeleton-level question that has not been answered, so this file deliberately
stops at "what a legal move looks like" and "how to send one".

Ported nothing: dil-core's minimal host emits a fixed marker, because it had no
environment to act into.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from .decisions import COMPLEX_ACTION_COORD_MAX, COMPLEX_ACTION_COORD_MIN
from .frame import Frame

RESET: Final = 0
COMPLEX_ACTION: Final = 6
SIMPLE_ACTIONS: Final = (1, 2, 3, 4, 5, 7)


class IllegalMove(Exception):
    """A move was formed that this frame does not afford."""


@dataclass(frozen=True, slots=True)
class Move:
    """One action the self may emit: an id, plus coordinates when id is 6.

    RHAE counts every one of these. Deliberation is free; this is not.
    """

    action_id: int
    x: int | None = None
    y: int | None = None

    def __post_init__(self) -> None:
        if self.action_id == COMPLEX_ACTION:
            if self.x is None or self.y is None:
                raise IllegalMove("ACTION6 needs x and y")
            for name, v in (("x", self.x), ("y", self.y)):
                if not COMPLEX_ACTION_COORD_MIN <= v <= COMPLEX_ACTION_COORD_MAX:
                    raise IllegalMove(
                        f"{name}={v} outside {COMPLEX_ACTION_COORD_MIN}-"
                        f"{COMPLEX_ACTION_COORD_MAX}"
                    )
        elif self.x is not None or self.y is not None:
            raise IllegalMove(f"action {self.action_id} takes no coordinates")
        elif self.action_id != RESET and self.action_id not in SIMPLE_ACTIONS:
            raise IllegalMove(f"unknown action id {self.action_id}")


def check_afforded(move: Move, frame: Frame) -> Move:
    """Refuse a move the frame does not afford.

    `available_actions` is per frame and per game — `vc33` afforded only
    ACTION6 — so a move must be checked against the frame it answers, never
    against a fixed table. RESET is exempt: it is how a terminal frame is left,
    and terminal frames afford nothing.
    """
    if move.action_id == RESET:
        return move
    if move.action_id not in frame.available_actions:
        raise IllegalMove(
            f"action {move.action_id} not in available_actions "
            f"{frame.available_actions} for {frame.game_id}"
        )
    return move


def to_engine(move: Move, game_action_cls: Any) -> tuple[Any, dict[str, int]]:
    """Translate a Move into the engine's `(GameAction, data)` pair.

    **Use `GameAction.from_id`, never `GameAction(n)`.** The enum's members are
    declared as `ACTION1 = (1, SimpleAction)` and rewrite `_value_` to the bare
    id inside `__init__` — after `_value2member_map_` was built from the tuple.
    So `GameAction(1)` raises `ValueError: 1 is not a valid GameAction` while
    `GameAction.from_id(1)` returns it. Found by running it, not by reading it.

    Takes the class rather than importing it, so this ring stays free of the SDK.
    """
    action = game_action_cls.from_id(move.action_id)
    data: dict[str, int] = {}
    if move.action_id == COMPLEX_ACTION:
        assert move.x is not None and move.y is not None  # enforced in __post_init__
        data = {"x": move.x, "y": move.y}
    return action, data
