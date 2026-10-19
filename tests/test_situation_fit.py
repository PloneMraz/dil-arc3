"""Tag H, `situation_fit`: what a frame is expected to be, and what bears it out.

An expectation that the region will be otherwise (`otherwise`) fits when the grid
returned differs from the one it was, where the mind reads; one expected as the
mind reads it (`as_read`) fits when every cell it reads is as expected. A grid
that is no grid — none, or empty — on either side bears nothing out (2026-10-19:
an empty return had fitted an expectation that the region would be otherwise).
"""

from arc3.decisions import situation_fit
from dil.loop.types import InfoUnit, RefFrame

FRAME = RefFrame(bound_layer=3, ref="channel:frame")
GRID = [[1, 0], [0, 0]]


def came(*grids) -> InfoUnit:
    return InfoUnit(content={"infoType": "raw", "channel": "frame",
                             "value": {"entity": "frame", "grids": list(grids)}}, ref_frame=FRAME, t=1)


def expected(kind: str, grid) -> InfoUnit:
    return InfoUnit(content={"infoType": "raw", "channel": "frame",
                             "value": {"entity": "frame", "grids": [grid], kind: True}}, ref_frame=FRAME, t=1)


def test_otherwise_fits_where_the_grid_returned_differs_and_not_where_it_is_the_same():
    assert situation_fit(came([[0, 1], [0, 0]]), expected("otherwise", GRID)) is True
    assert situation_fit(came(GRID), expected("otherwise", GRID)) is False, "silence: a mismatch"


def test_otherwise_reads_no_cell_it_does_not_read():
    assert situation_fit(came([[1, 0], [0, 9]]), expected("otherwise", [[1, 0], [0, None]])) is False, \
        "only a cell it does not read changed"


def test_otherwise_with_nothing_returned_or_nothing_expected_does_not_fit():
    assert situation_fit(came(), expected("otherwise", GRID)) is False, "an empty stack"
    assert situation_fit(came([]), expected("otherwise", GRID)) is False, "an empty grid"
    assert situation_fit(came([[]]), expected("otherwise", GRID)) is False, "a grid of empty rows"
    assert situation_fit(came(GRID), expected("otherwise", [])) is False, "nothing expected"


def test_as_read_fits_a_grid_as_expected_where_it_reads():
    assert situation_fit(came([[1, 0], [0, 7]]), expected("as_read", [[1, 0], [0, None]])) is True
    assert situation_fit(came([[1, 1], [0, 7]]), expected("as_read", [[1, 0], [0, None]])) is False


def test_as_read_with_nothing_returned_or_nothing_expected_does_not_fit():
    assert situation_fit(came(), expected("as_read", GRID)) is False
    assert situation_fit(came([]), expected("as_read", [])) is False, "an empty grid matched no empty grid"
    assert situation_fit(came(GRID), expected("as_read", [[]])) is False


def test_the_last_grid_of_a_stack_is_what_is_read():
    assert situation_fit(came(GRID, [[0, 1], [0, 0]]), expected("otherwise", GRID)) is True
    assert situation_fit(came([[0, 1], [0, 0]], GRID), expected("otherwise", GRID)) is False
