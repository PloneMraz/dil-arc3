"""The learning mind — one mind, which learns the region from nothing — in the loop.

A 3x3 "game": ACTION1 moves the one lit cell a step right, ACTION2 a step left.
The mind brings no knowledge of it: it learns each transition as it takes it,
writes it as data built from the frame and report it came in, expects from it
the next time, and is curious about what it has not tried — and the trace a third
party reads says so.
"""

from __future__ import annotations

from arc3.organs import ARC_ORGANS
from arc3.task import MIND_TASK, TASK_CUE
from mind.mind import Mind, mind_rule
from mind.models.learning import (
    CHOICE_TAGS, CLOCK_WINDOW, LEARNED_TAGS, LearningModel, grid_key, things,
)
from mind.organs import Step
from arc3.observe import FRAME_CHANNEL, STATUS_CHANNEL, admit, transducers
from dil.loop.cycle import HostCycleInput, Layers, create_cycle
from dil.loop.glob_mod import create_glob_mod
from dil.loop.layers.t1 import create_t1
from dil.loop.layers.t2 import Emission, create_t2
from dil.loop.layers.t3 import create_t3
from dil.loop.layers.t4 import create_t4
from dil.loop.layers.t5 import create_t5
from dil.loop.layers.t6 import create_t6
from dil.loop.layers.t7 import create_t7
from dil.loop.layers.t8 import create_t8
from dil.loop.types import Signal
from dil.store.data_store import create_data_store
from dil.store.event_log import create_event_log


def lit(c: int, clock: int = 0) -> list[list[int]]:
    return [[1 if col == c else 0 for col in range(3)], [0, 0, 0], [clock % 2, 0, 0]]


def frame(before, after, action=1, x=None, y=None) -> Signal:
    return Signal(source_id=FRAME_CHANNEL, t=1, raw_payload={
        "entity": "frame", "before": [before], "grids": [after],
        "move": {"kind": "move", "actionId": action, "x": x, "y": y},
        "context": f"action:{action}",
    })


def status(state="NOT_FINISHED", levels=0, action=1, affords=(1, 2)) -> Signal:
    return Signal(source_id=STATUS_CHANNEL, t=1, raw_payload={
        "entity": "region",
        "status": {"stateFrom": "NOT_FINISHED", "stateTo": state, "levelsDelta": levels, "depthDelta": 0},
        "context": f"action:{action}", "affords": list(affords),
    })


def create_mind() -> Mind:
    mind = Mind(LearningModel(ARC_ORGANS, priors={"task": TASK_CUE}), ARC_ORGANS)
    # What it reads, handed in as if recalled: the in-memory store admits no prior.
    mind.receive("task", MIND_TASK.payload, None)
    return mind


def loop():
    mind = create_mind()
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


def run(cycle, *signals):
    return cycle.run(HostCycleInput(signals=tuple(signals)))


def of_kind(data, kind):
    return [(k, d) for k, d in data.entries() if d.open.get("kind") == kind]


def test_what_it_takes_it_learns_as_data_built_from_the_frame_and_report():
    mind, cycle, data, events = loop()
    run(cycle, frame(lit(0), lit(1)), status())
    learned = of_kind(data, "transition")
    assert len(learned) == 1
    datum_id, datum = learned[0]
    assert datum.open == LEARNED_TAGS and datum.fixed.provenance == "nascent"
    assert datum.payload["act"] == [1, None, None] and datum.payload["changed"] is True
    assert datum.payload["status"] == {"stateTo": "NOT_FINISHED", "levelsDelta": 0, "depthDelta": 0}
    written = {w.datum_id: w.built_from for r in events.all() if getattr(r, "activity_kind", None) == "cycle-seal"
               for w in r.activity.written}
    assert written[datum_id] == ("signal-0-0", "signal-0-1"), "built from the frame and the report it came in"


def test_it_commands_an_act_not_yet_taken_and_says_why():
    mind, cycle, data, events = loop()
    result = run(cycle, frame(lit(0), lit(1)), status())
    # From lit(1) nothing is known: both acts are untried; ACTION1 changed the
    # state once, ACTION2 never tried — the less known is the more wanted.
    assert mind.commands[-1] == (1, (2, None, None))
    choice = [d for _, d in of_kind(data, "choice")][-1]
    assert choice.open == CHOICE_TAGS and choice.payload["why"] == "not yet taken from here"
    move = {"kind": "move", "actionId": 2, "x": None, "y": None}
    assert result.tests == (move,), "the command is T5's test"
    from_t5 = [r for r in events.all() if getattr(r, "activity_kind", None) == "emission" and r.issuing_layer == 5]
    assert {"kind": "test", "action": move} in [r.action for r in from_t5], "recorded from T5, as a test"


def test_an_act_taken_again_is_expected_as_learned_and_the_expectation_is_the_datums():
    mind, cycle, data, events = loop()
    run(cycle, frame(lit(0), lit(1)), status())          # learned: from lit(0), ACTION1 -> lit(1)
    run(cycle, frame(lit(1), lit(0), action=2), status(action=2))
    run(cycle, frame(lit(0), lit(1)), status())          # the same act from the same state
    assert mind.holds == [0, 0, 1], "the third it expected, from what it learned"
    learned_id = of_kind(data, "transition")[0][0]
    assert data.get(learned_id).fixed.provenance != "scar"


def test_the_same_act_giving_something_else_scars_the_datum_and_it_no_longer_holds():
    mind, cycle, data, events = loop()
    run(cycle, frame(lit(0), lit(1)), status())
    run(cycle, frame(lit(1), lit(0), action=2), status(action=2))
    run(cycle, frame(lit(0), lit(2)), status())          # the same act, from the same state, elsewhere
    learned_id = of_kind(data, "transition")[0][0]
    scars = [r for r in events.all() if type(r).__name__ == "EventRecord" and r.datum_id == learned_id]
    assert scars, "the expectation was the datum's, and the region refuted it"
    run(cycle, frame(lit(2), lit(1), action=2), status(action=2))
    assert data.get(learned_id).payload["holds"] is False, "revised: it no longer predicts from it"


def test_the_game_ended_is_met_with_reset():
    mind, cycle, data, events = loop()
    run(cycle, frame(lit(0), lit(1)), status(state="GAME_OVER"))
    assert mind.commands[-1] == (1, (0, None, None))
    assert mind.thoughts[-1].why.startswith("the game has ended")


def test_a_row_that_changes_whatever_is_done_is_the_clock_and_not_where_the_game_stands():
    model = LearningModel(ARC_ORGANS, priors={"task": TASK_CUE})
    grids = [lit(0, clock=i) for i in range(CLOCK_WINDOW + 1)]
    for i in range(CLOCK_WINDOW):
        a = [1, 2, 3][i % 3]
        model._learn_clock(Step(before=grids[i], act=(a, None, None), after=grids[i + 1]), ("act", a), None)
    assert model.clock == frozenset({2})
    assert grid_key(lit(0, 0), model.clock) == grid_key(lit(0, 1), model.clock)


def test_things_are_regions_of_one_colour_and_the_ground_is_left_out():
    grid = [[0] * 8 for _ in range(8)]
    grid[1][1] = grid[1][2] = 3
    grid[5][5] = 4
    found = things(grid)
    assert [(c, n) for c, n, _, _ in found] == [(4, 1), (3, 2)], "smallest first; the ground (0) is too large"
    assert found[0][2:] == (5, 5)


def test_clicking_that_never_did_anything_is_wanted_less_whatever_is_left_to_click():
    # ar25 and sk48 on Kaggle: 0 of ~200 clicks changed anything, and each new
    # thing to click was a new kind, so clicking went on (LOG.md). The action is
    # chosen first, over every kind of it.
    mind, cycle, data, events = loop()
    mind.model._actions = {6: [20, 0, 0], 1: [5, 5, 0]}
    mind.model._kinds = {("act", 1): [5, 5, 0]}
    run(cycle, frame(lit(0), lit(1)), status(affords=(1, 6)))
    assert mind.commands[-1][1][0] == 1, "the action that changes things, not an untried click"
