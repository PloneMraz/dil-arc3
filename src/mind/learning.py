"""The mind's learning — neutral about its region and about the model it learns with.

Plone (2026-09-28): learning is developing experience into what serves the agent,
not storing it; and it is the mind's, not the model's — another task, another
model, and learning is not defined again. The mind holds the loop; a model — an
inducer (`models/exact.py`, `grid.py`, `language_inducer.py`) — is its
computing: what a state is to it, what can be done in one, what an experience
suggests, what a hypothesis predicts.

THE LOOP, one step at a time:

- **Experience.** Each step — from where the region stood, an act, where it
  stands and what it reported of itself — is kept, accrued (INV-5), with how
  often it was met and how often the region ended on it.
- **Hypotheses are data.** What an experience suggests, the inducer says — asked
  of a step from a situation and act never met, and of one no hypothesis it held
  foresaw; the mind holds each as a hypothesis, once (what the inducer keys
  alike is one), and writes it (`kind: hypothesis`), built from the step and
  the report it came in.
- **Expecting.** For a step, the hypotheses that apply to where the region stood
  and the act; of those it holds, the one that fits the store best is the
  expectation, and is what the expectation is (`held_by`) — so when the region
  returns otherwise, it is scarred (v0.3.5).
- **Weighing.** Each return that a hypothesis predicted counts for it, each it
  did not counts against: a hypothesis is held while it has been right more
  often than wrong, and the one right at the highest rate is preferred (DECIDE@IMPL
  FIT_LAW; tag H: fit against the store, never a scored standard). When that
  changes, a new datum says so, built from the one before: nothing is revised
  in place.
- **Choosing.** Toward the aim it has reached before; else what it knows least
  (curiosity, below) — an act its hypotheses say leads where it has stood last,
  never out of reach;
  else the shortest way to where something is left to try, looking ahead by what
  its held hypotheses predict — through the situations it has stood in and, for
  an inducer whose hypotheses reach past where they were met, up to
  MAX_IMAGINED_STEPS past them, where a situation not stood in is itself
  something left to try; else RESET, or the known act toward the situation least
  visited.
- **The onlooker's word** strikes the mind as a collision; what it objects to is
  put behind every other act at every point of choice — never over a known way
  to the aim — and lifted when the onlooker says something else. A repetition
  whose every step went somewhere new is kept on, told once; told again, it is
  objected to.

CURIOSITY. Per kind of act, and per act over every kind of it: how often it was
tried, how often it reached a situation not met before, how often the aim came
of it. What most often brought the aim first; then the odds of somewhere new
(Laplace), raised by how little it has been tried (UCB1). Somewhere new, not a
change: an act that only takes it back where it stood (an undo) changes the
state every time and teaches it nothing (Plone, 2026-09-28: S2b).

A step ends one of three ways: nothing changed (blocked), it changed but came
back to a situation met before, or it reached one not met before. Which of them
the mind counts as worth trying is `curiosity` (CURIOSITY), each a law of the
mind naming no task; the default is S2b, the others are kept to be measured
against it (Plone, 2026-09-28):

  new               S2b  somewhere new
  changed           S2   a change: somewhere new or back where it stood
  new-then-changed  S2c  somewhere new; between kinds as likely to, a change
  new-plus-changed  S2d  the odds of somewhere new and of a change, added

What it holds but does not write — its counts, how often an experience was met
and ended the region, the situations it visited — follows from the observations
in the store only when those are replayed through it, in order. So does
`unseen`: of the steps from a situation and act never met, how many it expected
and how many of those it expected right — what it learned, reaching further.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Final

from dil.loop.field import ALERTNESS, axis, rising, shifted_count

from .models.base import Context, Expectation, Inducer, Proposal, Thinking, Write
from .organs import Act, Organs, Step

HYPOTHESIS_TAGS: Final = {"domain": "mind", "kind": "hypothesis", "object": "frame", "source": "mind"}
CHOICE_TAGS: Final = {"domain": "mind", "kind": "choice", "source": "mind"}
THOUGHT_TAGS: Final = {"domain": "mind", "kind": "thought", "source": "mind"}

# How far it searches the situations it knows for a way. DECLARED: a bound on work.
MAX_PATH_NODES: Final = 20_000
# How many steps it looks ahead past the situations it has stood in, on what its
# hypotheses predict. DECLARED: a bound on work.
MAX_IMAGINED_STEPS: Final = 3
# DECIDE@IMPL (tag H) — how a hypothesis is weighed against the store.
# What the mind counts as worth trying (the docstring's CURIOSITY), by name; the
# first is the default (S2b).
CURIOSITY: Final = ("new", "changed", "new-then-changed", "new-plus-changed")
FIT_LAW: Final = ("held while right more often than wrong (supports > fails); of those that apply, "
                  "the one right at the highest rate, (supports + 1) / (supports + fails + 2), is the "
                  "expectation; at an equal rate, the one right more often")


@dataclass(eq=False)
class Hypothesis:
    """A hypothesis the mind holds: the inducer's form, how often the region bore it
    out and how often not. Its own handle, as data."""

    form: Any
    supports: int = 1          # the experience it was induced from bears it out
    fails: int = 0
    written: bool = False
    datum_id: str | None = None

    @property
    def holds(self) -> bool:
        return self.supports > self.fails

    @property
    def rate(self) -> float:
        """How often it was right, Laplace's estimate: (right + 1) / (tried + 2)."""
        return (self.supports + 1) / (self.supports + self.fails + 2)


@dataclass(eq=False)
class Edge:
    """One experience: from a state, an act, came a state and a report. `source`
    and `to` are the states as they came (their own identities); where the region
    stood is read from them by the inducer's perception now."""

    source: str
    act: Act
    to: str
    kind: tuple
    changed: bool
    hypothesis: Hypothesis = field(default_factory=lambda: Hypothesis(None))
    status: dict[str, Any] | None = None
    ended: int = 0               # how many times the region ended on it
    seen: int = 1


class Answer:
    """What it answered an Other's word with — the thought it wrote — as its own
    handle: the mind's expectation that the Other stops saying it is this datum,
    and said again, it is scarred."""


@dataclass
class Choice:
    """One command, for the run's report (the trace is `[event]` and the store)."""

    frame_call: int
    act: Act | None
    why: str
    odds: float | None = None


class Learning:
    """The mind's learning loop, computing with an inducer — the model in the
    mind's seat for one. The mind holds it (`mind.py`), and its seams ask it what
    to expect, show it what came back, ask it what to do."""

    def __init__(self, inducer: Inducer, organs: Organs, priors: dict[str, dict[str, str]],
                 curiosity: str = CURIOSITY[0]) -> None:
        if curiosity not in CURIOSITY:
            raise ValueError(f"curiosity is one of {CURIOSITY}, not {curiosity!r}")
        self.inducer = inducer
        self.organs = organs
        self.curiosity = curiosity
        # How often each kind of act, and each act, changed the state (for the
        # laws that count a change: S2, S2c, S2d).
        self._kind_changes: dict[tuple, int] = {}
        self._action_changes: dict[int, int] = {}
        self._now_raw: str | None = None                       # the latest state's own identity
        self._last_choice: dict[str, Any] | None = None        # the choice it wrote last
        # What the onlooker's word made it object to, by what the word was: (the
        # state as it came, act). Held while the onlooker says it; lifted when it
        # says something else; read by the inducer's perception now.
        self._objected: dict[tuple, set[tuple[str, Act]]] = {}
        # Its answers to each word, while the word stands.
        self._answers: dict[tuple, list[Answer]] = {}
        self._cues = dict(priors)        # it reads the task, for its aim
        self.thoughts: list[Choice] = []
        self.holds_off_clock: list[int] = []
        self.version = 0                  # hypotheses written
        self.code = None                  # it writes no program
        self._aim: dict[str, Any] | None = None
        self._aim_new = False
        self._raw: dict[str, Any] = {}                      # a state, by its own identity
        self._state_of: dict[str, str] = {}                 # identity -> where the region stood
        self._grid_of: dict[str, str] = {}                  # a situation -> a state of it
        self._learned: list[Edge] = []                      # every experience, in the order met
        self._edges: dict[tuple[str, Act], Edge] = {}
        self._out: dict[str, dict[Act, Edge]] = {}
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
        self._keys: set = set()                              # what each hypothesis says, as the inducer keys it
        # Steps from a situation and act never met: how many, how many it expected,
        # how many of those it expected right — what it learned, reaching further.
        self.unseen = [0, 0, 0]
        self._unseen_expected: str | None = None
        self._imagined: dict[str, Any] = {}                  # a situation predicted, never stood in
        self._against: set[tuple[Edge, Edge]] = set()   # experiences read as one, counted against
        self._learned_since_reset = True
        self.frame_calls = 0
        # The mind's short-term perception at the step being learned: what an
        # inducer is shown when it is asked what the step suggests.
        self._seen_now: list = []
        self._chosen_kind: tuple | None = None

    # ── what it reads ──

    def cues(self) -> dict[str, dict[str, str]]:
        return dict(self._cues)

    def required(self) -> frozenset[str]:
        return frozenset()

    def receive_prior(self, name: str, payload: Any, datum_id: str) -> None:
        self.inducer.receive_prior(name, payload)
        aim = payload.get("aim") if isinstance(payload, dict) else None
        if name == "task" and isinstance(aim, dict) and isinstance(aim.get("reached_when"), dict):
            self._aim = {"aim": str(aim.get("aim") or ""), "source": "stated",
                         "reached_when": dict(aim["reached_when"]), "within": None}
            self._aim_new = True

    def stated_aim(self) -> dict[str, Any] | None:
        if self._aim_new:
            self._aim_new = False
            return dict(self._aim)
        return None

    def can_propose(self) -> bool:
        return True

    def held(self) -> tuple[object, ...]:
        return ()

    # ── hypotheses ──

    def _add(self, h: Hypothesis) -> None:
        self._hypotheses.append(h)
        self._scoped.setdefault(self.inducer.scope(h.form, self._situation_of), []).append(h)

    def _induce(self, source_raw: str, act: Act, step: Step, foreseen: bool) -> list[Hypothesis]:
        """What an experience suggests, held — save what it holds already. The
        inducer is told whether a hypothesis held foresaw the step, and shown
        short-term perception: one whose computing is costly computes only what
        was not foreseen."""
        out = []
        evidence = tuple((s, r) for s, _, r in self._seen_now)
        for form in self.inducer.induce(source_raw, act, step.before, step.after, foreseen=foreseen,
                                        evidence=evidence):
            key = self.inducer.key(form)
            if key in self._keys:
                continue
            self._keys.add(key)
            h = Hypothesis(form)
            self._add(h)
            out.append(h)
        return out

    def _applicable(self, situation: str, act: Act, state: Any = None) -> list[tuple[Hypothesis, Any, str]]:
        """The hypotheses that apply to a situation and act, each with what it
        predicts and the situation that is: worked out once, and again only for
        hypotheses induced since."""
        cached = self._applies.get((situation, act))
        checked, found = cached if cached is not None else ({}, [])
        for scope in self.inducer.scopes(situation, act):
            held = self._scoped.get(scope, ())
            start = checked.get(scope, 0)
            if start < len(held):
                if state is None:
                    state = self._state(situation)
                for h in held[start:]:
                    said = self.inducer.predict(h.form, situation, state, act, self._situation_of)
                    if said is not None:
                        found.append((h, said, self.inducer.situation(said.state)))
                checked[scope] = len(held)
        self._applies[(situation, act)] = (checked, found)
        return found

    def _best(self, situation: str, act: Act, state: Any = None) -> tuple[Hypothesis, Any, str] | None:
        """Of the hypotheses that apply and are held, the one right at the highest
        rate (FIT_LAW; Plone, 2026-09-28: a rate, not a count — by a count, a
        hypothesis held longer outranked a truer one met later)."""
        held = [a for a in self._applicable(situation, act, state) if a[0].holds]
        return max(held, key=lambda a: (a[0].rate, a[0].supports)) if held else None

    def _state(self, situation: str) -> Any:
        """A state of a situation: one it stood in, or one it predicted."""
        raw = self._grid_of.get(situation)
        return self._raw[raw] if raw is not None else self._imagined[situation]

    def acknowledge(self, handle: object, datum_id: str) -> None:
        if isinstance(handle, Hypothesis):
            handle.datum_id = datum_id

    # ── the onlooker ──

    def think(self, context: Context) -> Thinking | None:
        """It learns from every return, so a mismatch sets it thinking no further.
        The onlooker's word does — it reaches the mind as a collision, and the mind
        commands again once it has thought:

          - "repeating" an act, or going "back-and-forth" between two: the acts it
            names are objected to — where the region stands now, and, for a
            back-and-forth, at the states the alternation ran through. Said again
            after it was answered, the objection reaches back over the run the
            onlooker points at, as far as the field's alertness says (½–1½ of
            it, within short-term perception);
          - but told once that it repeats an act whose every step reached a state
            it had not stood in — its own evidence that the repetition is getting
            somewhere — it keeps on, and says why (`kept_on`); told again, it
            objects (Plone, 2026-09-28);
          - "standing still": it will act; with nothing else to do, RESET;
          - anything else, or nothing: what it objected to on an earlier word is
            lifted.

        What it objected to, and why, is written; that thought is its answer."""
        if context.on != "onlooker":
            return None
        remark = context.remark or {}
        said = self._said(remark)
        lifted = self._lift(said)
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
            self._objected.setdefault(said, set())
            payload = {"on": "onlooker", "remark": remark, "here": self._here, "kept_on":
                       "each step of the run reached a state it had not stood in"}
            if lifted:
                payload["lifted"] = lifted
            return Thinking(writes=[Write(payload=payload, tags=dict(THOUGHT_TAGS), built_from=built)])
        pairs = self._objecting(remark, context, again)
        self._objected.setdefault(said, set()).update(pairs)
        answer = Answer()
        answers = self._answers.setdefault(said, [])
        answers.append(answer)
        payload = {"on": "onlooker", "remark": remark, "here": self._here, "again": again,
                   "objected": sorted([self._state_of.get(raw, raw), list(act)] for raw, act in pairs)}
        if lifted:
            payload["lifted"] = lifted
        return Thinking(writes=[Write(payload=payload, tags=dict(THOUGHT_TAGS), handle=answer, built_from=built)],
                        answer=tuple(("handle", a) for a in answers))

    def _named(self, remark: dict[str, Any]) -> list[Act]:
        """The acts an onlooker's word names, as the body takes them."""
        named = [remark.get("act")] if remark.get("act") else list(remark.get("acts") or [])
        ids = {name.upper(): a for a, name in self.organs.acts.items()}
        out: list[Act] = []
        for said in named:
            if not isinstance(said, dict) or str(said.get("act", "")).upper() not in ids:
                continue
            a = ids[str(said["act"]).upper()]
            out.append((a, said.get("x"), said.get("y")) if a in self.organs.placed else (a, None, None))
        return out

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
        steps = [s for s, _, _ in context.seen]
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
        steps = [s for s, _, _ in context.seen][-run:] if run else []
        if len(steps) < run or not steps:
            return False
        states = [self.inducer.situation(steps[0].before)] + [self.inducer.situation(s.after) for s in steps]
        return len(set(states)) == len(states)

    def objections(self) -> set[tuple[str, Act]]:
        """What it objects to now, as (where the region stands, act)."""
        return {(self._state_of[raw], act) for held in self._objected.values() for raw, act in held
                if raw in self._state_of}

    # ── where the region stands ──

    def _reached(self, report: dict[str, Any] | None) -> bool:
        """Whether a report shows the aim reached."""
        fields = ((self._aim or {}).get("reached_when") or {}).get("fields") or {}
        return bool(fields) and bool(report) and all(report.get(k) == v for k, v in fields.items())

    def _meet(self, state: Any) -> str:
        raw = self.inducer.identity(state)
        if raw not in self._raw:
            self._raw[raw] = state
            situation = self.inducer.situation(state)
            self._state_of[raw] = situation
            self._grid_of.setdefault(situation, raw)
        return raw

    def _situation_of(self, raw: str) -> str:
        return self._state_of[raw]

    def _reindex(self, built_from) -> list[Write]:
        """Read every state again, the inducer's perception having changed; where two
        experiences are now one situation and act, the hypothesis of the first
        counts the other against it if they disagree."""
        self._state_of = {raw: self.inducer.situation(g) for raw, g in self._raw.items()}
        self._grid_of = {}
        for raw, situation in self._state_of.items():
            self._grid_of.setdefault(situation, raw)
        self._edges, self._out = {}, {}
        self._scoped, self._applies, self._imagined = {}, {}, {}
        for h in self._hypotheses:
            self._scoped.setdefault(self.inducer.scope(h.form, self._situation_of), []).append(h)
        writes: list[Write] = []
        for edge in self._learned:
            key = (self._state_of[edge.source], edge.act)
            first = self._edges.get(key)
            if first is None:
                self._edges[key] = edge
                self._out.setdefault(key[0], {})[edge.act] = edge
            elif self._state_of[first.to] != self._state_of[edge.to] and (first, edge) not in self._against:
                self._against.add((first, edge))   # one experience, counted against it once
                writes += self._weigh(first.hypothesis, False, built_from)
        if self._here is not None and self._now_raw is not None:
            self._here = self._state_of[self._now_raw]
        return writes

    # ── expecting, and learning ──

    def expect(self, step: Step) -> Expectation:
        self.frame_calls += 1
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
            state = [row[:] for row in said.state]
            fields = self.inducer.fields(h.form)
            self._expected = state
            return Expectation(state=state, fields=dict(fields) if fields else None,
                               held=(("handle", h),), by_model=True)
        self._expected = [row[:] for row in step.before] if isinstance(step.before, list) else step.before
        return Expectation(state=self._expected, by_model=False)

    def observe(self, step: Step, unit: Any, fields: dict[str, Any] | None, units: tuple[Any, ...],
                on_report: bool, seen: list | None = None) -> list[Write]:
        if on_report:
            return self._learn_report(fields, units)
        self._seen_now = list(seen or [(step, unit, None)])
        return self._learn_step(step, unit)

    def _weigh(self, h: Hypothesis, borne_out: bool, built_from: tuple[object, ...]) -> list[Write]:
        """Count a return for or against a hypothesis; when whether it holds
        changes, a datum of its own says so."""
        before = h.holds
        if borne_out:
            h.supports += 1
        else:
            h.fails += 1
        return self._revise(h, built_from) if h.holds != before else []

    def _learn_step(self, step: Step, unit: Any) -> list[Write]:
        writes: list[Write] = []
        if self._new:
            writes += self._write(())  # a step whose report never came
        o = self.organs
        act: Act = self.inducer.learnable(step.act)
        source_raw = self._meet(step.before)
        source = self._state_of[source_raw]
        known = self._edges.get((source, act))
        applied = list(self._applicable(source, act, step.before))
        new = self.inducer.situation(step.after) not in self._grid_of
        to_raw = self._meet(step.after)
        self.holds_off_clock.append(int(self.inducer.situation(self._expected) == self._state_of[to_raw])
                                    if self._expected is not None else 0)
        kind = known.kind if known is not None else (self._kind_of.get((source, act)) or self.inducer.default_kind(act))
        to = self._state_of[to_raw]
        changed = to != source
        if act[0] != o.reset[0]:
            for counts in (self._kinds.setdefault(kind, [0, 0, 0]), self._actions.setdefault(act[0], [0, 0, 0])):
                counts[0] += 1
                counts[1] += int(new)
            if changed:
                self._kind_changes[kind] = self._kind_changes.get(kind, 0) + 1
                self._action_changes[act[0]] = self._action_changes.get(act[0], 0) + 1
        self._last_new = known is None
        if self._unseen_expected is not None:
            self.unseen[2] += int(self._unseen_expected == to)
            self._unseen_expected = None
        # Every hypothesis that applied is borne out, or not, by where the region stands.
        foreseen = any(h.holds and said == to for h, _, said in applied)
        for h, _, said in applied:
            writes += self._weigh(h, said == to, (unit,))
        if known is None:
            self._new = self._induce(source_raw, act, step, foreseen)
            edge = Edge(source_raw, act, to_raw, kind, changed, hypothesis=self._new[0])
            self._learned.append(edge)
            self._edges[(source, act)] = edge
            self._out.setdefault(source, {})[act] = edge
        else:
            edge = known
            edge.seen += 1
            if not foreseen:
                # What came, no hypothesis it holds foresaw: it asks what this suggests.
                self._new = self._induce(source_raw, act, step, foreseen)
        # What the inducer said in computing — a language model's answers — kept
        # whole, built from the step it was asked on and the words it was told.
        for said in self.inducer.said():
            writes.append(Write(payload={**said.payload, "cycle": self.frame_calls}, tags=dict(said.tags),
                                built_from=(unit, ("prior", "task"))))
        self._last = edge
        self._here, self._unit, self._now_raw = to, unit, to_raw
        self._visits[to] = self._visits.get(to, 0) + 1
        if act[0] == o.reset[0]:
            self._learned_since_reset = False
        elif known is None:
            self._learned_since_reset = True
        perceived = self.inducer.perceive(step, kind)
        if perceived is not None:
            writes += self._reindex((unit,))
            writes.append(Write(payload={**perceived.payload, "cycle": self.frame_calls},
                                tags=dict(perceived.tags), built_from=(unit,)))
        return writes

    def _learn_report(self, report: dict[str, Any] | None, units: tuple[Any, ...]) -> list[Write]:
        edge = self._last
        if edge is None or report is None:
            return []
        writes: list[Write] = []
        said = {k: report.get(k) for k in self.organs.report_fields}
        if edge.status is None:
            edge.status = said
            if hasattr(edge.hypothesis.form, "status"):
                edge.hypothesis.form.status = said
        elif self._reached(edge.status) != self._reached(said):
            # The aim from one and not from the other: the hypothesis did not bear
            # out. The region ending one time and not another is the clock's doing
            # (a budget of acts), not the act's.
            writes += self._weigh(edge.hypothesis, False, units)
        if said.get(self.organs.state_field) in self.organs.ended:
            edge.ended += 1
        if self._reached(said) and edge.act[0] != self.organs.reset[0]:
            self._kinds.setdefault(edge.kind, [0, 0, 0])[2] += 1
            self._actions.setdefault(edge.act[0], [0, 0, 0])[2] += 1
        if self._new:
            writes += self._write(units)
        return writes

    def _describe(self, h: Hypothesis) -> dict[str, Any]:
        return {"inducer": self.inducer.kind, **self.inducer.describe(h.form, self._situation_of),
                "holds": h.holds, "supports": h.supports, "fails": h.fails}

    def _write(self, built_from: tuple[object, ...]) -> list[Write]:
        """The hypotheses the last experience suggested, each a datum built from it."""
        writes = []
        for h in self._new:
            h.written = True
            self.version += 1
            writes.append(Write(payload=self._describe(h), tags=dict(HYPOTHESIS_TAGS), handle=h,
                                built_from=built_from))
        self._new = []
        return writes

    def _revise(self, h: Hypothesis, built_from: tuple[object, ...]) -> list[Write]:
        """Whether a hypothesis holds has changed: said in a datum of its own, built
        from the one before — added, not revised in place."""
        if not h.written:
            return []
        return [Write(payload=self._describe(h), tags=dict(HYPOTHESIS_TAGS),
                      built_from=(*built_from, ("handle", h)))]

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
        level, new = self._odds_of(counts)
        tried = counts[0]
        more = math.sqrt(2 * math.log(total + 1) / (tried + 1))
        change = (changes + 1) / (tried + 2)
        if self.curiosity == "changed":
            return level, change + more
        if self.curiosity == "new-then-changed":
            return level, new + more, change
        if self.curiosity == "new-plus-changed":
            return level, new + change + more
        return level, new + more

    def _change_odds(self, kind: tuple) -> float:
        """The odds it gives a kind of act of a change."""
        return (self._kind_changes.get(kind, 0) + 1) / (self._kinds.get(kind, (0, 0, 0))[0] + 2)

    def _action_curiosity(self, act: int) -> tuple[float, ...]:
        """How much it wants an act at all, over every kind of it."""
        total = sum(a[0] for a in self._actions.values())
        return self._wanted(self._actions.get(act, (0, 0, 0)), self._action_changes.get(act, 0), total)

    def _curiosity(self, kind: tuple) -> tuple[float, ...]:
        """How much it wants a kind of act, by its law of curiosity."""
        total = sum(k[0] for k in self._kinds.values())
        return self._wanted(self._kinds.get(kind, (0, 0, 0)), self._kind_changes.get(kind, 0), total)

    def _candidates(self, here: str, offers: tuple[int, ...]) -> list[tuple[Act, tuple]]:
        return self.inducer.candidates(here, self._state(here), offers)

    def _open_here(self, here: str, offers: tuple[int, ...],
                   objected: set[tuple[str, Act]] | None = None) -> list[tuple[Act, tuple]]:
        """The acts not yet taken from here, and not objected to."""
        objected = self.objections() if objected is None else objected
        return [(act, kind) for act, kind in self._candidates(here, offers)
                if (here, act) not in self._edges and (here, act) not in objected]

    def _foreseen(self, here: str, act: Act) -> bool:
        """Whether its hypotheses say an act leads where it has stood. Such an act
        is put behind the others, never out of reach: a hypothesis that kept an
        act from being taken could never be refuted by it."""
        if not self.inducer.general:
            return False
        best = self._best(here, act)
        return best is not None and best[2] in self._grid_of

    def _ways(self, node: str, offers: tuple[int, ...]) -> list[tuple[Act, str, Hypothesis, Any]]:
        """From a situation, where each act leads, by the hypothesis it holds best
        there: the acts taken from it first, in the order taken — never one that
        ended the region every time — then, for an inducer whose hypotheses reach
        past where they were met, any other its hypotheses predict."""
        ways = []
        taken = self._out.get(node, {})
        for act, edge in taken.items():
            if act[0] == self.organs.reset[0] or edge.ended >= edge.seen:
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

    def _path(self, start: str, goal: Callable[[str], bool], offers: tuple[int, ...],
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
            if past[node] >= MAX_IMAGINED_STEPS:
                continue
            for act, to, h, said in self._ways(node, offers):
                if to in prev or (node == start and (start, act) in avoid):
                    continue
                if to not in self._grid_of:
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
        chosen = max({a for (a, _, _), _ in pool}, key=lambda a: (self._action_curiosity(a), -a))
        best = max((ak for ak in pool if ak[0][0] == chosen), key=lambda ak: self._curiosity(ak[1]))
        self._kind_of[(here, best[0])] = best[1]
        self._chosen_kind = best[1]
        if self.curiosity == "changed":
            return best[0], self._change_odds(best[1])
        return best[0], self._odds(best[1])[1]

    def _way(self, here: str, goal: Callable[[str], bool], offers: tuple[int, ...],
             objected: set[tuple[str, Act]]) -> tuple[list[tuple[Act, Hypothesis]] | None, bool]:
        """A way to where `goal` holds whose first act is not objected to; only if
        there is none, one that is (and says so)."""
        path = self._path(here, goal, offers, avoid=objected)
        if path:
            return path, False
        path = self._path(here, goal, offers)
        return path, bool(path)

    def propose(self, context: Context) -> tuple[Proposal, list[Write]]:
        here = self._here
        if here is None:
            return Proposal(None, why="nowhere yet"), []
        offers = context.offers
        through: list[Hypothesis] = []
        odds: float | None = None
        act: Act | None = None
        said = self._said(context.remark or {})
        lifted = self._lift(said)
        objected = self.objections()
        if context.ended is not None:
            act, why = self.organs.reset, f"the region has ended ({context.ended})"
        else:
            # Toward the aim it takes no objection.
            gained = {self._state_of[e.source] for e in self._edges.values()
                      if e.hypothesis.holds and self._reached(e.status)}
            aim_here = [e for e in self._out.get(here, {}).values() if e.hypothesis.holds and self._reached(e.status)]
            path = None if aim_here or not gained else self._path(here, lambda n: n in gained, offers)
            opened = self._open_here(here, offers, objected)
            fresh = [ak for ak in opened if not self._foreseen(here, ak[0])]
            if aim_here:
                act, why, through = aim_here[0].act, "an act that reached the aim before", [aim_here[0].hypothesis]
            elif path:
                act, why, through = path[0][0], f"toward the aim reached before ({len(path)} steps)", [h for _, h in path]
            elif fresh:
                act, odds = self._curious(here, fresh)
                why = "not yet taken from here"
            else:
                # Where it has not tried something it cannot foresee — a situation
                # it has not stood in is itself such a place; then what it can
                # foresee, here; then, anywhere.
                def fresh_at(n: str) -> bool:
                    return n not in self._grid_of or any(not self._foreseen(n, a)
                                                         for a, _ in self._open_here(n, offers, objected))

                def open_at(n: str) -> bool:
                    return n in self._grid_of and bool(self._open_here(n, offers, objected))

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
                elif self._learned_since_reset:
                    act, why = self.organs.reset, "nothing left to try from anywhere it can reach"
                else:
                    known = [e for e in self._out.get(here, {}).values()
                             if e.act[0] in offers and e.act[0] != self.organs.reset[0]]
                    free = [e for e in known if (here, e.act) not in objected]
                    if free:
                        least = min(free, key=lambda e: (self._visits.get(self._state_of[e.to], 0), e.seen,
                                                         e.act[0], e.act[1] or 0, e.act[2] or 0))
                        act, why, through = least.act, "all known; toward the state visited least", [least.hypothesis]
                    elif known:
                        act, why = self.organs.reset, "every act known here was objected to"
                    elif said is not None and said[0] == "standing still":
                        act, why = self.organs.reset, "standing still, and nothing else it can do here"
                    else:
                        why = "nothing it can do here"
        self.thoughts.append(Choice(self.frame_calls, act, why, odds))
        choice: dict[str, Any] = {"cycle": self.frame_calls, "here": here, "chose": list(act) if act else None,
                                  "why": why, "aim": (self._aim or {}).get("aim")}
        if odds is not None:
            if self.curiosity == "changed":
                choice["odds_of_change"] = round(odds, 3)
            else:
                choice["odds_of_new"] = round(odds, 3)
                if self.curiosity != "new":
                    choice["odds_of_change"] = round(self._change_odds(self._chosen_kind), 3)
        built: list[object] = [self._unit] if self._unit is not None else []
        if lifted:
            choice["lifted"] = lifted
        if context.on == "command again" and self._last_choice is not None \
                and self._last_choice.get("cycle") == self.frame_calls:
            choice["supersedes"] = {"chose": self._last_choice.get("chose"), "why": self._last_choice.get("why")}
        self._last_choice = choice
        if context.remark and context.remark.get("remark"):
            choice["onlooker"] = context.remark
            if context.remark_unit is not None:
                built.append(context.remark_unit)   # what it quotes, it was built from
        built += [("handle", h) for h in through]
        built.append(("prior", "task"))
        return Proposal(act, why=why), [Write(payload=choice, tags=dict(CHOICE_TAGS), built_from=tuple(built))]


__all__ = ["CHOICE_TAGS", "CURIOSITY", "FIT_LAW", "HYPOTHESIS_TAGS", "MAX_PATH_NODES", "THOUGHT_TAGS",
           "Answer", "Choice", "Edge", "Hypothesis", "Learning"]
