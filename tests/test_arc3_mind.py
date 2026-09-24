"""The mind — one, the model and its program — in the loop, with a scripted model.

A 3x3 "game": ACTION1 moves the one lit cell a step right. The mind predicts the
frame from the situation alone, thinks when the expectation fails, writes the
program as data, learns its datum's id when it arrives, and revises it — and the
trace a third party reads says so.
"""

from __future__ import annotations

from arc3.mind import (
    PROGRAM_TAGS, SCARRED_FRAMES, ModelEndpoint, Transition,
    compile_program, create_mind, mind_rule, render_evidence, run_program,
)
from arc3.observe import FRAME_CHANNEL, STATUS_CHANNEL, admit, transducers
from arc3.prior import DIRECTIVE
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
    wm = create_mind(ModelEndpoint(), chat_fn=model)
    rule = mind_rule(wm)
    data, events = create_data_store(), create_event_log()
    glob = create_glob_mod({"appraisalGain": 1.0}, 0)
    cycle = create_cycle(
        layers=Layers(
            t1=create_t1(), t2=create_t2(), t3=create_t3(transducers()), t4=create_t4(),
            t5=create_t5(predict=rule), t6=create_t6(), t7=create_t7(), t8=create_t8(),
        ),
        glob=glob, data=data, events=events,
        initial_emission=Emission(action="boot"), admit=admit,
    )
    loop.glob = glob
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

    written = [t for r in of_kind(events, "cycle-seal") for t in r.activity.written]
    assert [(w.datum_id, w.built_from) for w in written] == [("written-0-0", ("signal-0-0",))], \
        "the program says it was built from the frame in front of it"

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
    # The second prompt shows the held program and where it failed, and its
    # evidence already holds the first frame: T5's window, not a store answer.
    assert "Your function was run" in model.prompts[1][-1]["content"]
    assert wm.thoughts[1].evidence == 2
    written = {t.datum_id: t.built_from for r in of_kind(events, "cycle-seal") for t in r.activity.written}
    assert written["written-0-0"] == ("signal-0-0", "signal-1-0"), "the revision names both frames it drew on"
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


def test_evidence_that_would_not_fit_the_context_is_dropped_oldest_first(monkeypatch):
    import arc3.mind as wmod

    monkeypatch.setattr(wmod, "MAX_EVIDENCE_CHARS", 200)  # room for one small chain only
    model = Script(STILL, STILL)
    wm, cycle, data, events = loop(model)
    run(cycle, frame(lit(0), lit(1)))
    run(cycle, frame(lit(2), lit(0), action=2))  # not a chain with the first: two full grids
    assert wm.thoughts[-1].evidence == 1, "the older transition was dropped to fit"


# ── what the one mind reports to the field, which is all the self reads ──


def status(state: str = "NOT_FINISHED", levels: int = 0, action: int = 1) -> Signal:
    return Signal(source_id=STATUS_CHANNEL, t=1, raw_payload={
        "entity": "region", "status": {"stateTo": state, "levelsDelta": levels},
        "context": f"action:{action}", "affords": [1, 2],
    })


def test_the_mind_reports_per_action_how_its_program_holds_and_how_fast_that_moves():
    model = Script(RIGHT)
    wm, cycle, data, events = loop(model)
    run(cycle, frame(lit(0), lit(1)))            # miss: nothing changes was wrong
    run(cycle, frame(lit(1), lit(2)))            # hit: the program holds
    field = loop.glob.current().params
    assert field["resolved:action:1"] == 0.5, "one frame of two after ACTION1 predicted"
    assert field["progress:action:1"] == 1.0, "too few uses to have a progress: still being learned"
    assert wm.resolution("action:1") == 0.5


def test_progress_is_the_change_between_the_last_two_windows_of_uses():
    wm = create_mind(ModelEndpoint(), chat_fn=Script())
    wm._uses["action:1"] = [0, 0, 0, 0, 1, 1, 1, 1]
    assert wm.progress("action:1") == 1.0, "a revision that suddenly explains it: learning"
    wm._uses["action:1"] = [1] * 8
    assert wm.progress("action:1") == 0.0, "held and settled: nothing left to learn here"


def test_the_region_is_answered_against_the_directive_and_the_status_is_the_standing_expectation():
    model = Script()
    wm, cycle, data, events = loop(model)
    wm.take_return({"entity": DIRECTIVE.id, "payload": DIRECTIVE.payload, "open": {}}, None)
    run(cycle, status())
    run(cycle, status(levels=1))                 # a level: toward the objective
    field = loop.glob.current().params
    assert field["valence:action:1"] > 0
    scars = [r for r in events.all() if type(r).__name__ == "EventRecord"]
    assert [r.event.source_id for r in scars] == ["region"], "the status changed against 'it stays as it was'"
    assert model.prompts == [], "the model is not asked about the status"


def test_a_change_of_move_is_not_the_region_resisting():
    model = Script()
    wm, cycle, data, events = loop(model)
    run(cycle, status(action=1))
    run(cycle, status(action=2))                 # the self changed its move; the region said the same
    run(cycle, status(action=1))
    scars = [r for r in events.all() if type(r).__name__ == "EventRecord"]
    assert scars == [], "the action is the self's, not something the region returned"
    run(cycle, status(state="GAME_OVER", action=2))
    scars = [r for r in events.all() if type(r).__name__ == "EventRecord"]
    assert [r.event.source_id for r in scars] == ["region"], "what the region said still collides"
