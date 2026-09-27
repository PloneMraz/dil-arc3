"""What a model is to the mind: the part of the one mind that computes.

Not a second mind beside it, not a second brain (Plone, 2026-09-27). The mind
holds the seams with the loop — what it expects and which datum that is, when
it thinks, what it commands, what it writes, what it asks of its memory, its
aim — and asks its model to compute: what will come back, what to do next, and,
when an expectation fails, how to revise itself. The model writes nothing and
asks nothing itself: it says what should be written and asked, and the mind
does it, so every write and question goes through the one mind's seams.

A model may be a language model that writes a program (`language.py`) or one
that learns from nothing (`learning.py`); the mind is the same.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ..organs import Act, State, Step


@dataclass
class Expectation:
    """What the model expects to come back for a step."""

    state: State
    # The fields of the region's report it says will come; None says nothing.
    fields: dict[str, Any] | None = None
    # Which data the expectation is (`held_by`): the model's handles for data it
    # had written, or datum ids. Empty: no datum of the model's is it.
    held: tuple[object, ...] = ()
    # False: the model made no expectation; this is the standing one (nothing changes).
    by_model: bool = True


@dataclass
class Proposal:
    """What the model proposes the body do next, and what it is for."""

    act: Act | None
    # What the act is for, as what will come back: {"part": a part of the next
    # state, "fields": fields of the next report}. None: no claim.
    want: dict[str, Any] | None = None
    why: str | None = None


@dataclass
class Write:
    """A datum the model asks the mind to write: anew (with `tags`), or as a
    revision of one it wrote before (`revises`: that datum's handle)."""

    payload: Any
    tags: dict[str, str] | None = None
    handle: object | None = None
    revises: object | None = None
    # What it was built from: observation units, datum ids, handles of the
    # model's own data, or ("prior", name) for a prior the mind recalled.
    built_from: tuple[object, ...] = ()


@dataclass
class Thinking:
    """What came of one act of thinking."""

    writes: list[Write] = field(default_factory=list)
    # Questions to memory, each a cue by the store's tags; None when the model
    # could not think at all (its questions stand as they were).
    asks: list[dict[str, str]] | None = None
    # An aim the model now states: {"aim", "source", "reached_when": {"part",
    # "fields"}, "within"} (and anything the model keeps with it). None: it
    # states none, and the mind keeps the aim it held.
    aim: dict[str, Any] | None = None


@dataclass
class Context:
    """What the mind hands the model to think or propose from: all of it is the
    mind's — what it has seen and was answered, what the onlooker says, what the
    region offers, why it is thinking."""

    on: str
    # How many steps the mind has seen: the cycle a thought belongs to.
    frame_calls: int
    # Short-term perception: (step, unit, report fields or None), oldest first.
    seen: list[tuple[Step, Any, dict[str, Any] | None]]
    # What memory answered to what was asked: (datum id, step or None, open
    # tags, payload), oldest first.
    recalled: list[tuple[str, Step | None, dict[str, str], Any]]
    offers: tuple[int, ...]
    ended: str | None
    remark: dict[str, Any] | None
    # The unit the remark came in: what a datum built from the remark names.
    remark_unit: Any
    # What did not come, when an expectation of a want or an aim failed:
    # {"what": ..., and the part or fields wanted and what came}.
    missed: dict[str, Any] | None
    aim: dict[str, Any] | None
    priors: dict[str, tuple[Any, str | None]]


class Model(Protocol):
    """The part of the one mind that computes."""

    # For the run's report: each act of thinking, or each choice.
    thoughts: list[Any]

    def cues(self) -> dict[str, dict[str, str]]:
        """The priors this model reads, by name: the cue the mind recalls each by."""

    def required(self) -> frozenset[str]:
        """The priors it needs before it can think or propose."""

    def receive_prior(self, name: str, payload: Any, datum_id: str) -> None:
        """A prior it reads, recalled by the mind."""

    def stated_aim(self) -> dict[str, Any] | None:
        """An aim it states outside thinking (read from what it was told), once."""

    def can_propose(self) -> bool:
        """Whether it has anything to propose from: the mind holds it to an aim then."""

    def expect(self, step: Step) -> Expectation:
        """What will come back, from where the region stood and the act alone (INV-8)."""

    def observe(self, step: Step, unit: Any, fields: dict[str, Any] | None, units: tuple[Any, ...],
                on_report: bool) -> list[Write]:
        """What came back — the step, then its report — for a model that learns
        from every return. A model that revises only when it thinks returns []."""

    def propose(self, context: Context) -> tuple[Proposal, list[Write]]:
        """What to do next, from where the region stands and what it has seen."""

    def think(self, context: Context) -> Thinking | None:
        """Revise itself on what set the mind thinking. None: this model does not
        think on this (the mind does not wait on it)."""

    def held(self) -> tuple[object, ...]:
        """The data its expectations are, when it made them (its handles)."""

    def acknowledge(self, handle: object, datum_id: str) -> None:
        """The datum a write became, now that it is known."""


__all__ = ["Context", "Expectation", "Model", "Proposal", "Thinking", "Write"]
