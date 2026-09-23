"""What an observation about a thing, or about the region, is made of.

The shapes a change is reported in. The reading itself — which piece is which,
which pieces are one thing, what became of each — is `seeing.py`'s, because it
needs memory across frames. What is left here is what that reading produces.

WHAT AN OBSERVATION ABOUT A THING HAS TO BE. It has to REPEAT, or T5's expectation
can never match and confidence never ramps. Absolute position does not repeat.
What repeats is the CHANGE: a thing that moves five rows up moves five rows up
wherever it started. So what travels inward is what became of the thing, never
where it is.

WHAT WENT. An earlier version read changes per kind of stuff — every cell of one
value as one Other — through `changes_of`, `contacts` and `interactions_of`. The
stuff-level reading is superseded by tracked individuals grouped by common fate
(`seeing.py`), for a measured reason: value 9 in `ls20` is five pieces, one of
which moves, and any reading of the stuff was swamped by the four that do not.
Nothing in production called the stuff-level functions once `seeing.py`
existed, so they were removed rather than left to be mistaken for what runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .frame import Frame

# The region's own status, as an Other in its own right. The game reports its
# state and its level counter; the agent does not control either, and both can
# contradict an expectation. It is not a thing in the grid, so it gets its own id.
REGION_ENTITY: Final = "region"


@dataclass(frozen=True, slots=True)
class ThingChange:
    """What became of one thing between two frames.

    Every field is a difference or a flag. Nothing here says where anything is,
    because where a thing is does not repeat and what it did does.
    """

    # It was there before and is there now.
    persisted: bool
    # It was not there before and is now, or the reverse.
    appeared: bool
    vanished: bool
    # How far its centre of mass moved, rounded to whole cells. (0, 0) when it
    # held still; None when it was not there on both sides to be compared.
    moved: tuple[int, int] | None
    # Change in how many cells it occupies. Growth, shrinkage, or 0.
    grew: int
    # Change in how many separate pieces it is in. A thing splitting in two is
    # something happening, and cell count alone would miss it.
    pieces: int

    @property
    def is_null(self) -> bool:
        """Nothing observable happened to this thing."""
        return (
            self.persisted
            and self.moved == (0, 0)
            and self.grew == 0
            and self.pieces == 0
        )


def change_value(change: ThingChange) -> dict[str, object]:
    """A ThingChange as plain data.

    T5 compares expectations with `json.dumps(sort_keys=True)`, so this has to be
    JSON-shaped: lists rather than tuples, and no dataclass anywhere, or two
    structurally identical changes could still differ by repr.
    """
    return {
        "persisted": change.persisted,
        "appeared": change.appeared,
        "vanished": change.vanished,
        "moved": list(change.moved) if change.moved is not None else None,
        "grew": change.grew,
        "pieces": change.pieces,
        "null": change.is_null,
    }


def region_status(prev: Frame, now: Frame) -> dict[str, object]:
    """What the region itself reported, as its own observation.

    The game's state and level counter are the region speaking about itself. The
    agent does not control either, so they belong to an Other — this one — rather
    than to any thing in the grid.
    """
    return {
        "stateFrom": prev.state,
        "stateTo": now.state,
        "levelsDelta": now.levels_completed - prev.levels_completed,
        "depthDelta": now.depth - prev.depth,
    }
