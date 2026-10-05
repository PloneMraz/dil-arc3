"""S4 — a hypothesis about the aim, carried to the next level (Plone, 2026-09-28).

Reaching the aim is an experience too: the mind draws from it what brings the
aim, and uses it at the next level, in the same loop. The region comes back
changed nearly whole when a level is over, so the grid inducer reads what the act
was to change from what the mind expected of the step — for an act that takes a
place, from the thing it was put on — and what lay around it.

A 5x7 "game": a piece (2) moves right under ACTION4; the level ends when it comes
next to the exit (5), and the next level is another layout.
"""

from __future__ import annotations

from arc3.organs import ARC_ORGANS
from arc3.task import MIND_TASK, TASK_CUE
from mind.mind import Mind, mind_rule
from mind.models.exact import grid_key
from mind.models.grid import AimForm, GridInducer
from arc3.observe import admit, transducers
from dil.loop.cycle import Layers, create_cycle
from dil.loop.glob_mod import create_glob_mod
from dil.loop.layers.t1 import create_t1
from dil.loop.layers.t2 import Emission, create_t2
from dil.loop.layers.t3 import create_t3
from dil.loop.layers.t4 import create_t4
from dil.loop.layers.t5 import create_t5
from dil.loop.layers.t6 import create_t6
from dil.loop.layers.t7 import create_t7
from dil.loop.layers.t8 import create_t8
from dil.store.data_store import create_data_store
from dil.store.event_log import create_event_log
from tests.test_arc3_learning_mind import frame, of_kind, run, status

LEVELLED = {"stateTo": "NOT_FINISHED", "levelsDelta": 1, "depthDelta": 0}


def board(piece: tuple[int, int], exit_: tuple[int, int], mark: int = 0) -> list[list[int]]:
    """A 5x7 grid: the piece and the exit; `mark` tells one layout from another."""
    g = [[0] * 7 for _ in range(5)]
    g[piece[0]][piece[1]] = 2
    g[exit_[0]][exit_[1]] = 5
    g[4][6] = mark
    return g


def test_what_the_act_was_to_change_and_what_lay_around_it_bring_the_aim():
    grid = GridInducer(ARC_ORGANS)
    before, expected = board((2, 3), (2, 5)), board((2, 4), (2, 5))
    forms = grid.induce("s", (4, None, None), before, board((1, 1), (3, 3), 7), report=LEVELLED, expected=expected)
    assert len(forms) == 1 and isinstance(forms[0], AimForm) and forms[0].status == LEVELLED
    form = forms[0]
    elsewhere = board((1, 2), (1, 4), 7)          # the same cells, and the exit beside them, elsewhere
    said = grid.predict(form, grid_key(elsewhere), elsewhere, (4, None, None), lambda raw: raw)
    assert said is not None and said.state is None and said.fields == LEVELLED
    far = board((1, 1), (1, 5), 7)                # the piece, but not the exit where it lay
    assert grid.predict(form, grid_key(far), far, (4, None, None), lambda raw: raw) is None
    assert grid.predict(form, grid_key(elsewhere), elsewhere, (3, None, None), lambda raw: raw) is None
    assert grid.induce("s", (4, None, None), before, before, report=LEVELLED, expected=before) == [], \
        "nothing expected to change, and no place: nothing to say where"


def test_with_nothing_expected_what_the_region_showed_before_its_last_grid():
    # The step that brought the aim was foreseen by nothing: the mind expected no
    # change. The region returned a stack: the piece next to the exit, then the
    # next level. What the act was to change is read from the grid before the last.
    grid = GridInducer(ARC_ORGANS)
    before, shown = board((2, 3), (2, 5)), board((2, 4), (2, 5))
    nothing = grid.induce("s", (4, None, None), before, board((1, 1), (3, 3), 7), report=LEVELLED, expected=before)
    assert nothing == [], "nothing expected, nothing shown between: nothing to say where"
    forms = grid.induce("s", (4, None, None), before, board((1, 1), (3, 3), 7), report=LEVELLED, expected=before,
                        through=(shown,))
    assert len(forms) == 1 and isinstance(forms[0], AimForm)
    elsewhere = board((1, 2), (1, 4), 7)
    said = grid.predict(forms[0], grid_key(elsewhere), elsewhere, (4, None, None), lambda raw: raw)
    assert said is not None and said.fields == LEVELLED, "where the same cells lie again, the aim"


def test_the_eye_carries_what_the_region_showed_between():
    payload = {"before": [board((2, 3), (2, 5))], "grids": [board((2, 4), (2, 5)), board((1, 1), (3, 3), 7)],
               "move": {"actionId": 4, "x": None, "y": None}}
    step = ARC_ORGANS.step(payload)
    assert step.after == board((1, 1), (3, 3), 7) and step.through == (board((2, 4), (2, 5)),)


def test_for_an_act_that_takes_a_place_the_thing_it_was_put_on():
    grid = GridInducer(ARC_ORGANS)
    before = board((2, 3), (2, 5))
    forms = grid.induce("s", (6, 3, 2), before, board((0, 0), (4, 4), 7), report=LEVELLED)
    form = forms[0]
    assert form.placed and form.colour == 2
    elsewhere = board((1, 2), (4, 0), 7)
    assert grid.predict(form, grid_key(elsewhere), elsewhere, (6, 2, 1), lambda raw: raw).fields == LEVELLED
    assert grid.predict(form, grid_key(elsewhere), elsewhere, (6, 3, 1), lambda raw: raw) is None, \
        "put on another colour"


def loop():
    mind = Mind(GridInducer(ARC_ORGANS), ARC_ORGANS, priors={"task": TASK_CUE})
    mind.receive("task", MIND_TASK.payload, None)
    data, events = create_data_store(), create_event_log()
    cycle = create_cycle(
        layers=Layers(
            t1=create_t1(), t2=create_t2(), t3=create_t3(transducers()), t4=create_t4(),
            t5=create_t5(predict=mind_rule(mind)), t6=create_t6(), t7=create_t7(), t8=create_t8(),
        ),
        glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=data, events=events,
        initial_emission=Emission(action="boot"), admit=admit,
    )
    return mind, cycle, data


def test_at_the_next_level_it_takes_what_its_hypothesis_says_brings_the_aim():
    mind, cycle, data = loop()
    moves = (1, 2, 3, 4)
    run(cycle, frame(board((2, 1), (2, 5)), board((2, 2), (2, 5)), action=4), status(action=4, affords=moves))
    run(cycle, frame(board((2, 2), (2, 5)), board((2, 3), (2, 5)), action=4), status(action=4, affords=moves))
    # The piece comes next to the exit: the level is over, and the next one opens.
    level2 = board((1, 2), (1, 4), 7)
    run(cycle, frame(board((2, 3), (2, 5)), level2, action=4), status(levels=1, action=4, affords=moves))
    aims = [d for _, d in of_kind(data, "hypothesis") if d.payload.get("form") == "aim"]
    assert aims and aims[0].payload["status"]["levelsDelta"] == 1, "what brings the aim, held as data"
    assert mind.commands[-1][1] == (4, None, None)
    assert mind.learning.thoughts[-1].why == "an act its hypotheses say brings the aim here", \
        "at a layout it has never stood in, what its hypothesis says brings the aim"


def test_a_hypothesis_about_the_aim_that_does_not_bring_it_is_counted_against():
    mind, cycle, data = loop()
    moves = (1, 2, 3, 4)
    run(cycle, frame(board((2, 1), (2, 5)), board((2, 2), (2, 5)), action=4), status(action=4, affords=moves))
    run(cycle, frame(board((2, 2), (2, 5)), board((2, 3), (2, 5)), action=4), status(action=4, affords=moves))
    level2 = board((1, 2), (1, 4), 7)
    run(cycle, frame(board((2, 3), (2, 5)), level2, action=4), status(levels=1, action=4, affords=moves))
    # Outside a cycle the mind reads nothing: a hypothesis in hand is looked at
    # there, one in the store in the store, as a third party reads it.
    aim = next(h for h in mind.learning._hypotheses
               if (isinstance(h.held, AimForm) if h.recall is None
                   else data.get(h.datum_id).payload.get("form") == "aim"))
    # At the next level the same act, where the same cells lie, does not bring it.
    run(cycle, frame(level2, board((1, 3), (1, 4), 7), action=4), status(action=4, affords=moves))
    assert (aim.supports, aim.fails) == (1, 1) and not aim.holds, "right once, wrong once: no longer held"
