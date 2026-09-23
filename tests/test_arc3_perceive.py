"""Seeing things: the model's first act of interpretation.

The host carries the signal; the model reads it. These tests are about what is
found in a grid, and about the one property everything above T4 depends on — that
a thing stays the same thing while it persists.
"""

from __future__ import annotations

from arc3.perceive import (
    MIN_REGION_CELLS,
    Region,
    background_of,
    segment,
    segment_grid,
)
from tests.test_arc3_frame import FakeFrameData, grid
from arc3 import read_frame


def framed(cells: dict[tuple[int, int], int], fill: int = 0, **kw):
    g = grid(fill)
    for (r, c), v in cells.items():
        g[r][c] = v
    return read_frame(FakeFrameData([g], **kw))


def stacked(*layers: dict[tuple[int, int], int]):
    grids = []
    for cells in layers:
        g = grid(0)
        for (r, c), v in cells.items():
            g[r][c] = v
        grids.append(g)
    return read_frame(FakeFrameData(grids))


# ── the background is read, not assumed ──


def test_the_background_is_whatever_the_grid_is_mostly_made_of():
    assert background_of(tuple(tuple(row) for row in grid(7))) == 7


def test_a_world_on_a_non_zero_background_still_reads():
    """A hard-coded zero would see the whole grid as one enormous thing."""
    regions = segment(framed({(10, 10): 3}, fill=7))
    assert [r.value for r in regions] == [3]


# ── things ──


def test_a_run_of_one_value_is_one_thing():
    regions = segment(framed({(5, 5): 9, (5, 6): 9, (5, 7): 9}))
    assert len(regions) == 1
    assert regions[0].size == 3


def test_two_separated_runs_are_two_regions():
    regions = segment(framed({(5, 5): 9, (30, 30): 9}))
    assert len(regions) == 2


def test_things_are_held_together_by_edges_and_not_corners():
    """Four-connectivity, declared: touching at a point is not being joined."""
    regions = segment(framed({(5, 5): 9, (6, 6): 9}))
    assert len(regions) == 2


def test_different_values_touching_are_different_things():
    regions = segment(framed({(5, 5): 9, (5, 6): 3}))
    assert sorted(r.value for r in regions) == [3, 9]


def test_a_region_reports_where_it_is_and_how_big():
    region = segment(framed({(4, 6): 9, (4, 7): 9}))[0]
    assert region.size == 2
    assert region.centroid == (4.0, 6.5)
    assert region.bbox == (4, 6, 4, 7)
    assert (region.height, region.width) == (1, 2)


def test_every_channel_of_the_stack_is_looked_at():
    """The stack is several channels, not one picture."""
    regions = segment(stacked({(5, 5): 9}, {(20, 20): 3}))
    assert sorted((r.channel, r.value) for r in regions) == [(0, 9), (1, 3)]


# ── what a piece carries forward ──
#
# Identity is not decided here: which thing a piece belongs to, and whether it is
# the same thing as a piece in another frame, needs memory and is `seeing.py`'s.


def test_a_region_keeps_its_own_cells():
    """Tracking a piece and reading what lies ahead of it both need to know
    which cells are its own."""
    region = segment(framed({(4, 6): 9, (4, 7): 9}))[0]
    assert sorted(region.cells) == [(4, 6), (4, 7)]


def test_cells_do_not_decide_whether_two_regions_are_the_same():
    """A region is the same region by what it is, not by an enumeration of
    where — the cells are carried but excluded from equality."""
    a = segment(framed({(4, 6): 9, (4, 7): 9}))[0]
    b = segment(framed({(4, 6): 9, (4, 7): 9}))[0]
    assert a == b


# ── what it does not see ──


def test_a_grid_of_only_background_holds_no_things():
    assert segment(framed({})) == ()


def test_the_minimum_region_size_is_declared():
    assert MIN_REGION_CELLS >= 1
    assert isinstance(segment(framed({(1, 1): 4}))[0], Region)
