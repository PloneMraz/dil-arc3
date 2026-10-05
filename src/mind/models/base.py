"""What the mind's parts are to one another.

The mind holds the seams with the loop — what it expects and which datum that
is, when it thinks, what it commands, what it writes, what it asks of its
memory, its aim (`../mind.py`) — and its learning (`../learning.py`), which the
seams ask what will come back, show what came back, and ask what to do next
(`Learner`). Neither is replaceable: the mind is one, and so is its learning
(Plone, 2026-09-28: another model, and learning is not defined again).

Its model is what is replaceable: the part of the one mind that computes — not a
second mind beside it, not a second brain (Plone, 2026-09-27). It is an inducer
(`Inducer`: `exact.py`, `grid.py`), which only computes for the learning. Its
learning writes nothing and asks nothing itself: it says what should be written
and asked, and the mind does it, so every write and question goes through the
one mind's seams.

A language model is an inducer too (`language_inducer.py`; its shared parts,
the endpoint and the program's run, are in `language.py`). Its earlier form,
which submission `56588469` ran, sat where the learning sits and is gone:
`3b31806` keeps it (LOG.md, 2026-09-29).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ..organs import Act, State, Step


@dataclass
class Expectation:
    """What the mind's learning expects to come back for a step."""

    state: State
    # The fields of the region's report it says will come; None says nothing.
    fields: dict[str, Any] | None = None
    # Which data the expectation is (`held_by`): its learning's handles for data
    # it had written, or datum ids. Empty: no datum of its learning's is it.
    held: tuple[object, ...] = ()
    # False: its learning made no expectation; this is the standing one (nothing changes).
    by_model: bool = True


@dataclass
class Proposal:
    """What the mind's learning proposes the body do next, and why."""

    act: Act | None
    why: str | None = None


@dataclass
class Write:
    """A datum the mind's learning asks the mind to write: anew (with `tags`), or as a
    revision of one it wrote before (`revises`: that datum's handle)."""

    payload: Any
    tags: dict[str, str] | None = None
    handle: object | None = None
    revises: object | None = None
    # What it was built from: observation units, datum ids, handles of the
    # learning's own data, or ("prior", name) for a prior the mind recalled.
    built_from: tuple[object, ...] = ()


@dataclass
class Thinking:
    """What came of one act of thinking."""

    writes: list[Write] = field(default_factory=list)
    # Questions to memory, each a cue by the store's tags; None when it
    # could not think at all (its questions stand as they were).
    asks: list[dict[str, str]] | None = None
    # When it thought on what an Other said: the data that are its answer (its
    # handles, as in `Write.built_from`). The mind then expects the Other to
    # stop saying it, and that expectation is these data: said again, they are
    # scarred. Empty: no answer, and the Other is expected to say what it said.
    answer: tuple[object, ...] = ()


@dataclass
class Context:
    """What the mind hands its learning to think or propose from: all of it is the
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
    # The aim the mind holds (`../mind.py`): its own, or a goal's value.
    aim: dict[str, Any] | None
    priors: dict[str, tuple[Any, str | None]]
    # The cycle's field (INV-7), as every layer reads it: how readily a source is
    # trusted, how alert to mismatch, how far to explore. None: none reached it.
    field: Any = None


class Inducer(Protocol):
    """The mind's model: what its learning computes with (`../learning.py`). It
    declares where a hypothesis applies and only computes — never the learning
    itself: the learning holds the experiences and the hypotheses, weighs them,
    expects, is curious and chooses."""

    # Its name, for the run's report.
    kind: str
    # Whether its hypotheses apply past where they were met: the learning then
    # looks ahead past the situations it has stood in.
    general: bool

    # ── perception ──

    def identity(self, state: State) -> str:
        """A state's own identity, as it came."""

    def situation(self, state: State) -> str:
        """Where the region stands in a state, read by its perception now."""

    def made(self, step: Step) -> frozenset:
        """What a step made, as values: two steps that made the same give the same
        value; a step that changed nothing, none. What a law of curiosity may
        count as new (`learning.CURIOSITY`: made)."""

    def similarity(self, a: State, b: State) -> float:
        """How alike two states are, 0 to 1, as its perception reads them: what
        the learning weighs one experience against another by (attention)."""

    def perceive(self, step: Step, kind: tuple) -> Any:
        """What its perception learns from a step, as a datum to write (with
        `payload` and `tags`); None when nothing. The learning then reads every
        situation again."""

    # ── what can be done ──

    def learnable(self, act: Act) -> Act:
        """An act as it is learned."""

    def default_kind(self, act: Act) -> tuple:
        """The kind of an act it was not offered as a candidate."""

    def candidates(self, situation: str, state: State, offers: tuple[int, ...]) -> list[tuple[Act, tuple]]:
        """The acts it can take in a state, each with its kind."""

    def copy(self, state: State) -> State:
        """A state of its own, as the learning keeps what it expects."""

    def reported(self, form: Any, said: dict[str, Any]) -> None:
        """What the region reported the first time a hypothesis's step was met."""

    def coarse(self, kind: tuple) -> tuple | None:
        """The coarser kind a kind falls in, which the learning reads first — what
        was learned of it carries to every kind within it; None for none."""

    # ── hypotheses ──

    def induce(self, source: str, act: Act, before: State, after: State, *, foreseen: bool = False,
               evidence: tuple = (), report: dict | None = None, expected: State | None = None,
               through: tuple = ()) -> list[Any]:
        """What one experience suggests: hypotheses, in its own forms. The
        learning says whether a hypothesis it holds foresaw the step, and shows
        the steps of short-term perception as `evidence` ((step, report) pairs,
        oldest first, the step itself last): an inducer whose computing is
        costly computes only what the step was not foreseen by.

        Asked again with the step's `report` when the aim came (S4), the state
        the mind `expected` of it, and what the region showed between (`through`,
        the step's): what brings the aim — hypotheses whose prediction has no
        state (None) and says what the region will report."""

    def said(self) -> list[Any]:
        """What it said in computing since last asked, each a datum to keep whole
        (with `payload` and `tags`): a language model's answers. [] for none."""

    def receive_prior(self, name: str, payload: Any) -> None:
        """A prior the mind recalled, handed on by the learning: what a language
        model is told is data the mind read (`prior:mind-task`), never code."""

    def hold_aim(self, aim: dict[str, Any]) -> None:
        """The aim the mind holds, handed on by the learning, so a model that is
        told what it computes for is told it by the mind. A model has no aim."""

    def key(self, form: Any) -> tuple:
        """What a hypothesis says, as one value: two that say the same are one."""

    def scope(self, form: Any, situation_of: Any) -> tuple:
        """Where a hypothesis applies."""

    def scopes(self, situation: str, act: Act) -> list[tuple]:
        """The scopes a situation and act fall in."""

    def predict(self, form: Any, situation: str, state: State, act: Act, situation_of: Any) -> Any:
        """What a hypothesis predicts there (with `state` and `fields`); None
        when it says nothing there. A `state` of None: it says only what the
        region will report (a hypothesis about the aim)."""

    def fields(self, form: Any) -> dict[str, Any] | None:
        """What it says the region will report of itself."""

    def describe(self, form: Any, situation_of: Any) -> dict[str, Any]:
        """A hypothesis, said as data."""

    def keep(self, form: Any, recall: Any) -> None:
        """A form it said is a hypothesis the mind holds: `recall()` gives it back
        as the mind's memory holds it — in hand while new, read from the store
        once its datum is there. An inducer that computes with a form it said
        again (as its perception, say) keeps `recall`, never the form."""

    def restore(self, payload: dict[str, Any], step: Step) -> Any:
        """A hypothesis again, from its datum as the store holds it (`payload`,
        what `describe` said) and the step it was induced from, read from the
        store: the mind reads what its model computes from in its memory (Plone,
        2026-10-05). What `describe` leaves out, the step holds. The form
        restored is the form described: `key` says the same of both."""


class Learner(Protocol):
    """The mind's learning, as its seams ask it (`../mind.py`)."""

    # For the run's report: each act of thinking, or each choice.
    thoughts: list[Any]

    def cues(self) -> dict[str, dict[str, str]]:
        """The priors it reads, by name: the cue the mind recalls each by."""

    def required(self) -> frozenset[str]:
        """The priors it needs before it can think or propose."""

    def receive_prior(self, name: str, payload: Any, datum_id: str) -> None:
        """A prior it reads, recalled by the mind."""

    def hold_aim(self, aim: dict[str, Any]) -> None:
        """The aim the mind holds: its own, or a goal's value. It states none."""

    def expect(self, step: Step) -> Expectation:
        """What will come back, from where the region stood and the act alone (INV-8)."""

    def observe(self, step: Step, unit: Any, fields: dict[str, Any] | None, units: tuple[Any, ...],
                on_report: bool, seen: list[list[Any]] | None = None) -> list[Write]:
        """What came back — the step, then its report: it learns from every
        return. With a step, the mind's short-term perception (`seen`: step, its
        observation, the report or None, the report's observation or None; oldest
        first, this step last)."""

    def propose(self, context: Context) -> tuple[Proposal, list[Write]]:
        """What to do next, from where the region stands and what it has seen."""

    def think(self, context: Context) -> Thinking | None:
        """Think on what set the mind thinking. None: it does not think on this
        (the mind does not wait on it)."""

    def held(self) -> tuple[object, ...]:
        """The data its expectations are, when it made them (its handles)."""

    def recall_from(self, view: Any) -> None:
        """The store as the mind reads it this cycle (DEVIATION 7), or None."""

    def acknowledge(self, handle: object, datum_id: str) -> None:
        """The datum a write became, now that it is known."""


__all__ = ["Context", "Expectation", "Inducer", "Learner", "Proposal", "Thinking", "Write"]
