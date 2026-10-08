"""Where the aim may lie, before it has come (Plone, 2026-10-07): the inducer
suspects, the mind tests, and the region bears a suspect out or not."""

from __future__ import annotations

import json

from arc3.organs import ARC_ORGANS
from arc3.task import MIND_TASK, TASK_CUE
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
from arc3.observe import admit, transducers
from mind.mind import Mind, mind_rule
from mind.models.grid import GridInducer, SuspectForm
from tests.test_arc3_learning_mind import frame, of_kind, run, status

LEVELLED = {"levelsDelta": 1}


def board(piece=(6, 6)):
    """A floor of 0; two 1-cell things of 5 (one colour, two things); a 2x2 of
    3, the one thing of its colour; a 1-cell piece of 9 at `piece`."""
    g = [[0] * 8 for _ in range(8)]
    g[0][0] = g[0][7] = 5
    for r, c in ((3, 3), (3, 4), (4, 3), (4, 4)):
        g[r][c] = 3
    g[piece[0]][piece[1]] = 9
    return g


def said(inducer, form, state, act):
    got = inducer.predict(form, inducer.situation(state), state, act, lambda raw: raw)
    return None if got is None else got.fields


def test_a_thing_of_a_colour_no_other_has_is_suspected_for_each_act():
    inducer = GridInducer(ARC_ORGANS)
    forms = inducer.suspects(board(), LEVELLED)
    colours = {f.cells[0][2] for f in forms}
    assert colours == {3, 9}, "the one thing of its colour, not the two of 5"
    assert {f.act for f in forms if f.cells[0][2] == 3} == set(ARC_ORGANS.acts) - {ARC_ORGANS.reset[0]}
    click = next(f for f in forms if f.placed and f.cells[0][2] == 3)
    assert said(inducer, click, board(), (6, 3, 4)) == LEVELLED, "put on it"
    assert said(inducer, click, board(), (6, 0, 0)) is None, "put elsewhere"
    step = next(f for f in forms if f.act == 1 and f.cells[0][2] == 3)
    assert said(inducer, step, board(), (1, None, None)) is None, "nothing next to it yet"
    assert said(inducer, step, board((5, 3)), (1, None, None)) == LEVELLED, "something come next to it"
    gone = board((5, 3))
    gone[3][3] = 0
    assert said(inducer, step, gone, (1, None, None)) is None, "it no longer lies as it lay"
    again = inducer.restore(json.loads(json.dumps(inducer.describe(step, None))))
    assert isinstance(again, SuspectForm) and inducer.key(again) == inducer.key(step)


def loop():
    mind = Mind(GridInducer(ARC_ORGANS), ARC_ORGANS, priors={"task": TASK_CUE}, suspects=True)
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
    return mind, cycle, data, events


def test_the_mind_goes_to_test_a_suspect_and_drops_it_when_the_region_does_not_bear_it_out():
    mind, cycle, data, events = loop()
    run(cycle, frame(board(), board()), status(affords=(6,)))
    run(cycle, frame(board(), board(), action=6), status(affords=(6,), action=6))
    act, why = mind.learning.thoughts[-1].act, mind.learning.thoughts[-1].why
    assert act[0] == 6 and (act[2], act[1]) in {(3, 3), (3, 4), (4, 3), (4, 4), (6, 6)}, act
    assert why == "an act its hypotheses say brings the aim here"
    suspects = [k for k, d in of_kind(data, "hypothesis") if d.payload.get("form") == "suspect"]
    assert suspects, "written as data"
    x, y = act[1], act[2]
    run(cycle, frame(board(), board(), action=6, x=x, y=y), status(affords=(6,), action=6))
    tested = [d.payload for _, d in of_kind(data, "hypothesis") if d.payload.get("form") == "suspect"
              and d.payload["placed"] and [y, x] in [c[:2] for c in d.payload["cells"]]]
    assert tested and tested[-1]["fails"] == 1 and not tested[-1]["holds"], "not borne out: dropped"


def test_a_thing_too_large_to_be_more_than_a_wall_is_not_suspected():
    from mind.models.grid import MAX_SUSPECT_CELLS
    g = [[0] * 40 for _ in range(40)]
    for r in range(20):
        for c in range(15):
            g[r][c] = 6                                  # 300 cells of 6, the one thing of its colour
    g[30][30] = 9
    assert 20 * 15 > MAX_SUSPECT_CELLS
    colours = {f.cells[0][2] for f in GridInducer(ARC_ORGANS).suspects(g, LEVELLED)}
    assert colours == {9}
