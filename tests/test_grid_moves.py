"""Once the aim has come, grid reads what an act does as things that move
(A, 2026-10-08); before, it suggests what it did before."""

from __future__ import annotations

import json

from arc3.organs import ARC_ORGANS
from mind.models.grid import BlockForm, GridInducer, MoveForm

RIGHT = (4, None, None)


def board(piece=None, walls=(), size=8):
    """A floor of 0, a 2x2 piece of 9 with its corner at `piece`, walls of 5."""
    g = [[0] * size for _ in range(size)]
    for r, c in walls:
        g[r][c] = 5
    if piece is not None:
        for dr in (0, 1):
            for dc in (0, 1):
                g[piece[0] + dr][piece[1] + dc] = 9
    return g


def predicted(inducer, form, state):
    said = inducer.predict(form, inducer.situation(state), state, RIGHT, lambda raw: raw)
    return None if said is None else said.state


def aimed():
    inducer = GridInducer(ARC_ORGANS)
    inducer.induce("s", RIGHT, board((1, 1)), board((1, 2)), report={"levelsDelta": 1})
    return inducer


def test_before_the_aim_it_reads_no_move():
    inducer = GridInducer(ARC_ORGANS)
    assert not any(isinstance(f, MoveForm) for f in inducer.induce("s", RIGHT, board((1, 1)), board((1, 2))))


def test_once_the_aim_has_come_a_thing_moved_is_moved_wherever_it_lies_and_blocked_by_what_lay_in_its_way():
    inducer = aimed()
    move = next(f for f in inducer.induce("s", RIGHT, board((1, 1)), board((1, 2))) if isinstance(f, MoveForm))
    assert (move.dr, move.dc, move.trail) == (0, 1, 0)
    assert predicted(inducer, move, board((5, 3))) == board((5, 4))
    assert predicted(inducer, move, board((5, 3), walls=[(5, 5)])) is None
    inducer.keep(move, lambda: move)
    stuck = board((1, 2), walls=[(1, 4), (2, 4)])
    block = next(f for f in inducer.induce("s", RIGHT, stuck, stuck) if isinstance(f, BlockForm))
    far = board((5, 1), walls=[(5, 3), (6, 3)])
    assert block.blockers == frozenset({5}) and predicted(inducer, block, far) == far
    for form in (move, block):
        again = inducer.restore(json.loads(json.dumps(inducer.describe(form, lambda raw: raw))))
        assert inducer.key(again) == inducer.key(form)


def test_what_brought_the_aim_is_brought_by_any_act_whose_move_takes_the_thing_there():
    from mind.models.grid import IntoForm
    inducer = GridInducer(ARC_ORGANS)
    before = board((1, 1))
    before[1][3] = before[2][3] = 3                        # the exit, right of the piece
    stepped = board((1, 2))
    stepped[2][3] = 3
    stepped[1][3] = 9
    stepped[1][3], stepped[2][3] = 9, 9
    forms = inducer.induce("s", RIGHT, before, board(), report={"levelsDelta": 1}, through=(stepped,))
    into = next(f for f in forms if isinstance(f, IntoForm))
    assert into.colours == frozenset({3})
    down = (2, None, None)
    fell = next(f for f in inducer.induce("s", down, board((1, 1)), board((2, 1))) if isinstance(f, MoveForm))
    inducer.keep(fell, lambda: fell)
    below = board((1, 1))
    below[3][1] = below[3][2] = 3                          # the exit below it
    said = inducer.predict(into, inducer.situation(below), below, down, lambda raw: raw)
    assert said is not None and said.state is None
    assert inducer.predict(into, inducer.situation(below), below, RIGHT, lambda raw: raw) is None
