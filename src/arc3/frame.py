"""Reading an ARC-AGI-3 frame into something the loop may touch.

This is the host's sense organ, and it is deliberately a **gate**, not a
converter. §5's tagging gate refuses a datum that arrives without provenance; the
same stance applies at the boundary of the body: a frame that falls outside the
declaration in `decisions.py` is refused, not coerced. Silently clamping an
out-of-range cell would make the declaration a comment rather than a claim.

It takes a duck-typed object, not `arcengine.FrameData`, so the agent's own
boundary stays testable with the game uninstalled — and because the engine has
TWO frame types: `FrameData.frame` is `list[list[list[int]]]` while
`FrameDataRaw.frame` is `List[ndarray]`. Both are sequences of rows of ints, so
reading by iteration handles both; reading by type annotation would handle one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from .decisions import CELL_MAX, CELL_MIN, GRID_COLS, GRID_ROWS

Grid = tuple[tuple[int, ...], ...]


class FrameViolation(Exception):
    """A frame arrived outside the declared ActivityEnvironment (tag A)."""


@dataclass(frozen=True, slots=True)
class Frame:
    """One observation, as the host is willing to hand it inward.

    `grids` is a stack of 1..N grids, not one grid — the shape measured on real
    frames, and the part the documentation does not say.
    """

    game_id: str
    grids: tuple[Grid, ...]
    state: str
    available_actions: tuple[int, ...]
    levels_completed: int
    win_levels: int

    @property
    def depth(self) -> int:
        return len(self.grids)

    @property
    def top(self) -> Grid:
        """The last grid in the stack.

        WHICH grid of the stack is "the" current view is NOT settled here. This
        accessor exists for probes and reporting, and nothing in the loop may
        depend on it until the stack's meaning is decided.
        """
        return self.grids[-1]


# The engine's terminal and non-terminal states, by name. Reading the name rather
# than the enum keeps this module free of the SDK.
LIVE_STATES: Final = frozenset({"NOT_PLAYED", "NOT_FINISHED"})
TERMINAL_STATES: Final = frozenset({"WIN", "GAME_OVER"})


def _read_grid(raw: Any, where: str) -> Grid:
    try:
        rows = tuple(tuple(int(cell) for cell in row) for row in raw)
    except (TypeError, ValueError) as exc:
        raise FrameViolation(f"{where}: not a grid of integers ({exc})") from exc

    if len(rows) != GRID_ROWS:
        raise FrameViolation(f"{where}: {len(rows)} rows, declared {GRID_ROWS}")
    for i, row in enumerate(rows):
        if len(row) != GRID_COLS:
            raise FrameViolation(f"{where} row {i}: {len(row)} cols, declared {GRID_COLS}")
        for cell in row:
            if not CELL_MIN <= cell <= CELL_MAX:
                raise FrameViolation(
                    f"{where} row {i}: cell {cell} outside declared {CELL_MIN}-{CELL_MAX}"
                )
    return rows


def read_frame(raw: Any) -> Frame:
    """Read an engine frame, refusing anything the declaration does not cover.

    Raises `FrameViolation` rather than repairing. If this fires in a real run it
    is news: the declaration is wrong and must be re-measured, which is exactly
    what §12 asks a DECIDE@IMPL tag to expose.
    """
    game_id = str(getattr(raw, "game_id", "") or "")
    stack = getattr(raw, "frame", None)
    if stack is None:
        raise FrameViolation("frame: absent")

    grids = tuple(
        _read_grid(g, f"grid {i}") for i, g in enumerate(stack)
    )
    if not grids:
        raise FrameViolation(
            "frame: empty stack — the engine returns this before RESET; the host "
            "must not pass it inward as an observation"
        )

    state_raw = getattr(raw, "state", None)
    state = getattr(state_raw, "name", None) or str(state_raw)
    if state not in LIVE_STATES and state not in TERMINAL_STATES:
        raise FrameViolation(f"state: unknown {state!r}")

    actions = tuple(sorted({int(a) for a in getattr(raw, "available_actions", ()) or ()}))
    if state in LIVE_STATES and not actions:
        raise FrameViolation(
            f"available_actions: empty while state is {state} — nothing is affordable"
        )

    return Frame(
        game_id=game_id,
        grids=grids,
        state=state,
        available_actions=actions,
        # There is NO `score` field on the engine's frame. RHAE counts actions
        # against a human baseline per level, and the level counter is this.
        levels_completed=int(getattr(raw, "levels_completed", 0) or 0),
        win_levels=int(getattr(raw, "win_levels", 0) or 0),
    )
