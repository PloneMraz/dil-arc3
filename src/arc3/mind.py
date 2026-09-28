"""Where this host seated the one mind with a language model's earlier form — not seated now.

That form (`mind/models/language.py`: a program written by a language model,
which submission `56588469` ran) sat in the place of the mind's learning, so
with it the mind had no learning of its own. The mind now holds its learning,
and its model's seat takes an inducer (`mind/mind.py`), which that form is not;
its revision is one (`mind/models/language_inducer.py`). So `create_mind` is kept
and does not run (Plone, 2026-09-28; LOG.md). The rest names what that form's
tests reach for, bound to this host's organs — the fields of its report, its
acts, which act takes a cell. Nothing here thinks.
"""

from __future__ import annotations

from functools import partial
from typing import Any, Callable

from mind.mind import MAX_WAIT_THOUGHTS, Mind, expected_report, mind_rule
from mind.models import language as _language
from mind.models.language import (
    MAX_ASKS, MAX_MISSES_SHOWN, MAX_SHOWN, PROGRAM_SECONDS, PROGRAM_TAGS, THOUGHT_TAGS,
    LanguageModel, ModelEndpoint, ProgramError, Proposal, Thought, Transition,
    chat, compile_all, compile_functions, compile_program, extract_code, render_evidence, run_full,
    steps_of,
)

from .aim import AIM_CUE
from .observe import REMARK_KIND, STATUS_KIND
from .organs import ARC_ORGANS, REPORT_FIELDS
from .task import TASK_CUE

# The fields of this host's report, as a program may predict them.
STATUS_FIELDS = REPORT_FIELDS

# Why the language model is not seated.
UNSEATED = ("the language model's earlier form sat in the place of the mind's learning and is not an inducer; "
            "its seat is kept and not run, and its revision is the language inducer (LOG.md, 2026-09-28)")

goal_check = partial(_language.goal_check, fields=REPORT_FIELDS)
goal_of = partial(_language.goal_of, fields=REPORT_FIELDS)
extract_asks = partial(_language.extract_asks, keys=ARC_ORGANS.tag_keys)


def run_program(fn: Callable[..., Any], t: Transition):
    return _language.run_program(fn, t, REPORT_FIELDS)


def run_propose(fn: Callable[..., Any], grid, steps=None):
    return _language.run_propose(fn, grid, steps, ARC_ORGANS.acts, ARC_ORGANS.placed, REPORT_FIELDS)


def run_propose_full(fn: Callable[..., Any], grid, steps=None):
    return _language.run_propose_full(fn, grid, steps, ARC_ORGANS.acts, ARC_ORGANS.placed, REPORT_FIELDS)


def score(fn, evidence):
    return _language.score(fn, evidence, REPORT_FIELDS, ARC_ORGANS.unchanged)


def expected_status(said, standing):
    return expected_report(said, standing)


def create_mind(endpoint: ModelEndpoint | None = None,
                chat_fn: Callable[..., tuple[str, dict[str, Any]]] = chat,
                task: dict[str, str] | None = None, aim: dict[str, str] | None = None) -> Mind:
    """The one mind, thinking with a language model, on this host's organs. It
    read its task and aim from memory; a test could hand them in, as if recalled.
    Not run: the language model is not seated (the module's docstring)."""
    raise NotImplementedError(UNSEATED)
    # Not reached — how it was seated, kept as it was for the revision: the mind
    # no longer takes a model in its learning's place.
    model = LanguageModel(ARC_ORGANS, endpoint, chat_fn, priors={"task": TASK_CUE, "aim": AIM_CUE},
                          kinds={"status": STATUS_KIND, "remark": REMARK_KIND})
    mind = Mind(model, ARC_ORGANS)
    if task is not None:
        mind.receive("task", task, None)
    if aim is not None:
        mind.receive("aim", aim, None)
    return mind


__all__ = [
    "MAX_ASKS", "MAX_MISSES_SHOWN", "MAX_SHOWN", "MAX_WAIT_THOUGHTS", "PROGRAM_SECONDS", "PROGRAM_TAGS",
    "STATUS_FIELDS", "THOUGHT_TAGS", "UNSEATED", "LanguageModel", "Mind", "ModelEndpoint", "ProgramError",
    "Proposal",
    "Thought", "Transition", "chat", "compile_all", "compile_functions", "compile_program", "create_mind",
    "expected_status", "extract_asks", "extract_code", "goal_check", "goal_of", "mind_rule", "render_evidence",
    "run_full", "run_program", "run_propose", "run_propose_full", "score", "steps_of",
]
