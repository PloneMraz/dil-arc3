"""The grid inducer: hypotheses that reach past where they were met."""

from __future__ import annotations

from arc3.organs import ARC_ORGANS
from arc3.task import TASK_CUE
from mind.learning import Learning
from mind.models.grid import GridInducer, RewriteForm, StillForm, parts
from mind.organs import Step


def board(*pieces, size=6, wall=None):
    """A grid of 0 with a piece of 9 at each (row, column), and a wall of 5."""
    g = [[0] * size for _ in range(size)]
    for r, c in pieces:
        g[r][c] = 9
    for r, c in wall or ():
        g[r][c] = 5
    return g


def rewrite_of(inducer, before, act, after):
    return next(f for f in inducer.induce("s", act, before, after) if isinstance(f, RewriteForm))


def predicted(inducer, form, state, act):
    said = inducer.predict(form, inducer.situation(state), state, act, lambda raw: raw)
    return None if said is None else said.state


def test_a_move_learned_in_one_place_is_predicted_in_another():
    inducer = GridInducer(ARC_ORGANS)
    form = rewrite_of(inducer, board((1, 1)), (1, None, None), board((1, 2)))
    assert predicted(inducer, form, board((4, 3)), (1, None, None)) == board((4, 4))


def test_what_lies_in_the_way_is_part_of_the_rewrite():
    inducer = GridInducer(ARC_ORGANS)
    form = rewrite_of(inducer, board((1, 1)), (1, None, None), board((1, 2)))
    assert predicted(inducer, form, board((4, 3), wall=[(4, 4)]), (1, None, None)) is None


def test_a_rewrite_that_lies_at_two_places_says_nothing():
    inducer = GridInducer(ARC_ORGANS)
    form = rewrite_of(inducer, board((1, 1)), (1, None, None), board((1, 2)))
    assert predicted(inducer, form, board((1, 1), (4, 3)), (1, None, None)) is None


def test_a_click_that_changed_nothing_is_still_on_that_colour_anywhere():
    inducer = GridInducer(ARC_ORGANS)
    before = board((1, 1), (4, 4))
    forms = inducer.induce("s", (6, 1, 1), before, before)
    still = next(f for f in forms if isinstance(f, StillForm))
    assert (still.act, still.colour) == (6, 9)
    assert predicted(inducer, still, before, (6, 4, 4)) == before
    assert predicted(inducer, still, before, (6, 0, 0)) is None, "not on another colour"


def test_changed_cells_near_each_other_are_one_part():
    assert len(parts([(0, 0), (0, 2), (5, 5)])) == 2


def test_the_mind_expects_right_in_a_situation_it_never_met():
    model = Learning(GridInducer(ARC_ORGANS), ARC_ORGANS, priors={"task": TASK_CUE})
    for before, after in ((board((1, 1)), board((1, 2))), (board((4, 2)), board((4, 3)))):
        step = Step(before=before, act=(1, None, None), after=after)
        model.expect(step)
        model.observe(step, None, None, (), False)
    assert model.unseen == [2, 1, 1], "the second step: never met, expected, and right"


def test_each_part_is_found_on_its_own():
    # A piece moves and a counter at the edge ticks down: next time the piece and
    # the counter's boundary are elsewhere, each at its own distance.
    def with_counter(g, used):
        for r in range(6):
            g[r][5] = 3 if r < used else 4
        return g

    inducer = GridInducer(ARC_ORGANS)
    form = rewrite_of(inducer, with_counter(board((1, 1)), 2), (1, None, None), with_counter(board((1, 2)), 3))
    assert len(form.parts) == 2
    assert predicted(inducer, form, with_counter(board((4, 2)), 3), (1, None, None)) == \
        with_counter(board((4, 3)), 4)


def test_an_act_foreseen_to_lead_where_it_stood_is_put_last_not_out_of_reach():
    model = Learning(GridInducer(ARC_ORGANS), ARC_ORGANS, priors={"task": TASK_CUE})
    for before, act, after in ((board((1, 1)), (3, None, None), board((1, 1))),     # 3 changes nothing
                               (board((1, 1)), (1, None, None), board((1, 2)))):    # 1 moves right
        step = Step(before=before, act=act, after=after)
        model.expect(step)
        model.observe(step, None, None, (), False)
    here = model._here
    opened = [act for act, _ in model._open_here(here, (1, 2, 3))]
    assert (3, None, None) in opened, "never out of reach"
    assert model._foreseen(here, (3, None, None)), "foreseen: it changes nothing"
    assert not model._foreseen(here, (1, None, None)), "foreseen to lead somewhere not stood in"


def test_what_a_step_made_is_each_part_it_changed_where_it_lies_as_left():
    from mind.models.exact import ExactInducer
    inducer = ExactInducer(ARC_ORGANS)
    there = inducer.made(Step(board((1, 1)), (1, None, None), board((1, 2))))
    assert there == inducer.made(Step(board((1, 1)), (2, None, None), board((1, 2)))), "whatever the act"
    assert there != inducer.made(Step(board((4, 1)), (1, None, None), board((4, 2)))), "elsewhere, something else"
    assert len(inducer.made(Step(board((0, 0), (5, 5)), (1, None, None), board((0, 1), (5, 4))))) == 2, "two parts"
    assert inducer.made(Step(board((1, 1)), (1, None, None), board((1, 1)))) == frozenset(), "nothing changed"


def test_by_the_law_made_a_whole_never_met_is_not_new_when_each_part_was_made_before():
    def two(a, b):
        g = board()
        g[0][a], g[5][b] = 9, 9
        return g
    def counted(law):
        model = Learning(GridInducer(ARC_ORGANS), ARC_ORGANS, priors={"task": TASK_CUE}, curiosity=law)
        # Each piece moves right and back; then the top right and the bottom right:
        # a whole never met, each part as it was made before.
        for before, after in ((two(0, 0), two(1, 0)), (two(1, 0), two(0, 0)), (two(0, 0), two(0, 1)),
                              (two(0, 1), two(0, 0)), (two(0, 0), two(1, 0)), (two(1, 0), two(1, 1))):
            step = Step(before=before, act=(1, None, None), after=after)
            model.expect(step)
            model.observe(step, None, None, (), False)
        return model._kinds[("act", 1)][:2]
    assert counted("new") == [6, 3], "somewhere new: two pieces, then the last whole, never met"
    assert counted("made") == [6, 4], "made: each way of each piece once; the last whole made nothing new"
