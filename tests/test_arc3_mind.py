"""The mind — one, the model and its program — in the loop, with a scripted model.

A 3x3 "game": ACTION1 moves the one lit cell a step right. The mind predicts the
frame from the situation alone, thinks when the expectation fails, writes the
program as data, learns its datum's id when it arrives, and revises it — and the
trace a third party reads says so.
"""

from __future__ import annotations

from arc3.mind import (
    PROGRAM_TAGS, THOUGHT_TAGS, ModelEndpoint, Transition,
    compile_program, create_mind, mind_rule, render_evidence, run_program,
)
from arc3.observe import FRAME_CHANNEL, STATUS_CHANNEL, admit, transducers
from arc3.prior import DIRECTIVE
from arc3.aim import MIND_AIM
from arc3.task import MIND_TASK
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


def loop(model: Script, respond=None):
    # What the mind is told, handed in as if recalled; the store's road is tested
    # on its own below.
    wm = create_mind(ModelEndpoint(), chat_fn=model, task=MIND_TASK.payload, aim=MIND_AIM.payload)
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
        **({"respond": respond} if respond is not None else {}),
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
    assert [(w.datum_id, w.built_from) for w in written] == [("written-0-0", ("signal-0-0",)),
                                                              ("written-0-1", ("signal-0-0",))], \
        "the program, and the answer it came in, each say they were built from the frame in front of them"
    answer = data.get("written-0-1")
    assert answer.open == THOUGHT_TAGS and answer.payload["on"] == "frame" and answer.payload["kept"] is True
    assert answer.payload["text"].startswith("```python"), "the answer whole, as the model gave it"

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
    assert "Your predict was run" in model.prompts[1][-1]["content"]
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


# ── the region's own report ──


def status(state: str = "NOT_FINISHED", levels: int = 0, action: int = 1) -> Signal:
    return Signal(source_id=STATUS_CHANNEL, t=1, raw_payload={
        "entity": "region",
        "status": {"stateFrom": "NOT_FINISHED", "stateTo": state, "levelsDelta": levels, "depthDelta": 0},
        "context": f"action:{action}", "affords": [1, 2],
    })


def test_the_status_is_the_standing_expectation_and_its_mismatch_sets_the_mind_thinking():
    model = Script()
    wm, cycle, data, events = loop(model)
    run(cycle, status())
    run(cycle, status(levels=1))                 # a level: the region said something new
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

def propose(grid):
    return (1, None, None)

GOAL = {"aim": "a level", "source": "inferred", "reached_when": {"status": {"levelsDelta": 1}}, "within": 50}
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



# ── what it is told, from its store; what it commands; what the body does ──


PROPOSING = '''
def predict(grid, action, x=None, y=None):
    g = [row[:] for row in grid]
    if action == 1:
        for r, row in enumerate(grid):
            for c, v in enumerate(row):
                if v == 1 and c + 1 < len(row):
                    g[r][c] = 0
                    g[r][c + 1] = 1
    return g

def propose(grid):
    return (1, None, None)

GOAL = {"aim": "the lit cell at the far end", "source": "inferred",
        "reached_when": {"cells": {"0,2": 1}}, "within": 50}
'''


def test_what_it_is_told_comes_from_its_store_and_every_program_names_it():
    from dil.store.tagging_gate import HostDatum, admit_host_data

    model = Script(PROPOSING)
    wm = create_mind(ModelEndpoint(), chat_fn=model)  # told nothing in code
    data, events = create_data_store(), create_event_log()
    for item in (MIND_TASK, MIND_AIM):
        data.put(item.id, admit_host_data(HostDatum(payload=item.payload, admitting_layer=1, open=item.open), 0))
    cycle = create_cycle(
        layers=Layers(t1=create_t1(), t2=create_t2(), t3=create_t3(transducers()), t4=create_t4(),
                      t5=create_t5(predict=mind_rule(wm)), t6=create_t6(), t7=create_t7(), t8=create_t8()),
        glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=data, events=events,
        initial_emission=Emission(action="boot"), admit=admit,
    )
    run(cycle, frame(lit(0), lit(1)))  # a mismatch before it knows what it is for: it asks, and waits
    queries = [r.action for r in of_kind(events, "emission") if r.issuing_layer == 5]
    assert queries == [store_query({"domain": "mind-task"}), store_query({"domain": "mind-aim"})], \
        "what it is for, and what it does with any aim"
    assert model.prompts == [], "the thought waits for what it is for"
    run(cycle, frame(lit(1), lit(2)))  # it arrives from memory; the waiting thought happens
    assert len(model.prompts) == 1
    shown = model.prompts[0][0]["content"]
    assert shown.startswith("You are meeting a game you have not seen before.")
    assert "3x3 cells" in shown, "the grid's own size, not a fixed one"
    written = {t.datum_id: t.built_from for r in of_kind(events, "cycle-seal") for t in r.activity.written}
    assert MIND_TASK.id in written["written-1-0"], "what the mind was told is among what it was built from"
    assert MIND_AIM.id in written["written-1-0"]
    assert "Whatever you are asked to do has an aim." in shown
    assert data.get(MIND_TASK.id).fixed.provenance == "running", "recalled: it ran"


def test_a_block_indented_as_a_whole_still_loads():
    from arc3.mind import compile_functions

    fn, propose = compile_functions("    " + PROPOSING.replace("\n", "\n    "))
    assert fn([[1, 0]], 1) == [[0, 1]] and propose([[1, 0]]) == (1, None, None)


def test_the_mind_commands_as_t5s_test_and_the_body_carries_it_out():
    from arc3.command import carry_out
    from dil.loop.cycle import RespondContext  # noqa: F401 — what link 5 reads

    model = Script(PROPOSING)
    wm, cycle, data, events = loop(model, respond=carry_out)
    first = cycle.run(HostCycleInput(signals=(frame(lit(0), lit(1)), status())))
    assert first.tests == ({"kind": "move", "actionId": 1, "x": None, "y": None},), \
        "from where the game stands, the program it just wrote commands ACTION1"
    from_t5 = [r for r in of_kind(events, "emission") if r.issuing_layer == 5]
    assert from_t5[-1].action == {"kind": "test", "action": first.tests[0]}, "recorded from T5, as a test"
    assert first.response.action == {"kind": "move", "actionId": 1, "x": None, "y": None}, \
        "the body carried out the command, in the same cycle"
    assert wm.commands == [(1, (1, None, None))]


def test_with_no_command_the_mind_thinks_again_while_the_body_waits():
    no_propose = RIGHT  # predicts, proposes nothing
    from arc3.command import carry_out

    model = Script(no_propose, PROPOSING)
    wm, cycle, data, events = loop(model, respond=carry_out)
    result = cycle.run(HostCycleInput(signals=(frame(lit(0), lit(1)), status())))
    assert [t.on for t in wm.thoughts] == ["frame", "no goal"], "it holds no aim: it commands nothing yet"
    last = model.prompts[1][-1]["content"]
    assert "Your program holds no GOAL" in last, "said where the model reads what to do: the last message"
    assert "Your last answer's program was kept; its GOAL was not taken: the program defines no GOAL." in last, \
        "kept, and told so: not told it was not taken"
    assert result.response.action["actionId"] == 1, "the second thought gave a command, and it was carried out"


def test_the_body_carries_out_what_it_can_and_otherwise_stands_still():
    from types import SimpleNamespace

    from arc3.command import WAIT, carry_out

    def ctx(tests, affords=(1, 2, 3), state="NOT_FINISHED", cycle=5):
        sig = Signal(source_id=STATUS_CHANNEL, t=1, raw_payload={
            "entity": "region", "status": {"stateFrom": "NOT_FINISHED", "stateTo": state,
                                           "levelsDelta": 0, "depthDelta": 0},
            "context": "action:1", "affords": list(affords)})
        return SimpleNamespace(cycle=cycle, tests=tuple(tests), host=SimpleNamespace(signals=(sig,)))

    move = lambda a, x=None, y=None: {"kind": "move", "actionId": a, "x": x, "y": y}  # noqa: E731
    assert carry_out(ctx([move(3)]))["actionId"] == 3, "as commanded"
    assert carry_out(ctx([])) == WAIT, "no command: it waits"
    assert carry_out(ctx([], cycle=0))["actionId"] == 0, "cycle 0: start-up is the host's (§4)"
    assert carry_out(ctx([move(4)])) == WAIT, "not afforded: it does not substitute, it waits"
    assert carry_out(ctx([move(0)], affords=()))["actionId"] == 0, "RESET is always open"
    assert carry_out(ctx([move(1)], state="GAME_OVER")) == WAIT, "a terminal frame takes only RESET"
    click = carry_out(ctx([move(6, 5, 9)], affords=(6,)))
    assert (click["actionId"], click["x"], click["y"]) == (6, 5, 9), "the cell it was given"



# ── what propose reads; what the onlooker's objection can change ──


def test_propose_reads_the_steps_just_seen_and_may_reset():
    from arc3.mind import run_propose, steps_of

    over = Transition(before=lit(0), action=1, x=None, y=None, after=lit(1),
                      status={"stateFrom": "NOT_FINISHED", "stateTo": "GAME_OVER", "levelsDelta": 0})
    steps = steps_of([over])
    assert steps == [{"before": lit(0), "action": 1, "x": None, "y": None, "after": lit(1),
                      "state": "GAME_OVER", "levels": 0}]
    reads = lambda grid, steps: (0,) if steps and steps[-1]["state"] == "GAME_OVER" else (1,)  # noqa: E731
    assert run_propose(reads, lit(1), steps) == (0, None, None), "RESET is an action it may propose"
    assert run_propose(reads, lit(1), []) == (1, None, None)
    assert run_propose(lambda grid: (2,), lit(1), steps) == (2, None, None), "one written for the grid alone still runs"
    assert run_propose(lambda grid, steps: "RESET", lit(1), steps) == (0, None, None)
    assert run_propose(lambda grid: (3, 1, 1), lit(1)) == (3, None, None), "only ACTION6 carries a cell"
    assert run_propose(lambda grid: (6, 2, 1), lit(1)) == (6, 2, 1)


SAME_PREDICT_OTHER_MOVE = PROPOSING.replace("return (1, None, None)", "return (2, None, None)")


def test_after_the_onlooker_objects_a_program_that_predicts_as_well_is_kept():
    model = Script(PROPOSING, SAME_PREDICT_OTHER_MOVE)
    wm, cycle, data, events = loop(model)
    run(cycle, frame(lit(0), lit(1)))                   # PROPOSING written
    run(cycle, frame(lit(1), lit(2)))                   # it holds: no thought
    wm.think("onlooker", None, None)                    # the onlooker changed its stance
    assert wm.thoughts[-1].candidate_score == wm.thoughts[-1].held_score
    assert wm.thoughts[-1].adopted and wm.code == SAME_PREDICT_OTHER_MOVE, \
        "its objection is to how the agent acts: a program that acts otherwise and predicts as well is kept"


def test_on_a_frame_mismatch_a_program_that_predicts_only_as_well_is_not_kept():
    model = Script(PROPOSING, SAME_PREDICT_OTHER_MOVE)
    wm, cycle, data, events = loop(model)
    run(cycle, frame(lit(0), lit(1)))
    run(cycle, frame(lit(1), lit(2)))
    wm.think("frame", None, None)
    assert not wm.thoughts[-1].adopted and wm.code == PROPOSING


# ── what the command is for, the game's end, the onlooker's own thought, the answer's fences ──


WANTS_THE_CORNER = PROPOSING.replace("return (1, None, None)", 'return (1, None, None, {"cells": {"0,0": 1}})')
WANTS_NOTHING_ELSE = PROPOSING.replace("return (1, None, None)", "return (2, None, None)")


def test_a_command_that_does_not_bring_about_what_it_was_for_sets_the_mind_thinking():
    model = Script(WANTS_THE_CORNER, WANTS_NOTHING_ELSE)
    wm, cycle, data, events = loop(model)
    run(cycle, frame(lit(0), lit(1)), status())      # written; it commands ACTION1, wanting (0,0) lit
    assert wm.commands[-1] == (1, (1, None, None))
    run(cycle, frame(lit(1), lit(2)), status())      # the grid comes as predicted; the want does not
    assert [t.on for t in wm.thoughts] == ["frame", "want"]
    assert "did not bring about what your propose said it would" in model.prompts[1][0]["content"]
    assert data.get("signal-1-0").fixed.provenance == "scar", "the program's expectation of the step failed"
    assert wm.thoughts[-1].adopted and wm.code == WANTS_NOTHING_ELSE, \
        "met by acting otherwise: a program that predicts as well and commands otherwise is kept"


RESETTING = PROPOSING.replace("return (1, None, None)", "return (0, None, None)")


def test_after_the_game_ends_only_reset_is_a_command_and_the_mind_thinks_for_one():
    from arc3.command import carry_out

    model = Script(PROPOSING, PROPOSING, RESETTING)
    wm, cycle, data, events = loop(model, respond=carry_out)
    result = cycle.run(HostCycleInput(signals=(frame(lit(0), lit(1)), status(state="GAME_OVER"))))
    assert [t.on for t in wm.thoughts] == ["frame", "no command", "no command"], \
        "ACTION1 is offered, but the game has ended: the body would not carry it out, so it is no command"
    assert result.response.action["actionId"] == 0
    told = model.prompts[1][0]["content"]
    assert "The game has ended (GAME_OVER): the only action that can be taken now is RESET (0)." in told
    assert "The game now offers" not in told, "not what the game's own list still says"


def test_the_onlookers_objection_is_thought_on_even_in_a_cycle_already_thought_in():
    from arc3.observe import ONLOOKER_CHANNEL

    def remark(said):
        return Signal(source_id=ONLOOKER_CHANNEL, t=1, raw_payload={"entity": "onlooker", **said})

    model = Script(PROPOSING, PROPOSING, SAME_PREDICT_OTHER_MOVE)
    wm, cycle, data, events = loop(model)
    run(cycle, frame(lit(0), lit(1)), status(), remark({"remark": None}))
    run(cycle, frame(lit(1), lit(1)), status(), remark({"remark": "repeating", "act": {"act": 1}, "since": 0}))
    assert [t.on for t in wm.thoughts] == ["frame", "frame", "onlooker"]
    assert wm.thoughts[-1].adopted and wm.code == SAME_PREDICT_OTHER_MOVE


def test_a_fence_inside_a_docstring_does_not_close_the_block():
    from arc3.mind import extract_code

    code = 'def predict(grid, action, x=None, y=None):\n    """Like this:\n    ```\n    x\n    ```\n    """\n    return grid\n'
    text = f"Here it is.\n```python\n{code}```\nASK {{\"kind\": \"frame\"}}\n"
    assert extract_code(text) == code
    assert extract_code("    ```python\n    x = 1\n    ```") == "    x = 1\n    ", "all fences indented: read as before"


# ── the aim the mind holds itself to ──


GOAL_SOON = PROPOSING.replace('"within": 50', '"within": 1')
GOAL_SOON_OTHER = GOAL_SOON.replace("return (1, None, None)", "return (2, None, None)")


def test_an_aim_not_reached_when_the_program_said_sets_the_mind_thinking_on_the_goal():
    model = Script(GOAL_SOON, GOAL_SOON_OTHER)
    wm, cycle, data, events = loop(model)
    run(cycle, frame(lit(0), lit(1)), status())     # kept; its GOAL falls due one action on
    assert wm._goal["within"] == 1 and wm._goal["source"] == "inferred"
    run(cycle, frame(lit(1), lit(2)), status())     # the grid comes as predicted: (0,2) lit — reached
    assert [t.on for t in wm.thoughts] == ["frame"], "reached when it said: nothing to think on"
    run(cycle, frame(lit(2), lit(2)), status())     # held again from here; ACTION1 at the edge changes nothing
    run(cycle, frame(lit(0), lit(1)), status())     # due, and (0,2) is not lit
    assert wm.thoughts[-1].on == "goal"
    assert "was not reached when you said" in model.prompts[-1][0]["content"]
    assert wm.thoughts[-1].adopted and wm.code == GOAL_SOON_OTHER, "met by acting otherwise"


def test_an_aim_nothing_coming_back_could_show_is_not_one_it_holds():
    from arc3.mind import goal_of

    g = lit(0)
    assert goal_of({"aim": "find out what the aim is", "source": "inferred", "within": 5}, g) is None
    assert goal_of({"aim": "x", "reached_when": {"cells": {"9,9": 1}}, "within": 5}, g) is None, "off the grid"
    assert goal_of({"aim": "x", "reached_when": {"status": {"mood": "good"}}, "within": 5}, g) is None, \
        "not a field the region reports"
    assert goal_of({"aim": "x", "reached_when": {"cells": {"0,1": 1}}, "within": 0}, g) is None
    assert goal_of({"aim": "x", "reached_when": {"cells": {"0,1": 1}}, "within": 3}, g)["source"] == "inferred"


def test_an_aim_that_comes_sooner_than_said_is_thought_on():
    level_later = PROPOSING.replace('"reached_when": {"cells": {"0,2": 1}}, "within": 50',
                                    '"reached_when": {"status": {"levelsDelta": 1}}, "within": 9')
    model = Script(level_later, level_later)
    wm, cycle, data, events = loop(model)
    run(cycle, frame(lit(0), lit(1)), status())            # kept: a level, it says, in nine actions
    run(cycle, frame(lit(1), lit(2)), status(levels=1))    # it comes at once
    assert wm.thoughts[-1].on == "goal"
    assert "came sooner than you said" in model.prompts[-1][0]["content"]


def test_in_a_cycle_the_body_stood_still_the_mind_commands_after_the_onlooker():
    from arc3.command import carry_out
    from arc3.observe import ONLOOKER_CHANNEL

    def remark(said):
        return Signal(source_id=ONLOOKER_CHANNEL, t=1, raw_payload={"entity": "onlooker", **said})

    model = Script(PROPOSING, PROPOSING)
    standing = lambda: ("NOT_FINISHED", (1, 2))  # noqa: E731 — the frame the body stands on
    wm, cycle, data, events = loop(model, respond=lambda ctx: carry_out(ctx, standing=standing))
    cycle.run(HostCycleInput(signals=(frame(lit(0), lit(1)), status(), remark({"remark": None}))))
    assert len(wm.commands) == 1
    still = cycle.run(HostCycleInput(signals=(remark({"remark": "standing still", "since": 1, "for": 1}),),
                                     afforded=frozenset({"onlooker"})))
    assert [t.on for t in wm.thoughts] == ["frame", "onlooker"], "the nudge collides, and it thinks"
    assert len(wm.commands) == 2 and still.response.action["actionId"] == 1, \
        "nothing came from the region, so it commands after what the onlooker said"


NO_GOAL_BETTER = RIGHT + '''
def propose(grid):
    return (1, None, None)
'''


def test_the_aim_is_the_minds_a_better_program_with_none_does_not_take_it_away():
    model = Script(PROPOSING, NO_GOAL_BETTER)
    wm, cycle, data, events = loop(model)
    run(cycle, frame(lit(0), lit(1)), status())
    held = wm._goal
    assert held is not None
    wm.think("no command", None, None, again=True)     # a candidate with no GOAL, predicting as well, and kept
    assert wm.thoughts[-1].adopted and wm.code == NO_GOAL_BETTER
    assert wm._goal == held, "the mind keeps the aim it held"


def test_why_a_goal_is_not_taken_is_said():
    from arc3.mind import goal_check

    assert goal_check(None, lit(0)) == (None, "the program defines no GOAL")
    g, why = goal_check({"aim": "x", "reached_when": {"state": "WIN"}, "within": 3}, lit(0))
    assert g is None and "reached_when names nothing that comes back" in why and "stateTo" in why


def test_an_abandoned_block_before_a_whole_one_is_not_read():
    from arc3.mind import extract_code

    text = ("```python\ndef predict(grid, action):\n    \"\"\"\n    thinking, never closed\n\n"
            "```python\nGOAL = 1\ndef predict(grid, action):\n    return grid\n```\n")
    assert extract_code(text) == "GOAL = 1\ndef predict(grid, action):\n    return grid\n"


CLICK_NOWHERE = PROPOSING.replace("return (1, None, None)", "return (6,)")


def test_an_action6_with_no_cell_is_no_command_for_the_mind_as_for_the_body():
    from arc3.command import carry_out

    click_status = Signal(source_id=STATUS_CHANNEL, t=1, raw_payload={
        "entity": "region", "status": {"stateFrom": "NOT_FINISHED", "stateTo": "NOT_FINISHED",
                                       "levelsDelta": 0, "depthDelta": 0},
        "context": "action:6", "affords": [6]})
    model = Script(CLICK_NOWHERE, CLICK_NOWHERE, CLICK_NOWHERE)
    wm, cycle, data, events = loop(model, respond=carry_out)
    result = cycle.run(HostCycleInput(signals=(frame(lit(0), lit(1)), click_status)))
    assert [t.on for t in wm.thoughts] == ["frame", "no command", "no command"], \
        "the body would not carry it out, so the mind thinks again"
    assert result.response.action.get("actionId") != 6, "no click without a cell reached the body"


def test_a_program_the_model_asks_for_it_reads():
    model = Script(RIGHT, RIGHT, RIGHT, RIGHT, asks={1: 'ASK {"kind": "program"}'})
    wm, cycle, data, events = loop(model)
    run(cycle, frame(lit(0), lit(1)))              # it writes RIGHT
    run(cycle, frame(lit(1), lit(2)))              # RIGHT holds
    run(cycle, frame(lit(2), lit(0), action=2))    # RIGHT fails: it thinks, and asks for programs
    run(cycle, frame(lit(0), lit(2), action=2))    # the store answers with the program it held before
    run(cycle, frame(lit(2), lit(1), action=2))    # read at the thought after
    assert "- a program (version 1):" in model.prompts[-1][0]["content"], "asked for, and so read"


def test_what_the_mind_just_wrote_is_no_answer_to_what_it_asked():
    model = Script(PROPOSING, PROPOSING, asks={0: 'ASK {"kind": "thought"}\nASK {"kind": "program"}'})
    wm, cycle, data, events = loop(model)
    run(cycle, frame(lit(0), lit(1)), status())            # it asks; the store holds no thought, no program
    run(cycle, frame(lit(1), lit(2)), status())            # its own writes come back
    run(cycle, frame(lit(2), lit(0), action=2), status())  # it thinks again
    last = model.prompts[-1][0]["content"]
    assert "an answer you gave" not in last and "a program (version" not in last, \
        "memory is what the store held before the cycle that asked"
    written = {t.datum_id: t.built_from for r in of_kind(events, "cycle-seal") for t in r.activity.written}
    assert not any(b.startswith("written-") for bf in written.values() for b in bf)


def test_when_how_it_acts_set_it_thinking_the_same_action_again_is_not_kept():
    same = PROPOSING.replace('"aim": "the lit cell at the far end"', '"aim": "the same, again"')
    model = Script(PROPOSING, same)
    wm, cycle, data, events = loop(model)
    run(cycle, frame(lit(0), lit(1)), status())
    run(cycle, frame(lit(1), lit(2)), status())
    wm.think("onlooker", None, None)
    assert not wm.thoughts[-1].adopted and wm.code == PROPOSING, "it proposed ACTION1 again"
    assert "it proposed ACTION1 again" in wm.thoughts[-1].note


PROPOSES_NOTHING = PROPOSING.replace("return (1, None, None)", "return None")


def test_a_candidate_that_proposes_nothing_is_not_said_to_have_proposed_the_same():
    model = Script(PROPOSING, PROPOSES_NOTHING)
    wm, cycle, data, events = loop(model)
    run(cycle, frame(lit(0), lit(1)), status())
    run(cycle, frame(lit(1), lit(2)), status())
    wm.think("onlooker", None, None)
    assert not wm.thoughts[-1].adopted
    assert wm.thoughts[-1].note == "its propose gave no action from where the game stands now"
    assert wm._last_note.startswith("Your last answer was not taken: its propose gave no action")
