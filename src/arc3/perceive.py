"""Seeing things — the model's first act of interpretation.

A signal is not a thing. The region returns a grid of numbers; which of those
numbers belong to the same persisting *something* is not given, and working it
out is interpretation, not sensing. This module is where that happens, and it
belongs to the thinking side: the host carries the signal, the model reads it.

WHAT WENT WRONG BEFORE, so it is not repeated. The host used to hand the loop an
already-finished interpretation — "the thing of value 9 moved up five" — while
the model reached past the loop into the raw grid to decide for itself what was
worth looking at. Both roles were inverted: the body was concluding and the mind
was sensing. Worse, the model chose to look only at the square a move would land
on, which collapsed a 64x64 world into **nine** distinct situations; measured, it
exhausted them in fifteen cycles and the field went flat for ever after.

WHAT AN ENTITY IS, per §8.4: "an other-entity the agent does not control", and
§6.3 puts the layers that live off it — T6's OtherModel, T8's RelValue and
SocialEdge — above T4. An entity is therefore an *Other*: something in the
region that persists, returns, and can resist. It is not the self (T2 already
drew that line) and it is not an action the agent can take.

The earlier build made an entity out of each available ACTION. That passes T4
and T5 and starves everything above: measured over a real run, T8 produced
**zero** RelValues and **zero** SocialEdges across every cycle, because there was
never more than one "Other" present and two buttons interacting with each other
without the agent is not a thing that can happen.

SEGMENTATION, and its declared limits. Things are found as connected runs of one
value, four-connected, excluding whatever value the grid is mostly made of. That
is the cheapest reading that finds objects at all, and it is a reading: it will
merge two touching things of the same colour, and split one thing drawn in two
colours. Those are real failure modes, not hypotheticals, and no attempt is made
here to hide them.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from typing import Final

from .frame import Frame, Grid

# Four-connectivity: a thing is held together by edges, not corners. Declared,
# and the cheaper of the two readings — eight-connectivity would join things that
# merely touch at a point.
NEIGHBOURS: Final = ((-1, 0), (1, 0), (0, -1), (0, 1))

# Regions smaller than this are not treated as things. One stray cell is more
# often noise in the rendering than an object; two is the smallest run that can
# have an orientation.
MIN_REGION_CELLS: Final = 1


@dataclass(frozen=True, slots=True)
class Region:
    """One connected run of a single value — a candidate thing."""

    value: int
    # Which grid of the stack it was found in. The stack is several channels,
    # not one picture, so a thing belongs to the channel it was seen on.
    channel: int
    size: int
    # Centre of mass, in (row, col). Carried as a float pair so a one-cell move
    # of a large thing is still visible.
    centroid: tuple[float, float]
    # (min_row, min_col, max_row, max_col) — extent, from which shape follows.
    bbox: tuple[int, int, int, int]

    @property
    def height(self) -> int:
        return self.bbox[2] - self.bbox[0] + 1

    @property
    def width(self) -> int:
        return self.bbox[3] - self.bbox[1] + 1

    @property
    def kind(self) -> str:
        """The identity a thing keeps while it persists.

        MEASURED, not argued. Four readings were tried against 60 real frames
        per game, scored by churn — how many identities exist overall against how
        many are present in any one frame. An identity that changes when the
        thing changes is not an identity:

            identity          overall  per-frame  churn   ls20
            value + bbox          101       16.3   6.2x
            value + size          101       16.3   6.2x
            value                   8        8.0   1.0x   <- chosen
            value + channel        16        8.0   2.0x

        Value alone holds at 1.0x in BOTH games: every identity present in every
        frame, nothing appearing or vanishing because a shape shifted. Extent and
        cell-count both fail, and they fail hard — a thing that changes shape
        becomes a different thing six to ten times over.

        Channel was tried and rejected on the same evidence: `ls20`'s stack depth
        varies, so binding identity to a channel makes the same stuff read as two
        things. DECLARED: the same value on different channels is the same stuff.

        DECLARED LIMIT, and it is a real one. This is a kind of STUFF, not an
        individual: every cell of value 9 is one Other, however many separate
        objects they form. Telling individuals apart needs matching across
        frames, which is a further interpretation and is not done here. What this
        does buy is what the affordance reading could never buy — six to eight
        Others present at once, so T8 finally has the N >= 2 it needs.
        """
        return f"thing:{self.value}"


def background_of(grid: Grid) -> int:
    """Whatever the grid is mostly made of.

    Not a declared constant: the region says what its own background is, by
    being mostly that. A world whose background changes is still read correctly,
    which a hard-coded zero would not be.
    """
    counts: Counter[int] = Counter()
    for row in grid:
        counts.update(row)
    return counts.most_common(1)[0][0]


def segment_grid(grid: Grid, channel: int = 0) -> tuple[Region, ...]:
    """Find the things in one grid."""
    background = background_of(grid)
    rows, cols = len(grid), len(grid[0]) if grid else 0
    seen = [[False] * cols for _ in range(rows)]
    regions: list[Region] = []

    for r0 in range(rows):
        for c0 in range(cols):
            if seen[r0][c0]:
                continue
            value = grid[r0][c0]
            seen[r0][c0] = True
            if value == background:
                continue

            cells: list[tuple[int, int]] = []
            queue = deque([(r0, c0)])
            while queue:
                r, c = queue.popleft()
                cells.append((r, c))
                for dr, dc in NEIGHBOURS:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols and not seen[nr][nc]:
                        if grid[nr][nc] == value:
                            seen[nr][nc] = True
                            queue.append((nr, nc))

            if len(cells) < MIN_REGION_CELLS:
                continue
            rs = [r for r, _ in cells]
            cs = [c for _, c in cells]
            regions.append(
                Region(
                    value=value,
                    channel=channel,
                    size=len(cells),
                    centroid=(sum(rs) / len(cells), sum(cs) / len(cells)),
                    bbox=(min(rs), min(cs), max(rs), max(cs)),
                )
            )
    return tuple(regions)


def segment(frame: Frame) -> tuple[Region, ...]:
    """Find the things in a frame, across every channel of its stack."""
    return tuple(
        region
        for channel, grid in enumerate(frame.grids)
        for region in segment_grid(grid, channel)
    )
