"""The mind — one, the model and its program — in the loop, with a scripted model.

A 3x3 "game": ACTION1 moves the one lit cell a step right. The mind predicts the
frame from the situation alone, thinks when the expectation fails, writes the
program as data, learns its datum's id when it arrives, and revises it — and the
trace a third party reads says so.
"""

from __future__ import annotations

from arc3.mind import (
    PROGRAM_TAGS, ModelEndpoint, Transition,
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
    """A model that answers each prompt with the next program in its list, and
    any questions to memory it is given for that answer."""

    def __init__(self, *programs: str, asks: dict[int, str] | None = None) -> None:
        self.programs = list(programs)
        self.asks = asks or {}
        self.prompts: list[list[dict[str, str]]] = []

    def __call__(self, endpoint, messages):
        self.prompts.append(messages)
        code = self.programs.pop(0)
        ask = self.asks.get(len(self.prompts) - 1, "")
        return f"```python\n{code}```\n{ask}", {"completion_tokens": 10, "seconds": 0.0}


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


def test_a_mismatch_makes_it_think_and_the_program_is_written_as_data():
    model = Script(RIGHT)
    wm, cycle, data, events = loop(model)
    run(cycle, frame(lit(0), lit(1)))  # nothing-changes fails: think

    assert len(model.prompts) == 1
    queries = [r.action for r in of_kind(events, "emission") if r.issuing_layer == 5]
    assert queries == [], "nothing is asked for it: the model did not ask"
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


def test_the_model_chooses_what_to_read_and_each_question_is_a_store_query_from_t5():
    model = Script(RIGHT, asks={0: 'ASK {"kind": "remark"}\nASK {"kind": "frame", "provenance": "scar"}\n'
                                   'ASK {"quality": "good"}\nASK not json'})
    wm, cycle, data, events = loop(model)
    run(cycle, frame(lit(0), lit(1)))
    queries = [r.action for r in of_kind(events, "emission") if r.issuing_layer == 5]
    assert queries == [store_query({"kind": "remark"}), store_query({"kind": "frame", "provenance": "scar"})], \
        "what it asked, as asked; a cue on no tag key, or not a cue, is not a question the store can answer"
    assert wm.thoughts[0].asked == [{"kind": "remark"}, {"kind": "frame", "provenance": "scar"}]


def test_the_programs_expectation_is_the_programs_and_scars_it_when_it_fails():
    model = Script(STILL)
    wm, cycle, data, events = loop(model)
    run(cycle, frame(lit(0), lit(1)))  # no program: STILL is written, wrong as it is
    run(cycle, frame(lit(1), lit(1)))  # STILL holds: the program's expectation, in use
    run(cycle, frame(lit(1), lit(2)))  # STILL fails: the program met the mismatch
    moves = [(r.from_, r.to, r.cycle_mark) for r in of_kind(events, "provenance") if r.datum_id == "written-0-0"]
    assert moves == [("nascent", "running", 1), ("running", "scar", 2)]
    expectations = [r for r in of_kind(events, "expectation") if r.entity == "frame"]
    # DECLARED gap: the cycle the program first comes back, T5 meets the frame
    # before the store's arrival that tells the mind its datum's id, so that one
    # expectation is not yet attributed. From then on every one is the program's.
    assert [e.held_by for e in expectations] == [(), (), ("written-0-0",)]


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
        "entity": "region",
        "status": {"stateFrom": "NOT_FINISHED", "stateTo": state, "levelsDelta": levels, "depthDelta": 0},
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
    # Both sides of the one mismatch (v0.3.5): the status that returned, and the
    # status the standing expectation was.
    assert [(r.event.source_id, r.datum_id) for r in scars] == [("region", "signal-1-0"), ("region", "signal-0-0")], \
        "the status changed against 'it stays as it was'"
    # A mismatch on any channel sets the mind thinking, the status's too.
    assert len(model.prompts) == 1 and [t.on for t in wm.thoughts] == ["status"]


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
    assert [(r.event.source_id, r.datum_id) for r in scars] == [("region", "signal-3-0"), ("region", "signal-2-0")], \
        "what the region said still collides, and so does the status expected"


SAYS_LEVEL = '''
def predict(grid, action, x=None, y=None):
    return {"grid": [row[:] for row in grid], "status": {"levelsDelta": 1}}
'''


def test_a_program_that_says_the_status_is_what_meets_the_status_when_it_fails():
    model = Script(SAYS_LEVEL, SAYS_LEVEL)
    wm, cycle, data, events = loop(model)
    run(cycle, frame(lit(0), lit(1)), status())            # nothing-changes fails: SAYS_LEVEL written
    run(cycle, frame(lit(1), lit(1)), status())            # arrives; its grid holds, its level does not
    run(cycle, frame(lit(1), lit(1)), status(levels=1))    # a level comes, as it said: nothing to meet
    status_lines = [r for r in of_kind(events, "expectation") if r.entity == "region"]
    assert status_lines[-1].held_by == ("signal-1-1", "written-0-0"), \
        "the status expected is the status it stands on and the program that said the level"
    moves = [(r.from_, r.to, r.cycle_mark) for r in of_kind(events, "provenance") if r.datum_id == "written-0-0"]
    assert ("running", "scar", 1) not in moves, "cycle 1: not yet known as the program's (the declared gap)"
    scarred = {(r.datum_id, r.anchor.cycle) for r in events.all() if type(r).__name__ == "EventRecord"}
    assert ("written-0-0", 2) not in scarred, "cycle 2: it said a level and a level came"
    assert [t.on for t in wm.thoughts] == ["frame", "status"], "cycle 1: the level it said did not come"
    run(cycle, frame(lit(1), lit(1)), status())            # it says a level again; none comes
    scarred = {(r.datum_id, r.anchor.cycle) for r in events.all() if type(r).__name__ == "EventRecord"}
    assert ("written-0-0", 3) in scarred and ("signal-3-1", 3) in scarred, \
        "both sides of the status mismatch: the report that came, and the program that said otherwise"



def test_the_plain_prompt_is_the_grid_alone_as_before():
    from arc3.mind import PROMPT_PLAIN

    model = Script(RIGHT)
    wm = create_mind(ModelEndpoint(), chat_fn=model, prompt="plain")
    rule = mind_rule(wm)
    data, events = create_data_store(), create_event_log()
    cycle = create_cycle(
        layers=Layers(t1=create_t1(), t2=create_t2(), t3=create_t3(transducers()), t4=create_t4(),
                      t5=create_t5(predict=rule), t6=create_t6(), t7=create_t7(), t8=create_t8()),
        glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=data, events=events,
        initial_emission=Emission(action="boot"), admit=admit,
    )
    run(cycle, frame(lit(0), lit(1)), status())
    shown = model.prompts[0][0]["content"]
    t = Transition(before=lit(0), action=1, x=None, y=None, after=lit(1))
    assert shown == PROMPT_PLAIN.format(evidence=render_evidence([t])), "word for word, no report, no asking"
    assert "ASK" not in shown and "game:" not in shown
