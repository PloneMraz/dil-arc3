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
size of the thing it was put on. Those counts are read from what it learned;
they are not written again.

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
an act not taken from here, it makes no expectation of its own, unless it has
seen something move (below): the standing one holds, held by no datum of its.

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
but it thinks on the onlooker's word: an act the onlooker says it keeps
repeating, or goes back and forth with, is objected to where it stands, and put
behind every other act there; the thought is written (`kind: thought`).

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

from ..organs import Act, Organs, Step
from .base import Context, Expectation, Proposal, Thinking, Write
from .motion import blocked_by, changed, find_shift, imagine, locate, search

Grid = list[list[int]]

LEARNED_TAGS: Final = {"domain": "mind", "kind": "transition", "object": "frame", "source": "mind"}
CHOICE_TAGS: Final = {"domain": "mind", "kind": "choice", "source": "mind"}
CLOCK_TAGS: Final = {"domain": "mind", "kind": "clock", "object": "frame", "source": "mind"}
RULE_TAGS: Final = {"domain": "mind", "kind": "rule", "object": "frame", "source": "mind"}
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


class MotionRule:
    """What it learned of how things move — by how much each act moves the thing
    that moves, the ground it moves on, the colours that stop it. Each time it
    learns more, a new version is written as a datum of its own, built from the
    version before: nothing is revised in place, so every version is in the store
    and `[event]`, not only in a snapshot (Plone, 2026-09-27). Each version is its
    own handle; the expectations it makes are the latest."""

    def __init__(self, version: int = 0) -> None:
        self.version = version
        self.written = False

    def payload(self, moves: dict[int, tuple[int, int]], ground: int | None, blocks: set[int],
                size: int) -> dict[str, Any]:
        return {"version": self.version, "moves": {str(a): list(d) for a, d in sorted(moves.items())},
                "ground": ground, "blocks": sorted(blocks), "thing_cells": size}


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

    def __init__(self, organs: Organs, priors: dict[str, dict[str, str]], motion: bool = False) -> None:
        self.organs = organs
        # Whether it reads motion (`motion.py`). Off by default: on ls20 it did
        # worse than without (LOG.md, 2026-09-27); kept to work on.
        self.motion = motion
        self._moves: dict[int, tuple[int, int]] = {}         # act -> how far it moves the thing
        self._move_counts: dict[int, dict[tuple[int, int], int]] = {}
        self._pattern: tuple | None = None                     # the thing that moves, as it looks
        self._at: tuple[int, int] | None = None                # its top-left, in the latest grid
        self._ground: int | None = None
        self._blocks: set[int] = set()
        self._touched: set[int] = set()
        self._goal_colours: set[int] = set()
        self._places: set[tuple[int, int]] = set()             # where the thing has been, this level
        self._onto: set[int] = set()                           # what the last act moved it onto
        self._rule = MotionRule()
        self._now: Grid | None = None                          # the latest grid
        self._now_raw: str | None = None                       # its own key
        self._stuck: set[tuple[tuple[int, int], int]] = set()  # (place, act) that moved nothing there
        self._objected: set[tuple[str, Act]] = set()           # (state, act) the onlooker objected to
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
        The onlooker's word does (Plone, 2026-09-27): when it says the agent is
        repeating itself or going back and forth, the act or acts it names are
        objected to where the region stands now, and put behind every other while
        it stands there. What was objected to, and why, is written."""
        remark = context.remark or {}
        if context.on != "onlooker" or remark.get("remark") not in ("repeating", "back-and-forth"):
            return None
        named = [remark.get("act")] if remark.get("act") else list(remark.get("acts") or [])
        ids = {name.upper(): a for a, name in self.organs.acts.items()}
        objected: list[Act] = []
        for said in named:
            if not isinstance(said, dict) or str(said.get("act", "")).upper() not in ids:
                continue
            a = ids[str(said["act"]).upper()]
            act = (a, said.get("x"), said.get("y")) if a in self.organs.placed else (a, None, None)
            if self._here is not None:
                self._objected.add((self._here, act))
                objected.append(act)
        if not objected:
            return None
        payload = {"on": "onlooker", "remark": remark, "here": self._here, "objected": [list(a) for a in objected]}
        built = (context.seen[-1][1],) if context.seen else ()
        return Thinking(writes=[Write(payload=payload, tags=dict(THOUGHT_TAGS), built_from=built)])

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
        by = self._moves.get(step.act[0]) if self.motion else None
        if by is not None and self._pattern is not None and self._at is not None and self._ground is not None:
            out, onto = blocked_by(step.before, self._pattern, self._at, by, self._ground)
            if out or onto & self._blocks:
                state = [row[:] for row in step.before]
            else:
                state = imagine(step.before, self._pattern, self._at, by, self._ground)
            self._expected = state
            held = (("handle", self._rule),) if self._rule.written else ()
            return Expectation(state=state, held=held, by_model=True)
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
        if self.motion:
            writes += self._learn_motion(step, act, unit)
        self._now = step.after
        return writes

    def _learn_motion(self, step: Step, act: Act, unit: Any) -> list[Write]:
        """What the act did to the thing that moves (`motion.py`)."""
        o = self.organs
        before, after = step.before, step.after
        known = self._moves.get(act[0])
        self._onto = set()
        if known is not None and self._pattern is not None and self._at is not None and self._ground is not None:
            _, self._onto = blocked_by(before, self._pattern, self._at, known, self._ground)
        if act[0] == o.reset[0] or act[0] in o.placed:
            if self._pattern is not None:
                self._at = locate(after, self._pattern, near=self._at)
            return []
        learned = False
        place = self._at
        shift = find_shift(before, after, self.clock)
        if shift is not None:
            counts = self._move_counts.setdefault(act[0], {})
            counts[shift.by] = counts.get(shift.by, 0) + 1
            most = max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]
            if self._moves.get(act[0]) != most:
                self._moves[act[0]] = most
                learned = True
            if self._ground != shift.ground:
                learned = learned or self._ground is not None
            self._touched |= self._onto
            if self._blocks & self._onto:
                self._blocks -= self._onto  # it moved onto it: it does not stop it
                learned = True
            self._pattern, self._at, self._ground = shift.pattern, shift.at, shift.ground
            self._places.add(shift.at)
        elif known is not None and self._pattern is not None and self._at is not None \
                and not changed(before, after, self.clock):
            # It did not move: what it would have moved onto stops it — unless a
            # colour already known to stop it was there, which says why; never
            # its own colours, nor one it has moved onto (LOG.md: on ls20 a wall
            # beside two other colours made all three walls, and it shut itself in).
            own = {v for _, _, v in self._pattern}
            new = set() if self._onto & self._blocks else self._onto - self._touched - own
            if new:
                self._blocks |= new
                learned = True
        elif self._pattern is not None:
            self._at = locate(after, self._pattern, near=self._at)
            if self._at is not None:
                self._places.add(self._at)
        if shift is None and known is not None and place is not None and self._at == place:
            # It did not move from here: whatever the colours say, this act does not
            # take it anywhere from this place (LOG.md: on ls20, a colour it had
            # moved onto once stood ahead, nothing new was learned, and it asked the
            # same act 306 times).
            self._stuck.add((place, act[0]))
        if not learned or self._pattern is None:
            return []
        before_rule = self._rule
        self._rule = MotionRule(before_rule.version + 1)
        self._rule.written = True
        payload = self._rule.payload(self._moves, self._ground, self._blocks, len(self._pattern))
        built = (unit, ("handle", before_rule)) if before_rule.written else (unit,)
        return [Write(payload=payload, tags=dict(RULE_TAGS), handle=self._rule, built_from=built)]

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
        if self.motion and self._reached(said) and edge.act[0] != self.organs.reset[0]:
            # What the thing was moved onto when the aim came: what to seek next.
            self._goal_colours |= self._onto
            self._places = set()
            if self._pattern is not None and self._now is not None:
                self._at = locate(self._now, self._pattern, near=self._at)
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

    def _open_here(self, here: str, offers: tuple[int, ...]) -> list[tuple[Act, tuple]]:
        return [(act, kind) for act, kind in self._candidates(here, offers)
                if (here, act) not in self._edges and (here, act) not in self._objected]

    def _path(self, start: str, goal: Callable[[str], bool]) -> list[Edge] | None:
        """The shortest path it knows from `start` to a state `goal` holds of, by
        transitions that hold and did not end the region every time; None if none."""
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
                        and to not in prev:
                    prev[to] = edge
                    queue.append(to)
        return None

    def _plan(self, offers: tuple[int, ...]) -> tuple[Act, str] | None:
        """What its imagination proposes, once it has seen something move: first
        toward what brought the aim before; then an act it has not seen move
        anything, to learn it; then toward a place the thing has not been, or a
        colour it has not touched. None: nothing imagined to go for."""
        o = self.organs
        if self._pattern is None or self._at is None or self._ground is None or self._now is None:
            return None
        here = self._here
        for a in list(self._moves):
            e = self._out.get(here, {}).get((a, None, None)) if here is not None else None
            if e is not None and e.holds and not e.changed:
                self._stuck.add((self._at, a))   # what it saw here outranks what it imagines
        moves = {a: d for a, d in self._moves.items() if a in offers
                 and (here, (a, None, None)) not in self._objected}
        if self._goal_colours and moves:
            path = search(self._now, self._pattern, self._at, moves, self._ground, self._blocks,
                          lambda p, onto: bool(onto & self._goal_colours), self._stuck)
            if path:
                return (path[0], None, None), f"toward a colour that brought the aim before ({len(path)} steps)"
        unlearned = [a for a in offers if a != o.reset[0] and a not in o.placed and a not in self._moves
                     and self._actions.get(a, (0, 0, 0))[0] < 3]
        if unlearned:
            a = max(unlearned, key=lambda a: (self._action_curiosity(a), -a))
            return (a, None, None), "an act whose effect it has not learned"
        if moves:
            path = search(self._now, self._pattern, self._at, moves, self._ground, self._blocks,
                          lambda p, onto: p not in self._places or bool(onto - self._touched - self._blocks),
                          self._stuck)
            if path:
                return (path[0], None, None), f"toward a place or a colour not yet reached ({len(path)} steps)"
        return None

    def propose(self, context: Context) -> tuple[Proposal, list[Write]]:
        here = self._here
        if here is None:
            return Proposal(None, why="nowhere yet"), []
        offers = context.offers
        through: list[Edge] = []
        odds: float | None = None
        act: Act | None = None
        if context.ended is not None:
            act, why = self.organs.reset, f"the region has ended ({context.ended})"
        else:
            gained = {self._state_of[e.source] for e in self._edges.values() if e.holds and self._reached(e.status)}
            aim_here = [e for e in self._out.get(here, {}).values() if e.holds and self._reached(e.status)]
            path = None if aim_here or not gained else self._path(here, lambda n: n in gained)
            opened = self._open_here(here, offers)
            planned = self._plan(offers) if self.motion else None
            if planned is None and self.motion and self._pattern is not None:
                # What it can foresee it need not try: acts whose motion it knows.
                opened = [ak for ak in opened if ak[0][0] not in self._moves]
            if aim_here:
                act, why, through = aim_here[0].act, "an act that reached the aim before", [aim_here[0]]
            elif path:
                act, why, through = path[0].act, f"toward the aim reached before ({len(path)} steps)", path
            elif planned is not None:
                act, why = planned
                through = [self._rule]
            elif opened:
                # First which act, over every kind of it; then which of its kinds.
                chosen = max({a for (a, _, _), _ in opened}, key=lambda a: (self._action_curiosity(a), -a))
                best = max((ak for ak in opened if ak[0][0] == chosen), key=lambda ak: self._curiosity(ak[1]))
                act, odds = best[0], self._odds(best[1])[1]
                self._kind_of[(here, act)] = best[1]
                why = "not yet taken from here"
            else:
                path = self._path(here, lambda n: n in self._grid_of and bool(self._open_here(n, offers)))
                if path:
                    act, why, through = path[0].act, f"toward a state with an act not yet taken ({len(path)} steps)", path
                elif self._learned_since_reset:
                    act, why = self.organs.reset, "nothing left to try from anywhere it can reach"
                else:
                    known = [e for e in self._out.get(here, {}).values()
                             if e.act[0] in offers and e.act[0] != self.organs.reset[0]]
                    known = [e for e in known if (here, e.act) not in self._objected] or known
                    if known:
                        least = min(known, key=lambda e: (self._visits.get(self._state_of[e.to], 0), e.seen,
                                                          e.act[0], e.act[1] or 0, e.act[2] or 0))
                        act, why, through = least.act, "all known; toward the state visited least", [least]
                    else:
                        why = "nothing it can do here"
        self.thoughts.append(Choice(self.frame_calls, act, why, odds))
        choice: dict[str, Any] = {"cycle": self.frame_calls, "here": here, "chose": list(act) if act else None,
                                  "why": why, "aim": (self._aim or {}).get("aim")}
        if odds is not None:
            choice["odds_of_change"] = round(odds, 3)
        if context.remark and context.remark.get("remark"):
            choice["onlooker"] = context.remark
        built: list[object] = [self._unit] if self._unit is not None else []
        built += [("handle", e) for e in through if not isinstance(e, MotionRule) or e.written]
        built.append(("prior", "task"))
        return Proposal(act, why=why), [Write(payload=choice, tags=dict(CHOICE_TAGS), built_from=tuple(built))]


__all__ = ["RULE_TAGS", "MotionRule", "BIG_CHANGE", "CHOICE_TAGS", "CLOCK_CELLS", "CLOCK_KINDS", "CLOCK_TAGS", "CLOCK_WINDOW",
           "LEARNED_TAGS", "MAX_CLICK_TARGETS", "MAX_PATH_NODES", "MAX_THING_SHARE",
           "Choice", "Edge", "LearningModel", "grid_key", "things"]
