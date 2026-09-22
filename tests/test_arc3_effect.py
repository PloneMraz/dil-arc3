"""The effect signature, and the one property everything rests on.

If the same control used at two different places does not produce the SAME
signature, T5's persistence rule never matches, confidence never ramps, and the
agent cannot learn its own controls. That property is the first test here, and
it is not a detail.
"""

from __future__ import annotations

from arc3 import GRID_COLS, GRID_ROWS, read_frame
from arc3.effect import Effect, diff
from tests.test_arc3_frame import FakeFrameData, grid


def framed(cells: dict[tuple[int, int], int], **kw):
    """A frame of zeros with `cells` painted in."""
    g = grid(0)
    for (r, c), v in cells.items():
        g[r][c] = v
    return read_frame(FakeFrameData([g], **kw))


def marker(r: int, c: int, value: int = 9):
    return {(r, c): value, (r, c + 1): value}


# ── translation invariance: the load-bearing property ──


def test_the_same_move_from_two_places_gives_the_same_effect():
    up_here = diff(framed(marker(30, 30)), framed(marker(25, 30)))
    up_there = diff(framed(marker(12, 8)), framed(marker(7, 8)))
    assert up_here == up_there
    assert (9, -5, 0) in up_here.displacements


def test_the_background_mirrors_a_move_and_that_is_expected():
    """When an object moves into background, the hole it leaves moves too.

    The mirrored entry is redundant, not wrong, and it is consistent — so
    translation invariance survives it. On real ls20 frames it does not appear:
    enough else changes each step that the background fails the rigidity test.
    Documented rather than special-cased, because deciding which value "is" the
    background is a judgement that can misfire.
    """
    e = diff(framed(marker(30, 30)), framed(marker(25, 30)))
    assert e.displacements == ((0, 5, 0), (9, -5, 0))


def test_opposite_moves_give_different_effects():
    up = diff(framed(marker(30, 30)), framed(marker(25, 30)))
    down = diff(framed(marker(30, 30)), framed(marker(35, 30)))
    assert up != down
    assert (9, 5, 0) in down.displacements


def test_the_four_directions_measured_in_ls20():
    """The displacements the representation recovered from real ls20 frames."""
    start = framed(marker(30, 30))
    assert (9, -5, 0) in diff(start, framed(marker(25, 30))).displacements
    assert (9, 5, 0) in diff(start, framed(marker(35, 30))).displacements
    assert (9, 0, -5) in diff(start, framed(marker(30, 25))).displacements
    assert (9, 0, 5) in diff(start, framed(marker(30, 35))).displacements


# ── rigidity: the filter that cut 33 signatures to 10 ──


def test_a_value_that_grows_claims_no_displacement():
    """A spreading trail is not a moving object; its centroid is noise."""
    e = diff(
        framed({(10, 10): 3}),
        framed({(10, 11): 3, (10, 12): 3, (10, 13): 3}),
    )
    assert e.displacements == ()
    assert e.cells_changed == 4


def test_a_rigid_value_still_displaces_when_a_noisy_one_is_present():
    """The filter must drop the noise without dropping the signal."""
    before = framed({(30, 30): 9, (30, 31): 9, (5, 5): 3})
    after = framed({(25, 30): 9, (25, 31): 9, (5, 6): 3, (5, 7): 3})
    d = diff(before, after).displacements
    assert (9, -5, 0) in d
    assert not any(v == 3 for v, _, _ in d)


# ── the rest of the channel ──


def test_nothing_changing_reads_as_null():
    """A blocked move. An affordance that reliably does nothing is still a fact."""
    e = diff(framed(marker(30, 30)), framed(marker(30, 30)))
    assert e.is_null
    assert e.cells_changed == 0
    assert e.displacements == ()


def test_a_blocked_move_is_indistinguishable_by_direction():
    """Measured in ls20: one signature shared by all four actions. Correct."""
    blocked_up = diff(framed(marker(0, 30)), framed(marker(0, 30)))
    blocked_left = diff(framed(marker(30, 0)), framed(marker(30, 0)))
    assert blocked_up == blocked_left


def test_transitions_record_which_values_became_which():
    e = diff(framed({(1, 1): 11}), framed({(1, 1): 3}))
    assert e.transitions == ((11, 3, 1),)


def test_a_completed_level_shows_in_levels_delta():
    before = read_frame(FakeFrameData([grid()], levels_completed=0))
    after = read_frame(FakeFrameData([grid()], levels_completed=1))
    e = diff(before, after)
    assert e.levels_delta == 1
    assert not e.is_null


def test_a_state_change_shows_and_is_not_null():
    before = read_frame(FakeFrameData([grid()]))
    after = read_frame(FakeFrameData([grid()], state="GAME_OVER", actions=()))
    e = diff(before, after)
    assert (e.state_from, e.state_to) == ("NOT_FINISHED", "GAME_OVER")
    assert not e.is_null


def test_a_stack_that_grows_reports_depth_delta():
    before = read_frame(FakeFrameData([grid()]))
    after = read_frame(FakeFrameData([grid(), grid()]))
    e = diff(before, after)
    assert e.depth_delta == 1
    assert not e.is_null


def test_effects_are_hashable_so_they_can_be_counted():
    """T5 compares effects for equality; a Counter over them is how stability
    was measured in the first place."""
    a = diff(framed(marker(30, 30)), framed(marker(25, 30)))
    b = diff(framed(marker(9, 9)), framed(marker(4, 9)))
    assert len({a, b}) == 1
    assert isinstance(a, Effect)


def test_the_grid_is_compared_over_its_whole_declared_size():
    """A change in the last cell must not be missed."""
    after = framed({(GRID_ROWS - 1, GRID_COLS - 1): 7})
    e = diff(framed({}), after)
    assert e.cells_changed == 1
