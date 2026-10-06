"""The language inducer — a language model the mind learns with, in the loop.

The 3x3 "game" of the learning mind's tests: ACTION1 moves the lit cell a step
right, ACTION2 a step left; row 2, column 0 is a clock. A scripted model stands in
for the served one. The mind's learning holds, weighs and chooses; the model
writes programs — hypotheses, and how the grid is read — and only when no
hypothesis held foresaw a step (LOG.md, 2026-09-28).
"""

from __future__ import annotations

from arc3.organs import ARC_ORGANS
from arc3.task import MIND_TASK, TASK_CUE
from mind.learning import HYPOTHESIS_TAGS
from mind.mind import Mind, mind_rule
from mind.models.language_inducer import READING_TAGS, LanguageInducer, identity as grid_key
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


def loop(script: Script):
    inducer = LanguageInducer(ARC_ORGANS, chat_fn=script)
    mind = Mind(inducer, ARC_ORGANS, priors={"task": TASK_CUE})
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
    return mind, inducer, cycle, data


def test_the_model_writes_a_program_only_on_a_step_no_hypothesis_held_foresaw():
    script = Script(block(RIGHT))
    mind, inducer, cycle, data = loop(script)
    run(cycle, frame(lit(0), lit(1)), status())                         # nothing held: not foreseen
    run(cycle, frame(lit(1), lit(2, 1)), status())                      # the program foresees it
    run(cycle, frame(lit(2, 1), lit(1), action=2), status(action=2))    # and this
    assert len(script.shown) == 1, "asked once: every later step was foreseen by what it wrote"
    programs = [d for _, d in of_kind(data, "hypothesis") if d.payload.get("form") == "program"]
    assert programs and programs[0].open == {**HYPOTHESIS_TAGS, "object": "frame"}
    assert programs[0].payload["code"] == RIGHT, "the program is data, whole"
    assert mind.learning.holds_by_situation[1:] == [1, 1], \
        "the mind expected by the program, where it had never stood, as its where reads the grid"
    assert mind.holds[1:] == [0, 0], "the whole grid did not hold: this program does not predict the clock"


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
    run(cycle, frame(lit(0), lit(1)), status())
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
