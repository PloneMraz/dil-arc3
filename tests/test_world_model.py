"""The world-model mind, in the loop, with a scripted model in place of an LLM.

A 3x3 "game": ACTION1 moves the one lit cell a step right. The mind predicts the
frame from the situation alone, thinks when the expectation fails, writes the
program as data, learns its datum's id when it arrives, and revises it — and the
trace a third party reads says so.
"""

from __future__ import annotations

from arc3.mind import create_mind, predict_rule
from arc3.observe import FRAME_CHANNEL, admit, transducers
from arc3.world_model import (
    PROGRAM_TAGS, SCARRED_FRAMES, ModelEndpoint, Transition, WorldModel,
    compile_program, render_evidence, run_program, world_model_rule,
)
from dil.conformance.checker import check_conformance
from dil.loop.cycle import HostCycleInput, Layers, create_cycle
from dil.loop.glob_mod import create_glob_mod
from dil.loop.layers.t1 import create_t1
from dil.loop.layers.t2 import Emission, create_t2
from dil.loop.layers.t3 import create_t3, store_query
from dil.loop.layers.t4 import create_t4
from dil.loop.layers.t5 import create_t5
from dil.loop.layers.t6 import create_t6
from dil.loop.layers.t7 import create_t7
from dil.loop.layers.t8 import create_t8
from dil.loop.types import Signal
from dil.store.data_store import create_data_store
from dil.store.event_log import create_event_log

RIGHT = '''
def predict(grid, action, x=None, y=None):
    g = [row[:] for row in grid]
    if action == 1:
        for r, row in enumerate(grid):
            for c, v in enumerate(row):
                if v == 1 and c + 1 < len(row):
                    g[r][c] = 0
                    g[r][c + 1] = 1
    return g
'''
STILL = '''
def predict(grid, action, x=None, y=None):
    return [row[:] for row in grid]
'''


def lit(c: int) -> list[list[int]]:
    return [[1 if col == c else 0 for col in range(3)], [0, 0, 0], [0, 0, 0]]


def frame(before, after, action=1) -> Signal:
    return Signal(source_id=FRAME_CHANNEL, t=1, raw_payload={
        "entity": "frame", "before": [before], "grids": [after],
        "move": {"kind": "move", "actionId": action, "x": None, "y": None},
        "context": f"action:{action}",
    })


class Script:
    """A model that answers each prompt with the next program in its list."""

    def __init__(self, *programs: str) -> None:
        self.programs = list(programs)
        self.prompts: list[list[dict[str, str]]] = []

    def __call__(self, endpoint, messages):
        self.prompts.append(messages)
        code = self.programs.pop(0)
        return f"```python\n{code}```", {"completion_tokens": 10, "seconds": 0.0}


def loop(model: Script):
    wm = WorldModel(ModelEndpoint(), chat_fn=model)
    rule = world_model_rule(predict_rule(create_mind()), wm)
    data, events = create_data_store(), create_event_log()
    cycle = create_cycle(
        layers=Layers(
            t1=create_t1(), t2=create_t2(), t3=create_t3(transducers()), t4=create_t4(),
            t5=create_t5(predict=rule), t6=create_t6(), t7=create_t7(), t8=create_t8(),
        ),
        glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=data, events=events,
        initial_emission=Emission(action="boot"), admit=admit,
    )
    return wm, cycle, data, events


def run(cycle, *signals):
    cycle.run(HostCycleInput(signals=tuple(signals)))


def of_kind(events, kind):
    return [r for r in events.all() if getattr(r, "activity_kind", None) == kind]


def test_a_program_runs_on_a_transition_and_a_bad_one_is_caught():
    t = Transition(before=lit(0), action=1, x=None, y=None, after=lit(1))
    assert run_program(compile_program(RIGHT), t) == lit(1)
    assert "Starting from this grid" in render_evidence([t])


def test_no_mismatch_no_thinking_and_the_standing_expectation_is_nothing_changes():
    model = Script()
    wm, cycle, data, events = loop(model)
    run(cycle, frame(lit(0), lit(0)))
    assert model.prompts == [] and wm.thoughts == []
    assert [r for r in events.all() if type(r).__name__ == "EventRecord"] == []


def test_a_mismatch_makes_it_ask_and_think_and_the_program_is_written_as_data():
    model = Script(RIGHT)
    wm, cycle, data, events = loop(model)
    run(cycle, frame(lit(0), lit(1)))  # nothing-changes fails: think

    assert len(model.prompts) == 1
    queries = [r.action for r in of_kind(events, "emission") if r.issuing_layer == 5]
    assert queries == [store_query(SCARRED_FRAMES)], "the mind asked for what collided"
    written = data.get("written-0-0")
    assert written.fixed.provenance == "nascent"
    assert written.payload == {"code": RIGHT, "version": 1}
    assert written.open == PROGRAM_TAGS
    assert data.get("signal-0-0").fixed.provenance == "scar", "the frame the expectation failed on"

    run(cycle, frame(lit(1), lit(2)))  # the program now predicts it
    assert wm.datum_id == "written-0-0", "the mind learned its datum when it arrived"
    assert data.get("written-0-0").fixed.provenance == "running"
    assert data.get("signal-1-0").fixed.provenance == "running", "the expectation held: no scar"
    assert len(model.prompts) == 1, "no mismatch, no thinking"


def test_a_better_program_revises_the_datum_and_the_log_says_so():
    model = Script(STILL, RIGHT)
    wm, cycle, data, events = loop(model)
    run(cycle, frame(lit(0), lit(1)))  # no program: the first one is kept, wrong as it is
    run(cycle, frame(lit(1), lit(2)))  # STILL fails; RIGHT explains more, and is kept
    run(cycle, frame(lit(2), lit(2)))

    assert wm.version == 2 and wm.code == RIGHT
    revisions = [(r.datum_id, r.cycle_mark) for r in of_kind(events, "revision")]
    assert revisions == [("written-0-0", 1)]
    assert data.get("written-0-0").payload == {"code": RIGHT, "version": 2}
    assert data.get("written-0-0").fixed.provenance == "running", "a revision moves nothing"
    # The second prompt shows the held program and where it failed.
    assert "Your function was run" in model.prompts[1][-1]["content"]
    assert [t.adopted for t in wm.thoughts] == [True, True]

    report = check_conformance(events)
    assert [f"{r.id}: {r.detail}" for r in report.results if r.verdict == "fail"] == []


def test_a_worse_program_is_not_kept():
    model = Script(RIGHT, STILL)
    wm, cycle, data, events = loop(model)
    run(cycle, frame(lit(0), lit(1)))
    run(cycle, frame(lit(2), lit(0), action=2))  # RIGHT does not know ACTION2 wraps; STILL is no better
    assert wm.code == RIGHT and wm.version == 1
    assert of_kind(events, "revision") == []
    assert wm.thoughts[-1].adopted is False
