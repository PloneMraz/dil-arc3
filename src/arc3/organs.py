"""This host's eye and body, declared for the one mind (`mind.organs`).

The eye delivers a frame as the stacks of grids the engine returned and the move
between (`observe.frame_payload`); the mind reads the last grid of each stack —
a reading declared here, as it was in the language mind: of 159 recorded ls20
transitions, 157 were single grids. A grid is rows of cells, each a colour 0-15.
The region reports its state, its level count and its stack depth
(`observe.region_status`), and what it offers next. The body carries out RESET
always, and any other act the region offers unless the game has ended
(`command.can_carry_out`); ACTION6 carries a cell.

Every value below is read from the host's own code; nothing is decided here.
"""

from __future__ import annotations

import json
from typing import Any, Final

from mind.organs import Act, Organs, Step

from .action import COMPLEX_ACTION, RESET, SIMPLE_ACTIONS
from .command import can_carry_out
from .decisions import OPEN_TAG_KEYS
from .frame import TERMINAL_STATES
from .observe import FRAME_CHANNEL, ONLOOKER_CHANNEL, STATUS_CHANNEL

Grid = list[list[int]]

# The fields of the region's report a model may predict (`observe.region_status`).
REPORT_FIELDS: Final = ("stateTo", "levelsDelta", "depthDelta")


def _step(payload: dict[str, Any]) -> Step | None:
    """The step a frame payload records: the last grid of each stack, and the move."""
    try:
        move = payload["move"]
        action = int(move["actionId"])
        x, y = move.get("x"), move.get("y")
        return Step(
            before=[list(r) for r in payload["before"][-1]],
            act=(action, x, y),
            after=[list(r) for r in payload["grids"][-1]],
        )
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _expected_payload(payload: dict[str, Any], state: Grid) -> dict[str, Any]:
    """The frame as an expectation puts it: the grid expected in place of what came."""
    return {**payload, "grids": [state]}


def _overlay(grid: Grid, cells: dict[tuple[int, int], int] | None) -> Grid:
    out = [row[:] for row in grid]
    for (r, c), v in (cells or {}).items():
        if r < len(out) and c < len(out[r]):
            out[r][c] = v
    return out


def _missed(cells: dict[tuple[int, int], int], got: Grid) -> str:
    return json.dumps({f"{r},{c}": [v, got[r][c]] for (r, c), v in cells.items()
                       if r < len(got) and c < len(got[r]) and got[r][c] != v})


def _unchanged(status: dict[str, Any]) -> dict[str, Any]:
    """The report as it would read had nothing changed."""
    return {**status, "stateTo": status.get("stateFrom"), "levelsDelta": 0, "depthDelta": 0}


def _command(act: Act) -> dict[str, Any]:
    return {"kind": "move", "actionId": act[0], "x": act[1], "y": act[2]}


ARC_ORGANS: Final = Organs(
    state_kind="grid: rows of cells, each a colour 0-15",
    acts={RESET: "RESET", **{a: f"ACTION{a}" for a in (*SIMPLE_ACTIONS, COMPLEX_ACTION)}},
    placed=frozenset({COMPLEX_ACTION}),
    reset=(RESET, None, None),
    step=_step,
    expected_payload=_expected_payload,
    overlay=_overlay,
    missed=_missed,
    report_key="status",
    report_fields=REPORT_FIELDS,
    unchanged=_unchanged,
    state_field="stateTo",
    ended=frozenset(TERMINAL_STATES),
    offers_key="affords",
    can_carry_out=can_carry_out,
    command=_command,
    tag_keys=frozenset(OPEN_TAG_KEYS),
    channels={"frame": FRAME_CHANNEL, "report": STATUS_CHANNEL, "others": ONLOOKER_CHANNEL},
    own_keys=("context",),
)

__all__ = ["ARC_ORGANS", "REPORT_FIELDS"]
