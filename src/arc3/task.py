"""What the mind is told its thinking is for — host data, and so a `prior`.

The words the model is given are data the host had before the loop ran, and
every program the mind writes is built from them. Written into code they would
be a side door: in no store, under no tag, in no `[event]` line, in no
`built_from` (Plone, 2026-09-25: "Bản chất prompt cũng có khác gì datum có tag
'prior' đâu"). So they enter as a `prior` item through the tagging-gate, the
mind recalls them on a cue, and each program it writes names this datum among
what it was built from. A third party reads exactly what the mind was told.

The words are this project's own, not quoted from the competition's documents,
and the tag says so (`source: dil-arc3`). They are neutral: the scored games are
unseen, so nothing here names a kind of game, a mechanic or a strategy. They
give the aim — to get through the levels — and the task that serves it: work the
rules out as a program that says what the game returns, and propose the next
action toward the aim. Proposing is not acting: the proposal is data the self
answers (§6.4); the mind acts on nothing.

`{rows}`, `{cols}`, `{evidence}` and `{also}` are filled when the mind thinks.
"""

from __future__ import annotations

from typing import Final

from dil.host import PreexistingItem

TASK_DOMAIN: Final = "mind-task"
TASK_SOURCE: Final = "dil-arc3"

TASK: Final = """You are meeting a game you have not seen before. The aim is to find how to get through its levels. Nobody has told you its rules: work them out from what you have seen.

Each step shows the game's state, a grid of {rows}x{cols} cells, each a colour 0-15 written as one hex digit; the action taken; and what the game returned. Actions are ACTION1 to ACTION7; ACTION6 also carries a cell (x = column, y = row).

{evidence}
{also}
Write two Python functions, using only the standard library:

    def predict(grid, action, x=None, y=None):
        # the grid the game will return for this state and this action
    def propose(grid):
        # the action you would take next to get through the level: (action, x, y)

State the game's own rules, whatever they turn out to be, not these particular steps. Return one ```python code block. To see more of what you have met before you think again, add lines such as ASK {{"kind": "frame", "provenance": "scar"}} (kinds: frame, status, remark, program; provenance: scar or running)."""

FEEDBACK: Final = """Your predict was run on those steps. It got {ok}/{n} exactly right.
Some it got wrong (expected vs yours, as changed cells relative to the grid before):
{misses}

Revise your functions so they explain all the evidence. Return one ```python code block."""

MIND_TASK: Final = PreexistingItem(
    id="prior:mind-task",
    payload={"task": TASK, "feedback": FEEDBACK},
    open={"domain": TASK_DOMAIN, "kind": "instructions", "source": TASK_SOURCE, "object": "mind"},
)

# The cue the mind recalls its task with, once, at its first arrival: it reads
# what it is for from its own memory, as it reads anything else.
TASK_CUE: Final = {"domain": TASK_DOMAIN}

__all__ = ["FEEDBACK", "MIND_TASK", "TASK", "TASK_CUE", "TASK_DOMAIN", "TASK_SOURCE"]
