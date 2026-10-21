"""The language inducer — a language model the mind learns with, in the loop.

The 3x3 "game" of the learning mind's tests: ACTION1 moves the lit cell a step
right, ACTION2 a step left; row 2, column 0 is a clock. A scripted model stands in
for the served one. The mind's learning holds, weighs and chooses; the model
writes programs — hypotheses, and how the grid is read — and only when no
hypothesis held foresaw a step (LOG.md, 2026-09-28).
"""

from __future__ import annotations

import pytest

from arc3.decisions import situation_fit
from arc3.organs import ARC_ORGANS
from arc3.task import MIND_TASK, TASK_CUE
from mind.learning import HYPOTHESIS_TAGS
from mind.mind import Mind, mind_rule
from mind.models.language import READING_TAGS, LanguageInducer, identity as grid_key
from mind.organs import Step
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
from tests.test_arc3_learning_mind import frame, lit, of_kind, run, status

# How the game behaves, as a model that got it right would write it.
RIGHT = '''
def predict(grid, action, x, y):
    g = [row[:] for row in grid]
    c = g[0].index(1) if 1 in g[0] else 0
    n = min(2, max(0, c + (1 if action == 1 else -1 if action == 2 else 0)))
    g[0] = [1 if i == n else 0 for i in range(3)]
    return g

def where(grid):
    g = [row[:] for row in grid]
    g[2][0] = -1
    return g
'''

# A program that says nothing ever changes: from a step that changed, no hypothesis.
STILL = '''
def predict(grid, action, x, y):
    return [row[:] for row in grid]
'''


@pytest.fixture(autouse=True)
def one_answer_an_asking(monkeypatch):
    """These tests judge one answer an asking; the model writing again within an
    asking has tests of its own (below), which set MAX_REVISIONS back."""
    import mind.models.language as language
    monkeypatch.setattr(language, "MAX_REVISIONS", 0)


class Script:
    """A served model, scripted: each answer in turn; what it was shown, kept."""

    def __init__(self, *answers: str) -> None:
        self.answers = list(answers)
        self.shown: list[list[dict[str, str]]] = []

    def __call__(self, endpoint, messages):
        self.shown.append(messages)
        if not self.answers:
            raise RuntimeError("no more answers")
        return self.answers.pop(0), {"completion_tokens": 10, "seconds": 0.1}


def block(code: str) -> str:
    return f"Here it is.\n```python\n{code}```\n"


def loop(script: Script, told: bool = True):
    """The loop, the mind seated; `told`: the task's words given now — else later,
    as in a run, where the mind recalls them after its first cycle."""
    inducer = LanguageInducer(ARC_ORGANS, chat_fn=script)
    mind = Mind(inducer, ARC_ORGANS, priors={"task": TASK_CUE})
    if told:
        mind.receive("task", MIND_TASK.payload, None)
    data, events = create_data_store(), create_event_log()
    cycle = create_cycle(
        layers=Layers(
            t1=create_t1(), t2=create_t2(), t3=create_t3(transducers()), t4=create_t4(),
            t5=create_t5(predict=mind_rule(mind), fit=situation_fit), t6=create_t6(), t7=create_t7(), t8=create_t8(),
        ),
        glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=data, events=events,
        initial_emission=Emission(action="boot"), admit=admit,
    )
    return mind, inducer, cycle, data


def test_the_model_writes_a_program_only_on_a_step_no_hypothesis_held_foresaw():
    script = Script(block(RIGHT))
    mind, inducer, cycle, data = loop(script)
    run(cycle, frame(lit(2), lit(2, 1)), status())                      # at the edge: only the clock; not foreseen
    run(cycle, frame(lit(2, 1), lit(1), action=2), status(action=2))    # what it commanded, foreseen
    run(cycle, frame(lit(1), lit(0, 1), action=2), status(action=2))    # and again
    assert len(script.shown) == 1, "asked once: every later step was foreseen by what it wrote"
    programs = [d for _, d in of_kind(data, "hypothesis") if d.payload.get("form") == "program"]
    assert programs and programs[0].open == {**HYPOTHESIS_TAGS, "object": "frame"}
    assert programs[0].payload["code"] == RIGHT, "the program is data, whole"
    assert mind.learning.holds_by_situation[1:] == [1, 1], \
        "the mind expected by the program, where it had never stood, as its where reads the grid"
    assert mind.holds[-1] == 1, \
        "where it expected by the program, the frame held: the clock its where reads out is expected nothing of"


def test_it_is_shown_the_steps_seen_and_the_step_not_foreseen():
    script = Script(block(STILL), block(RIGHT))
    mind, inducer, cycle, data = loop(script)
    run(cycle, frame(lit(0), lit(1)), status())
    run(cycle, frame(lit(1), lit(2)), status())
    user = script.shown[1][0]["content"]   # one message: the last answer was no program
    assert "#0 ACTION1" in user and "#1 ACTION1" in user, "the recent steps, oldest first"
    assert "No program you wrote foresaw the last step." in user


def test_a_program_that_does_not_bear_out_its_step_is_no_hypothesis_and_says_why():
    script = Script(block(STILL), block(RIGHT))
    mind, inducer, cycle, data = loop(script)
    run(cycle, frame(lit(0), lit(1)), status())
    assert not [d for _, d in of_kind(data, "hypothesis") if d.payload.get("form") == "program"]
    answer = [d for _, d in of_kind(data, "thought")][-1]
    assert answer.payload["program"] is None and "does not give" in answer.payload["why_not"]
    assert answer.payload["text"] == block(STILL), "the answer is kept whole"
    run(cycle, frame(lit(1), lit(2)), status())
    assert len(script.shown) == 2, "still not foreseen: asked again"


def test_its_where_is_how_the_grid_is_read_and_a_change_of_reading_is_data():
    script = Script(block(RIGHT))
    mind, inducer, cycle, data = loop(script)
    assert inducer.situation(lit(1, 0)) != inducer.situation(lit(1, 1)), "before any program: the grid as it came"
    run(cycle, frame(lit(2), lit(2, 1)), status())   # the clock, changing where nothing else did
    assert inducer.situation(lit(1, 0)) == inducer.situation(lit(1, 1)), "the clock cell, read out by its where"
    readings = of_kind(data, "reading")
    assert readings and readings[0][1].open == READING_TAGS
    assert readings[0][1].payload["where"] is True


def test_its_targets_are_where_an_act_that_takes_a_cell_may_be_put():
    targets = RIGHT + '''
def targets(grid):
    return [(c, 0) for c in range(3) if grid[0][c] == 1]
'''
    inducer = LanguageInducer(ARC_ORGANS, chat_fn=Script(block(targets)))
    inducer.receive_prior("task", MIND_TASK.payload)
    assert [a for a, _ in inducer.candidates(grid_key(lit(1)), lit(1), (6,))] == [], "no program: no cell"
    inducer.induce(grid_key(lit(0)), (1, None, None), lit(0), lit(1))
    situation = inducer.situation(lit(1))
    assert inducer.candidates(situation, lit(1), (1, 6)) == [((1, None, None), ("act", 1)),
                                                            ((6, 1, 0), ("click",))]


def test_a_model_that_does_not_answer_leaves_the_mind_learning_as_before():
    script = Script()   # it raises
    mind, inducer, cycle, data = loop(script)
    run(cycle, frame(lit(0), lit(1)), status())
    run(cycle, frame(lit(1), lit(0), action=2), status(action=2))
    answer = [d for _, d in of_kind(data, "thought")][-1]
    assert answer.payload["program"] is None and "did not answer" in answer.payload["why_not"]
    assert of_kind(data, "hypothesis") == [] and len(of_kind(data, "experience")) == 2, \
        "no program, and what it met is the mind's experience still"
    assert mind.commands[-1][1] is not None, "and the mind commands"


def test_a_program_predicts_wherever_it_applies_and_is_weighed_there():
    inducer = LanguageInducer(ARC_ORGANS, chat_fn=Script(block(RIGHT)))
    inducer.receive_prior("task", MIND_TASK.payload)
    forms = inducer.induce(grid_key(lit(0)), (1, None, None), lit(0), lit(1),
                           evidence=((Step(lit(0), (1, None, None), lit(1)), None),))
    program = forms[0]
    assert inducer.scope(program, lambda raw: raw) == ("program",)
    said = inducer.predict(program, "anywhere", lit(1), (2, None, None), lambda raw: raw)
    assert said is not None and said.state == lit(0)


def test_what_it_is_told_is_the_prior_and_it_is_asked_nothing_before():
    script = Script(block(STILL), block(RIGHT))
    inducer = LanguageInducer(ARC_ORGANS, chat_fn=script)
    step = (Step(lit(0), (1, None, None), lit(1)), None)
    assert inducer.induce(grid_key(lit(0)), (1, None, None), lit(0), lit(1), evidence=(step,))[1:] == []
    assert script.shown == [], "not told yet: not asked"
    inducer.receive_prior("task", MIND_TASK.payload)
    inducer.induce(grid_key(lit(0)), (1, None, None), lit(0), lit(1), evidence=(step,))
    first = script.shown[0][0]["content"]
    assert "region" in first and "game" not in first.lower(), "no word of a game (Plone, 2026-09-28)"
    assert "ACTION1" in first and "ACTION6 also carries a cell" in first, "the acts, as the host declares them"
    assert "propose" not in first and "GOAL" not in first and "working toward" not in first, \
        "no aim told: the mind has told it none yet"


def test_its_answers_name_the_prior_among_what_they_were_built_from():
    from mind.learning import Learning
    learning = Learning(LanguageInducer(ARC_ORGANS, chat_fn=Script(block(RIGHT))), ARC_ORGANS,
                        priors={"task": TASK_CUE})
    learning.receive_prior("task", MIND_TASK.payload, "prior:mind-task")
    writes = learning.observe(Step(lit(0), (1, None, None), lit(1)), "unit", None, ("unit",), on_report=False)
    answers = [w for w in writes if (w.tags or {}).get("kind") == "thought"]
    assert answers and answers[0].built_from == ("unit", ("prior", "task")), \
        "built from the step it was asked on and the words it was told"


def test_the_program_it_wrote_last_is_shown_with_how_it_did():
    inducer = LanguageInducer(ARC_ORGANS, chat_fn=(script := Script(block(RIGHT), block(RIGHT))))
    inducer.receive_prior("task", MIND_TASK.payload)
    one = (Step(lit(0), (1, None, None), lit(1)), None)
    two = (Step(lit(1), (2, None, None), lit(1)), None)   # not what RIGHT says
    inducer.induce(grid_key(lit(0)), (1, None, None), lit(0), lit(1), evidence=(one,))
    inducer.induce(grid_key(lit(1)), (2, None, None), lit(1), lit(1), evidence=(one, two))
    shown = script.shown[1]
    assert [m["role"] for m in shown] == ["user", "assistant", "user"], "as the earlier form was shown"
    assert shown[1]["content"] == f"```python\n{RIGHT}```"
    assert shown[2]["content"].startswith("Your predict was run on those steps. It got 1/2 exactly right.")


def test_the_mind_tells_the_model_what_the_program_is_for():
    # Plone, 2026-09-28: the model has no aim; the mind tells it what it computes
    # for — the aim it holds, which takes the goal's value.
    script = Script(block(STILL))
    mind, inducer, cycle, data = loop(script)
    run(cycle, frame(lit(0), lit(1)), status())
    first = script.shown[0][0]["content"]
    assert "The program is for a mind working toward this: the region reports levelsDelta 1." in first


def test_a_fence_inside_a_docstring_does_not_close_the_block():
    from mind.models.language import extract_code
    code = 'def predict(grid, action, x=None, y=None):\n    """Like this:\n    ```\n    x\n    ```\n    """\n    return grid\n'
    assert extract_code(f"Here it is.\n```python\n{code}```\n") == code
    assert extract_code("    ```python\n    x = 1\n    ```") == "    x = 1\n    ", "all fences indented: read as before"


def test_an_abandoned_block_before_a_whole_one_is_not_read():
    from mind.models.language import extract_code
    text = ("```python\ndef predict(grid, action):\n    \"\"\"\n    thinking, never closed\n\n"
            "```python\ndef predict(grid, action):\n    return grid\n```\n")
    assert extract_code(text) == "def predict(grid, action):\n    return grid\n"


# What version 4's model wrote, in this game (LOG.md, 2026-10-19): a predict that
# changes nothing, and a where that sets to -1 the cells the act moves.
HIDES = '''
def predict(grid, action, x, y):
    return [row[:] for row in grid]

def where(grid):
    g = [row[:] for row in grid]
    g[0] = [-1, -1, -1]
    g[2][0] = -1
    return g
'''

# Right about everything, the clock too, with a where that also hides the lit row.
EXACT = '''
def predict(grid, action, x, y):
    g = [row[:] for row in grid]
    c = g[0].index(1) if 1 in g[0] else 0
    n = min(2, max(0, c + (1 if action == 1 else -1 if action == 2 else 0)))
    g[0] = [1 if i == n else 0 for i in range(3)]
    g[2][0] = 1 - g[2][0]
    return g

def where(grid):
    g = [row[:] for row in grid]
    g[0] = [-1, -1, -1]
    g[2][0] = -1
    return g
'''

STEPS = ((Step(lit(2), (1, None, None), lit(2, 1)), None), (Step(lit(2, 1), (2, None, None), lit(1)), None))


def test_a_program_is_not_judged_by_a_where_the_steps_do_not_bear_out():
    inducer = LanguageInducer(ARC_ORGANS, chat_fn=Script(block(HIDES)))
    mind = Mind(inducer, ARC_ORGANS, priors={"task": TASK_CUE})
    mind.receive("task", MIND_TASK.payload, None)
    forms = inducer.induce(grid_key(lit(2, 1)), (2, None, None), lit(2, 1), lit(1), evidence=STEPS)
    assert forms[1:] == [], "its predict changes nothing; read through its own where it would have matched"
    answer = inducer.answers[-1]
    assert answer["program"] is None and "does not give" in answer["why_not"]
    assert "rows 0-0" in answer["where_not"], "the lit row never changes alone, and stays put at the edge"
    assert inducer.situation(lit(0)) != inducer.situation(lit(1)), "no state read as another"


def test_the_part_of_a_where_the_steps_bear_out_is_kept_and_stays_kept_from_memory():
    inducer = LanguageInducer(ARC_ORGANS, chat_fn=Script(block(EXACT)))
    mind = Mind(inducer, ARC_ORGANS, priors={"task": TASK_CUE})
    mind.receive("task", MIND_TASK.payload, None)
    forms = inducer.induce(grid_key(lit(2, 1)), (2, None, None), lit(2, 1), lit(1), evidence=STEPS)
    program = forms[-1]
    assert program.where_cells == {(2, 0)}, "the clock borne out and kept; the lit row struck"
    assert "rows 0-0" in inducer.answers[-1]["where_not"] and "the rest kept" in inducer.answers[-1]["where_not"]
    assert inducer.situation(lit(0)) != inducer.situation(lit(1)), "the lit row read"
    assert inducer.situation(lit(1, 0)) == inducer.situation(lit(1, 1)), "the clock read out"
    payload = inducer.describe(program, lambda raw: raw)
    assert payload["where"] is True and payload["where_cells"] == [[2, 0]]
    back = inducer.restore(payload)
    assert back.where_cells == {(2, 0)} and back.where(lit(1, 1))[0] == [0, 1, 0], "struck again from memory"


def test_a_where_with_no_region_borne_out_is_set_aside_whole():
    hides_only_the_row = HIDES.replace("    g[2][0] = -1\n", "")
    inducer = LanguageInducer(ARC_ORGANS, chat_fn=Script(block(hides_only_the_row.replace(
        "return [row[:] for row in grid]", "return [row[:] for row in grid]"))))
    mind = Mind(inducer, ARC_ORGANS, priors={"task": TASK_CUE})
    mind.receive("task", MIND_TASK.payload, None)
    inducer.induce(grid_key(lit(2, 1)), (2, None, None), lit(2, 1), lit(1), evidence=STEPS)
    assert "the rest kept" not in inducer.answers[-1]["where_not"]
    assert inducer.situation(lit(1, 0)) != inducer.situation(lit(1, 1)), "nothing read out"


def test_the_model_is_told_what_its_functions_are_given():
    script = Script(block(STILL))
    mind, inducer, cycle, data = loop(script)
    run(cycle, frame(lit(0), lit(1)), status())
    words = script.shown[0][0]["content"]
    assert "a list of 3 rows, each a list of 3 integers 0-15" in words
    assert "ACTION1 is 1" in words and "ACTION6 is 6" in words


def test_a_where_is_borne_out_by_every_step_the_mind_gives_not_only_those_shown():
    import mind.models.language as language
    inducer = LanguageInducer(ARC_ORGANS, chat_fn=Script(block(RIGHT)))
    mind = Mind(inducer, ARC_ORGANS, priors={"task": TASK_CUE})
    mind.receive("task", MIND_TASK.payload, None)
    blocked = (Step(lit(2), (1, None, None), lit(2, 1)), None)              # only the clock: it bears the where out
    moves = [(Step(lit(c, c), (1, None, None), lit(c + 1, c + 1)), None) for c in (0, 1)] * 13
    shown_before = language.MAX_SHOWN
    try:
        language.MAX_SHOWN = 4                                                # the blocked step not shown
        inducer.induce(grid_key(lit(1, 1)), (1, None, None), lit(1, 1), lit(2, 2), evidence=(blocked, *moves))
    finally:
        language.MAX_SHOWN = shown_before
    answer = inducer.answers[-1]
    assert answer["program"] is not None and answer["where_not"] is None
    assert inducer.situation(lit(1, 0)) == inducer.situation(lit(1, 1)), "the clock read out"


def test_what_it_expects_is_the_grid_as_its_where_reads_it():
    script = Script(block(RIGHT))
    mind, inducer, cycle, data = loop(script)
    assert inducer.as_read(lit(1, 1)) == lit(1, 1), "before a reading it holds: the grid as it came"
    run(cycle, frame(lit(2), lit(2, 1)), status())                            # the where borne out
    assert inducer.as_read(lit(1, 1)) == [[0, 1, 0], [0, 0, 0], [None, 0, 0]], "the clock cell, left out"


# A program written from a state alone: where an act that takes a cell may be put.
NAMES = '''
def predict(grid, action, x, y):
    return [row[:] for row in grid]

def where(grid):
    return [[-1] * len(row) for row in grid]

def targets(grid):
    return [(1, 0), (2, 0)]
'''


def clicks_only(script: Script):
    """A run's start in a region of clicks only: the start-up's return before the
    task's words, then a cycle in which the body has nothing it can do."""
    mind, inducer, cycle, data = loop(script, told=False)
    run(cycle, frame(lit(0), lit(0), action=0), status(action=0, affords=(6,)))
    mind.receive("task", MIND_TASK.payload, None)
    run(cycle, status(action=0, affords=(6,)))
    return mind, inducer, cycle, data


def test_with_nothing_it_can_do_it_asks_its_model_what_can_be_done_here():
    script = Script(block(NAMES))
    mind, inducer, cycle, data = clicks_only(script)
    assert len(script.shown) == 1, "asked while the body waited"
    words = script.shown[0][0]["content"]
    assert "No step has been seen yet" in words and "Starting from this grid" in words
    assert mind.commands[-1][1] == (6, 1, 0), "it commands at a cell its model named"
    thought = [d for _, d in of_kind(data, "thought") if d.payload.get("on") == "nothing to do"]
    assert thought and thought[0].payload["text"] == block(NAMES), "the answer kept whole"
    assert "no step" in thought[0].payload["where_not"], "a where no step bears out is set aside"
    reading = [d for _, d in of_kind(data, "reading") if d.payload.get("on") == "nothing to do"]
    assert reading and reading[0].payload["code"] == NAMES and reading[0].payload["where"] is False
    assert not of_kind(data, "hypothesis"), "no hypothesis: no step was met to build one from"


def test_it_asks_once_in_a_situation_and_not_where_it_can_act():
    script = Script(block(STILL))                                                 # names no cell
    mind, inducer, cycle, data = clicks_only(script)
    run(cycle, status(action=0, affords=(6,)))
    assert len(script.shown) == 1, "asked once where it stands, though it still can do nothing"
    assert mind.commands[-1][1] is None, "and the body waits"
    mind2, inducer2, cycle2, _ = loop(Script(block(STILL)))
    run(cycle2, frame(lit(0), lit(1)), status())                                 # it can act: asked on the step only
    assert [a["on"] for a in inducer2.answers] == ["not foreseen"], "never asked what can be done where it can act"


def test_an_act_never_once_taken_is_not_put_last_by_what_a_hypothesis_says_of_it():
    # Right about acts 1 and 2; says act 3 and 4 change nothing, never having met them.
    two_acts = RIGHT.replace("    g = [row[:] for row in grid]\n    c =",
                             "    g = [row[:] for row in grid]\n    if action not in (1, 2):\n        return g\n    c =", 1)
    script = Script(block(two_acts))
    mind, inducer, cycle, data = loop(script)
    run(cycle, frame(lit(2), lit(2, 1)), status(affords=(1, 2, 3, 4)))
    run(cycle, frame(lit(2, 1), lit(1), action=2), status(action=2, affords=(1, 2, 3, 4)))
    assert not mind.learning._foreseen(mind.learning._here, (3, None, None)), "never taken: not foreseen"
    assert mind.commands[-1][1] == (3, None, None), \
        "of the acts not yet taken here, the one never taken anywhere, most wanted, is commanded"



def revising(monkeypatch, n: int = 2) -> None:
    import mind.models.language as language
    monkeypatch.setattr(language, "MAX_REVISIONS", n)


def test_a_program_not_held_is_run_on_the_steps_and_the_model_writes_again(monkeypatch):
    revising(monkeypatch)
    script = Script(block(STILL), block(RIGHT))
    mind, inducer, cycle, data = loop(script)
    run(cycle, frame(lit(0), lit(1)), status())
    assert len(script.shown) == 2, "asked once, written again within the asking"
    again = script.shown[1]
    assert again[-2] == {"role": "assistant", "content": block(STILL)}
    assert "It got 0/1 exactly right" in again[-1]["content"], "told where its program missed, run on the steps"
    assert [(a["round"], a["program"] is None) for a in inducer.answers] == [(0, True), (1, False)]
    assert [d for _, d in of_kind(data, "hypothesis") if d.payload.get("form") == "program"], "the second held"
    assert len([d for _, d in of_kind(data, "thought") if "round" in d.payload]) == 2, "each answer kept whole"


def test_a_program_that_will_not_run_is_told_why_and_written_again(monkeypatch):
    revising(monkeypatch)
    script = Script(block("def predict(grid, action, x, y)\n    return grid\n"), block(RIGHT))   # will not load
    mind, inducer, cycle, data = loop(script)
    run(cycle, frame(lit(0), lit(1)), status())
    assert "could not be run on those steps" in script.shown[1][-1]["content"]
    assert inducer.answers[-1]["program"] is not None


def test_it_writes_again_at_most_max_revisions_times(monkeypatch):
    revising(monkeypatch, 2)
    script = Script(block(STILL), block(STILL), block(STILL), block(RIGHT))
    mind, inducer, cycle, data = loop(script)
    run(cycle, frame(lit(0), lit(1)), status())
    assert len(script.shown) == 3 and [a["round"] for a in inducer.answers] == [0, 1, 2]
    assert not [d for _, d in of_kind(data, "hypothesis") if d.payload.get("form") == "program"]



def test_each_round_is_shown_its_last_answer_only_not_every_round_before(monkeypatch):
    revising(monkeypatch, 2)
    script = Script(block(STILL), block(STILL + "# again"), block(RIGHT))
    mind, inducer, cycle, data = loop(script)
    run(cycle, frame(lit(0), lit(1)), status())
    third = script.shown[2]
    assert len(third) == len(script.shown[1]), "the third round no longer than the second"
    assert third[-2]["content"] == block(STILL + "# again"), "shown its last answer"


LOOK = '''
def look(steps):
    for s in steps:
        changed = [(r, c) for r in range(len(s["before"])) for c in range(len(s["before"][r]))
                   if s["before"][r][c] != s["after"][r][c]]
        print(s["action"], changed)
'''


def test_it_looks_at_the_steps_with_its_own_code_before_it_writes():
    script = Script(block(LOOK), block(RIGHT))
    mind, inducer, cycle, data = loop(script)
    run(cycle, frame(lit(0), lit(1)), status())
    assert "may look at the steps with code" in script.shown[0][0]["content"]
    told = script.shown[1][-1]["content"]
    assert "look(steps) printed:" in told and "1 [(0, 0), (0, 1)]" in told, "what its own code printed, run on the step"
    looks = [d for _, d in of_kind(data, "thought") if "look" in d.payload]
    assert looks and looks[0].payload["text"] == block(LOOK) and "1 [(0, 0), (0, 1)]" in looks[0].payload["printed"]
    assert [d for _, d in of_kind(data, "hypothesis") if d.payload.get("form") == "program"], "then it wrote, held"


def test_it_looks_at_most_max_looks_times_then_must_write(monkeypatch):
    import mind.models.language as language
    monkeypatch.setattr(language, "MAX_LOOKS", 1)
    script = Script(block(LOOK), block(LOOK), block(RIGHT))
    mind, inducer, cycle, data = loop(script)
    run(cycle, frame(lit(0), lit(1)), status())
    assert len(script.shown) == 2, "one look, then a look taken for its functions: it defines no predict"
    assert inducer.answers[-1]["why_not"] == "defines no predict()"


def test_a_look_that_fails_is_told_so():
    script = Script(block("def look(steps):\n    print(steps[99])\n"), block(RIGHT))
    mind, inducer, cycle, data = loop(script)
    run(cycle, frame(lit(0), lit(1)), status())
    assert "look raised IndexError" in script.shown[1][-1]["content"]


def test_told_to_answer_with_its_code_alone_only_when_so_seated():
    script = Script(block(STILL))
    mind, inducer, cycle, data = loop(script)
    run(cycle, frame(lit(0), lit(1)), status())
    assert "code block alone" not in script.shown[0][0]["content"], "by default, nothing said of its prose"
    script2 = Script(block(STILL))
    inducer2 = LanguageInducer(ARC_ORGANS, chat_fn=script2, code_only=True)
    mind2 = Mind(inducer2, ARC_ORGANS, priors={"task": TASK_CUE})
    mind2.receive("task", MIND_TASK.payload, None)
    inducer2.induce(grid_key(lit(0)), (1, None, None), lit(0), lit(1))
    assert "Answer with the one ```python code block alone" in script2.shown[0][0]["content"]
