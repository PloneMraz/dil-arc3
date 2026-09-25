"""The onlooker (tag E): an Other in the world, who sees the agent act and says what it sees.

WHERE IT STANDS. Outside the agent and outside the host: in the world, beside
the region the agent acts on (`world/__init__.py`). The host does not hold it,
wrap it or call it; it hears what the onlooker says on a channel of its own, as
it sees what the region returns (Plone, 2026-09-25: "onlooker không thể ở bên
trong host"). §2: an Other is "any entity occupying the relational position
not-Self"; §8.4: reflection comes from outside, "a collision read into
coordinates by a third party ('you drifted at this point')".

WHAT IT IS. Not an agent and not a mind: a separate piece of code that judges
how the agent behaves. It plays no game and analyses no region.

WHAT IT SEES. Only the agent's acts, as they appear in the world, and the
moments in which it did not act. An act is opaque to it: two acts are the same
or they are not. It does not see the grid, the region's report, or anything in
the agent: its store, its `[event]` log, its program, its thinking. It knows no
game: no levels, no RESET, nothing a particular environment means by an act.

WHAT IT SAYS. Remarks on behaviour, neutral about any environment, each with the
moment it points at (DECIDE@IMPL tag E, declared, not measured):

  - "standing still": the agent has not acted since a moment, and `for` how
    many. It says so again each moment the agent stays still: the same fact,
    longer, as a person who nudges again.
  - "repeating": the same act `REPEAT_AT` times running;
  - "back-and-forth": two acts alternating, x y x y.

Otherwise nothing. A remark is its view, with no claim of being right: a
repetition that is getting somewhere is remarked on too, and what to make of it
is the agent's.

It returns and does not write (§8.4): it holds no handle on the agent.
"""

from __future__ import annotations

import json
from typing import Any, Final

# How many identical acts running before the onlooker says the agent is
# repeating itself. NOT MEASURED: declared as chosen.
REPEAT_AT: Final = 4
# An alternation is read over the last four acts: x y x y.
ALTERNATION: Final = 4

Act = Any  # whatever the world shows of an act; None for a moment with none


def _same(a: Act, b: Act) -> bool:
    return json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)


class Onlooker:
    """What the onlooker has seen of the agent, and what it makes of it."""

    __slots__ = ("_seen",)

    def __init__(self) -> None:
        # (moment, act) for each moment it has watched; act None: no act.
        self._seen: list[tuple[int, Act]] = []

    def saw(self, moment: int, act: Act) -> None:
        """At `moment` the agent did `act` — or nothing, when `act` is None."""
        self._seen.append((moment, act))

    def remark(self) -> dict[str, Any]:
        """What the onlooker says now."""
        still = _trailing(self._seen, lambda e: e[1] is None)
        if still:
            return {"remark": "standing still", "since": still[0][0], "for": len(still)}
        acts = _trailing(self._seen, lambda e: e[1] is not None)
        run = _repeat_run(acts)
        if len(run) >= REPEAT_AT:
            return {"remark": "repeating", "act": run[0][1], "since": run[0][0]}
        alt = _alternation_run(acts)
        if len(alt) >= ALTERNATION:
            return {"remark": "back-and-forth", "acts": [alt[0][1], alt[1][1]], "since": alt[0][0]}
        return {"remark": None}


def _trailing(seen: list, keep) -> list:
    out = []
    for entry in reversed(seen):
        if not keep(entry):
            break
        out.append(entry)
    return out[::-1]


def _repeat_run(acts: list) -> list:
    run: list = []
    for entry in reversed(acts):
        if run and not _same(entry[1], run[-1][1]):
            break
        run.append(entry)
    return run[::-1]


def _alternation_run(acts: list) -> list:
    run: list = []
    for entry in reversed(acts):
        if len(run) >= 1 and _same(entry[1], run[-1][1]):
            break
        if len(run) >= 2 and not _same(entry[1], run[-2][1]):
            break
        run.append(entry)
    return run[::-1] if len(run) >= 2 and not _same(run[0][1], run[1][1]) else []


__all__ = ["ALTERNATION", "REPEAT_AT", "Onlooker"]
