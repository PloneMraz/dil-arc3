"""The action vocabulary: what counts as a legal move, and what the engine wants.

Nothing here produces a move. These tests cover the SHAPE of a move, which is
tag A's ActivityEnvironment; who forms one is not decided.
"""

from __future__ import annotations

import pytest

from arc3 import GRID_COLS, GRID_ROWS, IllegalMove, Move, check_afforded, read_frame, to_engine
from tests.test_arc3_frame import FakeFrameData, grid


class FakeGameAction:
    """Reproduces the engine enum's `from_id`, and its refusal of `cls(n)`."""

    def __init__(self, action_id: int) -> None:
        self.value = action_id

    def __eq__(self, other):  # pragma: no cover - convenience
        return isinstance(other, FakeGameAction) and other.value == self.value

    @classmethod
    def from_id(cls, action_id: int) -> "FakeGameAction":
        if action_id not in range(0, 8):
            raise ValueError(f"No GameAction with id {action_id}")
        return cls(action_id)


def test_a_simple_move_carries_no_coordinates():
    assert Move(3).x is None


def test_a_simple_move_with_coordinates_is_refused():
    with pytest.raises(IllegalMove, match="takes no coordinates"):
        Move(3, x=1, y=1)


def test_action6_without_coordinates_is_refused():
    with pytest.raises(IllegalMove, match="needs x and y"):
        Move(6)


def test_action6_coordinates_must_lie_on_the_grid():
    Move(6, x=0, y=63)
    with pytest.raises(IllegalMove, match="outside"):
        Move(6, x=64, y=0)
    with pytest.raises(IllegalMove, match="outside"):
        Move(6, x=0, y=-1)


def test_coordinate_bound_matches_the_grid_the_host_reads():
    """63 is the last index of a 64-wide grid; the two must not drift apart."""
    Move(6, x=GRID_COLS - 1, y=GRID_ROWS - 1)
    with pytest.raises(IllegalMove):
        Move(6, x=GRID_COLS, y=0)


def test_an_unknown_action_id_is_refused():
    with pytest.raises(IllegalMove, match="unknown action id"):
        Move(9)


# ── afforded, per frame ──


def test_a_move_the_frame_does_not_afford_is_refused():
    """vc33 afforded only ACTION6. ACTION1 there is not a weak move, it is none."""
    f = read_frame(FakeFrameData([grid()], actions=(6,), game_id="vc33"))
    with pytest.raises(IllegalMove, match="not in available_actions"):
        check_afforded(Move(1), f)


def test_a_move_the_frame_affords_passes():
    f = read_frame(FakeFrameData([grid()], actions=(1, 2, 3, 4)))
    assert check_afforded(Move(2), f).action_id == 2


def test_reset_is_afforded_even_by_a_terminal_frame():
    f = read_frame(FakeFrameData([grid()], state="GAME_OVER", actions=()))
    assert check_afforded(Move(0), f).action_id == 0


# ── translation ──


def test_translation_uses_from_id_not_the_constructor():
    """`GameAction(1)` raises in the real engine. This must not depend on it."""
    action, data = to_engine(Move(1), FakeGameAction)
    assert action.value == 1
    assert data == {}


def test_complex_translation_carries_x_and_y():
    action, data = to_engine(Move(6, x=12, y=30), FakeGameAction)
    assert action.value == 6
    assert data == {"x": 12, "y": 30}
