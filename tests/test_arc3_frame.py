"""The host's boundary: what it accepts, and what it refuses.

Every shape asserted here came off real frames from `ls20` and `vc33`
(2026-09-22, 42 frames), not off the SDK's type hints.
"""

from __future__ import annotations

import pytest

from arc3 import (
    CELL_MAX,
    GRID_COLS,
    GRID_ROWS,
    Frame,
    FrameViolation,
    read_frame,
)


class FakeState:
    """Stands in for `GameState`, which carries `.name`."""

    def __init__(self, name: str) -> None:
        self.name = name


class FakeFrameData:
    def __init__(self, frame, state="NOT_FINISHED", actions=(1, 2, 3, 4), **kw):
        self.game_id = kw.get("game_id", "ls20")
        self.frame = frame
        self.state = FakeState(state)
        self.available_actions = list(actions)
        self.levels_completed = kw.get("levels_completed", 0)
        self.win_levels = kw.get("win_levels", 3)


class RowLike:
    """A row that is iterable but is not a list — the `ndarray` case.

    `FrameDataRaw.frame` is `List[ndarray]`, so a reader that pattern-matches on
    `list` would read one of the engine's two frame types and silently fail the
    other.
    """

    def __init__(self, values):
        self._values = tuple(values)

    def __iter__(self):
        return iter(self._values)


def grid(fill: int = 0):
    return [[fill] * GRID_COLS for _ in range(GRID_ROWS)]


# ── the shapes actually observed ──


def test_reads_the_single_grid_stack_observed_in_ls20():
    f = read_frame(FakeFrameData([grid(5)]))
    assert isinstance(f, Frame)
    assert f.depth == 1
    assert len(f.top) == GRID_ROWS
    assert len(f.top[0]) == GRID_COLS
    assert f.available_actions == (1, 2, 3, 4)


def test_reads_the_six_grid_stack_observed_in_vc33():
    """An observation is a stack. A reader assuming one grid drops five of six."""
    f = read_frame(FakeFrameData([grid(i) for i in range(6)], actions=(6,)))
    assert f.depth == 6
    assert f.available_actions == (6,)
    assert f.top[0][0] == 5  # the last grid in the stack, not the first


def test_reads_rows_that_are_not_lists():
    raw = [[RowLike([0] * GRID_COLS) for _ in range(GRID_ROWS)]]
    assert read_frame(FakeFrameData(raw)).depth == 1


def test_available_actions_are_deduplicated_and_sorted():
    f = read_frame(FakeFrameData([grid()], actions=(4, 1, 4, 2)))
    assert f.available_actions == (1, 2, 4)


def test_levels_completed_is_the_score_channel_not_a_score_field():
    f = read_frame(FakeFrameData([grid()], levels_completed=2))
    assert f.levels_completed == 2
    assert not hasattr(f, "score")


# ── what it refuses ──


def test_refuses_an_empty_stack():
    """The engine returns this before RESET. It is not an observation."""
    with pytest.raises(FrameViolation, match="empty stack"):
        read_frame(FakeFrameData([]))


def test_refuses_a_cell_outside_the_declared_range():
    g = grid()
    g[7][9] = CELL_MAX + 1
    with pytest.raises(FrameViolation, match="outside declared"):
        read_frame(FakeFrameData([g]))


def test_refuses_a_short_grid_instead_of_padding_it():
    with pytest.raises(FrameViolation, match="rows, declared"):
        read_frame(FakeFrameData([[[0] * GRID_COLS] * (GRID_ROWS - 1)]))


def test_refuses_a_ragged_row():
    g = grid()
    g[3] = [0] * (GRID_COLS - 2)
    with pytest.raises(FrameViolation, match="cols, declared"):
        read_frame(FakeFrameData([g]))


def test_refuses_an_unknown_state():
    with pytest.raises(FrameViolation, match="unknown"):
        read_frame(FakeFrameData([grid()], state="PAUSED"))


def test_refuses_a_live_frame_affording_nothing():
    with pytest.raises(FrameViolation, match="nothing is affordable"):
        read_frame(FakeFrameData([grid()], actions=()))


def test_accepts_a_terminal_frame_affording_nothing():
    """GAME_OVER legitimately affords nothing until RESET."""
    f = read_frame(FakeFrameData([grid()], state="GAME_OVER", actions=()))
    assert f.state == "GAME_OVER"
    assert f.available_actions == ()


def test_refuses_an_absent_frame():
    bad = FakeFrameData([grid()])
    bad.frame = None
    with pytest.raises(FrameViolation, match="absent"):
        read_frame(bad)
