"""A model that learns from nothing — the one mind's computing, with no trained weights.

Where the language model brings weights trained before the loop ever ran, this
one brings none. Everything it knows accrues in the loop, one return at a time
(INV-5), and the mind writes it as it is learned, each datum saying what it was
built from. Its thinking is an algorithm; its curiosity, want and expectation
are computed in it — in the mind's own computing, not for it (Plone:
"cấm tính hộ, không phải cấm code"). It reads no region from code: what the eye
delivers and what the body can do is the host's declaration (`organs`), and the
aim is what the task it was told states will come back when it is reached.

WHAT IT LEARNS. What an act does where the region stands. A state is what the
eye delivers (the organs say: a grid of cells); an act is what the body takes.
Each step is a transition it learns — from this state, this act, came that state,
and the region reported this of itself — written (`kind: transition`) built from
the step and the report it came in. It keeps, per kind of act, how often it was
tried, how often it changed where the region stands, and how often the aim came
of it: a kind of act is an act, or for an act that takes a place the colour and
size of the thing it was put on. Those counts are held, not written, as are how
often a transition was taken and ended the region, and the states it visited:
they follow from the observations in the store only when those are replayed
through it, in order.

HOW IT READS A GRID — its own perception, declared, not measured, naming no game:

- **Things.** A region of one colour joined side to side, at its cell nearest
  its middle — at most MAX_CLICK_TARGETS, smallest first, none larger than
  MAX_THING_SHARE of the grid (that large is taken for the ground). They are
  where an act that takes a place may be put.
- **The clock.** A row that changed in every one of the last CLOCK_WINDOW steps,
  under CLOCK_KINDS kinds of act or more, by no more than CLOCK_CELLS cells each
  time, is a clock the region keeps whatever is done — a bar that counts steps
  (ls20's rows 61-62, vc33's row 0; LOG.md) — not where it stands. Two grids are
  one state when they agree off the clock. The clock only grows; when it does it
  is written (`kind: clock`) and every grid met is read again under it. The clock
  is not predicted: an expectation carries it as it was.

WHAT IT EXPECTS. For an act taken from this state before, what came then: the
state, and the report. That expectation is the transition's datum (`held_by`).
Where the region keeps a clock, the grid never comes back as it was — the clock
is not predicted — so almost every such expectation fails on the clock's rows
alone, and the datum is scarred for that: in `[event]` a scar of this model is,
almost always, the clock, not a refutation (Kaggle, 300 cycles: ls20 held 4 of
299 whole, 125 off the clock). Only when the same act from the same state gives
another state off the clock is the transition refuted: said in a new datum. For
an act not taken from here, it makes no expectation of its own: the standing one
holds, held by no datum of its.

WHAT IT DOES NEXT, in this order:

  1. toward the aim: if a path it knows leads to an act that brought the aim
     before, the next step of that path;
  2. curiosity: an act not yet taken from here, chosen in two steps — first the
     act, over every kind of it, then (for an act that takes a place) where to
     put it. At each step, first what most often brought the aim; then what has
     the highest odds of changing where the region stands (one untried and one
     tried in its favour: Laplace), raised by how little it has been tried
     (UCB1). What it knows least, it is most curious about; what changes nothing
     falls behind as it is tried — the whole act, when no kind of it did anything;
  3. the next step of the shortest path it knows to a state with an act not yet
     taken — never through an act that no longer holds, or that ended the region
     every time it was taken;
  4. the act that is always open (RESET), when nothing is left to try from
     anywhere it can reach and it learned something since it last took it;
     otherwise the known act toward the state it has visited least.

THE ONLOOKER. It does not think on a mismatch — it learns from every return —
but it thinks on the onlooker's word, which strikes the mind as a collision: the
acts it names are objected to (see `think`), put behind every other at every
point of choice, never over a known way to the aim, and lifted when the onlooker
says something else; the thought is written (`kind: thought`), and is its answer.

When the region has ended, the act that is always open. Each choice is written
(`kind: choice`): what it chose, why, the odds it gave a change, and what it was
built from — the step it stands on, the transitions its path runs through, the
task. It does not think on a mismatch: it learns from every return instead.
"""

from __future__ import annotations

import hashlib
import math
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Final

from dil.loop.field import ALERTNESS, axis, rising, shifted_count

from ..organs import Act, Organs, Step
from .base import Context, Expectation, Proposal, Thinking, Write

Grid = list[list[int]]

LEARNED_TAGS: Final = {"domain": "mind", "kind": "transition", "object": "frame", "source": "mind"}
CHOICE_TAGS: Final = {"domain": "mind", "kind": "choice", "source": "mind"}
CLOCK_TAGS: Final = {"domain": "mind", "kind": "clock", "object": "frame", "source": "mind"}
THOUGHT_TAGS: Final = {"domain": "mind", "kind": "thought", "source": "mind"}

# What an act that takes a place may be put on. DECLARED, not measured.
MAX_CLICK_TARGETS: Final = 64
MAX_THING_SHARE: Final = 0.5
# How far it searches the states it knows for a path. DECLARED: a bound on work.
MAX_PATH_NODES: Final = 20_000
# The clock. DECLARED, not measured: on ls20 a looser rule took the rows a moving
# piece crossed for the clock (LOG.md).
CLOCK_WINDOW: Final = 6
CLOCK_KINDS: Final = 3
CLOCK_CELLS: Final = 2
BIG_CHANGE: Final = 64 * 64 // 4


def grid_key(grid: Grid, clock: frozenset[int] = frozenset()) -> str:
    """A grid's identity: two grids are one state when every cell off the clock's
    rows is the same."""
    cells = bytes(0 if r in clock else v & 0xFF for r, row in enumerate(grid) for v in row)
    return hashlib.blake2b(cells + bytes([len(grid)]), digest_size=12).hexdigest()


def things(grid: Grid) -> list[tuple[int, int, int, int]]:
    """Each thing on the grid: (colour, size, x, y), a region of one colour joined
    side to side, at its cell nearest its middle; smallest first, the ground left
    out."""
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    seen = [[False] * cols for _ in range(rows)]
    out = []
    for r0 in range(rows):
        for c0 in range(cols):
            if seen[r0][c0]:
                continue
            colour = grid[r0][c0]
            cells = []
            stack = [(r0, c0)]
            seen[r0][c0] = True
            while stack:
                r, c = stack.pop()
                cells.append((r, c))
                for rr, cc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                    if 0 <= rr < rows and 0 <= cc < cols and not seen[rr][cc] and grid[rr][cc] == colour:
                        seen[rr][cc] = True
                        stack.append((rr, cc))
            if len(cells) > MAX_THING_SHARE * rows * cols:
                continue
            mr = sum(r for r, _ in cells) / len(cells)
            mc = sum(c for _, c in cells) / len(cells)
            r, c = min(cells, key=lambda rc: ((rc[0] - mr) ** 2 + (rc[1] - mc) ** 2, rc))
            out.append((colour, len(cells), c, r))
    out.sort(key=lambda t: (t[1], t[3], t[2]))
    return out[:MAX_CLICK_TARGETS]


@dataclass(eq=False)
class Edge:
    """One transition it learned: from a state, an act, came a state and a report.
    `source` and `to` are the grids as they came (their own keys); where the
    region stood is read from them under the clock it holds. Its own handle."""

    source: str
    act: Act
    to: str
    kind: tuple
    changed: bool
    status: dict[str, Any] | None = None
    ended: int = 0               # how many times the region ended on it
    holds: bool = True           # False once the same act from the same state gave two things
    datum_id: str | None = None
    seen: int = 1
    written: bool = False

    def payload(self, state: Callable[[str], str]) -> dict[str, Any]:
        return {"from": state(self.source), "act": list(self.act), "to": state(self.to) if self.holds else None,
                "changed": self.changed, "status": self.status, "holds": self.holds}


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


class LearningModel:
    """The one mind's computing, learning: it expects from what it learned, is
    curious about what it has not, and proposes the body's next act."""

    def __init__(self, organs: Organs, priors: dict[str, dict[str, str]]) -> None:
        self.organs = organs
        self._now_raw: str | None = None                       # the latest grid's own key
        self._last_choice: dict[str, Any] | None = None        # the choice it wrote last
        # What the onlooker's word made it object to, by what the word was: (the
        # grid as it came, act). Held while the onlooker says it; lifted when it
        # says something else (Plone, 2026-09-27); read under the clock it holds.
        self._objected: dict[tuple, set[tuple[str, Act]]] = {}
        # Its answers to each word, while the word stands: the mind's expectation
        # that the onlooker stops is all of them — the first is the one whose datum
        # is known by the time the word comes back again.
        self._answers: dict[tuple, list[Answer]] = {}
        self._cues = dict(priors)        # it reads the task, for its aim
        self.thoughts: list[Choice] = []
        self.holds_off_clock: list[int] = []
        self.version = 0                  # transitions written
        self.code = None                  # it writes no program
        self._aim: dict[str, Any] | None = None
        self._aim_new = False
        self.clock: frozenset[int] = frozenset()
        self._recent: deque = deque(maxlen=CLOCK_WINDOW)   # (kind, rows changed) per step
        self._raw: dict[str, Grid] = {}                     # a grid, by its own key
        self._state_of: dict[str, str] = {}                 # a grid's key -> where the region stood
        self._grid_of: dict[str, str] = {}                  # a state -> a grid of it
        self._things: dict[str, list[tuple[int, int, int, int]]] = {}
        self._learned: list[Edge] = []                      # every transition, in the order learned
        self._edges: dict[tuple[str, Act], Edge] = {}
        self._out: dict[str, dict[Act, Edge]] = {}
        self._kinds: dict[tuple, list[int]] = {}   # kind -> [tried, changed, aim]
        self._actions: dict[int, list[int]] = {}   # act -> [tried, changed, aim], every kind of it
        self._kind_of: dict[tuple[str, Act], tuple] = {}
        self._here: str | None = None
        self._unit: Any = None
        self._last: Edge | None = None
        self._last_new = False
        self._last_act: Act | None = None
        self._expected: Grid | None = None
        self._visits: dict[str, int] = {}
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
        if isinstance(handle, Edge):
            handle.datum_id = datum_id

    def think(self, context: Context) -> Thinking | None:
        """It learns from every return, so a mismatch sets it thinking no further.
        The onlooker's word does (Plone, 2026-09-27) — it reaches the mind as a
        collision, and the mind commands again once it has thought:

          - "repeating" an act, or going "back-and-forth" between two: the acts it
            names are objected to — where the region stands now, and, for a
            back-and-forth, at the states the alternation ran through. Said again
            after it was answered, the objection reaches back over the run the
            onlooker points at, as far as the field's alertness says (½–1½ of
            it, within short-term perception);
          - but told once that it repeats an act whose every step reached a state
            it had not stood in — its own evidence that the repetition is getting
            somewhere — it keeps on, and says why (`kept_on`); told again, it
            objects (Plone, 2026-09-28: on ls20 the onlooker's word turned such
            runs 16 times and cost 47 actions to level 1);
          - "standing still": it will act; with nothing else to do, RESET;
          - anything else, or nothing: what it objected to on an earlier word is
            lifted.

        An objection puts an act behind every other where it holds; it is taken
        only when nothing else can be, and never over a way it knows to the aim
        (H5 (i): the onlooker does not claim to be right). What it objected to,
        and why, is written; that thought is its answer."""
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
            # Told once that it repeats an act whose every step so far reached a
            # state it had not stood in: its own evidence says the repetition is
            # getting somewhere, and it keeps on — the onlooker does not claim to
            # be right. It answers so, expecting to hear it again if it is wrong:
            # said again, it objects (a word repeated raises the mind's attention).
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

    # ── what the onlooker's word is, and what it objects to ──

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
        """What the onlooker says, as one word: its stance and the acts it names —
        not how long it has said it (a word said again is the same word)."""
        stance = remark.get("remark")
        if not stance:
            return None
        return (stance, *sorted(self._named(remark)))

    def _lift(self, said: tuple | None) -> list[list[Any]]:
        """Lift what it objected to on any word the onlooker no longer says (H7 (ii))."""
        lifted = [list(k) for k in self._objected if k != said]
        self._objected = {k: v for k, v in self._objected.items() if k == said}
        self._answers = {k: v for k, v in self._answers.items() if k == said}
        return lifted

    def _objecting(self, remark: dict[str, Any], context: Context, again: bool) -> set[tuple[str, Act]]:
        """The (grid as it came, act) pairs a word objects to: the named acts where
        the region stands now, for a repetition; the steps of the alternation, for
        a back-and-forth; and, said again, the steps of the run it points at, as
        far as alertness reaches."""
        named = set(self._named(remark))
        pairs: set[tuple[str, Act]] = set()
        if self._now_raw is not None and remark.get("remark") == "repeating":
            pairs |= {(self._now_raw, act) for act in named}
        run = int(remark.get("at_least") or 0)
        steps = [s for s, _, _ in context.seen]
        if remark.get("remark") == "back-and-forth":
            reach = min(run, len(steps)) if run else 0
        else:
            reach = 0
        if again and run:
            reach = min(len(steps), int(shifted_count(run, rising(axis(context.field, ALERTNESS)))))
        for step in steps[len(steps) - reach:] if reach else []:
            act = step.act if step.act[0] in self.organs.placed else (step.act[0], None, None)
            if act in named:
                pairs.add((grid_key(step.before), act))
        return pairs

    def _getting_somewhere(self, remark: dict[str, Any], context: Context) -> bool:
        """Whether each step of the run the onlooker points at reached a state it had
        not stood in before in that run — a repetition going somewhere, not one
        standing or circling."""
        run = int(remark.get("at_least") or 0)
        steps = [s for s, _, _ in context.seen][-run:] if run else []
        if len(steps) < run or not steps:
            return False
        states = [grid_key(steps[0].before, self.clock)] + [grid_key(s.after, self.clock) for s in steps]
        return len(set(states)) == len(states)

    def objections(self) -> set[tuple[str, Act]]:
        """What it objects to now, as (where the region stands, act) under the clock it holds."""
        return {(self._state_of[raw], act) for held in self._objected.values() for raw, act in held
                if raw in self._state_of}

    # ── where the region stands ──

    def _reached(self, report: dict[str, Any] | None) -> bool:
        """Whether a report shows the aim reached."""
        fields = ((self._aim or {}).get("reached_when") or {}).get("fields") or {}
        return bool(fields) and bool(report) and all(report.get(k) == v for k, v in fields.items())

    def _meet(self, grid: Grid) -> str:
        raw = grid_key(grid)
        if raw not in self._raw:
            self._raw[raw] = grid
            state = grid_key(grid, self.clock)
            self._state_of[raw] = state
            self._grid_of.setdefault(state, raw)
        return raw

    def _state_key(self, raw: str) -> str:
        return self._state_of[raw]

    def _learn_clock(self, step: Step, kind: tuple, unit: Any) -> list[Write]:
        before, after = step.before, step.after
        per_row = {r: sum(1 for a, b in zip(before[r], after[r]) if a != b)
                   for r in range(min(len(before), len(after))) if before[r] != after[r]}
        if step.act == self.organs.reset or step.act[0] == self.organs.reset[0] \
                or sum(per_row.values()) > BIG_CHANGE:
            return []
        self._recent.append((kind, frozenset(r for r, n in per_row.items() if n <= CLOCK_CELLS)))
        if len(self._recent) < CLOCK_WINDOW or len({k for k, _ in self._recent}) < CLOCK_KINDS:
            return []
        always = frozenset.intersection(*(r for _, r in self._recent))
        if not always or always <= self.clock:
            return []
        self.clock = self.clock | always
        writes = self._reindex((unit,))
        writes.append(Write(payload={"rows": sorted(self.clock), "cycle": self.frame_calls},
                            tags=dict(CLOCK_TAGS), built_from=(unit,)))
        return writes

    def _reindex(self, built_from) -> list[Write]:
        self._state_of = {raw: grid_key(g, self.clock) for raw, g in self._raw.items()}
        self._grid_of = {}
        for raw, state in self._state_of.items():
            self._grid_of.setdefault(state, raw)
        self._things = {}
        self._edges, self._out = {}, {}
        writes: list[Write] = []
        for edge in self._learned:
            key = (self._state_of[edge.source], edge.act)
            first = self._edges.get(key)
            if first is None:
                self._edges[key] = edge
                self._out.setdefault(key[0], {})[edge.act] = edge
            elif first.holds and self._state_of[first.to] != self._state_of[edge.to]:
                first.holds = False
                writes += self._revise(first, built_from)
        if self._here is not None and self._now_raw is not None:
            self._here = self._state_of[self._now_raw]   # where it stands, read again under the clock
        return writes

    # ── the expectation, and learning ──

    def expect(self, step: Step) -> Expectation:
        self.frame_calls += 1
        source = grid_key(step.before, self.clock)
        known = self._edges.get((source, step.act if step.act[0] in self.organs.placed
                                 else (step.act[0], None, None)))
        if known is not None and known.holds:
            state = [row[:] for row in self._raw[known.to]]
            self._expected = state
            return Expectation(state=state, fields=dict(known.status) if known.status else None,
                               held=(("handle", known),), by_model=True)
        self._expected = [row[:] for row in step.before]
        return Expectation(state=self._expected, by_model=False)

    def observe(self, step: Step, unit: Any, fields: dict[str, Any] | None, units: tuple[Any, ...],
                on_report: bool) -> list[Write]:
        return self._learn_report(fields, units) if on_report else self._learn_step(step, unit)

    def _learn_step(self, step: Step, unit: Any) -> list[Write]:
        writes: list[Write] = []
        if self._last is not None and self._last_new and not self._last.written:
            writes += self._write_edge(self._last, ())  # a step whose report never came
        o = self.organs
        act: Act = step.act if step.act[0] in o.placed else (step.act[0], None, None)
        source_raw = self._meet(step.before)
        source = self._state_of[source_raw]
        known = self._edges.get((source, act))
        to_raw = self._meet(step.after)
        self.holds_off_clock.append(int(grid_key(self._expected, self.clock) == self._state_of[to_raw])
                                    if self._expected is not None else 0)
        kind = known.kind if known is not None else (self._kind_of.get((source, act)) or ("act", act[0]))
        to = self._state_of[to_raw]
        changed = to != source
        if act[0] != o.reset[0]:
            for counts in (self._kinds.setdefault(kind, [0, 0, 0]), self._actions.setdefault(act[0], [0, 0, 0])):
                counts[0] += 1
                counts[1] += int(changed)
        self._last_new = known is None
        if known is None:
            edge = Edge(source_raw, act, to_raw, kind, changed)
            self._learned.append(edge)
            self._edges[(source, act)] = edge
            self._out.setdefault(source, {})[act] = edge
        else:
            edge = known
            edge.seen += 1
            if edge.holds and self._state_of[edge.to] != to:
                edge.holds = False  # the same act from the same state gave two things
                writes += self._revise(edge, (unit,))
        self._last, self._last_act = edge, act
        self._here, self._unit, self._now_raw = to, unit, to_raw
        self._visits[to] = self._visits.get(to, 0) + 1
        if act[0] == o.reset[0]:
            self._learned_since_reset = False
        elif known is None:
            self._learned_since_reset = True
        writes += self._learn_clock(step, kind, unit)
        return writes

    def _learn_report(self, report: dict[str, Any] | None, units: tuple[Any, ...]) -> list[Write]:
        edge = self._last
        if edge is None or report is None:
            return []
        writes: list[Write] = []
        said = {k: report.get(k) for k in self.organs.report_fields}
        if edge.status is None:
            edge.status = said
        elif self._reached(edge.status) != self._reached(said) and edge.holds:
            # The aim from one and not from the other: the act does not hold. The
            # region ending one time and not another is the clock's doing (a budget
            # of acts), not the act's.
            edge.holds = False
            writes += self._revise(edge, units)
        if said.get(self.organs.state_field) in self.organs.ended:
            edge.ended += 1
        if self._reached(said) and edge.act[0] != self.organs.reset[0]:
            # Counted each time, as tries are (it was counted only on a new edge).
            self._kinds.setdefault(edge.kind, [0, 0, 0])[2] += 1
            self._actions.setdefault(edge.act[0], [0, 0, 0])[2] += 1
        if self._last_new and not edge.written:
            writes += self._write_edge(edge, units)
        return writes

    def _write_edge(self, edge: Edge, built_from: tuple[object, ...]) -> list[Write]:
        edge.written = True
        self.version += 1
        return [Write(payload=edge.payload(self._state_key), tags=dict(LEARNED_TAGS), handle=edge,
                      built_from=built_from)]

    def _revise(self, edge: Edge, built_from: tuple[object, ...]) -> list[Write]:
        """A transition that no longer holds: said in a datum of its own, built from
        the one it refutes — added, not revised in place (Plone, 2026-09-27)."""
        if not edge.written:
            return []
        return [Write(payload=edge.payload(self._state_key), tags=dict(LEARNED_TAGS),
                      built_from=(*built_from, ("handle", edge)))]

    # ── what to do next ──

    @staticmethod
    def _odds_of(counts) -> tuple[float, float]:
        tried, changed, aim = counts
        return (aim + 1) / (tried + 2) if aim else 0.0, (changed + 1) / (tried + 2)

    def _odds(self, kind: tuple) -> tuple[float, float]:
        """The odds it gives a kind of act: of the aim, and of the state changing."""
        return self._odds_of(self._kinds.get(kind, (0, 0, 0)))

    def _action_curiosity(self, act: int) -> tuple[float, float]:
        """How much it wants an act at all, over every kind of it (the first of
        the two choices): an act none of whose kinds did anything anywhere is
        wanted less, however many places are left to put it (LOG.md: ar25 and
        sk48 spent two steps in three on clicks that changed nothing)."""
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
        out: list[tuple[Act, tuple]] = []
        for a in sorted(offers):
            if a == self.organs.reset[0]:
                continue
            if a in self.organs.placed:
                if here not in self._things:
                    self._things[here] = things(self._raw[self._grid_of[here]])
                for colour, size, x, y in self._things[here]:
                    out.append(((a, x, y), ("click", colour, size)))
            else:
                out.append(((a, None, None), ("act", a)))
        return out

    def _open_here(self, here: str, offers: tuple[int, ...],
                   objected: set[tuple[str, Act]] | None = None) -> list[tuple[Act, tuple]]:
        objected = self.objections() if objected is None else objected
        return [(act, kind) for act, kind in self._candidates(here, offers)
                if (here, act) not in self._edges and (here, act) not in objected]

    def _path(self, start: str, goal: Callable[[str], bool],
              avoid: set[tuple[str, Act]] | frozenset = frozenset()) -> list[Edge] | None:
        """The shortest path it knows from `start` to a state `goal` holds of, by
        transitions that hold and did not end the region every time, and whose
        first act is none of `avoid` there; None if none."""
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
                if edge.holds and edge.ended < edge.seen and edge.act[0] != self.organs.reset[0] \
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
        # What the onlooker no longer says is lifted; what it says stands.
        said = self._said(context.remark or {})
        lifted = self._lift(said)
        objected = self.objections()
        if context.ended is not None:
            act, why = self.organs.reset, f"the region has ended ({context.ended})"
        else:
            # Toward the aim it takes no objection (H5 (i)).
            gained = {self._state_of[e.source] for e in self._edges.values() if e.holds and self._reached(e.status)}
            aim_here = [e for e in self._out.get(here, {}).values() if e.holds and self._reached(e.status)]
            path = None if aim_here or not gained else self._path(here, lambda n: n in gained)
            opened = self._open_here(here, offers, objected)
            if aim_here:
                act, why, through = aim_here[0].act, "an act that reached the aim before", [aim_here[0]]
            elif path:
                act, why, through = path[0].act, f"toward the aim reached before ({len(path)} steps)", path
            elif opened:
                # First which act, over every kind of it; then which of its kinds.
                chosen = max({a for (a, _, _), _ in opened}, key=lambda a: (self._action_curiosity(a), -a))
                best = max((ak for ak in opened if ak[0][0] == chosen), key=lambda ak: self._curiosity(ak[1]))
                act, odds = best[0], self._odds(best[1])[1]
                self._kind_of[(here, act)] = best[1]
                why = "not yet taken from here"
            else:
                def open_at(n: str) -> bool:
                    return n in self._grid_of and bool(self._open_here(n, offers, objected))

                # A way whose first act is not objected to here; only if there is
                # none, one that is (H1).
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
                        # Every act it knows here was objected to: the act that is
                        # always open, before one objected to (H3).
                        act, why = self.organs.reset, "every act known here was objected to"
                    elif said is not None and said[0] == "standing still":
                        # Told it stands still, with nothing to do here: the act that
                        # is always open, rather than standing on (H6).
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
            # A second command this cycle, on what the onlooker said: the body
            # carries out this one, and this datum says which choice it replaces.
            choice["supersedes"] = {"chose": self._last_choice.get("chose"), "why": self._last_choice.get("why")}
        self._last_choice = choice
        if context.remark and context.remark.get("remark"):
            choice["onlooker"] = context.remark
            if context.remark_unit is not None:
                built.append(context.remark_unit)   # what it quotes, it was built from
        built += [("handle", e) for e in through]
        built.append(("prior", "task"))
        return Proposal(act, why=why), [Write(payload=choice, tags=dict(CHOICE_TAGS), built_from=tuple(built))]


__all__ = ["BIG_CHANGE", "CHOICE_TAGS", "CLOCK_CELLS", "CLOCK_KINDS", "CLOCK_TAGS", "CLOCK_WINDOW",
           "LEARNED_TAGS", "MAX_CLICK_TARGETS", "MAX_PATH_NODES", "MAX_THING_SHARE",
           "Answer", "Choice", "Edge", "LearningModel", "grid_key", "things"]
