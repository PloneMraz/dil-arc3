"""The one mind as this host seats it, thinking with a language model.

The mind is neutral about its region (`mind/mind.py`); its model is the part of
it that computes (`mind/models/language.py`: a program written by a language
model); this host declares its eye and body (`organs.py`). This module puts them
together for ARC-AGI-3 and names what the host's tests and scripts reach for,
bound to this host's organs — the fields of its report, its acts, which act
takes a cell. Nothing here thinks.
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
    reads its task and aim from memory; a test may hand them in, as if recalled."""
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
    "STATUS_FIELDS", "THOUGHT_TAGS", "LanguageModel", "Mind", "ModelEndpoint", "ProgramError", "Proposal",
    "Thought", "Transition", "chat", "compile_all", "compile_functions", "compile_program", "create_mind",
    "expected_status", "extract_asks", "extract_code", "goal_check", "goal_of", "mind_rule", "render_evidence",
    "run_full", "run_program", "run_propose", "run_propose_full", "score", "steps_of",
]
