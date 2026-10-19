"""This host's eye and body, declared for the one mind (`mind.organs`).

The eye delivers a frame as the stacks of grids the engine returned and the move
between (`observe.frame_payload`); the mind reads the last grid of each stack —
a reading declared here, as it was in the language mind: of the 159 recorded
ls20 transitions (`scripts/data/frames.pkl`), 157 came back as a single grid,
two as a stack of six — and the step carries the grids before the last, which
the region showed between: at a level's end, what the act did before the next
level came (every level ended in version 19 came as a stack of 2 to 27). A grid is rows of cells, each a colour 0-15.
The region reports its state, its level count and its stack depth
(`observe.region_status`), and what it offers next. The body carries out RESET
always, and any other act the region offers unless the game has ended
(`command.can_carry_out`); ACTION6 carries a cell.

Every value below is read from the host's own code; nothing is decided here.
"""

from __future__ import annotations

import json
from typing import Any, Final

from mind.organs import Act, AsRead, Organs, Otherwise, Step

from .action import COMPLEX_ACTION, RESET, SIMPLE_ACTIONS
from .command import can_carry_out
from .decisions import OPEN_TAG_KEYS
from .frame import TERMINAL_STATES
from .observe import FRAME_CHANNEL, FRAME_ENTITY, ONLOOKER_CHANNEL, STATUS_CHANNEL

Grid = list[list[int]]

# The fields of the region's report a model may predict (`observe.region_status`).
REPORT_FIELDS: Final = ("stateTo", "levelsDelta", "depthDelta")


def _step(payload: dict[str, Any]) -> Step | None:
    """The step a frame payload records: the last grid of each stack, and the move;
    and the grids the region returned before its last, which it showed between
    (at a level's end, the act's doing before the next level: LOG.md, 2026-10-05)."""
    try:
        move = payload["move"]
        action = int(move["actionId"])
        x, y = move.get("x"), move.get("y")
        return Step(
            before=[list(r) for r in payload["before"][-1]],
            act=(action, x, y),
            after=[list(r) for r in payload["grids"][-1]],
            through=tuple([list(r) for r in g] for g in payload["grids"][:-1]),
        )
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _expected_payload(payload: dict[str, Any], state: Grid | Otherwise) -> dict[str, Any]:
    """The frame as an expectation puts it: the grid expected in place of what came;
    or, for an expectation that it will be otherwise, the grid it was, as the mind
    reads it (None where it does not read), marked so (`decisions.situation_fit`)."""
    if isinstance(state, Otherwise):
        return {**payload, "grids": [state.state], "otherwise": True}
    if isinstance(state, AsRead):
        return {**payload, "grids": [state.state], "as_read": True}
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


def _quiet(said: dict[str, Any]) -> dict[str, Any]:
    """The onlooker with nothing to say (world/onlooker.py: `{"remark": None}`)."""
    return {"entity": said.get("entity"), "remark": None}


def _command(act: Act) -> dict[str, Any]:
    return {"kind": "move", "actionId": act[0], "x": act[1], "y": act[2]}


# An act here is (action id, x, y): x and y for ACTION6's cell, None otherwise.
def _can_carry_out(act: Act, state: str | None, offers: tuple) -> bool:
    return can_carry_out(act[0], act[1], act[2], state, offers)


def _family(act: Act) -> int:
    return act[0]


def _offered(act: Act, offers: tuple) -> bool:
    return act[0] in offers


def _read_offers(value: Any) -> tuple[int, ...]:
    return tuple(int(a) for a in value or ())


def _order(act: Act) -> tuple[int, int, int]:
    return act[0], act[1] or 0, act[2] or 0


def _record(act: Act) -> list:
    return list(act)


_NAMES: Final = {RESET: "RESET", **{a: f"ACTION{a}" for a in (*SIMPLE_ACTIONS, COMPLEX_ACTION)}}


def _named_by(said: Any) -> Act | None:
    """The act an onlooker's word names (world/onlooker.py: {"act": "ACTION6", "x", "y"})."""
    if not isinstance(said, dict):
        return None
    ids = {name: a for a, name in _NAMES.items()}
    a = ids.get(str(said.get("act", "")).upper())
    if a is None:
        return None
    return (a, said.get("x"), said.get("y")) if a == COMPLEX_ACTION else (a, None, None)


def _name_of(act: Act | None) -> str:
    if act is None:
        return "no action"
    base = _NAMES.get(act[0], f"act {act[0]}")
    return base + (f" at ({act[1]}, {act[2]})" if act[1] is not None else "")


ARC_ORGANS: Final = Organs(
    state_kind="grid: rows of cells, each a colour 0-15",
    acts=dict(_NAMES),
    placed=frozenset({COMPLEX_ACTION}),
    restart=(RESET, None, None),
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
    can_carry_out=_can_carry_out,
    command=_command,
    family=_family,
    offered=_offered,
    read_offers=_read_offers,
    order=_order,
    record=_record,
    named_by=_named_by,
    name_of=_name_of,
    tag_keys=frozenset(OPEN_TAG_KEYS),
    state_object=FRAME_ENTITY,
    channels={"step": FRAME_CHANNEL, "report": STATUS_CHANNEL, "others": ONLOOKER_CHANNEL},
    own_keys=("context",),
    quiet=_quiet,
)

__all__ = ["ARC_ORGANS", "REPORT_FIELDS"]
