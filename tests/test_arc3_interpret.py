"""The shapes an observation is reported in.

What becomes of a thing is read by `seeing.py`; these are the forms that reading
takes, and the region's report of itself.
"""

from __future__ import annotations

import json

from arc3 import read_frame
from arc3.interpret import REGION_ENTITY, ThingChange, change_value, region_status
from tests.test_arc3_frame import FakeFrameData, grid


def test_a_held_still_thing_is_a_null_change():
    change = ThingChange(persisted=True, appeared=False, vanished=False,
                         moved=(0, 0), grew=0, pieces=0)
    assert change.is_null


def test_any_movement_growth_or_split_is_not_null():
    base = dict(persisted=True, appeared=False, vanished=False, moved=(0, 0), grew=0, pieces=0)
    assert not ThingChange(**{**base, "moved": (-5, 0)}).is_null
    assert not ThingChange(**{**base, "grew": 1}).is_null
    assert not ThingChange(**{**base, "pieces": 1}).is_null


def test_a_change_never_says_where_the_thing_is():
    """Position does not repeat; what the thing did does."""
    value = change_value(ThingChange(persisted=True, appeared=False, vanished=False,
                                     moved=(-5, 0), grew=0, pieces=0))
    assert set(value) == {"persisted", "appeared", "vanished", "moved", "grew", "pieces", "null"}
    assert value["moved"] == [-5, 0]


def test_a_change_is_json_shaped_so_t5_can_compare_it():
    value = change_value(ThingChange(persisted=False, appeared=True, vanished=False,
                                     moved=None, grew=2, pieces=1))
    assert json.loads(json.dumps(value)) == value


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
