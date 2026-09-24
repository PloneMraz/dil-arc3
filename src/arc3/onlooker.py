"""B: an onlooker — an Other outside the agent, judging how it behaves (tag E).

§8.4 wants reflection to come from outside: the agent cannot see where it
drifts, so a third party says "you drifted at this point". A Kaggle session has
no person to say it. The onlooker is the third party it can have: not an agent
and not a mind — a separate piece of code that watches what the agent does and
says when it thinks the agent is stuck.

WHAT IT WATCHES, AND WHAT IT DOES NOT. Only what a spectator sees of the
agent's behaviour: the moves it commits, and whether the region's level count
moved while it made them. It does not look at the grid, does not read the
agent's store, its `[event]` log or its program, and plays no game of its own.
It judges the agent's behaviour, not the region; its lens is its own and shares
nothing with the agent's mind.

ITS STANCE, DECLARED (DECIDE@IMPL tag E; approved by Plone, 2026-09-25). Two
remarks, each with the cycle it points at:

  - "repeating": the same move `REPEAT_AT` times running, the level unchanged;
  - "back-and-forth": two moves alternating, x y x y, the level unchanged — the
    agent undoing itself.

Otherwise it says nothing. A remark is its view, with no claim of being right.

WHERE THE MISMATCH IS. The agent's standing expectation of the onlooker is what
it said last; at the start, nothing — the agent does not think it is stuck. When
the onlooker changes its stance, the expectation fails: that is a mismatch
between the agent and the onlooker, held on the datum of the remark, not the
onlooker retelling a collision the agent already recorded. While it keeps its
stance, nothing collides.

It returns and does not write (§8.4): its one channel is the signal the host
carries in, and it holds no handle on the agent.
"""

from __future__ import annotations

from typing import Any, Final

from dil.loop.cycle import HostCycleInput
from dil.loop.layers.t2 import Emission
from dil.loop.types import Signal
from dil.runtime.host_source import HostSource

from .action import RESET, IllegalMove
from .observe import ONLOOKER_CHANNEL, ONLOOKER_ENTITY, STATUS_CHANNEL, move_from_value

# How many identical moves running, the level unchanged, before the onlooker
# says the agent is repeating itself. NOT MEASURED: declared as chosen, like the
# inherited tag B thresholds, until a run gives grounds to change it.
REPEAT_AT: Final = 4
# An alternation is read over the last four moves: x y x y.
ALTERNATION: Final = 4


class Onlooker:
    """What the onlooker has seen of the agent, and what it makes of it."""

    __slots__ = ("_seen",)

    def __init__(self) -> None:
        # (cycle, move, level moved) for each move the agent made since its last RESET.
        self._seen: list[tuple[int, tuple[int, Any, Any], bool]] = []

    def saw(self, cycle: int, move: tuple[int, Any, Any], levelled: bool) -> None:
        """At `cycle` the agent committed `move`; the region's level count then
        moved (`levelled`) or did not."""
        if move[0] == RESET:
            self._seen = []
        else:
            self._seen.append((cycle, move, levelled))

    def remark(self) -> dict[str, Any]:
        """What the onlooker says now. Stable while its view is: it points at where
        the pattern began, not at how long it has run."""
        run = _repeat_run(self._seen)
        if len(run) >= REPEAT_AT:
            return {"remark": "repeating", "move": list(run[0][1]), "since": run[0][0]}
        alt = _alternation_run(self._seen)
        if len(alt) >= ALTERNATION:
            return {"remark": "back-and-forth", "moves": [list(alt[0][1]), list(alt[1][1])],
                    "since": alt[0][0]}
        return {"remark": None}


def _unlevelled_tail(seen: list) -> list:
    """The moves since the level last moved: a level reached is not being stuck."""
    tail = []
    for entry in reversed(seen):
        if entry[2]:
            break
        tail.append(entry)
    return tail[::-1]


def _repeat_run(seen: list) -> list:
    tail = _unlevelled_tail(seen)
    run = []
    for entry in reversed(tail):
        if run and entry[1] != run[-1][1]:
            break
        run.append(entry)
    return run[::-1]


def _alternation_run(seen: list) -> list:
    tail = _unlevelled_tail(seen)
    run = []
    for entry in reversed(tail):
        if len(run) >= 1 and entry[1] == run[-1][1]:
            break
        if len(run) >= 2 and entry[1] != run[-2][1]:
            break
        run.append(entry)
    return run[::-1] if len(run) >= 2 and run[0][1] != run[1][1] else []


def _levelled(host_input: HostCycleInput) -> bool:
    for signal in host_input.signals:
        if signal.source_id == STATUS_CHANNEL and isinstance(signal.raw_payload, dict):
            status = signal.raw_payload.get("status") or {}
            return (status.get("levelsDelta") or 0) != 0
    return False


class OnlookedSource:
    """The body's source, with the onlooker standing by.

    It passes every move to the body unchanged and every cycle's input back
    unchanged, adding one signal: what the onlooker says about the move just
    made. The onlooker is present every cycle, so its silence is never an
    absence.
    """

    __slots__ = ("_inner", "_onlooker", "_move", "_cycle")

    def __init__(self, inner: HostSource, onlooker: Onlooker | None = None) -> None:
        self._inner = inner
        self._onlooker = onlooker if onlooker is not None else Onlooker()
        # The move last committed, with the cycle that committed it.
        self._move: tuple[int, tuple[int, Any, Any]] | None = None
        # The cycle the next input is for; the cycle a move is committed in is
        # the one whose input came last.
        self._cycle = 0

    def next(self) -> HostCycleInput | None:
        host_input = self._inner.next()
        if host_input is None:
            return None
        if self._move is not None:
            self._onlooker.saw(*self._move, _levelled(host_input))
            self._move = None
        self._cycle += 1
        t = max((s.t for s in host_input.signals), default=0)
        said = Signal(source_id=ONLOOKER_CHANNEL, t=t,
                      raw_payload={"entity": ONLOOKER_ENTITY, **self._onlooker.remark()})
        afforded = host_input.afforded
        return HostCycleInput(
            signals=(*host_input.signals, said),
            changes=host_input.changes,
            interactions=host_input.interactions,
            afforded=None if afforded is None else afforded | {ONLOOKER_ENTITY},
        )

    def deliver(self, response: Emission) -> None:
        try:
            move = move_from_value(response.action)
            self._move = (self._cycle - 1, (move.action_id, move.x, move.y))
        except IllegalMove:
            self._move = None
        self._inner.deliver(response)


def onlooked(inner: HostSource, onlooker: Onlooker | None = None) -> OnlookedSource:
    return OnlookedSource(inner, onlooker)


__all__ = ["ALTERNATION", "REPEAT_AT", "OnlookedSource", "Onlooker", "onlooked"]
