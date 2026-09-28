"""The mind's learning — neutral about its region and about the model it learns with.

Plone (2026-09-28): learning is developing experience into what serves the agent,
not storing it; and it is the mind's, not the model's — another task, another
model, and learning is not defined again. The mind holds the loop; a model — an
inducer (`models/exact.py`) — is its computing: what a state is to it, what can
be done in one, what an experience suggests, what a hypothesis predicts.

THE LOOP, one step at a time:

- **Experience.** Each step — from where the region stood, an act, where it
  stands and what it reported of itself — is kept, accrued (INV-5), with how
  often it was met and how often the region ended on it.
- **Hypotheses are data.** What an experience suggests, the inducer says; the
  mind holds it as a hypothesis and writes it (`kind: hypothesis`), built from
  the step and the report it came in.
- **Expecting.** For a step, the hypotheses that apply to where the region stood
  and the act; of those it holds, the one that fits the store best is the
  expectation, and is what the expectation is (`held_by`) — so when the region
  returns otherwise, it is scarred (v0.3.5).
- **Weighing.** Each return that a hypothesis predicted counts for it, each it
  did not counts against: a hypothesis is held while it has been right more
  often than wrong, and the one right most often is preferred (DECIDE@IMPL
  FIT_LAW; tag H: fit against the store, never a scored standard). When that
  changes, a new datum says so, built from the one before: nothing is revised
  in place.
- **Choosing.** Toward the aim it has reached before; else what it knows least
  (curiosity, below); else the shortest way it knows to where something is left
  to try; else RESET, or the known act toward the situation least visited.
- **The onlooker's word** strikes the mind as a collision; what it objects to is
  put behind every other act at every point of choice — never over a known way
  to the aim — and lifted when the onlooker says something else. A repetition
  whose every step went somewhere new is kept on, told once; told again, it is
  objected to.

CURIOSITY. Per kind of act, and per act over every kind of it: how often it was
tried, how often it changed where the region stands, how often the aim came of
it. What most often brought the aim first; then the odds of a change (Laplace),
raised by how little it has been tried (UCB1).

What it holds but does not write — its counts, how often an experience was met
and ended the region, the situations it visited — follows from the observations
in the store only when those are replayed through it, in order.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Final

from dil.loop.field import ALERTNESS, axis, rising, shifted_count

from .models.base import Context, Expectation, Proposal, Thinking, Write
from .organs import Act, Organs, Step

HYPOTHESIS_TAGS: Final = {"domain": "mind", "kind": "hypothesis", "object": "frame", "source": "mind"}
CHOICE_TAGS: Final = {"domain": "mind", "kind": "choice", "source": "mind"}
THOUGHT_TAGS: Final = {"domain": "mind", "kind": "thought", "source": "mind"}

# How far it searches the situations it knows for a way. DECLARED: a bound on work.
MAX_PATH_NODES: Final = 20_000
# DECIDE@IMPL (tag H) — how a hypothesis is weighed against the store.
FIT_LAW: Final = ("held while right more often than wrong (supports > fails); of those that apply, "
                  "the one right most often is the expectation")


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
    """The mind's learning loop, computing with an inducer. It stands in the mind's
    seat for a model: the mind's seams (`mind.py`) ask it what to expect, show it
    what came back, ask it what to do."""

    def __init__(self, inducer: Any, organs: Organs, priors: dict[str, dict[str, str]]) -> None:
        self.inducer = inducer
        self.organs = organs
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
        self._kinds: dict[tuple, list[int]] = {}   # kind -> [tried, changed, aim]
        self._actions: dict[int, list[int]] = {}   # act -> [tried, changed, aim], every kind of it
        self._kind_of: dict[tuple[str, Act], tuple] = {}
        self._here: str | None = None
        self._unit: Any = None
        self._last: Edge | None = None
        self._last_new = False
        self._expected: Any = None
        self._visits: dict[str, int] = {}
        self._against: set[tuple[Edge, Edge]] = set()   # experiences read as one, counted against
        self._learned_since_reset = True
        self.frame_calls = 0

    # ── what it reads ──

    def cues(self) -> dict[str, dict[str, str]]:
        return dict(self._cues)

    def required(self) -> frozenset[str]:
        return frozenset()

    def receive_prior(self, name: str, payload: Any, datum_id: str) -> None:
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
        writes: list[Write] = []
        for edge in self._learned:
            key = (self._state_of[edge.source], edge.act)
            first = self._edges.get(key)
            if first is None:
                self._edges[key] = edge
                self._out.setdefault(key[0], {})[edge.act] = edge
            elif self._state_of[first.to] != self._state_of[edge.to] and (first, edge) not in self._against:
                self._against.add((first, edge))   # one experience, counted against it once
                writes += self._weigh(first, False, built_from)
        if self._here is not None and self._now_raw is not None:
            self._here = self._state_of[self._now_raw]
        return writes

    # ── expecting, and learning ──

    def expect(self, step: Step) -> Expectation:
        self.frame_calls += 1
        source = self.inducer.situation(step.before)
        act = self.inducer.learnable(step.act)
        known = self._edges.get((source, act))
        if known is not None and known.hypothesis.holds:
            said = self.inducer.predict(known.hypothesis.form, source, act, self._situation_of)
            if said is not None:
                self._expected = said.state
                return Expectation(state=said.state, fields=said.fields,
                                   held=(("handle", known.hypothesis),), by_model=True)
        self._expected = [row[:] for row in step.before] if isinstance(step.before, list) else step.before
        return Expectation(state=self._expected, by_model=False)

    def observe(self, step: Step, unit: Any, fields: dict[str, Any] | None, units: tuple[Any, ...],
                on_report: bool) -> list[Write]:
        return self._learn_report(fields, units) if on_report else self._learn_step(step, unit)

    def _weigh(self, edge: Edge, borne_out: bool, built_from: tuple[object, ...]) -> list[Write]:
        """Count a return for or against an experience's hypothesis; when whether it
        holds changes, a datum of its own says so."""
        h = edge.hypothesis
        before = h.holds
        if borne_out:
            h.supports += 1
        else:
            h.fails += 1
        return self._revise(edge, built_from) if h.holds != before else []

    def _learn_step(self, step: Step, unit: Any) -> list[Write]:
        writes: list[Write] = []
        if self._last is not None and self._last_new and not self._last.hypothesis.written:
            writes += self._write(self._last, ())  # a step whose report never came
        o = self.organs
        act: Act = self.inducer.learnable(step.act)
        source_raw = self._meet(step.before)
        source = self._state_of[source_raw]
        known = self._edges.get((source, act))
        to_raw = self._meet(step.after)
        self.holds_off_clock.append(int(self.inducer.situation(self._expected) == self._state_of[to_raw])
                                    if self._expected is not None else 0)
        kind = known.kind if known is not None else (self._kind_of.get((source, act)) or self.inducer.default_kind(act))
        to = self._state_of[to_raw]
        changed = to != source
        if act[0] != o.reset[0]:
            for counts in (self._kinds.setdefault(kind, [0, 0, 0]), self._actions.setdefault(act[0], [0, 0, 0])):
                counts[0] += 1
                counts[1] += int(changed)
        self._last_new = known is None
        if known is None:
            forms = self.inducer.induce(source_raw, act, step.after)
            edge = Edge(source_raw, act, to_raw, kind, changed, hypothesis=Hypothesis(forms[0]))
            self._learned.append(edge)
            self._edges[(source, act)] = edge
            self._out.setdefault(source, {})[act] = edge
        else:
            edge = known
            edge.seen += 1
            # The same act from the same situation gave the same, or another.
            writes += self._weigh(edge, self._state_of[edge.to] == to, (unit,))
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
            writes += self._weigh(edge, False, units)
        if said.get(self.organs.state_field) in self.organs.ended:
            edge.ended += 1
        if self._reached(said) and edge.act[0] != self.organs.reset[0]:
            self._kinds.setdefault(edge.kind, [0, 0, 0])[2] += 1
            self._actions.setdefault(edge.act[0], [0, 0, 0])[2] += 1
        if self._last_new and not edge.hypothesis.written:
            writes += self._write(edge, units)
        return writes

    def _describe(self, edge: Edge) -> dict[str, Any]:
        h = edge.hypothesis
        return {"inducer": self.inducer.kind, **self.inducer.describe(h.form, self._situation_of),
                "changed": edge.changed, "holds": h.holds, "supports": h.supports, "fails": h.fails}

    def _write(self, edge: Edge, built_from: tuple[object, ...]) -> list[Write]:
        edge.hypothesis.written = True
        self.version += 1
        return [Write(payload=self._describe(edge), tags=dict(HYPOTHESIS_TAGS), handle=edge.hypothesis,
                      built_from=built_from)]

    def _revise(self, edge: Edge, built_from: tuple[object, ...]) -> list[Write]:
        """Whether a hypothesis holds has changed: said in a datum of its own, built
        from the one before — added, not revised in place."""
        if not edge.hypothesis.written:
            return []
        return [Write(payload=self._describe(edge), tags=dict(HYPOTHESIS_TAGS),
                      built_from=(*built_from, ("handle", edge.hypothesis)))]

    # ── what to do next ──

    @staticmethod
    def _odds_of(counts) -> tuple[float, float]:
        tried, changed, aim = counts
        return (aim + 1) / (tried + 2) if aim else 0.0, (changed + 1) / (tried + 2)

    def _odds(self, kind: tuple) -> tuple[float, float]:
        """The odds it gives a kind of act: of the aim, and of the state changing."""
        return self._odds_of(self._kinds.get(kind, (0, 0, 0)))

    def _action_curiosity(self, act: int) -> tuple[float, float]:
        """How much it wants an act at all, over every kind of it."""
        level, change = self._odds_of(self._actions.get(act, (0, 0, 0)))
        tried = self._actions.get(act, (0, 0, 0))[0]
        total = sum(a[0] for a in self._actions.values())
        return level, change + math.sqrt(2 * math.log(total + 1) / (tried + 1))

    def _curiosity(self, kind: tuple) -> tuple[float, float]:
        """How much it wants a kind of act: the odds of the aim first; then the
        odds of a change, raised by how little it knows the kind (UCB1)."""
        level, change = self._odds(kind)
        tried = self._kinds.get(kind, (0, 0, 0))[0]
        total = sum(k[0] for k in self._kinds.values())
        return level, change + math.sqrt(2 * math.log(total + 1) / (tried + 1))

    def _candidates(self, here: str, offers: tuple[int, ...]) -> list[tuple[Act, tuple]]:
        return self.inducer.candidates(here, self._raw[self._grid_of[here]], offers)

    def _open_here(self, here: str, offers: tuple[int, ...],
                   objected: set[tuple[str, Act]] | None = None) -> list[tuple[Act, tuple]]:
        objected = self.objections() if objected is None else objected
        return [(act, kind) for act, kind in self._candidates(here, offers)
                if (here, act) not in self._edges and (here, act) not in objected]

    def _path(self, start: str, goal: Callable[[str], bool],
              avoid: set[tuple[str, Act]] | frozenset = frozenset()) -> list[Edge] | None:
        """The shortest way it knows from `start` to a situation `goal` holds of, by
        experiences whose hypothesis holds and that did not end the region every
        time, and whose first act is none of `avoid` there; None if none."""
        prev: dict[str, Edge | None] = {start: None}
        queue = deque([start])
        while queue and len(prev) < MAX_PATH_NODES:
            node = queue.popleft()
            if node != start and goal(node):
                path = []
                while prev[node] is not None:
                    edge = prev[node]
                    path.append(edge)
                    node = self._state_of[edge.source]
                return path[::-1]
            for edge in self._out.get(node, {}).values():
                to = self._state_of[edge.to]
                if edge.hypothesis.holds and edge.ended < edge.seen and edge.act[0] != self.organs.reset[0] \
                        and to not in prev and not (node == start and (start, edge.act) in avoid):
                    prev[to] = edge
                    queue.append(to)
        return None

    def propose(self, context: Context) -> tuple[Proposal, list[Write]]:
        here = self._here
        if here is None:
            return Proposal(None, why="nowhere yet"), []
        offers = context.offers
        through: list[Edge] = []
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
            path = None if aim_here or not gained else self._path(here, lambda n: n in gained)
            opened = self._open_here(here, offers, objected)
            if aim_here:
                act, why, through = aim_here[0].act, "an act that reached the aim before", [aim_here[0]]
            elif path:
                act, why, through = path[0].act, f"toward the aim reached before ({len(path)} steps)", path
            elif opened:
                chosen = max({a for (a, _, _), _ in opened}, key=lambda a: (self._action_curiosity(a), -a))
                best = max((ak for ak in opened if ak[0][0] == chosen), key=lambda ak: self._curiosity(ak[1]))
                act, odds = best[0], self._odds(best[1])[1]
                self._kind_of[(here, act)] = best[1]
                why = "not yet taken from here"
            else:
                def open_at(n: str) -> bool:
                    return n in self._grid_of and bool(self._open_here(n, offers, objected))

                path = self._path(here, open_at, avoid=objected)
                over = False
                if not path:
                    path = self._path(here, open_at)
                    over = bool(path)
                if path:
                    act, through = path[0].act, path
                    why = f"toward a state with an act not yet taken ({len(path)} steps)" + \
                        ("; objected to, and no other way" if over else "")
                elif self._learned_since_reset:
                    act, why = self.organs.reset, "nothing left to try from anywhere it can reach"
                else:
                    known = [e for e in self._out.get(here, {}).values()
                             if e.act[0] in offers and e.act[0] != self.organs.reset[0]]
                    free = [e for e in known if (here, e.act) not in objected]
                    if free:
                        least = min(free, key=lambda e: (self._visits.get(self._state_of[e.to], 0), e.seen,
                                                         e.act[0], e.act[1] or 0, e.act[2] or 0))
                        act, why, through = least.act, "all known; toward the state visited least", [least]
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
            choice["odds_of_change"] = round(odds, 3)
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
        built += [("handle", e.hypothesis) for e in through]
        built.append(("prior", "task"))
        return Proposal(act, why=why), [Write(payload=choice, tags=dict(CHOICE_TAGS), built_from=tuple(built))]


__all__ = ["CHOICE_TAGS", "FIT_LAW", "HYPOTHESIS_TAGS", "MAX_PATH_NODES", "THOUGHT_TAGS",
           "Answer", "Choice", "Edge", "Hypothesis", "Learning"]
