"""The body: what it reports inward, and what it refuses to do.

The host holds the game and executes what the self committed. It never chooses.
Every test here is written against a fake engine, because the host takes the
environment and the action class as arguments precisely so it can be.
"""

from __future__ import annotations

import pytest

from arc3.action import IllegalMove, Move
from arc3.host import Arc3Source, StepFailed, declaration
from arc3.observe import FRAME_CHANNEL, STATUS_CHANNEL, move_value
from dil.loop.layers.t2 import Emission
from dil.runtime.host_source import HostSource
from tests.test_arc3_frame import FakeFrameData, grid


class FakeGameAction:
    def __init__(self, action_id: int) -> None:
        self.value = action_id
        self.data: dict[str, int] = {}

    def set_data(self, data: dict[str, int]) -> None:
        self.data = data

    @classmethod
    def from_id(cls, action_id: int) -> "FakeGameAction":
        return cls(action_id)


class FakeEnv:
    """An engine whose frames the test controls."""

    def __init__(self, frames, opening=None) -> None:
        self._frames = list(frames)
        self._opening = opening
        self.steps: list[tuple[int, dict]] = []

    def reset(self):
        return self._opening if self._opening is not None else self._frames[0]

    def step(self, action, data=None):
        self.steps.append((action.value, data or {}))
        if not self._frames:
            return None
        return self._frames.pop(0)


def f(mark: int = 0, **kw):
    """A frame with one thing in it, placed at `mark` rows down.

    A uniform grid holds no things at all — every cell is the background — so a
    fixture without a mark would test segmentation finding nothing.
    """
    g = grid(0)
    g[mark][5] = 9
    g[mark][6] = 9
    return FakeFrameData([g], **kw)


def a_source(frames, opening=None, budget=10):
    return Arc3Source(FakeEnv(frames, opening), FakeGameAction, action_budget=budget)


def test_it_is_a_host_source():
    assert isinstance(a_source([f()]), HostSource)


# ── opening ──


def test_cycle_zero_reports_the_reset_with_a_null_effect():
    """There is no earlier frame to difference the opening against, and saying
    the agent has done nothing observable yet is accurate."""
    src = a_source([f()], opening=f())
    host_input = src.next()
    # Cycle 0 pairs the opening frame with itself, so nothing changed.
    frame, status = host_input.signals
    assert frame.source_id == FRAME_CHANNEL and status.source_id == STATUS_CHANNEL
    assert frame.raw_payload["before"] == frame.raw_payload["grids"], "the frame as taken in, unchanged"
    assert frame.raw_payload["move"]["actionId"] == 0, "the RESET that opened it"
    assert status.raw_payload["entity"] == "region"
    assert status.raw_payload["status"]["levelsDelta"] == 0


def test_an_empty_opening_frame_is_reset_until_the_game_starts():
    """MEASURED: reset() returns a populated frame for ls20 and an EMPTY one
    for vc33, which needs RESET sent as an action first."""
    env = FakeEnv([f(3)], opening=FakeFrameData([]))
    src = Arc3Source(env, FakeGameAction)
    src.next()
    assert env.steps == [(0, {})]
    assert src.frame is not None


def test_a_game_that_never_yields_a_frame_is_reported_not_waited_on():
    env = FakeEnv([FakeFrameData([])] * 5, opening=FakeFrameData([]))
    with pytest.raises(StepFailed, match="no frame after"):
        Arc3Source(env, FakeGameAction).next()


# ── acting ──


def test_deliver_executes_the_committed_move():
    src = a_source([f(3)], opening=f(0))
    src.next()
    src.deliver(Emission(action=move_value(Move(1))))
    assert src.spent == 1
    assert src.delivered == [Move(1)]


def test_a_complex_move_carries_its_coordinates_to_the_engine():
    src = a_source([f(3)], opening=f(0, actions=(6,)))
    src.next()
    src.deliver(Emission(action=move_value(Move(6, 12, 30))))
    assert src._env.steps == [(6, {"x": 12, "y": 30})]


def test_the_following_next_reports_what_the_act_did():
    """The daemon's order is next -> run -> deliver, so deliver acts and the
    FOLLOWING next reports it. That is INV-1 closing against a real region."""
    src = a_source([f(3)], opening=f(0))
    src.next()
    src.deliver(Emission(action=move_value(Move(1))))
    host_input = src.next()
    # The frame the region returned after the act, carried as it is, and the
    # region's report on itself. Nothing computed from the grid travels.
    frame, status = host_input.signals
    assert frame.raw_payload["before"] != frame.raw_payload["grids"], "the move changed the grid"
    assert frame.raw_payload["move"] == move_value(Move(1))
    assert status.raw_payload["entity"] == "region"
    assert set(frame.raw_payload) == {"entity", "before", "grids", "move", "context"}


def test_next_returns_none_when_nothing_has_happened_since_the_last_report():
    src = a_source([f()], opening=f())
    src.next()
    assert src.next() is None


# ── what it refuses ──


def test_an_unafforded_move_is_refused_not_substituted():
    """Quietly swapping in a legal action would put the choice in the body."""
    src = a_source([f()], opening=f(0, actions=(6,)))
    src.next()
    with pytest.raises(IllegalMove, match="not in available_actions"):
        src.deliver(Emission(action=move_value(Move(1))))


def test_an_emission_that_is_not_a_move_is_refused():
    """dil-core's marker reaching deliver means the policy was never declared."""
    src = a_source([f()], opening=f())
    src.next()
    with pytest.raises(IllegalMove, match="not a committed move"):
        src.deliver(Emission(action={"kind": "respond", "cycle": 0, "valence": 0.0}))


def test_an_engine_that_returns_nothing_is_reported():
    src = a_source([], opening=f())
    src.next()
    with pytest.raises(StepFailed, match="returned nothing"):
        src.deliver(Emission(action=move_value(Move(1))))


# ── the budget RHAE charges for ──


def test_the_action_budget_stops_the_run():
    src = a_source([f(3), f(4), f(5)], opening=f(0), budget=2)
    src.next()
    src.deliver(Emission(action=move_value(Move(1))))
    src.next()
    src.deliver(Emission(action=move_value(Move(1))))
    assert src.spent == 2
    assert src.next() is None


# ── the declaration the gate reads ──


def test_the_declaration_states_what_this_host_actually_does():
    d = declaration("ls20")
    assert d.boundary.present
    assert [c.id for c in d.channels] == [FRAME_CHANNEL, STATUS_CHANNEL]
    assert d.channels[0].can_return
    assert d.emitter.can_emit_first_action
    assert d.trace.externally_readable
    # Wiping on mismatch would destroy the accrual INV-5 rests on.
    assert not d.resilience.wipes_state_on_mismatch
