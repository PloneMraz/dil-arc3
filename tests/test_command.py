"""The host's effectors carry out the mind's command at link 5, and weighs nothing (`arc3/command.py`)."""

from __future__ import annotations

from types import SimpleNamespace

from arc3.command import WAIT, carry_out
from arc3.observe import STATUS_CHANNEL
from dil.loop.types import Signal


def test_the_body_carries_out_what_it_can_and_otherwise_stands_still():
    def ctx(tests, affords=(1, 2, 3), state="NOT_FINISHED", cycle=5):
        sig = Signal(source_id=STATUS_CHANNEL, t=1, raw_payload={
            "entity": "region", "status": {"stateFrom": "NOT_FINISHED", "stateTo": state,
                                           "levelsDelta": 0, "depthDelta": 0},
            "context": "action:1", "affords": list(affords)})
        return SimpleNamespace(cycle=cycle, tests=tuple(tests), host=SimpleNamespace(signals=(sig,)))

    move = lambda a, x=None, y=None: {"kind": "move", "actionId": a, "x": x, "y": y}  # noqa: E731
    assert carry_out(ctx([move(3)]))["actionId"] == 3, "as commanded"
    assert carry_out(ctx([])) == WAIT, "no command: it waits"
    assert carry_out(ctx([], cycle=0))["actionId"] == 0, "cycle 0: start-up is the host's (§4)"
    assert carry_out(ctx([move(4)])) == WAIT, "not afforded: it does not substitute, it waits"
    assert carry_out(ctx([move(0)], affords=()))["actionId"] == 0, "RESET is always open"
    assert carry_out(ctx([move(1)], state="GAME_OVER")) == WAIT, "a terminal frame takes only RESET"
    click = carry_out(ctx([move(6, 5, 9)], affords=(6,)))
    assert (click["actionId"], click["x"], click["y"]) == (6, 5, 9), "the cell it was given"
