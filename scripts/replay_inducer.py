"""How far an inducer's hypotheses reach: a run's steps replayed through the mind's learning.

    python scripts/replay_inducer.py scripts/data/<run> [--inducer exact|grid ...]

The steps a run took (`steps_of.py`) are shown, in order, to the mind's learning
(`mind/learning.py`) with each inducer named: it expects, then learns from what
came. The acts are the run's, so every inducer meets the same steps; what differs
is only what it expected. Counted per inducer, off the clock:

  expected   steps it held an expectation for, and of those right
  unseen     steps from a situation and act it had never met (where an exact
             hypothesis cannot apply), it held an expectation for, and of those
             right — the direct evidence that what it learned reaches further
  hypotheses how many it holds, and how many of them hold
"""

from __future__ import annotations

import argparse
import sys
import time

from _paths import SRC  # noqa: E402 — see scripts/_paths.py

sys.path.insert(0, str(SRC))

from arc3.organs import ARC_ORGANS  # noqa: E402
from arc3.task import TASK_CUE  # noqa: E402
from mind.learning import Learning  # noqa: E402
from mind.models.exact import ExactInducer  # noqa: E402
from mind.models.grid import GridInducer  # noqa: E402
from mind.organs import Step  # noqa: E402
from steps_of import steps_of  # noqa: E402

INDUCERS = {"exact": ExactInducer, "grid": GridInducer}


def replay(run: str, name: str) -> None:
    model = Learning(INDUCERS[name](ARC_ORGANS), ARC_ORGANS, priors={"task": TASK_CUE})
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
        ok = e.by_model and model.inducer.situation(e.state) == model.inducer.situation(after)
        expected += int(e.by_model)
        right += int(ok)
        if not met:
            unseen += 1
            unseen_expected += int(e.by_model)
            unseen_right += int(ok)
        model.observe(step, None, None, (), False)
    held = sum(1 for h in model._hypotheses if h.holds)
    print(f"{name:6} expected {expected} (right {right})  unseen {unseen}: expected {unseen_expected}"
          f" (right {unseen_right})  hypotheses {len(model._hypotheses)} (held {held})  {time.time() - t0:.0f} s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--inducer", nargs="+", default=list(INDUCERS), choices=list(INDUCERS))
    a = ap.parse_args()
    print(a.run)
    for name in a.inducer:
        replay(a.run, name)
