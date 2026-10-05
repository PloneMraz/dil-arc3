"""What a host declares of its eye and its body, for the one mind to read through.

The mind knows no region (Plone, 2026-09-27: its code is neutral; what is
particular to one region is data it reads). It still needs to know how its own
organs work: how an arrival carries where the region stands and the act that
led there, what the region reports of itself, what the body can carry out. That
is the host's to declare — "the host declares where its faculties are" — as it
declares its channels; it is not knowledge of the world, and it is not learned.
What the region is, what it wants, how it behaves: that the mind reads from its
priors and learns from what comes back.

A state is opaque to the mind: it compares two for equality (tag H) and lays a
part of one over another, through the eye's own operations; how a state is
shown to a model is the model's business, told what kind of state it is.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

State = Any
# An act as the body takes it: its id and the arguments it carries (for an act
# that takes a place, its x and y; None otherwise).
Act = tuple[int, "int | None", "int | None"]


@dataclass(frozen=True, slots=True)
class Step:
    """One step as the eye delivers it: where the region stood, the act, where it
    stands — and what the region showed between, as it returned it, oldest first
    (none when it returned one state)."""

    before: State
    act: Act
    after: State
    through: tuple = ()


@dataclass(frozen=True)
class Organs:
    """The host's declaration of its eye and body, as the mind uses them."""

    # What kind of state the eye delivers, and what an act can be — said to a
    # model so it can read them (for a model, not for the mind).
    state_kind: str
    acts: dict[int, str]                       # every act id -> its name
    placed: frozenset[int]                     # acts that carry a place (x, y)
    reset: Act                                 # the act the body can always carry out

    # The eye: a frame arrival as a step; the state an expectation puts in place
    # of what came; a part of a state laid over one; what of a part did not come.
    step: Callable[[dict[str, Any]], "Step | None"]
    expected_payload: Callable[[dict[str, Any], State], dict[str, Any]]
    overlay: Callable[[State, Any], State]
    missed: Callable[[Any, State], str]

    # The region's report of itself: the key its fields sit under, the fields a
    # model may predict, what the report says had nothing changed (the standing
    # expectation), the field that names the region's state, the states in which
    # it has ended, and the key under which it says what it offers next.
    report_key: str
    report_fields: tuple[str, ...]
    unchanged: Callable[[dict[str, Any]], dict[str, Any]]
    state_field: str
    ended: frozenset[str]
    offers_key: str

    # The body: whether it can carry out an act, from the region's state and what
    # it offers; and the test payload that commands an act.
    can_carry_out: Callable[[int, "int | None", "int | None", "str | None", tuple[int, ...]], bool]
    command: Callable[[Act], dict[str, Any]]

    # The store's open-tag keys: what a question to memory may be asked by.
    tag_keys: frozenset[str]

    # What the host calls a step's state: the `object` a datum about it is tagged
    # with.
    state_object: str
    # The host's channels, by what arrives on them: "frame" (a step), "report"
    # (the region's report of itself), "others" (what an Other says of the agent).
    channels: dict[str, str]
    # Keys of a report's payload that carry the agent's own act, not the region's
    # word: not expected back (tag H).
    own_keys: tuple[str, ...] = ()
    # What an Other's word is when it has nothing to say, from what it last said:
    # what the mind expects once it has answered a remark (it should stop). None:
    # the host does not say, and the mind expects the Other to say what it said.
    quiet: "Callable[[dict[str, Any]], dict[str, Any]] | None" = None

    def name(self, act: Act | None) -> str:
        """An act as a model reads it."""
        if act is None:
            return "no action"
        base = self.acts.get(act[0], f"act {act[0]}")
        return base + (f" at ({act[1]}, {act[2]})" if act[1] is not None else "")


__all__ = ["Act", "Organs", "State", "Step"]
