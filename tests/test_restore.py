"""A hypothesis restored from its datum (Plone, 2026-10-05: what a model computes
from, the mind reads from its memory). What `describe` writes, passed through the
store's JSON as SQLite keeps it, with the step it was induced from, gives back the
form described: the same key, the same predictions."""

from __future__ import annotations

import json

from arc3.organs import ARC_ORGANS
from mind.models.exact import ExactInducer, grid_key
from mind.models.grid import AimForm, GridInducer, RewriteForm, StillForm
from mind.models.language_inducer import LanguageInducer, compile_program
from mind.organs import Step
from tests.test_aim_hypothesis import LEVELLED, board as layout
from tests.test_grid_inducer import board
from tests.test_language_inducer import RIGHT


def stored(inducer, form, before):
    """The form's datum as the store gives it back."""
    return json.loads(json.dumps(inducer.describe(form, lambda raw: inducer.situation(before))))


def same(inducer, form, again, state, act):
    assert inducer.key(again) == inducer.key(form)
    situation = grid_key(state)
    said = inducer.predict(form, situation, state, act, lambda raw: situation)
    said_again = inducer.predict(again, situation, state, act, lambda raw: situation)
    assert (said is None) == (said_again is None)
    if said is not None:
        assert (said.state, said.fields) == (said_again.state, said_again.fields)


def test_an_exact_hypothesis_comes_back_from_its_datum_and_its_step():
    inducer = ExactInducer(ARC_ORGANS)
    step = Step(board((1, 1)), (1, None, None), board((1, 2)))
    form = inducer.induce(inducer.identity(step.before), step.act, step.before, step.after)[0]
    inducer.reported(form, {"stateTo": "NOT_FINISHED", "levelsDelta": 0, "depthDelta": 0})
    again = inducer.restore(stored(inducer, form, step.before), step)
    same(inducer, form, again, step.before, step.act)
    assert again.status == form.status


def test_still_rewrite_and_aim_hypotheses_come_back_from_their_datum_alone():
    inducer = GridInducer(ARC_ORGANS)
    before, after = board((1, 1), (4, 4)), board((1, 2), (4, 4))
    aim_before, expected = layout((2, 3), (2, 5)), layout((2, 4), (2, 5))
    steps = (Step(before, (1, None, None), after), Step(before, (6, 4, 4), before))
    forms = [(f, step) for step in steps
             for f in inducer.induce(inducer.identity(step.before), step.act, step.before, step.after)]
    forms += [(f, None) for f in inducer.induce("s", (4, None, None), aim_before, layout((1, 1), (3, 3), 7),
                                                report=LEVELLED, expected=expected)]
    assert {type(f) for f, _ in forms} >= {RewriteForm, StillForm, AimForm}
    for form, step in forms:
        again = inducer.restore(stored(inducer, form, before), step)
        assert type(again) is type(form)
        for state, act in ((board((4, 3)), (1, None, None)), (before, (6, 4, 4)),
                           (layout((1, 2), (1, 4), 7), (4, None, None))):
            same(inducer, form, again, state, act)


def test_a_program_comes_back_from_its_datum_loaded_again():
    inducer = LanguageInducer(ARC_ORGANS, chat_fn=lambda *a: ("", {}))
    form = compile_program(RIGHT)
    grid = [[1, 0, 0], [0, 0, 0], [0, 0, 0]]
    again = inducer.restore(stored(inducer, form, grid), Step(grid, (1, None, None), grid))
    same(inducer, form, again, grid, (1, None, None))
