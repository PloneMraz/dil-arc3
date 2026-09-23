"""Reading what happened to each thing — the model's second act of interpretation.

`perceive.py` finds the things; this reads what became of them. Both are
interpretation and both belong to the thinking side. The host carries signals;
it does not conclude.

WHAT CHANGED FROM THE EARLIER BUILD. `effect.py` computed one signature for the
WHOLE frame — how many cells changed, which values turned into which, what
displaced — and the host handed that finished reading to the loop as though it
were a sensation. It also had to be translation-invariant by hand, because it was
describing an unsegmented grid and had no idea what a thing was.

Segmenting first makes most of that unnecessary. A thing's displacement is just
the difference between where it was and where it is; nothing has to be recovered
from a soup of cell transitions, and nothing has to be filtered for rigidity,
because a thing is already a thing.

WHAT AN OBSERVATION ABOUT A THING HAS TO BE. It has to REPEAT, or T5's expectation
can never match and confidence never ramps. Absolute position does not repeat.
What repeats is the CHANGE: a thing that moves five rows up moves five rows up
wherever it started. So what travels inward is what became of the thing, never
where it is — which is the same lesson the frame-level signature had to learn the
hard way, arrived at here for free.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .frame import Frame
from .perceive import Region, segment

# The region's own status, as an Other in its own right. The game reports its
# state and its level counter; the agent does not control either, and both can
# contradict an expectation. It is not a thing in the grid, so it gets its own id.
REGION_ENTITY: Final = "region"


@dataclass(frozen=True, slots=True)
class ThingChange:
    """What became of one kind of stuff between two frames.

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
    # Change in how many cells the stuff occupies. Growth, shrinkage, or 0.
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


def _by_kind(regions: tuple[Region, ...]) -> dict[str, list[Region]]:
    out: dict[str, list[Region]] = {}
    for region in regions:
        out.setdefault(region.kind, []).append(region)
    return out


def _centroid_of(regions: list[Region]) -> tuple[float, float]:
    """The centre of mass of all the stuff of one kind, weighted by size."""
    total = sum(r.size for r in regions)
    return (
        sum(r.centroid[0] * r.size for r in regions) / total,
        sum(r.centroid[1] * r.size for r in regions) / total,
    )


def changes_of(prev: Frame, now: Frame) -> dict[str, ThingChange]:
    """What became of each kind of stuff, between two frames.

    Every kind seen on either side gets an entry, so a thing that vanished is
    reported as vanished rather than silently dropped — T7 needs to be able to
    tell "gone" from "never mentioned".
    """
    before = _by_kind(segment(prev))
    after = _by_kind(segment(now))

    out: dict[str, ThingChange] = {}
    for kind in before.keys() | after.keys():
        was, is_ = before.get(kind), after.get(kind)
        if was and is_:
            br, bc = _centroid_of(was)
            ar, ac = _centroid_of(is_)
            out[kind] = ThingChange(
                persisted=True,
                appeared=False,
                vanished=False,
                moved=(round(ar - br), round(ac - bc)),
                grew=sum(r.size for r in is_) - sum(r.size for r in was),
                pieces=len(is_) - len(was),
            )
        else:
            out[kind] = ThingChange(
                persisted=False,
                appeared=is_ is not None,
                vanished=was is not None,
                moved=None,
                grew=(sum(r.size for r in is_) if is_ else 0)
                - (sum(r.size for r in was) if was else 0),
                pieces=(len(is_) if is_ else 0) - (len(was) if was else 0),
            )
    return out


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
