"""How far an inducer's hypotheses reach: a run's steps replayed through the mind's learning.

    python scripts/replay_inducer.py scripts/data/<run> [--inducer grid ...]
    python scripts/replay_inducer.py scripts/data/<run> --inducer language --program PROBE.json [--propose]

The steps a run took (`steps_of.py`) are shown, in order, to the mind's learning
(`mind/learning.py`) with each inducer named: it expects, then learns from what
came. The acts are the run's, so every inducer meets the same steps; what differs
is only what it expected. Counted per inducer, off the clock:

  expected   steps it held an expectation for, and of those right
  unseen     steps from a situation and act it had never met (where no
             experience applies), it held an expectation for, and of those
             right — the direct evidence that what it learned reaches further
  hypotheses how many it holds, and how many of them hold

`--inducer language` has no served model here: a scripted one answers every
question with the program in PROBE.json (a probe's `best.code`, written outside
the loop on 2026-09-24), under an adapter giving its `predict(grid, action)` the
inducer's `predict(grid, action, x, y)`. A fixture for the mechanism — what the
learning does with a program, what it costs — never evidence about a model.
`--propose` also has the learning choose at each step (the run's act is taken
all the same) and times it: the look-ahead runs the held programs.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from _paths import SRC  # noqa: E402 — see scripts/_paths.py

sys.path.insert(0, str(SRC))

from arc3.organs import ARC_ORGANS  # noqa: E402
from arc3.task import MIND_TASK, TASK_CUE  # noqa: E402
from mind.learning import Learning  # noqa: E402
from mind.models.grid import GridInducer  # noqa: E402
from mind.models.base import Context  # noqa: E402
from mind.models.language_inducer import LanguageInducer  # noqa: E402
from mind.organs import AsRead, Step  # noqa: E402
from steps_of import steps_of  # noqa: E402

INDUCERS = {"grid": GridInducer, "language": LanguageInducer}

# The probe's program takes (grid, action); the inducer calls (grid, action, x, y).
ADAPTER = """

_probe_predict = predict


def predict(grid, action, x=None, y=None):
    return _probe_predict(grid, action)
"""


def scripted(program: str):
    """A served model, scripted: every answer is the fixture's program."""
    calls = []

    def chat(endpoint, messages):
        calls.append(len(messages[-1]["content"]))
        return f"```python\n{program}{ADAPTER}```\n", {"completion_tokens": 0, "seconds": 0.0}
    return chat, calls


def replay(run: str, name: str, program: str | None = None, propose: bool = False) -> None:
    calls: list = []
    if name == "language":
        chat, calls = scripted(program or "")
        inducer = LanguageInducer(ARC_ORGANS, chat_fn=chat)
    else:
        inducer = INDUCERS[name](ARC_ORGANS)
    model = Learning(inducer, ARC_ORGANS, priors={"task": TASK_CUE})
    model.receive_prior("task", MIND_TASK.payload, None)
    choosing = 0.0
    expected = right = unseen = unseen_expected = unseen_right = 0
    t0 = time.time()
    for _, before, act, after in steps_of(run):
        step = Step(before=before, act=act, after=after)
        situation = model.inducer.situation(before)
        met = (situation, model.inducer.learnable(act)) in model._edges
        # The kind of act as the mind names it when it chooses (propose is not run).
        for candidate, kind in model.inducer.candidates(situation, before, (act[0],)):
            if candidate == model.inducer.learnable(act):
                model._kind_of[(situation, candidate)] = kind
        e = model.expect(step)
        # What it expected, as it reads it (an expectation is a state as read, since
        # 2026-10-11: `organs.AsRead`), against what came.
        ok = e.by_model and (e.state.matches(after) if isinstance(e.state, AsRead)
                             else model.inducer.situation(e.state) == model.inducer.situation(after))
        expected += int(e.by_model)
        right += int(ok)
        if not met:
            unseen += 1
            unseen_expected += int(e.by_model)
            unseen_right += int(ok)
        model.observe(step, None, None, (), False)
        if propose:
            t = time.time()
            model.propose(Context(on="command", steps_seen=model.steps, seen=[], recalled=[],
                                  offers=tuple(sorted(ARC_ORGANS.acts)), ended=None, remark=None,
                                  remark_unit=None, aim=None, priors={}))
            choosing += time.time() - t
    held = sum(1 for h in model._hypotheses if h.holds)
    print(f"{name:6} expected {expected} (right {right})  unseen {unseen}: expected {unseen_expected}"
          f" (right {unseen_right})  hypotheses {len(model._hypotheses)} (held {held})  {time.time() - t0:.0f} s"
          + (f"  choosing {choosing:.0f} s" if propose else ""))
    if name == "language":
        programs = [h for h in model._hypotheses if type(h.form).__name__ == "ProgramForm"]
        print(f"       model asked {len(calls)} times; programs {len(programs)}: "
              + ", ".join(f"{h.form.digest[:8]} for {h.supports} against {h.fails}" for h in programs))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--inducer", nargs="+", default=["grid"], choices=list(INDUCERS))
    ap.add_argument("--program", default=None, help="for language: a probe's JSON, whose best.code answers")
    ap.add_argument("--propose", action="store_true", help="also choose at each step, and time it")
    a = ap.parse_args()
    program = json.load(open(a.program))["best"]["code"] if a.program else None
    print(a.run)
    for name in a.inducer:
        replay(a.run, name, program, a.propose)
