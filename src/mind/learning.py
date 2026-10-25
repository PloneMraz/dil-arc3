"""The mind's learning — neutral about its region and about the model it learns with.

Plone (2026-09-28): learning is developing experience into what serves the agent,
not storing it; and it is the mind's, not the model's — another task, another
model, and learning is not defined again. The mind holds the loop; a model — an
inducer (`models/`) — is its computing: what a state is to it, what can be done in one, what an experience
suggests, what a hypothesis predicts.

THE LOOP, one step at a time:

- **Experience.** Each step — from where the region stood, an act, where it
  stands and what it reported of itself — is kept, accrued (INV-5), with how
  often it was met and how often the region ended on it. What it says — that
  the act gives there what it gave — is the mind's own expectation, from its
  memory, weighed as a hypothesis is; an outcome other than the ones met is an
  experience of its own (Plone, 2026-10-06: no model need say it).
- **Hypotheses are data.** What an experience suggests past itself, the inducer says — asked
  of a step from a situation and act never met, and of one no hypothesis it held
  foresaw; the mind holds each as a hypothesis, once (what the inducer keys
  alike is one), and writes it (`kind: hypothesis`), built from the step and
  the report it came in.
- **Expecting.** For a step, the experiences of the act there and the hypotheses
  that apply to where the region stood and the act; of those it holds, the one
  that fits the store best is the expectation, and is what the expectation is
  (`held_by`) — so when the region returns otherwise, it is scarred (v0.3.5).
- **Weighing.** Each return that a hypothesis predicted counts for it, each it
  did not counts against: a hypothesis is held while it has been right more
  often than wrong, and the one right at the highest rate is preferred (DECIDE@IMPL
  FIT_LAW; tag H: fit against the store, never a scored standard). Each weighing
  revises its datum in place — how often it was borne out and
  whether it holds are in `[data]` as they change — and when whether it holds
  changes, a datum of its own says so too, built from it (Plone, 2026-10-04).
- **Experience, written.** Each experience is a datum (`kind: experience`): from where,
  by what act, to where, how often met, how often it reached somewhere new or
  the aim or ended the region, what the region reported. Written once the step's
  report has come, and revised in place as it changes. `[data]` is the agent's
  memory (protocol v0.3.8).
- **Memory.** `[data]` is the agent's memory, and what its model
  computes from, the mind reads there (Plone, 2026-10-05): the states it has
  stood in, the hypotheses it predicts with, the recent steps. What came in a
  cycle is in hand in that cycle — met in it, not yet
  memory; from the next, it is read from the store, and its content is no
  longer held. Each read is the store's to record (v0.3.7 §9), and what is
  written from what was read names it among what it was built from.
- **The aim.** Reaching it is an experience too (S4, Plone, 2026-09-28): asked
  with the step's report and what it expected of the step, the inducer says
  what brings the aim — hypotheses that predict no state, only the report —
  held and written as any are, weighed by each report where they applied.
- **Choosing.** Toward the aim it has reached before, or where its held
  hypotheses say an act brings it; else what it knows least
  (curiosity, below) — an act its hypotheses say leads where it has stood last,
  never out of reach, and an act never once taken never so;
  else the shortest way to where something is left to try, looking ahead by what
  its held hypotheses predict — through the situations it has stood in and, for
  an inducer whose hypotheses reach past where they were met, up to
  MAX_IMAGINED_STEPS past them, where a situation not stood in is itself
  something left to try; else the act that starts the region again (if the host
  has one), or the known act toward the situation least
  visited.
- **A collision turns its thinking** (Plone, 2026-10-11: a mismatch is not a
  penalty; it is data that deviates from what was expected, and the scar it
  leaves turns how the mind thinks and builds what it does next — which changes
  the region, which changes what it expects). When a step's return does not
  come as expected, it thinks on what collided and writes that thought, built
  from the return: silence where it expected an answer turns it from that kind
  of act; an answer other than it foresaw turns it to where the answer differed
  (where its model says an act lies there: `Inducer.unlike`, `Inducer.at`). The
  turn holds for the next choice, which names the thought among what it was
  built from; the next collision turns it again. No count is kept of it.
- **What it met where it stood alike, it expects again** (Plone, 2026-10-11:
  memory of collisions reaching what it expects, not a rule of reaction). Where
  nothing it knows of this act here says what will come, it recalls what the
  same kind of act did where it stood in states alike to this one (its
  attention, `ATTENTION_K` experiences by the inducer's `similarity`): if they
  weigh more for nothing coming of it, it expects nothing to come of it here —
  held by those experiences, so an answer collides with them — and such an act
  counts as foreseen (tried last, never out of reach); else it expects the
  region to be otherwise.
- **The field reaches how it builds what it does** (INV-7; Plone, 2026-10-11:
  context, memory and the field, even half a bit, make expectations and
  behaviour differ). Each axis on the operation it names: how readily a source
  is trusted — how far an experience or hypothesis must have been borne out
  more often than not before it expects by it (`trust`); how alert to mismatch
  — how many choices a collision's turn holds for (`alertness`); how far it
  leans to explore — how many steps it looks ahead past where it has stood
  (`exploration`). At NEUTRAL each is the declared operation; each choice
  says what it read of the field.
- **The onlooker's word** strikes the mind as a collision; what it objects to is
  put behind every other act at every point of choice — never over a known way
  to the aim — and lifted when the onlooker says something else. A repetition
  whose every step went somewhere new is kept on, told once; told again, it is
  objected to.

CURIOSITY. Per kind of act, and per act over every kind of it: how often it was
tried, how often it reached a situation not met before, how often the aim came
of it. What most often brought the aim first; then the odds of somewhere new
(Laplace), raised by how little it has been tried (UCB1). Somewhere new, not a
change: an act that only takes it back where it stood changes the
state every time and teaches it nothing (Plone, 2026-09-28: S2b). A kind the
inducer puts within a coarser one (`Inducer.coarse`) is read coarse first: how
much the coarser kind is wanted, then the kind itself — what was learned of
the coarser kind carries to every kind within it (Plone, 2026-09-29).

A step ends one of three ways: nothing changed (blocked), it changed but came
back to a situation met before, or it reached one not met before. Which of them
the mind counts as worth trying is `curiosity` (CURIOSITY), each a law of the
mind naming no task; the default is S2b, the others are kept to be measured
against it (Plone, 2026-09-28):

  new               S2b  somewhere new
  changed           S2   a change: somewhere new or back where it stood
  new-then-changed  S2c  somewhere new; between kinds as likely to, a change
  new-plus-changed  S2d  the odds of somewhere new and of a change, added
  made              B1   something made not made before: where the parts of a
                         whole change apart, the whole seldom comes again, and
                         somewhere new is everywhere (LOG.md, 2026-10-05); what
                         a step made is its model's to say (`Inducer.made`)
  test              T1   each command tests the expectation that least says
                         what will come (Plone, 2026-10-11/18). For each act
                         not yet taken here, what holds what it expects of it
                         — a hypothesis, which names what will come and is
                         wrong at its rate; the experiences recalled from
                         states alike; or nothing — and how likely what comes
                         is something memory does not hold: wrong × unnamed,
                         or unnamed where nothing names it; unnamed =
                         (made + 1) / (tried + 2), how often that kind of act
                         made something not made before, as its model reads
                         what a step made (alike first, then anywhere, then
                         its coarser kind) — not a whole state never met,
                         which parts changed apart make at every step; the
                         evidence weighed by the field's trust (½–1½). No
                         bonus for being tried little: an act whose outcome
                         memory names is not tried again for that. What
                         brings the aim first, as for every law; at an equal
                         likelihood, the spread of the expectation's rate,
                         sqrt(p(1 - p) / (n + 3)) — the one least sure of.
                         The choice says both (`unheld`, `unsure`) and what
                         held the expectation it tests, which it is built from

What it holds and does not write as such — the counts its curiosity weighs
with, the situations it visited — follows from its experiences in `[data]`. Not
written: `unseen` (of the steps from a situation and act never met, how many it
expected and how many of those it expected right), a measure for the run's
report, not something it learned.
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Callable, Final

from dil.loop.field import ALERTNESS, EXPLORATION, TRUST, axis, falling, rising, round_half_up, shifted_count

from .models.base import Context, Expectation, Inducer, Proposal, Thinking, Write
from .organs import Act, AsRead, Organs, Otherwise, Step

# A hypothesis's tags; its `object`, what it is about, is what the host calls a
# step's state (`Organs.state_object`).
HYPOTHESIS_TAGS: Final = {"domain": "mind", "kind": "hypothesis", "source": "mind"}
CHOICE_TAGS: Final = {"domain": "mind", "kind": "choice", "source": "mind"}
# An experience's tags; its `object`, as a hypothesis's, is what the host calls a
# step's state.
EXPERIENCE_TAGS: Final = {"domain": "mind", "kind": "experience", "source": "mind"}
THOUGHT_TAGS: Final = {"domain": "mind", "kind": "thought", "source": "mind"}

# What the learning writes in a hypothesis's datum beside what its inducer said:
# how it weighs it. A revision of these alone changes nothing the inducer said.
TALLIES: Final = ("holds", "supports", "fails")
# How far it searches the situations it knows for a way. DECLARED: a bound on work.
MAX_PATH_NODES: Final = 20_000
# How many steps it looks ahead past the situations it has stood in, on what its
# hypotheses predict. DECLARED: a bound on work.
MAX_IMAGINED_STEPS: Final = 3
# How many predictions one search for a way may make for situations it has not
# stood in; past it, it looks no further past where it has stood. What it
# predicts there is kept for that choice only, never after (2026-09-29: kept, the
# predictions of every imagined situation for every act once filled 5 GB in 37
# cycles; LOG.md). DECLARED: a bound on work.
MAX_IMAGINED_PREDICTIONS: Final = 20_000
# DECIDE@IMPL (tag H) — how a hypothesis is weighed against the store.
# ATTENTION (idea (a), Plone, 2026-09-29): with it, how much an act is wanted is
# read not from all it did everywhere but from what it did in the situations most
# like this one — the K most alike, each weighed by how alike, raised to SHARPNESS
# (as a softmax's temperature sharpens) — when they weigh at least MIN_WEIGHT;
# else from all, as without it. How alike is the inducer's to say (`similarity`).
# DECLARED, not measured.
ATTENTION_K: Final = 16
ATTENTION_SHARPNESS: Final = 4
ATTENTION_MIN_WEIGHT: Final = 1.0
# What the mind counts as worth trying (the docstring's CURIOSITY), by name; the
# first is the default (S2b).
CURIOSITY: Final = ("new", "changed", "new-then-changed", "new-plus-changed", "made", "test")
# The laws by which a step is new when it made something not made before.
MADE_LAWS: Final = ("made", "test")
FIT_LAW: Final = ("held while right more often than wrong (supports > fails); of those that apply, "
                  "the one right at the highest rate, (supports + 1) / (supports + fails + 2), is the "
                  "expectation; at an equal rate, the one right more often")


class Weighed:
    """What the mind expects by, weighed by the returns: how often the region bore
    it out (`supports`) and how often not (`fails`)."""

    supports: int
    fails: int

    @property
    def holds(self) -> bool:
        return self.supports > self.fails

    @property
    def rate(self) -> float:
        """How often it was right, Laplace's estimate: (right + 1) / (tried + 2)."""
        return (self.supports + 1) / (self.supports + self.fails + 2)


@dataclass(eq=False)
class Hypothesis(Weighed):
    """A hypothesis the mind holds: the inducer's form, how often the region bore it
    out and how often not. Its own handle, as data.

    Its form is in hand while it is new; once its datum is in the store, the form
    is read there (`recall`), and is no longer held."""

    held: Any                  # its form, in hand until it is read from the store
    supports: int = 1          # the experience it was induced from bears it out
    fails: int = 0
    written: bool = False
    datum_id: str | None = None
    # The step it was induced from, its observation (what its datum is built
    # from), until its datum is in the store; what was read to induce it, by id.
    unit: Any = None
    read: tuple[str, ...] = ()
    recall: Callable[["Hypothesis"], Any] | None = field(default=None, repr=False)

    @property
    def form(self) -> Any:
        return self.held if self.recall is None else self.recall(self)


@dataclass(eq=False)
class Reading:
    """A way of reading states its model gave while the host waited (`consider`):
    no hypothesis — no step was met to build one from — but what the model reads
    states with, so its form is in hand only until its datum is in the store, and
    then read there (`recall`), as a hypothesis's is."""

    held: Any
    datum_id: str | None = None
    recall: Callable[["Reading"], Any] | None = field(default=None, repr=False)

    @property
    def form(self) -> Any:
        return self.held if self.recall is None else self.recall(self)


@dataclass(eq=False)
class TurnHandle:
    """A thought on a collision, as a handle: what the choice it turned is built from."""

    cycle: int


class ChoiceHandle:
    """A choice, as a handle: the mind names on it, once their ids come back, what
    it was built from that had none when it was written (`Write.relinks`)."""


# How many choices a collision's turn holds for at NEUTRAL alertness. DECLARED.
TURN_HOLD: Final = 2
# What a choice a collision turned says of it.
TURN_WHYS: Final = ("; turned from what was silent", "; turned to where the answer differed",
                    "; turned from what ended the region")


@dataclass(frozen=True)
class Recalled:
    """A state as memory holds it: in the datum `datum`, on its `side` — where the
    region stood before the step it records, or after."""

    datum: str
    side: str


class Evidence(Sequence):
    """The recent steps as an inducer is shown them, each (step, report): what
    came in an earlier cycle read from the store when the inducer looks at it,
    and only then; what came in this one, as it came."""

    def __init__(self, learning: "Learning", seen: list) -> None:
        self._learning, self._seen = learning, seen

    def __len__(self) -> int:
        return len(self._seen)

    def __getitem__(self, i):
        if isinstance(i, slice):
            return [self[j] for j in range(*i.indices(len(self)))]
        step, unit, report, *rest = self._seen[i]
        return self._learning.recalled_step(step, unit, report, rest[0] if rest else None)


class RecordEvidence(Sequence):
    """The recent steps as an inducer is shown them, read from the record of what
    happened (`[event]`, protocol v0.3.9) when the inducer looks, and only then:
    the seals of the latest cycles say which step and which report each cycle
    admitted, by id, and memory (`[data]`) holds what they were. The step in hand,
    met this cycle, is the last, as it came. Each seal read is a record read, and
    what is built from what the inducer read names it (`event:<seq>`) beside the
    data read (Plone, 2026-10-25: the steps it is shown come from its history,
    not from what the mind keeps)."""

    def __init__(self, learning: "Learning", seen: list) -> None:
        self._learning, self._seen, self._steps = learning, seen, None

    def _read(self) -> list:
        if self._steps is None:
            self._steps = self._learning.recent_from_record([tuple(s[:3]) for s in self._seen])
        return self._steps

    def __len__(self) -> int:
        return len(self._read())

    def __getitem__(self, i):
        steps = self._read()
        if isinstance(i, slice):
            return [steps[j] for j in range(*i.indices(len(steps)))]
        return steps[i]


@dataclass(eq=False)
class Edge(Weighed):
    """One experience: from a state, an act, came a state and a report. `source`
    and `to` are the states as they came (their own identities); where the region
    stood is read from them by the inducer's reading now.

    It is also what the mind expects of that act there — what came, as memory
    holds it — weighed as a hypothesis is: borne out each time the act there
    gives it again, not when it gives something else, which is an experience of
    its own (Plone, 2026-10-06: what an experience says is the learning's, not a
    model's). Its datum is what such an expectation is (`held_by`)."""

    source: str
    act: Act
    to: str
    kind: tuple
    changed: bool
    supports: int = 1            # it bears itself out
    fails: int = 0
    report: dict[str, Any] | None = None   # what the region reported of itself
    ended: int = 0               # how many times the region ended on it
    seen: int = 1
    new: int = 0                 # how many times it reached a situation not met before
    reached: int = 0             # how many times the aim came of it
    made: int = 0                # how many times it made something not made before
    written: bool = False        # its datum entered the store


class Recall:
    """What an experience says will come back: the state it came to, as memory
    holds it (read only when asked for), and what the region reported."""

    __slots__ = ("_learning", "_raw", "fields")

    def __init__(self, learning: "Learning", raw: str, fields: dict[str, Any] | None) -> None:
        self._learning, self._raw, self.fields = learning, raw, fields

    @property
    def state(self) -> Any:
        return self._learning._stood(self._raw)


class Answer:
    """What it answered an Other's word with — the thought it wrote — as its own
    handle: the mind's expectation that the Other stops saying it is this datum,
    and said again, it is scarred."""


@dataclass
class Choice:
    """One command, for the run's report (the trace is `[event]` and the store)."""

    step: int
    act: Act | None
    why: str
    odds: float | None = None


class Learning:
    """The mind's learning loop, computing with an inducer — the model in the
    mind's seat for one. The mind holds it (`mind.py`), and its seams ask it what
    to expect, show it what came back, ask it what to do."""

    def __init__(self, inducer: Inducer, organs: Organs, priors: dict[str, dict[str, str]],
                 curiosity: str = CURIOSITY[0], attention: bool = False) -> None:
        if curiosity not in CURIOSITY:
            raise ValueError(f"curiosity is one of {CURIOSITY}, not {curiosity!r}")
        self.inducer = inducer
        self.organs = organs
        self.curiosity = curiosity
        self._hypothesis_tags = {**HYPOTHESIS_TAGS, "object": organs.state_object}
        self._experience_tags = {**EXPERIENCE_TAGS, "object": organs.state_object}
        # The experiences changed since their datum was last written (`[data]` is
        # the agent's memory: every change in what it learned is written).
        self._pending: list[Edge] = []
        self.attention = attention
        # For a choice being made: how alike each state met is to where it stands
        # (attention), and what the chosen act was weighed by.
        self._alike: dict[str, float] = {}
        self._attended: list[tuple[Edge, float]] = []
        self._last_attended: list[tuple[Edge, float]] = []
        self._tested_by: list[Hypothesis] = []       # T1: the hypothesis whose expectation a choice tests
        self._unsure = 0.0                           # T1: how unsure the expectation it tests is
        self._attended_change = 0.0
        # For a choice being made with attention: the experiences ranked by how
        # alike, once, and what each kind or act was found to weigh.
        self._ranked: list[tuple[float, Edge]] | None = None
        # Where `_alike` was read from: what it recalls holds for that place only.
        self._alike_for: str | None = None
        self._attend_memo: dict[tuple, tuple] = {}
        # How often each kind of act, and each act, changed the state (for the
        # laws that count a change: S2, S2c, S2d).
        self._kind_changes: dict[tuple, int] = {}
        # The same counts for the coarser kinds the inducer puts kinds in.
        self._coarse: dict[tuple, list[int]] = {}
        self._coarse_changes: dict[tuple, int] = {}
        self._action_changes: dict[int, int] = {}
        self._now_raw: str | None = None                       # the latest state's own identity
        self._last_choice: dict[str, Any] | None = None        # the choice it wrote last
        # What the onlooker's word made it object to, by what the word was: (the
        # state as it came, act). Held while the onlooker says it; lifted when it
        # says something else; read by the inducer now.
        self._objected: dict[tuple, set[tuple[str, Act]]] = {}
        # Its answers to each word, while the word stands.
        self._answers: dict[tuple, list[Answer]] = {}
        self._cues = dict(priors)        # it reads the task, for its aim
        self.thoughts: list[Choice] = []
        self.holds_by_situation: list[int] = []
        self.version = 0                  # hypotheses written
        self.code = None                  # it writes no program
        self._aim: dict[str, Any] | None = None
        # What the region has reported, and how often: the mind's own aim is a
        # report other than the one it has been making (`mind.OWN_AIM`).
        self._reports: dict[tuple, int] = {}
        self._raw: dict[str, Any] = {}                      # a state, by its own identity
        self._state_of: dict[str, str] = {}                 # identity -> where the region stood
        self._raw_of: dict[str, str] = {}                  # a situation -> a state of it
        self._learned: list[Edge] = []                      # every experience, in the order met
        self._edges: dict[tuple[str, Act], Edge] = {}        # the first experience of a situation and act
        # Every experience of a situation and act, one for each different outcome:
        # what it expects of the act there.
        self._outcomes: dict[tuple[str, Act], list[Edge]] = {}
        self._out: dict[str, dict[Act, Edge]] = {}
        # What every step has made, for the law that counts something made as new.
        self._made: set = set()
        self._kinds: dict[tuple, list[int]] = {}   # kind -> [tried, somewhere new, aim]
        self._actions: dict[int, list[int]] = {}   # act -> [tried, somewhere new, aim], every kind of it
        self._kind_of: dict[tuple[str, Act], tuple] = {}
        self._here: str | None = None
        self._unit: Any = None
        self._last: Edge | None = None
        self._last_new = False
        self._expected: Any = None
        self._visits: dict[str, int] = {}
        # Every hypothesis, in the order induced, and by the scope the inducer says
        # it applies in; what applies to a situation and act, and what it predicts,
        # as far as it has been worked out.
        self._hypotheses: list[Hypothesis] = []
        self._scoped: dict[tuple, list[Hypothesis]] = {}
        self._applies: dict[tuple[str, Act], tuple[dict, list]] = {}
        self._new: list[Hypothesis] = []                     # induced, not yet written
        self._keys: dict[tuple, Hypothesis] = {}             # what each hypothesis says, as the inducer keys it
        # Steps from a situation and act never met: how many, how many it expected,
        # how many of those it expected right — what it learned, reaching further.
        self.unseen = [0, 0, 0]
        self._unseen_expected: str | None = None
        self._imagined: dict[str, Any] = {}                  # a situation predicted, never stood in: this choice's
        self._imagined_left = MAX_IMAGINED_PREDICTIONS
        self._against: set[tuple[Edge, Edge]] = set()   # experiences read as one, counted against
        self._learned_since_restart = True
        self.steps = 0
        # The mind's recent steps at the step being learned: what an
        # inducer is shown when it is asked what the step suggests.
        self._seen_now: list = []
        # Memory as the mind reads it: the store's view this cycle (v0.3.7 §9),
        # each state read this cycle, by where memory holds it; the states met in
        # a cycle that is not memory yet, each with the observation it came in;
        # each hypothesis read, with the datum it was read from; and what was read
        # or computed from what was read since the last datum was built from it.
        self._view: Any = None
        self._memo: dict[Recalled, Any] = {}
        self._unsettled: list[tuple[str, Any, str]] = []
        # Each hypothesis read, by its datum: the payload read, the form restored
        # from it, and what its inducer said in it (the payload off the tallies).
        self._restored: dict[str, tuple[Any, Any, dict[str, Any]]] = {}
        self._considered: set[str] = set()   # where it thought while the host waited
        self._used: dict[str, None] = {}
        self._chosen_kind: tuple | None = None
        # Hypotheses about the aim (S4): those that applied to the step being
        # learned, weighed by its report; the step; whether any is held yet.
        self._aim_applied: list[Hypothesis] = []
        # The region's report before the last and the last (`_think_on_report`).
        self._report_was: dict[str, Any] | None = None
        self._report_now: dict[str, Any] | None = None
        self._report_unit: Any = None
        # Whether the last step came to a situation not met before (its vote on
        # the field's exploration, cast by the mind at T5).
        self.came_somewhere_new = False
        # How a collision turned it, for the next choice (`_think_on_collision`):
        # ("silence", the kind it turns from, the coarser kind) or
        # ("unforeseen", where the answer differed); and the thought's handle.
        self._turn: tuple | None = None
        self._turn_left = 0
        # The record of what happened (`[event]`), as the mind reads it this cycle
        # (protocol v0.3.9: an open link), and the source its steps come from.
        # What collided and turned it, by the return that collided: (collision,
        # situation, kind) — the return's datum id once it has come back
        # (`recall_from`); the region's scars are read against it (`_repeats`).
        self._record: Any = None
        self.step_source: str | None = None
        self._collided: dict[str, tuple] = {}
        self._read_for_word: dict[str, None] = {}
        self._collided_unsettled: list[tuple[tuple, Any]] = []
        # The cycle's field, as every layer reads it (INV-7; `read_field`).
        self._field: Any = None
        # B2 (Plone, 2026-10-18): what it reads of the field each cycle, as whole
        # counts that follow the field on average — each count is the field's
        # real value plus what earlier cycles' rounding left over (`_counted`).
        self._counts: dict[str, int] = {}
        self._carried: dict[str, float] = {}
        self._counted_at: Any = None
        self._turn_thought: object | None = None
        # What the thought that turned it was built from: what every choice the
        # turn holds for is built from, the first and the later ones alike.
        self._turn_from: tuple[object, ...] = ()
        self._expected_otherwise = False
        self._last_step: tuple[str, Act, Step, Any] | None = None
        self._expected_from: tuple[str, ...] = ()
        self._aim_held = False

    # ── what it reads ──

    def cues(self) -> dict[str, dict[str, str]]:
        return dict(self._cues)

    def required(self) -> frozenset[str]:
        return frozenset()

    def receive_prior(self, name: str, payload: Any, datum_id: str) -> None:
        self.inducer.receive_prior(name, payload)

    def hold_aim(self, aim: dict[str, Any]) -> None:
        """The aim the mind holds — its own, or a goal's value (`mind.py`): what
        it goes toward and weighs hypotheses about the aim by. Its model is told."""
        self._aim = dict(aim)
        self.inducer.hold_aim(self._aim)

    def held(self) -> tuple[object, ...]:
        return ()

    # ── memory ──

    def recall_from(self, view: Any) -> None:
        """The store as the mind reads it this cycle (v0.3.7 §9: `read(datum,
        purpose)`, `id_of(observation)`). What came in an earlier cycle is memory
        now: read from the store from here on, its content no longer held."""
        if view is self._view:
            return
        self._view, self._memo = view, {}
        if view is None:
            return
        unsettled, self._unsettled = self._unsettled, []
        for raw, unit, side in unsettled:
            datum = view.id_of(unit)
            if datum is None:
                self._unsettled.append((raw, unit, side))
            else:
                self._raw[raw] = Recalled(datum, side)
        collided, self._collided_unsettled = self._collided_unsettled, []
        for key, unit in collided:
            datum = view.id_of(unit)
            if datum is None:
                self._collided_unsettled.append((key, unit))
            else:
                self._collided[datum] = key

    def read_record(self, record: Any) -> None:
        """The record of what happened (`[event]`) as the mind reads it this cycle
        (protocol v0.3.9 §9, "Reading the record"): open to it every cycle, each
        read recorded. None outside a cycle."""
        self._record = record

    def _repeats(self, key: tuple) -> list[int]:
        """Where the record says this collision came before: the scars on the
        source its steps come from whose return collided as this one does — the
        same way, in the same situation, by the same kind of act — by their place
        in the chain, as far back as the record's view reaches. The region's
        scars, not the mind's own account of its thoughts: what the region pushed
        (INV-6)."""
        if self._record is None or self.step_source is None:
            return []
        return [found.seq for found in self._record.scars(self.step_source, "collisions")
                if self._collided.get(getattr(found.record, "datum_id", None)) == key]

    def _settle(self, h: Hypothesis) -> None:
        """A hypothesis whose datum is in the store: read there from now on."""
        if self._view is None or h.datum_id is None or h.recall is not None:
            return
        h.unit, h.held, h.recall = None, None, self._recall

    def _recall(self, h: Hypothesis) -> Any:
        """A hypothesis's form, read from its datum. Restored again only when what
        its inducer said in it has changed — not the tallies the learning keeps in
        it — and the form kept when it still says the same, so what its model has
        computed with it holds."""
        payload = self._view.read(h.datum_id, "hypothesis").payload
        self._used[h.datum_id] = None
        kept = self._restored.get(h.datum_id)
        if kept is not None and kept[0] is payload:
            return kept[1]
        said = {k: v for k, v in payload.items() if k not in TALLIES}
        if kept is not None and kept[2] == said:
            self._restored[h.datum_id] = (payload, kept[1], said)
            return kept[1]
        form = self.inducer.restore(payload)
        if kept is not None and self.inducer.key(form) == self.inducer.key(kept[1]):
            form = kept[1]
        self._restored[h.datum_id] = (payload, form, said)
        return form

    def _recall_reading(self, r: Reading) -> Any:
        """A reading's form, read from its datum; restored again only when the datum
        changed."""
        payload = self._view.read(r.datum_id, "reading").payload
        self._used[r.datum_id] = None
        kept = self._restored.get(r.datum_id)
        if kept is not None and kept[0] is payload:
            return kept[1]
        form = self.inducer.restore(payload)
        self._restored[r.datum_id] = (payload, form, {})
        return form

    def _stood(self, raw: str) -> Any:
        """A state it stood in: in hand in the cycle it came, else read from the store."""
        held = self._raw[raw]
        if not isinstance(held, Recalled):
            return held
        datum = self._view.read(held.datum, "state")
        self._used[held.datum] = None
        state = self._memo.get(held)
        if state is None:
            step = self.organs.step(datum.payload)
            state = step.before if held.side == "before" else step.after
            self._memo[held] = state
        return state

    def recalled_step(self, step: Step, unit: Any, report: dict[str, Any] | None,
                      report_unit: Any) -> tuple[Step, dict[str, Any] | None]:
        """One of the recent steps, and what the region reported of it:
        read from the store when it came in an earlier cycle (`Evidence`)."""
        view = self._view
        datum = view.id_of(unit) if view is not None and unit is not None else None
        if datum is None:
            return step, report
        self._used[datum] = None
        step = self.organs.step(view.read(datum, "evidence").payload) or step
        said = view.id_of(report_unit) if report_unit is not None else None
        if said is not None:
            self._used[said] = None
            payload = view.read(said, "evidence").payload
            report = payload.get(self.organs.report_key) if isinstance(payload, dict) else report
        return step, report

    def recent_from_record(self, seen: list, into: dict | None = None) -> list[tuple[Step, dict[str, Any] | None]]:
        """The recent steps `seen` — (step, unit, report), the last the newest — as
        the record says they came: all of them read from it when the newest came
        in an earlier cycle, else those before it, and the one in hand, met this
        cycle, as it came. As they are, without a record to read."""
        if not seen:
            return []
        if self._record is None or self._view is None:
            return [(s, r) for s, _, r in seen]
        step, unit, report = seen[-1]
        in_store = unit is not None and self._view.id_of(unit) is not None
        out = self.steps_from_record(len(seen) if in_store else len(seen) - 1, into)
        return out if in_store else out + [(step, report)]

    def steps_from_record(self, n: int, into: dict | None = None) -> list[tuple[Step, dict[str, Any] | None]]:
        """The `n` steps before the one in hand, oldest first, as the record says
        they came: each cycle's seal names the step and the report it admitted —
        by the channel each came on (its `source`) — and memory holds what they
        were. Fewer where the record's view does not reach so far. What was read
        goes `into` what the next datum written is built from (the learning's
        `_used`, unless another is given)."""
        used = self._used if into is None else into
        record, view = self._record, self._view
        if n <= 0 or record is None or view is None or getattr(record, "cycles", None) is None:
            return []
        step_channel = self.organs.channels.get("step")
        report_channel = self.organs.channels.get("report")
        out: list[tuple[Step, dict[str, Any] | None]] = []
        for found in record.cycles("evidence", 2 * n):
            admitted = found.record.activity.admitted
            came = {t.open.get("source"): t.datum_id for t in admitted}
            frame = came.get(step_channel)
            if frame is None:
                continue
            held = view.read(frame, "evidence")
            step = self.organs.step(held.payload) if held is not None else None
            if step is None:
                continue
            used[frame] = None
            used[f"event:{found.seq}"] = None
            report = None
            said = came.get(report_channel)
            if said is not None:
                payload = view.read(said, "evidence")
                if payload is not None:
                    used[said] = None
                    payload = payload.payload
                    report = payload.get(self.organs.report_key) if isinstance(payload, dict) else None
            out.append((step, report))
            if len(out) >= n:
                break
        out.reverse()
        return out

    def _take_used(self) -> tuple[str, ...]:
        """What was read, or computed from what was read, since this was last asked:
        what is written now was built from it."""
        used, self._used = tuple(self._used), {}
        return used

    # ── hypotheses ──

    def _add(self, h: Hypothesis) -> None:
        self._hypotheses.append(h)
        self._scoped.setdefault(self.inducer.scope(h.form, self._situation_of), []).append(h)

    def _induce(self, source_raw: str, act: Act, step: Step, foreseen: bool, unit: Any = None,
                report: dict[str, Any] | None = None) -> list[Hypothesis]:
        """What an experience suggests, held — save what it holds already. The
        inducer is told whether a hypothesis held foresaw the step, and shown
        the recent steps: one whose computing is costly computes only what
        was not foreseen. With the step's `report`, when the aim came: what
        brings the aim, from what the mind expected of the step and what the
        region showed between (S4)."""
        out = []
        evidence = RecordEvidence(self, self._seen_now) if self._record is not None else Evidence(self, self._seen_now)
        extra = {"report": report, "expected": self._expected, "through": step.through} if report is not None else {}
        used = self._take_used()
        forms = self.inducer.induce(source_raw, act, step.before, step.after, foreseen=foreseen,
                                    evidence=evidence, **extra)
        read = self._take_used()     # what the inducer read of the recent steps
        self._used = dict.fromkeys(used)
        for form in forms:
            key = self.inducer.key(form)
            h = self._keys.get(key)
            if h is None:
                h = self._keys[key] = Hypothesis(form, unit=unit, read=read)
                self._add(h)
                out.append(h)
            # What the inducer said is a hypothesis the mind holds: an inducer that
            # computes with it again has it back from the mind's memory.
            self.inducer.keep(form, lambda h=h: h.form)
        return out

    def _applicable(self, situation: str, act: Act, state: Any = None) -> list[tuple[Weighed, Any, str]]:
        """What applies to a situation and act, each with what it predicts and the
        situation that is: the experiences of the act there, from memory, and the
        hypotheses that apply there — worked out once, and again only for
        hypotheses induced since."""
        experienced = [(e, Recall(self, e.to, e.report), self._state_of[e.to])
                       for e in self._outcomes.get((situation, act), ())]
        stood = situation in self._raw_of
        if not stood and self._imagined_left <= 0:
            return []          # it has looked as far past where it stood as a choice may
        cached = self._applies.get((situation, act)) if stood else None
        checked, found = cached if cached is not None else ({}, [])
        for scope in self.inducer.scopes(situation, act):
            held = self._scoped.get(scope, ())
            start = checked.get(scope, 0)
            if start < len(held):
                if state is None:
                    state = self._state(situation)
                for h in held[start:]:
                    said = self.inducer.predict(h.form, situation, state, act, self._situation_of)
                    if not stood:
                        self._imagined_left -= 1
                    if said is not None:
                        # A prediction with no state says only what the region will
                        # report: a hypothesis about the aim (S4).
                        to = self.inducer.situation(said.state) if said.state is not None else None
                        found.append((h, said, to))
                checked[scope] = len(held)
        if stood:
            self._applies[(situation, act)] = (checked, found)
            if self._view is not None and found:
                # What it predicts here was computed from these hypotheses and
                # this state, read now or in a cycle before.
                held = self._raw[self._raw_of[situation]]
                if isinstance(held, Recalled):
                    self._used[held.datum] = None
                for h, _, _ in found:
                    if h.recall is not None:
                        self._used[h.datum_id] = None
        return [*experienced, *found] if experienced else found

    def _best(self, situation: str, act: Act, state: Any = None) -> tuple[Hypothesis, Any, str] | None:
        """Of the hypotheses that apply and are held, the one right at the highest
        rate (FIT_LAW; Plone, 2026-09-28: a rate, not a count — by a count, a
        hypothesis held longer outranked a truer one met later)."""
        need = self._borne_out_by()
        held = [a for a in self._applicable(situation, act, state)
                if a[0].holds and a[0].supports - a[0].fails >= need and a[2] is not None]
        return max(held, key=lambda a: (a[0].rate, a[0].supports)) if held else None

    def _aims(self, situation: str, act: Act, state: Any = None) -> list[Hypothesis]:
        """The held hypotheses that say this act, here, brings the aim (S4)."""
        return [h for h, said, to in self._applicable(situation, act, state)
                if to is None and h.holds and self._reached(said.fields)]

    def _aims_at(self, situation: str, offers: tuple) -> list[tuple[Act, Hypothesis]]:
        """The acts here its held hypotheses say bring the aim, each with the one."""
        if not self._aim_held:
            return []
        out = []
        for act, _ in self._candidates(situation, offers):
            aims = self._aims(situation, act)
            if aims:
                out.append((act, max(aims, key=lambda h: (h.rate, h.supports))))
        return out

    def _state(self, situation: str) -> Any:
        """A state of a situation: one it stood in, or one it predicted."""
        raw = self._raw_of.get(situation)
        return self._stood(raw) if raw is not None else self._imagined[situation]

    def acknowledge(self, handle: object, datum_id: str) -> None:
        if isinstance(handle, Hypothesis):
            handle.datum_id = datum_id
            self._settle(handle)
        elif isinstance(handle, Reading):
            handle.datum_id = datum_id
            if self._view is not None and handle.recall is None:
                handle.held, handle.recall = None, self._recall_reading   # read there from now on

    # ── the onlooker ──

    def think(self, context: Context) -> Thinking | None:
        """It thinks on what collided, and writes the thought:

          - a step's return otherwise than it expected (`step`): silence turns it
            from that kind of act, an answer other than it foresaw to where the
            answer differed (`_think_on_collision`);
          - the region's report otherwise (`report`): an end turns it from the
            kind of act that led there, any other field turns nothing of its own
            (`_think_on_report`);
          - the onlooker's word (`onlooker`), which reaches the mind as a
            collision, and the mind commands again once it has thought.

        On the host waiting for want of a command, it thinks on where it stands,
        once in a situation (`_think_while_waiting`); on anything else — the host
        waiting for want of an aim — it does not think (None), so the mind does
        not wait on it. On the onlooker's
        word:

          - "repeating" an act, or going "back-and-forth" between two: the acts it
            names are objected to — where the region stands now, and, for a
            back-and-forth, at the states the alternation ran through. Said again
            after it was answered, the objection reaches back over the run the
            onlooker points at, as far as the field's alertness says (½–1½ of
            it, within the recent steps);
          - but told once that it repeats an act whose every step reached a state
            it had not stood in — its own evidence that the repetition is getting
            somewhere — it keeps on, and says why (`kept_on`); told again, it
            objects (Plone, 2026-09-28);
          - "standing still": it will act; with nothing else to do, it starts the
            region again;
          - anything else, or nothing: what it objected to on an earlier word is
            lifted.

        What it objected to, and why, is written; that thought is its answer."""
        if context.on == "step":
            return self._think_on_collision(context)
        if context.on == "report":
            return self._think_on_report(context)
        if context.on == "no command":
            return self._think_while_waiting()
        if context.on != "onlooker":
            return None
        remark = context.remark or {}
        said = self._said(remark)
        lifted = self._lift(said)
        # What it reads of its history to weigh the word, named in the answer.
        self._read_for_word = {}
        built = (context.seen[-1][1],) if context.seen else ()
        if context.remark_unit is not None:
            built = (*built, context.remark_unit)   # what it objected on
        if said is None or said[0] not in ("repeating", "back-and-forth", "standing still"):
            if not lifted:
                return None
            payload = {"on": "onlooker", "remark": remark, "lifted": lifted}
            return Thinking(writes=[Write(payload=payload, tags=dict(THOUGHT_TAGS), built_from=built)])
        again = said in self._objected
        if said[0] == "repeating" and not again and self._getting_somewhere(remark, context):
            built = (*built, *self._read_for_word)
            self._objected.setdefault(said, set())
            payload = {"on": "onlooker", "remark": remark, "here": self._here, "kept_on":
                       "each step of the run reached a state it had not stood in"}
            if lifted:
                payload["lifted"] = lifted
            return Thinking(writes=[Write(payload=payload, tags=dict(THOUGHT_TAGS), built_from=built)])
        pairs = self._objecting(remark, context, again)
        built = (*built, *(r for r in self._read_for_word if r not in built))
        self._objected.setdefault(said, set()).update(pairs)
        answer = Answer()
        answers = self._answers.setdefault(said, [])
        answers.append(answer)
        payload = {"on": "onlooker", "remark": remark, "here": self._here, "again": again,
                   "objected": sorted([self._state_of.get(raw, raw), self.organs.record(act)] for raw, act in pairs)}
        if lifted:
            payload["lifted"] = lifted
        return Thinking(writes=[Write(payload=payload, tags=dict(THOUGHT_TAGS), handle=answer, built_from=built)],
                        answer=tuple(("handle", a) for a in answers))

    def _think_while_waiting(self) -> Thinking | None:
        """The host waits with nothing it can do here: it thinks on where it
        stands, asking its model for a way to read this state it does not hold
        (`Inducer.consider`) — once in a situation, so a wait is thought on and
        does not set off another thought (the regress stops: the mind thinks on
        what comes from outside or while the host waits). Its model's answer is
        kept whole; a reading it gives is written, built from the state it stood
        in, and every state is read again. None where its model says nothing new
        (Plone, 2026-10-19: where every act wants what the model names, a model
        asked only on a step was never asked)."""
        if self._here is None or self._here in self._considered:
            return None
        self._considered.add(self._here)
        given = self.inducer.consider(self._here, self._state(self._here))
        built = (self._unit,) if self._unit is not None else ()
        writes = [Write(payload={**said.payload, "step": self.steps}, tags=dict(said.tags),
                        built_from=(*built, ("prior", "task"))) for said in self.inducer.said()]
        if given is not None:
            form, note = given
            reading = Reading(held=form)
            self.inducer.keep(form, lambda r=reading: r.form)
            writes += self._reindex(built)
            writes.append(Write(payload={**note.payload, "step": self.steps}, tags=dict(note.tags),
                                handle=reading, built_from=(*built, ("prior", "task"))))
        return Thinking(writes=writes) if writes else None

    def _think_on_collision(self, context: Context) -> Thinking | None:
        """A step's return did not come as it expected: it thinks on what collided,
        and the thought turns its next choice (the module's docstring)."""
        if self._last_step is None:
            return None
        source_raw, act, step, unit = self._last_step
        before, after = step.before, step.after
        situation = self.inducer.situation(before)
        if self.organs.restarts(act):
            return None
        kind = self._kind_of.get((situation, act)) or self.inducer.default_kind(act)
        if self._expected_otherwise and self.inducer.situation(after) == situation:
            self._turn = ("from", kind, self.inducer.coarse(kind) or kind, TURN_WHYS[0])
            said = {"collided": "silence", "act": self.organs.record(act), "turns": "from that kind of act"}
        elif not self._expected_otherwise and self._expected is not None:
            where = self.inducer.unlike(self._expected, after)
            if where is None:
                return None
            self._turn = ("unforeseen", where)
            said = {"collided": "unforeseen", "act": self.organs.record(act), "turns": "to where it differed"}
        else:
            return None
        # A collision the record says came before, the same way here by the same
        # kind of act, turns it for longer: a choice more for each time (DECLARED,
        # not measured; Plone, 2026-10-25: history as evidence to the thought).
        key = (said["collided"], situation, kind)
        repeats = self._repeats(key)
        if unit is not None:
            self._collided_unsettled.append((key, unit))
        self._turn_thought = TurnHandle(self.steps)
        self._turn_left = self._turn_hold() + len(repeats)
        built = ((unit,) if unit is not None else ()) + tuple(f"event:{seq}" for seq in repeats)
        self._turn_from = built
        if repeats:
            said = {**said, "came before": len(repeats), "holds for": self._turn_left}
        payload = {"on": "step", "step": self.steps, "here": self._state_of.get(source_raw), **said}
        return Thinking(writes=[Write(payload=payload, tags=dict(THOUGHT_TAGS), handle=self._turn_thought,
                                      built_from=built)])

    def _think_on_report(self, context: Context) -> Thinking | None:
        """The region's report did not come as it expected: it thinks on what
        collided, and writes it — an end turns it from the kind of act that led
        there, through the restart into the start again; the aim, which it learns
        from where it learns the report (S4), and any other field otherwise turn
        nothing of their own (a field that changes at every step, as a count
        does, turned it to repeat itself: LOG.md, 2026-10-11). Not a penalty, not
        a reward: a report that deviated (Plone, 2026-10-11)."""
        if self._last_step is None or self._report_now is None or self._report_was is None:
            return None
        source_raw, act, step, unit = self._last_step
        if self.organs.restarts(act):
            return None
        now, was = self._report_now, self._report_was
        fields = {k: [was.get(k), now.get(k)] for k in self.organs.report_fields if was.get(k) != now.get(k)}
        if not fields:
            return None
        situation = self.inducer.situation(step.before)
        kind = self._kind_of.get((situation, act)) or self.inducer.default_kind(act)
        coarse = self.inducer.coarse(kind) or kind
        handle = TurnHandle(self.steps)
        if self._ended(now) and not self._ended(was):
            self._turn = ("from", kind, coarse, TURN_WHYS[2])
            self._turn_thought = handle
            self._turn_left = self._turn_hold()
            self._turn_from = tuple(u for u in (unit, self._report_unit) if u is not None)
            said = {"collided": "the region ended", "turns": "from that kind of act"}
        elif self._reached(now):
            said = {"collided": "the aim came", "turns": "nothing of its own: what brings it is learned (S4)"}
        else:
            said = {"collided": "the report otherwise", "turns": "nothing of its own"}
        built = tuple(u for u in (unit, self._report_unit) if u is not None)
        payload = {"on": "report", "step": self.steps, "here": self._state_of.get(source_raw),
                   "act": self.organs.record(act), "fields": fields, **said}
        return Thinking(writes=[Write(payload=payload, tags=dict(THOUGHT_TAGS), handle=handle, built_from=built)])

    def _turned(self, here: str, fresh: list[tuple[Act, tuple]]) -> tuple[list[tuple[Act, tuple]], str]:
        """Of the acts not yet taken here, those a collision turned it to, with why;
        all of them, and no why, when it turned to none of them or was not turned."""
        if self._turn is None:
            return fresh, ""
        if self._turn[0] == "from":
            _, kind, coarse, turn_why = self._turn
            others = [ak for ak in fresh if ak[1] != kind and (self.inducer.coarse(ak[1]) or ak[1]) != coarse]
            return (others, turn_why) if others else (fresh, "")
        where = self._turn[1]
        state = self._state(here)
        there = [ak for ak in fresh if self.inducer.at(ak[0], state, where)]
        return (there, TURN_WHYS[1]) if there else (fresh, "")

    def read_field(self, field: Any) -> None:
        """The cycle's field, as it reaches every layer (INV-7); what it counts by
        it, once a cycle."""
        self._field = field
        t = getattr(field, "t", None)
        if field is None or t is None or t == self._counted_at:
            return
        self._counted_at = t
        self._counts = {
            "borne_out_by": self._counted("borne_out_by", 1 * falling(axis(field, TRUST))),
            "turn_hold": self._counted("turn_hold", TURN_HOLD * rising(axis(field, ALERTNESS))),
            "look_ahead": self._counted("look_ahead", MAX_IMAGINED_STEPS * rising(axis(field, EXPLORATION))),
        }

    def _counted(self, name: str, real: float) -> int:
        """A count the field shifts, as a whole number that follows it on average:
        the real value plus what rounding left over before, rounded down, never
        below 1; what is left over is carried to the next cycle (B2, Plone,
        2026-10-18: before, each count was rounded on its own, and in the ranges
        the field keeps the counts did not move). Deterministic: the same field,
        the same counts."""
        total = real + self._carried.get(name, 0.0)
        n = max(1, math.floor(total + 1e-9))      # what floating point leaves just short of a whole
        self._carried[name] = total - n if total >= 1 else 0.0
        return n

    def _borne_out_by(self) -> int:
        """How many more times than not an experience or hypothesis must have been
        borne out before it expects by it: 1 at NEUTRAL trust, more as trust falls."""
        if "borne_out_by" in self._counts:
            return self._counts["borne_out_by"]
        return round_half_up(shifted_count(1, falling(axis(self._field, TRUST))))

    def _turn_hold(self) -> int:
        """How many choices a collision's turn holds for: TURN_HOLD at NEUTRAL
        alertness, more as it grows alert."""
        if "turn_hold" in self._counts:
            return self._counts["turn_hold"]
        return round_half_up(shifted_count(TURN_HOLD, rising(axis(self._field, ALERTNESS))))

    def _look_ahead(self) -> int:
        """How many steps it looks ahead past where it has stood: MAX_IMAGINED_STEPS
        at NEUTRAL exploration, fewer as it consolidates, more as it explores."""
        if "look_ahead" in self._counts:
            return self._counts["look_ahead"]
        return round_half_up(shifted_count(MAX_IMAGINED_STEPS, rising(axis(self._field, EXPLORATION))))

    def _named(self, remark: dict[str, Any]) -> list[Act]:
        """The acts an onlooker's word names, as the host takes them (the host says
        which act a word names: `Organs.named_by`)."""
        named = [remark.get("act")] if remark.get("act") else list(remark.get("acts") or [])
        return [act for act in (self.organs.named_by(said) for said in named) if act is not None]

    def _said(self, remark: dict[str, Any]) -> tuple | None:
        """What the onlooker says, as one word: its stance and the acts it names."""
        stance = remark.get("remark")
        if not stance:
            return None
        return (stance, *sorted(self._named(remark)))

    def _lift(self, said: tuple | None) -> list[list[Any]]:
        """Lift what it objected to on any word the onlooker no longer says."""
        lifted = [list(k) for k in self._objected if k != said]
        self._objected = {k: v for k, v in self._objected.items() if k == said}
        self._answers = {k: v for k, v in self._answers.items() if k == said}
        return lifted

    def _objecting(self, remark: dict[str, Any], context: Context, again: bool) -> set[tuple[str, Act]]:
        """The (state as it came, act) pairs a word objects to."""
        named = set(self._named(remark))
        pairs: set[tuple[str, Act]] = set()
        if self._now_raw is not None and remark.get("remark") == "repeating":
            pairs |= {(self._now_raw, act) for act in named}
        run = int(remark.get("at_least") or 0)
        steps = [s for s, _ in self.recent_from_record(context.seen, self._read_for_word)]
        reach = min(run, len(steps)) if run and remark.get("remark") == "back-and-forth" else 0
        if again and run:
            reach = min(len(steps), int(shifted_count(run, rising(axis(context.field, ALERTNESS)))))
        for step in steps[len(steps) - reach:] if reach else []:
            act = self.inducer.learnable(step.act)
            if act in named:
                pairs.add((self.inducer.identity(step.before), act))
        return pairs

    def _getting_somewhere(self, remark: dict[str, Any], context: Context) -> bool:
        """Whether each step of the run the onlooker points at reached a situation
        not stood in before in that run."""
        run = int(remark.get("at_least") or 0)
        steps = [s for s, _ in self.recent_from_record(context.seen, self._read_for_word)][-run:] if run else []
        if len(steps) < run or not steps:
            return False
        states = [self.inducer.situation(steps[0].before)] + [self.inducer.situation(s.after) for s in steps]
        return len(set(states)) == len(states)

    def objections(self) -> set[tuple[str, Act]]:
        """What it objects to now, as (where the region stands, act)."""
        return {(self._state_of[raw], act) for held in self._objected.values() for raw, act in held
                if raw in self._state_of}

    # ── where the region stands ──

    def _report_key(self, report: dict[str, Any]) -> tuple:
        return tuple(report.get(k) for k in self.organs.report_fields)

    def _reached(self, report: dict[str, Any] | None) -> bool:
        """Whether a report shows the aim reached: a goal's fields, as they came;
        or, for the mind's own aim, a report other than the one the region has
        been making most, in a state it has not ended in (`mind.OWN_AIM`)."""
        if not report:
            return False
        reached_when = (self._aim or {}).get("reached_when") or {}
        fields = reached_when.get("fields") or {}
        if fields:
            return all(report.get(k) == v for k, v in fields.items())
        if reached_when.get("new") and self._reports:
            ordinary = max(self._reports, key=self._reports.get)
            return self._report_key(report) != ordinary and \
                report.get(self.organs.state_field) not in self.organs.ended
        return False

    def _ended(self, report: dict[str, Any] | None) -> bool:
        """Whether a report says the region has ended."""
        return bool(report) and report.get(self.organs.state_field) in self.organs.ended

    def _meet(self, state: Any, unit: Any = None, side: str = "after") -> str:
        """A state met: in hand this cycle, and from the next read from the store,
        on its `side` of the step `unit` came with."""
        raw = self.inducer.identity(state)
        if raw not in self._raw:
            self._raw[raw] = state
            if unit is not None:
                self._unsettled.append((raw, unit, side))
            situation = self.inducer.situation(state)
            self._state_of[raw] = situation
            self._raw_of.setdefault(situation, raw)
        return raw

    def _situation_of(self, raw: str) -> str:
        return self._state_of[raw]

    def _reindex(self, built_from) -> list[Write]:
        """Read every state again, the inducer's reading having changed; where two
        experiences are now one situation and act, the first counts the other
        against it if they disagree."""
        self._state_of = {raw: self.inducer.situation(self._stood(raw)) for raw in self._raw}
        self._raw_of = {}
        for raw, situation in self._state_of.items():
            self._raw_of.setdefault(situation, raw)
        self._edges, self._out, self._outcomes = {}, {}, {}
        self._scoped, self._applies, self._imagined = {}, {}, {}
        for h in self._hypotheses:
            self._scoped.setdefault(self.inducer.scope(h.form, self._situation_of), []).append(h)
        built_from = (*built_from, *self._take_used())
        writes: list[Write] = []
        for edge in self._learned:
            key = (self._state_of[edge.source], edge.act)
            self._outcomes.setdefault(key, []).append(edge)
            first = self._edges.get(key)
            if first is None:
                self._edges[key] = edge
                self._out.setdefault(key[0], {})[edge.act] = edge
            elif self._state_of[first.to] != self._state_of[edge.to] and (first, edge) not in self._against:
                self._against.add((first, edge))   # one experience, counted against it once
                writes += self._weigh(first, False, built_from)
        if self._here is not None and self._now_raw is not None:
            self._here = self._state_of[self._now_raw]
        # What it wrote of its experiences and hypotheses named situations as it
        # read them: read again, each written one is revised.
        for edge in self._learned:
            if edge.written:
                self._touch(edge)
        writes += [Write(payload=self._describe(h), revises=h, built_from=built_from)
                   for h in self._hypotheses if h.written]
        return writes

    # ── expecting, and learning ──

    def expect(self, step: Step) -> Expectation:
        self.steps += 1
        source = self.inducer.situation(step.before)
        act = self.inducer.learnable(step.act)
        best = self._best(source, act, step.before)
        unseen = (source, act) not in self._edges
        self._unseen_expected = None
        if unseen:
            self.unseen[0] += 1
        if best is not None:
            h, said, to = best
            if unseen:
                self.unseen[1] += 1
                self._unseen_expected = to
            state = self.inducer.copy(said.state)
            fields = said.fields
            self._expected = state
            self._expected_otherwise = False
            # The state it expects, as it reads it: what its model does not read
            # it expects nothing of, and an answer is not wrong for it.
            read = self.inducer.as_read(state)
            as_read = AsRead(state=read, matches=lambda after: self.inducer.as_read(after) == read)
            return Expectation(state=as_read, fields=dict(fields) if fields else None,
                               held=(("handle", h),), by_model=True)
        # Nothing it knows of this act here: what the same kind of act did where
        # it stood alike, it expects again — nothing, if that weighs more.
        self._expected = self.inducer.copy(step.before)
        recalled = self._recalled(source, act)
        if recalled is not None and recalled[0]:
            self._expected_otherwise = False
            read = self.inducer.as_read(step.before)
            return Expectation(state=AsRead(state=read, matches=lambda after: self.inducer.as_read(after) == read),
                               held=tuple(("handle", e) for e in recalled[1]), by_model=True)
        # Nothing it knows or recalls says what will come: it expects the region
        # to be otherwise than it was — what the act was commanded for (Plone,
        # 2026-10-11). Silence is then a mismatch; its scar falls on the return
        # and on what the expectation stood on (T5's standing expectation): the
        # choice that commanded the act comes back only after this step is met.
        self._expected_otherwise = True
        read = self.inducer.as_read(step.before)
        otherwise = Otherwise(state=read, differs=lambda after: self.inducer.as_read(after) != read)
        return Expectation(state=otherwise, by_model=False)

    def observe(self, step: Step, unit: Any, fields: dict[str, Any] | None, units: tuple[Any, ...],
                on_report: bool, seen: list | None = None) -> list[Write]:
        if on_report:
            return self._learn_report(fields, units)
        self._seen_now = list(seen or [(step, unit, None, None)])
        return self._learn_step(step, unit)

    def _weigh(self, h: Weighed, borne_out: bool, built_from: tuple[object, ...]) -> list[Write]:
        """Count a return for or against what it expects by — a hypothesis, or an
        experience — and revise its datum: how often it was borne out, and whether
        it holds, are in the store as they change (one not yet written enters with
        them; an experience's datum is revised once the step's report has come).
        When whether it holds changes, a datum of its own says so too, built from
        it: a refutation is an event a reader looks for (Plone, 2026-10-04)."""
        before = h.holds
        if borne_out:
            h.supports += 1
        else:
            h.fails += 1
        if isinstance(h, Edge):
            self._touch(h)
            if h.written and h.holds != before:
                return [Write(payload=self._experience(h), tags=self._experience_tags,
                              built_from=(*built_from, ("handle", h)))]
            return []
        if not h.written:
            return []
        # What a revision was built from: what it read, save itself.
        built_from = tuple(b for b in built_from if b != h.datum_id)
        writes = [Write(payload=self._describe(h), revises=h, built_from=built_from)]
        if h.holds != before:
            writes.append(Write(payload=self._describe(h), tags=self._hypothesis_tags,
                                built_from=(*built_from, ("handle", h))))
        return writes

    def _touch(self, edge: Edge) -> None:
        """An experience changed: its datum is written, or revised, once the step's
        report has come."""
        if edge not in self._pending:
            self._pending.append(edge)

    def _experience(self, edge: Edge) -> dict[str, Any]:
        """An experience, said as data."""
        return {"from": self._state_of[edge.source], "act": list(edge.act), "to": self._state_of[edge.to],
                "kind": list(edge.kind), "changed": edge.changed, "seen": edge.seen, "new": edge.new,
                **({"made": edge.made} if self.curiosity in MADE_LAWS else {}),
                "reached": edge.reached, "ended": edge.ended, "report": edge.report,
                "holds": edge.holds, "supports": edge.supports, "fails": edge.fails}

    def _experiences(self, built_from: tuple[object, ...]) -> list[Write]:
        """The experiences changed in this step, each written anew or revised."""
        writes = []
        for edge in self._pending:
            payload = self._experience(edge)
            if edge.written:
                writes.append(Write(payload=payload, revises=edge, built_from=built_from))
            else:
                edge.written = True
                writes.append(Write(payload=payload, tags=self._experience_tags, handle=edge,
                                    built_from=built_from))
        self._pending = []
        return writes

    def _learn_step(self, step: Step, unit: Any) -> list[Write]:
        writes: list[Write] = []
        # A turn holds for as many choices after the collision that made it as
        # alertness says; a collision in this step turns the mind again (`think`).
        if self._turn is not None and not self.organs.restarts(step.act):
            # A restart the region's end made is no choice the turn was for.
            self._turn_left -= 1
            if self._turn_left <= 0:
                self._turn = None
        if self._new:
            writes += self._write(())  # a step whose report never came
        if self._pending:
            writes += self._experiences(())
        o = self.organs
        act: Act = self.inducer.learnable(step.act)
        source_raw = self._meet(step.before, unit, "before")
        source = self._state_of[source_raw]
        known = self._edges.get((source, act))
        applied = list(self._applicable(source, act, step.before))
        new = self.inducer.situation(step.after) not in self._raw_of
        self.came_somewhere_new = new
        made = False
        if self.curiosity in MADE_LAWS:
            things = self.inducer.made(step)
            made = not things <= self._made
            self._made |= things
        novel = made if self.curiosity in MADE_LAWS else new   # what its law of curiosity counts as new
        to_raw = self._meet(step.after, unit, "after")
        self.holds_by_situation.append(int(self.inducer.situation(self._expected) == self._state_of[to_raw])
                                    if self._expected is not None else 0)
        kind = known.kind if known is not None else (self._kind_of.get((source, act)) or self.inducer.default_kind(act))
        to = self._state_of[to_raw]
        changed = to != source
        if not o.restarts(act):
            coarse = self.inducer.coarse(kind)
            for counts in (self._kinds.setdefault(kind, [0, 0, 0]), self._actions.setdefault(o.family(act), [0, 0, 0]),
                           *([self._coarse.setdefault(coarse, [0, 0, 0])] if coarse is not None else [])):
                counts[0] += 1
                counts[1] += int(novel)
            if changed:
                self._kind_changes[kind] = self._kind_changes.get(kind, 0) + 1
                if coarse is not None:
                    self._coarse_changes[coarse] = self._coarse_changes.get(coarse, 0) + 1
                self._action_changes[o.family(act)] = self._action_changes.get(o.family(act), 0) + 1
        self._last_new = known is None
        if self._unseen_expected is not None:
            self.unseen[2] += int(self._unseen_expected == to)
            self._unseen_expected = None
        # Every hypothesis that applied is borne out, or not, by where the region
        # stands — one about the aim, by what the region reports (below).
        self._aim_applied = [h for h, _, said in applied if said is None]
        applied = [a for a in applied if a[2] is not None]
        foreseen = any(h.holds and said == to for h, _, said in applied)
        # What it expected, and weighs by, was computed from what it read.
        self._expected_from = self._take_used()
        for h, _, said in applied:
            writes += self._weigh(h, said == to, (unit, *self._expected_from))
        self._last_step = (source_raw, act, step, unit)
        if known is None or not foreseen:
            # Never met, or what came nothing it holds foresaw: it asks what this suggests.
            self._new = self._induce(source_raw, act, step, foreseen, unit)
        # The experience of this outcome: met again, or one of its own.
        outcomes = self._outcomes.setdefault((source, act), [])
        edge = next((e for e in outcomes if self._state_of[e.to] == to), None)
        if edge is None:
            edge = Edge(source_raw, act, to_raw, kind, changed)
            outcomes.append(edge)
            self._learned.append(edge)
            if known is None:
                self._edges[(source, act)] = edge
                self._out.setdefault(source, {})[act] = edge
        else:
            edge.seen += 1
        edge.new += int(new)
        edge.made += int(made)
        self._touch(edge)
        # What the inducer said in computing — a language model's answers — kept
        # whole, built from the step it was asked on and the words it was told.
        for said in self.inducer.said():
            writes.append(Write(payload={**said.payload, "step": self.steps}, tags=dict(said.tags),
                                built_from=(unit, ("prior", "task"))))
        self._last = edge
        self._here, self._unit, self._now_raw = to, unit, to_raw
        self._visits[to] = self._visits.get(to, 0) + 1
        if o.restarts(act):
            self._learned_since_restart = False
        elif known is None:
            self._learned_since_restart = True
        reading = self.inducer.learn_reading(step, kind)
        if reading is not None:
            writes += self._reindex((unit,))
            writes.append(Write(payload={**reading.payload, "step": self.steps},
                                tags=dict(reading.tags), built_from=(unit,)))
        return writes

    def _learn_report(self, report: dict[str, Any] | None, units: tuple[Any, ...]) -> list[Write]:
        edge = self._last
        if edge is None or report is None:
            return []
        writes: list[Write] = []
        said = {k: report.get(k) for k in self.organs.report_fields}
        self._report_was, self._report_now = self._report_now, said
        self._report_unit = units[-1] if units else None
        key = self._report_key(said)
        self._reports[key] = self._reports.get(key, 0) + 1
        if edge.report is None:
            edge.report = said
        elif self._reached(edge.report) != self._reached(said):
            # The aim from one and not from the other: the experience did not bear
            # out. Whether the region ended is not weighed here: a region may end
            # for what the act did not do.
            writes += self._weigh(edge, False, units)
        # Each hypothesis that said this act, there, brings the aim is borne out
        # by the report, or not (S4).
        for h in self._aim_applied:
            writes += self._weigh(h, self._reached(said), (*units, *self._expected_from))
        self._aim_applied = []
        if self._reached(said) and not self.organs.restarts(edge.act) and self._last_step is not None:
            # Reaching the aim is an experience too: what it suggests brings the
            # aim, held and written as any hypothesis is (S4, Plone, 2026-09-28).
            source_raw, act, step, unit = self._last_step
            aims = self._induce(source_raw, act, step, False, unit, report=said)
            if aims:
                self._aim_held = True
                self._new = [*self._new, *aims]
        if said.get(self.organs.state_field) in self.organs.ended:
            edge.ended += 1
        if self._reached(said) and not self.organs.restarts(edge.act):
            edge.reached += 1
            self._kinds.setdefault(edge.kind, [0, 0, 0])[2] += 1
            coarse = self.inducer.coarse(edge.kind)
            if coarse is not None:
                self._coarse.setdefault(coarse, [0, 0, 0])[2] += 1
            self._actions.setdefault(self.organs.family(edge.act), [0, 0, 0])[2] += 1
        if self._new:
            writes += self._write(units)
        self._touch(edge)
        writes += self._experiences((*units, *self._expected_from))
        return writes

    def _describe(self, h: Hypothesis) -> dict[str, Any]:
        return {"inducer": self.inducer.kind, **self.inducer.describe(h.form, self._situation_of),
                **dict(zip(TALLIES, (h.holds, h.supports, h.fails)))}

    def _write(self, built_from: tuple[object, ...]) -> list[Write]:
        """The hypotheses the last experience suggested, each a datum built from it."""
        writes = []
        for h in self._new:
            h.written = True
            self.version += 1
            # Built from its step, what came with the step's report, and what was read to induce it.
            built = (*((h.unit,) if h.unit is not None else ()), *built_from, *h.read)
            writes.append(Write(payload=self._describe(h), tags=self._hypothesis_tags, handle=h,
                                built_from=built))
        self._new = []
        return writes

    # ── what to do next ──

    @staticmethod
    def _odds_of(counts) -> tuple[float, float]:
        tried, new, aim = counts
        return (aim + 1) / (tried + 2) if aim else 0.0, (new + 1) / (tried + 2)

    def _odds(self, kind: tuple) -> tuple[float, float]:
        """The odds it gives a kind of act: of the aim, and of somewhere new."""
        return self._odds_of(self._kinds.get(kind, (0, 0, 0)))

    def _wanted(self, counts, changes: int, total: int) -> tuple[float, ...]:
        """How much it wants what `counts` counts: the odds of the aim first; then,
        by its law of curiosity, the odds of somewhere new, of a change, or both,
        raised by how little it has been tried (UCB1)."""
        aim, new = self._odds_of(counts)
        tried = counts[0]
        more = math.sqrt(2 * math.log(total + 1) / (tried + 1))
        change = (changes + 1) / (tried + 2)
        if self.curiosity == "changed":
            return aim, change + more
        if self.curiosity == "new-then-changed":
            return aim, new + more, change
        if self.curiosity == "new-plus-changed":
            return aim, new + change + more
        return aim, new + more

    def _change_odds(self, kind: tuple) -> float:
        """The odds it gives a kind of act of a change."""
        return (self._kind_changes.get(kind, 0) + 1) / (self._kinds.get(kind, (0, 0, 0))[0] + 2)

    def _action_curiosity(self, act: int) -> tuple[float, ...]:
        """How much it wants an act at all, over every kind of it."""
        total = sum(a[0] for a in self._actions.values())
        attended = self._attend(lambda e: self.organs.family(e.act) == act, ("act", act))
        if attended is not None:
            return self._wanted(*attended, total)
        return self._wanted(self._actions.get(act, (0, 0, 0)), self._action_changes.get(act, 0), total)

    def _curiosity(self, kind: tuple) -> tuple[float, ...]:
        """How much it wants a kind of act, by its law of curiosity: the coarser
        kind it falls in first, when it has one, then the kind itself."""
        total = sum(k[0] for k in self._kinds.values())
        attended = self._attend(lambda e: e.kind == kind, ("kind", kind))
        fine = self._wanted(*attended, total) if attended is not None else \
            self._wanted(self._kinds.get(kind, (0, 0, 0)), self._kind_changes.get(kind, 0), total)
        coarse = self.inducer.coarse(kind)
        if coarse is None:
            return fine
        attended = self._attend(lambda e: self.inducer.coarse(e.kind) == coarse, ("coarse", coarse))
        wide = self._wanted(*attended, total) if attended is not None else \
            self._wanted(self._coarse.get(coarse, (0, 0, 0)), self._coarse_changes.get(coarse, 0), total)
        return (*wide, *fine)

    def _attend(self, which: Callable[[Edge], bool], key: tuple | None = None
                ) -> tuple[tuple[float, float, float], float] | None:
        """What an act did in the situations most like where it stands (ATTENTION):
        (tried, somewhere new, aim) and changes, each weighed by how alike; None
        without attention, or when too little alike to go by.

        Within a choice (`_look_alike`), the experiences are ranked once and what
        each `key` gave is kept: the sort is stable, so ranking all and then
        keeping those `which` holds gives what sorting those alone gave."""
        if not self.attention or not self._alike:
            return None
        if self._ranked is not None and key is not None:
            kept = self._attend_memo.get(key)
            if kept is not None:
                self._last_attended = kept[1]
                return kept[0]
            met = []
            for se in self._ranked:
                if which(se[1]):
                    met.append(se)
                    if len(met) == ATTENTION_K:
                        break
            got = self._attended_from(met)
            self._attend_memo[key] = (got, self._last_attended)
            return got
        met = sorted(((self._alike.get(e.source, 0.0), e) for e in self._learned
                      if not self.organs.restarts(e.act) and which(e)), key=lambda se: -se[0])[:ATTENTION_K]
        return self._attended_from(met)

    def _attended_from(self, met: list[tuple[float, Edge]]) -> tuple[tuple[float, float, float], float] | None:
        """The counts of the experiences attended to, each weighed by how alike."""
        self._last_attended = []
        weighed = [(e, a ** ATTENTION_SHARPNESS) for a, e in met if a > 0]
        tried = sum(w * e.seen for e, w in weighed)
        if tried < ATTENTION_MIN_WEIGHT:
            return None
        self._last_attended = weighed
        new = sum(w * (e.made if self.curiosity in MADE_LAWS else e.new) for e, w in weighed)
        aim = sum(w * e.reached for e, w in weighed)
        changes = sum(w * e.seen for e, w in weighed if e.changed)
        return (tried, new, aim), changes

    def _look_alike(self, here: str) -> None:
        """How alike each state met is to where it stands, for a choice (attention);
        once a choice — again only for another place."""
        if self._ranked is not None and self._alike_for == here:
            return
        self._alike_for = here
        self._alike, self._attended, self._last_attended = {}, [], []
        if not self.attention or here not in self._raw_of:
            return
        now = self._state(here)
        for raw in {e.source for e in self._learned}:
            self._alike[raw] = self.inducer.similarity(now, self._stood(raw))
        self._ranked = sorted(((self._alike.get(e.source, 0.0), e) for e in self._learned
                               if not self.organs.restarts(e.act)), key=lambda se: -se[0])
        self._attend_memo = {}

    def _candidates(self, here: str, offers: tuple) -> list[tuple[Act, tuple]]:
        return self.inducer.candidates(here, self._state(here), offers)

    def _open_here(self, here: str, offers: tuple,
                   objected: set[tuple[str, Act]] | None = None) -> list[tuple[Act, tuple]]:
        """The acts not yet taken from here, and not objected to."""
        objected = self.objections() if objected is None else objected
        return [(act, kind) for act, kind in self._candidates(here, offers)
                if (here, act) not in self._edges and (here, act) not in objected]

    def _foreseen(self, here: str, act: Act) -> bool:
        """Whether its hypotheses say an act leads where it has stood. Such an act
        is put behind the others, never out of reach: a hypothesis that kept an
        act from being taken could never be refuted by it. And an act never once
        taken is never foreseen: what a hypothesis says of an act no return has
        borne out or refuted is not yet anything learned of it (Plone,
        2026-10-19: where every state was new, an act still to be tried in each
        stood ahead of two acts a hypothesis said led nowhere, never having met
        them, and those two were never taken in 300 steps)."""
        if not self.inducer.general:
            return False
        if not self._actions.get(self.organs.family(act), (0, 0, 0))[0]:
            return False
        best = self._best(here, act)
        if best is not None:
            return best[2] in self._raw_of
        # Recalled from where it stood alike: nothing comes of it — it leads here.
        if (here, act) in self._edges:
            return False
        recalled = self._recalled(here, act)
        return recalled is not None and recalled[0]

    def _recalled(self, here: str, act: Act) -> tuple[bool, list[Edge]] | None:
        """What the same kind of act did where it stood in states alike to here
        (its attention): whether more weight came to nothing, and the experiences
        that did as that weight says; None without attention or too little alike."""
        if not self.attention or not self._alike or here != self._alike_for or self.organs.restarts(act):
            return None
        kind = self._kind_of.get((here, act)) or self.inducer.default_kind(act)
        got = self._attend(lambda e: e.kind == kind, ("kind", kind))
        if got is None:
            return None
        (tried, _, _), changes = got
        silent = changes < tried / 2
        return silent, [e for e, _ in self._last_attended if (not e.changed) == silent]

    def _ways(self, node: str, offers: tuple) -> list[tuple[Act, str, Hypothesis, Any]]:
        """From a situation, where each act leads, by the hypothesis it holds best
        there: the acts taken from it first, in the order taken — never one that
        ended the region every time — then, for an inducer whose hypotheses reach
        past where they were met, any other its hypotheses predict."""
        ways = []
        taken = self._out.get(node, {})
        for act, edge in taken.items():
            if self.organs.restarts(act) or edge.ended >= edge.seen:
                continue
            best = self._best(node, act)
            if best is not None:
                ways.append((act, best[2], best[0], best[1]))
        if self.inducer.general:
            for act, _ in self._candidates(node, offers):
                if act not in taken:
                    best = self._best(node, act)
                    if best is not None:
                        ways.append((act, best[2], best[0], best[1]))
        return ways

    def _path(self, start: str, goal: Callable[[str], bool], offers: tuple,
              avoid: set[tuple[str, Act]] | frozenset = frozenset()) -> list[tuple[Act, Hypothesis]] | None:
        """The shortest way from `start` to a situation `goal` holds of, looking
        ahead by what its held hypotheses predict — through situations it has stood
        in, and at most MAX_IMAGINED_STEPS past them — whose first act is none of
        `avoid` there: each step an act and the hypothesis it goes by; None if none."""
        prev: dict[str, tuple[str, Act, Hypothesis] | None] = {start: None}
        past: dict[str, int] = {start: 0}          # steps taken past where it has stood
        queue = deque([start])
        while queue and len(prev) < MAX_PATH_NODES:
            node = queue.popleft()
            if node != start and goal(node):
                path = []
                while prev[node] is not None:
                    node, act, h = prev[node]
                    path.append((act, h))
                return path[::-1]
            if past[node] >= self._look_ahead():
                continue
            for act, to, h, said in self._ways(node, offers):
                if to in prev or (node == start and (start, act) in avoid):
                    continue
                if to not in self._raw_of:
                    self._imagined.setdefault(to, said.state)
                    past[to] = past[node] + 1
                else:
                    past[to] = 0
                prev[to] = (node, act, h)
                queue.append(to)
        return None

    def _curious(self, here: str, pool: list[tuple[Act, tuple]]) -> tuple[Act, float]:
        """Of the acts in `pool`, the one it is most curious about: first which act,
        over every kind of it; then which of its kinds. With the odds it gives it."""
        self._look_alike(here)
        try:
            return self._most_curious(here, pool)
        finally:
            self._ranked, self._attend_memo = None, {}

    @staticmethod
    def _spread(agreeing: float, n: float) -> float:
        """How unsure an expectation is: the spread of its rate, by its evidence."""
        p = (agreeing + 1) / (n + 2)
        return math.sqrt(p * (1 - p) / (n + 3))

    def _held_of(self, here: str, act: Act, kind: tuple, weight: float
                 ) -> tuple[float, float, float, list[Any]]:
        """What it expects of an act here, as T1 weighs it: (how likely what comes is
        a state memory does not hold, agreeing, evidence, what holds the
        expectation). It is held by the hypothesis it expects by — which names
        what will come, and is wrong at its rate — or by the experiences it
        recalls from states alike (each with its weight), or by nothing; where
        nothing names it, how often that kind of act made something not made
        before (`Inducer.made`), alike first, then anywhere, then its coarser
        kind. The evidence is weighed by the field's trust (`weight`)."""
        got = self._attend(lambda e: e.kind == kind, ("kind", kind))
        recalled = self._last_attended
        if got is not None:
            tried, new = got[0][0], got[0][1]
        else:
            coarse = self.inducer.coarse(kind)
            counts = self._kinds.get(kind, (0, 0, 0))
            if not counts[0] and coarse is not None:
                counts = self._coarse.get(coarse, (0, 0, 0))
            tried, new = counts[0], counts[1]
        unnamed = (new * weight + 1) / (tried * weight + 2)
        best = self._best(here, act)
        if best is not None:
            h = best[0]
            right = (h.supports * weight + 1) / ((h.supports + h.fails) * weight + 2)
            return (1 - right) * unnamed, h.supports, h.supports + h.fails, [h]
        if got is not None:
            changes = got[1]
            silent = changes < tried / 2
            return unnamed, max(changes, tried - changes), tried, \
                [(e, w) for e, w in recalled if (not e.changed) == silent]
        return unnamed, 0.0, 0.0, []

    def _kind_spread(self, counts, changes: float) -> float:
        """How unsure what a kind of act does everywhere is: a change or not."""
        tried = counts[0]
        return self._spread(max(changes, tried - changes), tried)

    def _least_sure(self, here: str, pool: list[tuple[Act, tuple]]) -> tuple[Act, float]:
        """T1: of the acts in `pool`, the one whose expectation least says what will
        come — the likeliest to come where memory holds nothing; at an equal
        likelihood, the one it is least sure of. What brings the aim first."""
        weight = rising(axis(self._field, TRUST))
        ranked = []
        for act, kind in pool:
            unheld, agreeing, n, held = self._held_of(here, act, kind, weight)
            spread = self._spread(agreeing * weight, n * weight)
            coarse = self.inducer.coarse(kind)
            fine = (self._kinds.get(kind, (0, 0, 0)), self._kind_changes.get(kind, 0))
            wide = (self._coarse.get(coarse, (0, 0, 0)), self._coarse_changes.get(coarse, 0)) \
                if coarse is not None else fine
            key = (self._odds_of(wide[0])[0], self._odds_of(fine[0])[0], round(unheld, 9), round(spread, 9),
                   self._kind_spread(*wide), self._kind_spread(*fine), tuple(-n for n in self.organs.order(act)))
            ranked.append((key, act, kind, unheld, spread, held))
        _, act, kind, unheld, spread, held = max(ranked, key=lambda r: r[0])
        self._unsure = round(spread, 3)
        self._kind_of[(here, act)] = kind
        self._chosen_kind = kind
        self._attended = [ew for ew in held if isinstance(ew, tuple)]
        self._tested_by = [h for h in held if isinstance(h, Hypothesis)]
        return act, unheld

    def _most_curious(self, here: str, pool: list[tuple[Act, tuple]]) -> tuple[Act, float]:
        if self.curiosity == "test":
            return self._least_sure(here, pool)
        # Which of the host's acts first (its family), over every kind of it; at
        # equal want, the first in the host's order.
        first: dict = {}
        for act, _ in pool:
            f = self.organs.family(act)
            first[f] = min(first.get(f, self.organs.order(act)), self.organs.order(act))
        chosen = max(first, key=lambda f: (self._action_curiosity(f), tuple(-n for n in first[f])))
        best = max((ak for ak in pool if self.organs.family(ak[0]) == chosen), key=lambda ak: self._curiosity(ak[1]))
        self._kind_of[(here, best[0])] = best[1]
        self._chosen_kind = best[1]
        attended = self._attend(lambda e: e.kind == best[1], ("kind", best[1]))     # what the chosen kind was weighed by
        if attended is not None:
            self._attended = list(self._last_attended)
            (tried, new, aim), changes = attended
            self._attended_change = (changes + 1) / (tried + 2)
            return best[0], self._attended_change if self.curiosity == "changed" else self._odds_of((tried, new, aim))[1]
        if self.curiosity == "changed":
            return best[0], self._change_odds(best[1])
        return best[0], self._odds(best[1])[1]

    def _way(self, here: str, goal: Callable[[str], bool], offers: tuple,
             objected: set[tuple[str, Act]]) -> tuple[list[tuple[Act, Hypothesis]] | None, bool]:
        """A way to where `goal` holds whose first act is not objected to; only if
        there is none, one that is (and says so)."""
        path = self._path(here, goal, offers, avoid=objected)
        if path:
            return path, False
        path = self._path(here, goal, offers)
        return path, bool(path)

    def propose(self, context: Context) -> tuple[Proposal, list[Write]]:
        # What it imagined for the last choice is not kept: each choice looks ahead anew.
        self._imagined, self._imagined_left = {}, MAX_IMAGINED_PREDICTIONS
        here = self._here
        if here is None:
            return Proposal(None, why="nowhere yet"), []
        # How alike each state met is to here, read anew for this choice: what it
        # recalls from where it stood alike (`_recalled`) and what it attends to.
        self._ranked = None
        self._look_alike(here)
        offers = context.offers
        through: list[Weighed] = []
        odds: float | None = None
        act: Act | None = None
        said = self._said(context.remark or {})
        lifted = self._lift(said)
        objected = self.objections()
        if context.ended is not None:
            act, why = self.organs.restart, f"the region has ended ({context.ended})"
        else:
            # Toward the aim it takes no objection.
            gained = {self._state_of[e.source] for e in self._learned if e.holds and self._reached(e.report)}
            aim_here = [e for e in self._learned
                        if self._state_of[e.source] == here and e.holds and self._reached(e.report)]
            # What its hypotheses say brings the aim, where it stands or where it
            # can go (S4): after what reached it, before what it has not tried.
            said_here = [] if aim_here else self._aims_at(here, offers)
            path = None if aim_here or said_here or not gained else self._path(here, lambda n: n in gained, offers)
            toward = None
            if not (aim_here or said_here or path) and self._aim_held:
                toward = self._path(here, lambda n: bool(self._aims_at(n, offers)), offers)
            opened = self._open_here(here, offers, objected)
            fresh = [ak for ak in opened if not self._foreseen(here, ak[0])]
            if aim_here:
                act, why, through = aim_here[0].act, "an act that reached the aim before", [aim_here[0]]
            elif said_here:
                act, h = said_here[0]
                why, through = "an act its hypotheses say brings the aim here", [h]
            elif path:
                act, why, through = path[0][0], f"toward the aim reached before ({len(path)} steps)", [h for _, h in path]
            elif toward:
                act, through = toward[0][0], [h for _, h in toward]
                why = f"toward where its hypotheses say an act brings the aim ({len(toward)} steps)"
            elif fresh:
                turned, turn_why = self._turned(here, fresh)
                act, odds = self._curious(here, turned)
                why = "not yet taken from here" + turn_why
            else:
                # Where it has not tried something it cannot foresee — a situation
                # it has not stood in is itself such a place; then what it can
                # foresee, here; then, anywhere.
                def fresh_at(n: str) -> bool:
                    return n not in self._raw_of or any(not self._foreseen(n, a)
                                                         for a, _ in self._open_here(n, offers, objected))

                def open_at(n: str) -> bool:
                    return n in self._raw_of and bool(self._open_here(n, offers, objected))

                path, over = self._way(here, fresh_at, offers, objected)
                foreseen = False
                if not path and not opened and self.inducer.general:
                    path, over = self._way(here, open_at, offers, objected)
                    foreseen = bool(path)
                if path:
                    act, through = path[0][0], [h for _, h in path]
                    why = f"toward a state with an act not yet taken ({len(path)} steps)" + \
                        ("; its hypotheses say where each leads" if foreseen else "") + \
                        ("; objected to, and no other way" if over else "")
                elif opened:
                    act, odds = self._curious(here, opened)
                    why = "not yet taken from here; its hypotheses say where each leads"
                elif self._learned_since_restart:
                    act, why = self.organs.restart, "nothing left to try from anywhere it can reach"
                else:
                    known = [e for e in self._out.get(here, {}).values()
                             if self.organs.offered(e.act, offers) and not self.organs.restarts(e.act)]
                    free = [e for e in known if (here, e.act) not in objected]
                    if free:
                        least = min(free, key=lambda e: (self._visits.get(self._state_of[e.to], 0), e.seen,
                                                         *self.organs.order(e.act)))
                        act, why, through = least.act, "all known; toward the state visited least", [least]
                    elif known:
                        act, why = self.organs.restart, "every act known here was objected to"
                    elif said is not None and said[0] == "standing still":
                        act, why = self.organs.restart, "standing still, and nothing else it can do here"
                    else:
                        why = "nothing it can do here"
        self.thoughts.append(Choice(self.steps, act, why, odds))
        choice: dict[str, Any] = {"step": self.steps, "here": here, "chose": self.organs.record(act) if act is not None else None,
                                  "counts": dict(self._counts),
                                  # What rounding left over, carried into the next cycle's counts
                                  # (B2): with the fields, a reader recomputes every count.
                                  "carried": {k: round(v, 6) for k, v in self._carried.items()},
                                  "field": {name: round(axis(self._field, name), 3) for name in (TRUST, ALERTNESS,
                                                                                                 EXPLORATION)},
                                  "why": why, "aim": (self._aim or {}).get("aim")}
        if odds is not None and self.curiosity == "test":
            choice["unheld"] = round(odds, 3)
            choice["unsure"] = self._unsure
            through = [*through, *(h for h in self._tested_by if h not in through)]
        elif odds is not None:
            if self.curiosity == "changed":
                choice["odds_of_change"] = round(odds, 3)
            else:
                choice["odds_of_new"] = round(odds, 3)
                if self.curiosity != "new":
                    choice["odds_of_change"] = round(self._attended_change if self._attended
                                                     else self._change_odds(self._chosen_kind), 3)
        built: list[object] = [self._unit] if self._unit is not None else []
        if odds is not None and self._attended:
            # The experiences it went by (attention), each with its weight; what
            # each suggested, it was built from.
            choice["attended"] = [{"at": self._state_of[e.source], "act": self.organs.record(e.act), "weight": round(w, 3)}
                                  for e, w in self._attended]
            through = [*through, *(e for e, _ in self._attended if e not in through)]
        if lifted:
            choice["lifted"] = lifted
        if context.on == "command again" and self._last_choice is not None \
                and self._last_choice.get("step") == self.steps:
            choice["supersedes"] = {"chose": self._last_choice.get("chose"), "why": self._last_choice.get("why")}
        self._last_choice = choice
        if context.remark and context.remark.get("remark"):
            choice["onlooker"] = context.remark
            if context.remark_unit is not None:
                built.append(context.remark_unit)   # what it quotes, it was built from
        built += [("handle", h) for h in through]
        if self._turn_thought is not None and why.endswith(TURN_WHYS):
            # What turned it: the return that collided — for every choice the turn
            # holds for — and the thought on it, whose id is known only once it
            # comes back, in a later cycle: the mind names it then (`relinks`).
            built += [u for u in self._turn_from if u not in built]
            built.append(("handle", self._turn_thought))
        built.append(("prior", "task"))
        # And what it read, or computed from what it read, to choose.
        built += [b for b in self._take_used() if b not in built]
        return Proposal(act, why=why), [Write(payload=choice, tags=dict(CHOICE_TAGS), built_from=tuple(built),
                                              handle=ChoiceHandle(), relinks=True)]


__all__ = ["CHOICE_TAGS", "CURIOSITY", "EXPERIENCE_TAGS", "FIT_LAW", "HYPOTHESIS_TAGS", "MAX_PATH_NODES", "THOUGHT_TAGS",
           "Answer", "Choice", "Edge", "Hypothesis", "Learning"]
