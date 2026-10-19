"""What the mind is told — host data, and so a `prior`.

The words a model is given, and the goal the task sets, are data the host had
before the loop ran. Written into code they would be a side door: in no store,
under no tag, in no `[event]` line, in no `built_from` (Plone, 2026-09-25: "Bản
chất prompt cũng có khác gì datum có tag 'prior' đâu"). So they enter as a
`prior` item through the tagging-gate, and the mind recalls them on a cue. A
third party reads exactly what the mind was told.

They are this project's own words, and the tag says so (`source: dil-arc3`).

- **The goal** (`goal`): an instruction from outside — to get through the
  levels — said as what will come back when it is met, in the fields of the
  region's report. It is not the mind's aim: the mind's aim takes the goal's
  value, and without a goal the mind holds its own (`mind/mind.py`, Plone,
  2026-09-28).
- **What a language model is asked** (`induce`, `induce_feedback`, `unforeseen`,
  `aimed`): to work out how the region behaves and write it as a program. They
  name no game and give the model no aim: it only computes, and the mind tells it
  what the program is for (`aimed`, filled with the aim the mind holds). What
  the region is like is filled in from what the host declares of it: `{rows}`,
  `{cols}`, `{acts}`, `{placed}`; and `{evidence}`, `{also}`, `{aim}`,
  `{seconds}` when the mind asks (`mind/models/language_inducer.py`).

The words the language model's earlier form was told (`TASK`, `FEEDBACK`, and
`prior:mind-aim`) went with it; `3b31806` keeps them (LOG.md, 2026-09-29).
"""

from __future__ import annotations

from typing import Final

from dil.host import PreexistingItem

TASK_DOMAIN: Final = "mind-task"
TASK_SOURCE: Final = "dil-arc3"

# The task's goal, in the form a mind that reads no text can hold its aim to:
# what will come back when it is met, in the fields of the region's report
# (Plone, 2026-09-27: what is particular to the region is data the mind reads).
TASK_GOAL: Final = {"aim": "get through the levels", "reached_when": {"fields": {"levelsDelta": 1}}}

INDUCE: Final = """You are shown what was seen of a region: its states, the actions taken on it, and what came back. Work out, from what was seen, the rules by which it behaves.

Each step shows the region's state, a grid of {rows}x{cols} cells, each a colour 0-15 written as one hex digit, with each row's number at its left and each column's number above it (tens over units); the action taken; and what came back. The actions are {acts}; {placed} also carries a cell (x = column, y = row).

{evidence}
{also}{aim}
Write Python functions, using only the standard library:

    def predict(grid, action, x=None, y=None):
        # the grid that comes back for this state and this action
    def where(grid):
        # if you can: the grid as it bears on where the region stands, a copy with every
        # cell that changes whatever is done (a counter, a timer) set to -1
    def targets(grid):
        # if you can: the cells (x, y) worth taking an action that carries a cell on

They are given the grid as Python data: a list of {rows} rows, each a list of {cols} integers 0-15 (the value of the hex digit shown: a is 10, f is 15), and predict and where give back a grid of the same form. action is the action's number ({numbers}); x and y are integers, or None for an action that carries no cell. A cell where sets to -1 must be one the steps show changing whatever is done: changing at every step at which anything else changed, and at some step at which nothing else did.

Each run of predict, where or targets must end within {seconds} seconds.

State the region's own rules, whatever they turn out to be, not these particular steps. Return one ```python code block."""

INDUCE_FEEDBACK: Final = """Your predict was run on those steps. It got {ok}/{n} exactly right.
Some it got wrong (expected vs yours, as changed cells relative to the grid before):
{misses}

Revise your program — predict, where and targets — so it explains all the evidence. Return one ```python code block."""

UNFORESEEN: Final = "\nNo program you wrote foresaw the last step.\n"

UNRUNNABLE: Final = ("Your program could not be run on those steps: {why}.\n\n"
                     "Revise it so that it runs and explains all the evidence. Return one ```python code block.")

# Asked before any step, where nothing can be done until a program names a cell.
NOTHING_SEEN: Final = ("\nNo step has been seen yet, and no action can be taken here until a targets of yours "
                       "names a cell. What you write cannot be checked against a step yet; the steps will check it.\n")

# What the mind says the program is for, filled with the aim it holds.
AIMED: Final = "The program is for a mind working toward this: {aim}.\n"

MIND_TASK: Final = PreexistingItem(
    id="prior:mind-task",
    payload={"goal": TASK_GOAL, "induce": INDUCE, "induce_feedback": INDUCE_FEEDBACK,
             "unforeseen": UNFORESEEN, "aimed": AIMED, "nothing_seen": NOTHING_SEEN, "unrunnable": UNRUNNABLE},
    open={"domain": TASK_DOMAIN, "kind": "instructions", "source": TASK_SOURCE, "object": "mind"},
)

# The cue the mind recalls its task with, once, at its first arrival: it reads
# what it is for from its own memory, as it reads anything else.
TASK_CUE: Final = {"domain": TASK_DOMAIN}

__all__ = ["AIMED", "INDUCE", "INDUCE_FEEDBACK", "MIND_TASK", "TASK_CUE", "TASK_DOMAIN", "TASK_GOAL",
           "TASK_SOURCE", "UNFORESEEN"]
