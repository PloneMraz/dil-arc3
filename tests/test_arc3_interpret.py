"""Reading what became of each thing.

The load-bearing property is the first test: what happens to a thing must be the
same wherever it happens, or T5's expectation can never match and confidence
never ramps. The superseded frame-level signature had to engineer that
invariance by hand; here it falls out of having segmented first.
"""

from __future__ import annotations

from arc3.interpret import REGION_ENTITY, changes_of, change_value, region_status
from tests.test_arc3_perceive import framed, stacked
from arc3 import read_frame
from tests.test_arc3_frame import FakeFrameData, grid


def thing(r: int, c: int, value: int = 9, **kw):
    return framed({(r, c): value, (r, c + 1): value}, **kw)


# ── the property everything rests on ──


def test_the_same_move_in_two_places_reads_as_the_same_change():
    here = changes_of(thing(30, 30), thing(25, 30))["thing:9"]
    there = changes_of(thing(12, 8), thing(7, 8))["thing:9"]
    assert here == there
    assert here.moved == (-5, 0)


def test_opposite_moves_read_differently():
    up = changes_of(thing(30, 30), thing(25, 30))["thing:9"]
    down = changes_of(thing(30, 30), thing(35, 30))["thing:9"]
    assert up != down
    assert down.moved == (5, 0)


def test_the_four_directions():
    start = thing(30, 30)
    assert changes_of(start, thing(25, 30))["thing:9"].moved == (-5, 0)
    assert changes_of(start, thing(35, 30))["thing:9"].moved == (5, 0)
    assert changes_of(start, thing(30, 25))["thing:9"].moved == (0, -5)
    assert changes_of(start, thing(30, 35))["thing:9"].moved == (0, 5)


def test_nothing_moving_is_a_null_change():
    change = changes_of(thing(30, 30), thing(30, 30))["thing:9"]
    assert change.is_null
    assert change.moved == (0, 0)


def test_a_change_never_says_where_the_thing_is():
    """Position does not repeat; what the thing did does."""
    change = change_value(changes_of(thing(30, 30), thing(25, 30))["thing:9"])
    assert set(change) == {"persisted", "appeared", "vanished", "moved", "grew", "pieces", "null"}
    assert change["moved"] == [-5, 0]


# ── coming and going, which an affordance could never do ──


def test_a_thing_that_arrives_is_reported_as_appearing():
    change = changes_of(framed({}), thing(10, 10))["thing:9"]
    assert change.appeared and not change.vanished and not change.persisted
    assert change.moved is None


def test_a_thing_that_goes_is_reported_as_vanishing():
    change = changes_of(thing(10, 10), framed({}))["thing:9"]
    assert change.vanished and not change.appeared
    assert change.moved is None


def test_every_thing_on_either_side_gets_an_entry():
    """T7 has to be able to tell "gone" from "never mentioned"."""
    changes = changes_of(framed({(1, 1): 9}), framed({(1, 1): 3}))
    assert set(changes) == {"thing:9", "thing:3"}
    assert changes["thing:9"].vanished
    assert changes["thing:3"].appeared


# ── growing, splitting ──


def test_stuff_that_grows_reports_how_much():
    change = changes_of(framed({(5, 5): 9}), framed({(5, 5): 9, (5, 6): 9}))["thing:9"]
    assert change.grew == 1
    assert not change.is_null


def test_stuff_that_splits_reports_the_extra_piece():
    """Cell count alone would miss a thing breaking in two."""
    change = changes_of(
        framed({(5, 5): 9, (5, 6): 9}), framed({(5, 5): 9, (30, 30): 9})
    )["thing:9"]
    assert change.pieces == 1
    assert change.grew == 0
    assert not change.is_null


def test_stuff_spread_over_channels_is_weighed_together():
    """One kind of stuff, wherever in the stack it is seen."""
    before = stacked({(10, 10): 9}, {(20, 20): 9})
    after = stacked({(11, 10): 9}, {(21, 20): 9})
    assert changes_of(before, after)["thing:9"].moved == (1, 0)


# ── the region as an Other in its own right ──


def test_the_region_reports_its_own_status():
    before = read_frame(FakeFrameData([grid()], levels_completed=0))
    after = read_frame(FakeFrameData([grid()], levels_completed=1))
    status = region_status(before, after)
    assert status["levelsDelta"] == 1
    assert status["stateFrom"] == "NOT_FINISHED"


def test_the_region_reports_a_state_change():
    before = read_frame(FakeFrameData([grid()]))
    after = read_frame(FakeFrameData([grid()], state="GAME_OVER", actions=()))
    assert region_status(before, after)["stateTo"] == "GAME_OVER"


def test_the_region_is_not_a_thing_in_the_grid():
    assert not REGION_ENTITY.startswith("thing:")
