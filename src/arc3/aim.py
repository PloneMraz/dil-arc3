"""What the mind holds of an aim, whatever it is asked to do — host data, and so a `prior`.

This is the mind's, not the environment's. `task.py` says what this environment
asks and how its returns are written; this says what the mind does with any
task: it holds an expectation of reaching the task's aim, and the region can
refute it (Plone, 2026-09-25: "mind luôn giữ một kỳ vọng về việc hoàn thành một
mục tiêu bất kỳ có trong prompt mà mind nhận được"). Another environment brings
another task; these words stay.

Not every task names its aim. Then the mind works one out, and says it is its
own inference: a hypothesis the region can refute. The aim is one the region can
be seen to meet: it is stated as what will come back when it is reached, in the
form the task gives for what comes back. An aim nothing that comes back could
show — "to find out what the aim is" — is none the mind can be held to, and is
not taken. That is where a regress stops: every aim grounds out in what the
world returns.

Whether the mind may refuse an aim is left for later (Plone).
"""

from __future__ import annotations

from typing import Final

from dil.host import PreexistingItem

AIM_DOMAIN: Final = "mind-aim"

AIM: Final = """Whatever you are asked to do has an aim. If what you were asked states it, take it as stated. If it does not, work out from what you have seen what the aim most likely is, and say that it is your inference.

Hold yourself to it: in the same code block, write

    GOAL = {"aim": "the aim, in your words", "source": "stated" or "inferred",
            "reached_when": what will come back when the aim is reached, in the form given above for what comes back,
            "within": how many more actions you expect it to take}

If the aim is not reached when you said, or comes sooner, you will be told, and you will think again. An aim that nothing coming back could show is not one you can be held to."""

MIND_AIM: Final = PreexistingItem(
    id="prior:mind-aim",
    payload={"aim": AIM},
    open={"domain": AIM_DOMAIN, "kind": "instructions", "source": "dil-arc3", "object": "mind"},
)

AIM_CUE: Final = {"domain": AIM_DOMAIN}

__all__ = ["AIM", "AIM_CUE", "AIM_DOMAIN", "MIND_AIM"]
