"""The objects inducer (on trial, Plone, 2026-10-07): what an act does to a thing,
wherever the thing lies."""

from __future__ import annotations

import json

from arc3.organs import ARC_ORGANS
from mind.models.objects import BlockForm, MoveForm, ObjectsInducer
from mind.organs import Step


def board(piece=None, walls=(), size=8):
    """A floor of 0, a 2x2 piece of 9 with its corner at `piece`, walls of 5."""
    g = [[0] * size for _ in range(size)]
    for r, c in walls:
        g[r][c] = 5
    if piece is not None:
        r, c = piece
        for dr in (0, 1):
            for dc in (0, 1):
                g[r + dr][c + dc] = 9
    return g


RIGHT = (4, None, None)


def predicted(inducer, form, state, act=RIGHT):
    said = inducer.predict(form, inducer.situation(state), state, act, lambda raw: raw)
    return None if said is None else said.state


def moved(inducer):
    forms = inducer.induce("s", RIGHT, board((1, 1)), board((1, 2)))
    return next(f for f in forms if isinstance(f, MoveForm))


def test_a_thing_moved_by_an_act_is_moved_by_it_wherever_it_lies():
    inducer = ObjectsInducer(ARC_ORGANS)
    move = moved(inducer)
    assert (move.dr, move.dc, move.trail) == (0, 1, 0)
    assert predicted(inducer, move, board((5, 3))) == board((5, 4)), "elsewhere, the same move"
    assert predicted(inducer, move, board((5, 3), walls=[(5, 5)])) is None, "a wall in its way: it says nothing"


def test_an_act_that_moved_nothing_is_blocked_by_what_lay_in_the_way_wherever_it_lies():
    inducer = ObjectsInducer(ARC_ORGANS)
    move = moved(inducer)
    inducer.keep(move, lambda: move)                       # the mind holds it, and hands it back
    stuck = board((1, 2), walls=[(1, 4), (2, 4)])
    blocked = next(f for f in inducer.induce("s", RIGHT, stuck, stuck) if isinstance(f, BlockForm))
    assert blocked.blockers == frozenset({5})
    far = board((5, 1), walls=[(5, 3), (6, 3)])
    assert predicted(inducer, blocked, far) == far, "another wall of that colour, elsewhere: nothing changes"
    assert predicted(inducer, blocked, board((5, 1))) is None, "nothing in its way: it says nothing"
    edge = board((5, 6))
    assert predicted(inducer, blocked, edge) is None, "the edge is not what blocked it"


def test_its_hypotheses_come_back_from_their_datum():
    inducer = ObjectsInducer(ARC_ORGANS)
    move = moved(inducer)
    inducer.keep(move, lambda: move)
    stuck = board((1, 2), walls=[(1, 4), (2, 4)])
    blocked = next(f for f in inducer.induce("s", RIGHT, stuck, stuck) if isinstance(f, BlockForm))
    for form in (move, blocked):
        again = inducer.restore(json.loads(json.dumps(inducer.describe(form, lambda raw: raw))))
        assert inducer.key(again) == inducer.key(form)
        for state in (board((5, 3)), board((5, 1), walls=[(5, 3), (6, 3)])):
            assert predicted(inducer, again, state) == predicted(inducer, form, state)


def test_what_brought_the_aim_is_a_relation_that_holds_on_another_layout():
    from mind.models.objects import AimForm
    inducer = ObjectsInducer(ARC_ORGANS)
    move = moved(inducer)
    inducer.keep(move, lambda: move)
    levelled = {"stateTo": "NOT_FINISHED", "levelsDelta": 1, "depthDelta": 0}
    before = board((1, 1))
    before[1][3] = before[2][3] = 3                      # the exit, where the piece goes next
    aim = inducer.induce("s", RIGHT, before, board(), report=levelled)
    assert len(aim) == 1 and isinstance(aim[0], AimForm) and aim[0].colours == frozenset({3})
    other = board((5, 4))
    other[5][6] = other[6][6] = 3                        # another layout, the exit elsewhere
    said = inducer.predict(aim[0], inducer.situation(other), other, RIGHT, lambda raw: raw)
    assert said is not None and said.state is None and said.fields == levelled
    away = board((1, 1))
    away[5][6] = 3
    assert inducer.predict(aim[0], inducer.situation(away), away, RIGHT, lambda raw: raw) is None, \
        "the exit not where it goes: it says nothing"
    again = inducer.restore(json.loads(json.dumps(inducer.describe(aim[0], lambda raw: raw))))
    assert inducer.key(again) == inducer.key(aim[0])


def test_the_aim_is_brought_by_any_act_that_moves_the_thing_there():
    from mind.models.objects import AimForm
    inducer = ObjectsInducer(ARC_ORGANS)
    move = moved(inducer)
    inducer.keep(move, lambda: move)
    down = (2, None, None)
    fell = next(f for f in inducer.induce("s", down, board((1, 1)), board((2, 1))) if isinstance(f, MoveForm))
    inducer.keep(fell, lambda: fell)
    before = board((1, 1))
    before[1][3] = before[2][3] = 3
    aim = inducer.induce("s", RIGHT, before, board(), report={"levelsDelta": 1})
    assert isinstance(aim[0], AimForm)
    below = board((1, 1))
    below[3][1] = below[3][2] = 3                        # the exit below it: reached going down
    assert inducer.predict(aim[0], inducer.situation(below), below, down, lambda raw: raw) is not None
    assert inducer.predict(aim[0], inducer.situation(below), below, RIGHT, lambda raw: raw) is None


def test_reset_is_no_move():
    inducer = ObjectsInducer(ARC_ORGANS)
    assert inducer.induce("s", ARC_ORGANS.reset, board((5, 5)), board((1, 1))) == []
