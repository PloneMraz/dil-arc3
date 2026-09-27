"""The learning mind — one mind, which learns the region from nothing.

Another mind for the one seat (CLAUDE.md, "One mind"; Plone, 2026-09-27). The
language mind (`mind.py`) thinks with a model trained before the loop ever ran;
this one brings no weights and no text. Everything it knows accrues in the loop,
one return at a time (INV-5), and is written to the store as it is learned, each
datum saying what it was built from. Its thinking is an algorithm, and its
curiosity, want and expectation are computed in it — by it, not for it (Plone:
"cấm tính hộ, không phải cấm code").

WHAT IT LEARNS. What an action does where the game stands. A state is the grid
the region returned (the last of the stack, as the language mind reads it); an
act is the action, with its cell for ACTION6. Each step it takes is a transition
it learns — from this grid, this act, came that grid, and the region reported
this of itself — written as a datum (`kind: transition`) built from the frame
and the report it came in. It also keeps, per kind of act, how often it was
tried, how often it changed the grid, and how often a level came of it: a kind
of act is an action, or for ACTION6 the colour and size of the thing clicked.
Those counts are read from the transitions it wrote; they are not written again.

WHERE THE GAME STANDS, AND THE CLOCK. Two grids are the same state when they
agree everywhere but on the clock: a row that changed in every one of the last
CLOCK_WINDOW steps, under at least two kinds of act, is taken for a clock the
region keeps whatever is done — a bar that counts steps — not for where the game
stands (ls20's rows 61-62, vc33's row 0; LOG.md): a row that changed in every
one of the last CLOCK_WINDOW steps, under CLOCK_KINDS kinds of act or more, by
no more than CLOCK_CELLS cells each time. DECLARED, not measured. The
clock only grows; when it does, the mind writes it (`kind: clock`) and re-reads
every grid it has met under it. It does not predict the clock: an expectation
from a transition carries the clock as it was then, and meets the region there.

WHAT IT EXPECTS. For an act it has taken from this grid before, what came then:
the grid, and the region's report. That expectation is the transition datum's
(`held_by`): when the region returns something else, the datum is scarred with
the return, and the mind revises it as not holding — the same act from the same
grid gave two things, so it no longer predicts from it. For an act it has not
taken from here, it holds the standing expectation: nothing changes.

WHAT IT IS CURIOUS ABOUT, AND WANTS. Its aim, as it reads the task it was told
(`prior:mind-task`: get through the levels), is a report of a level gained —
declared here, and named with the task's datum in what each choice is built
from. What it does next, in this order:

  1. toward a level: if a path it knows leads to an act that gained a level
     before, the next step of that path;
  2. curiosity: an act not yet taken from here, chosen in two steps — first the
     action, over every kind of it, then (for ACTION6) which thing to click.
     At each step, first what most often gained a level; then what has the
     highest odds of changing where the game stands (one untried and one tried
     in its favour: Laplace), raised by how little it has been tried (UCB1).
     What it knows least, it is most curious about; what changes nothing falls
     behind as it is tried — clicking as a whole, when no click did anything;
  3. the next step of the shortest path it knows to a grid with an act not yet
     taken — never through an act that ended the game or no longer holds;
  4. RESET, when nothing is left to try from anywhere it can reach and it has
     learned something since the last RESET; otherwise the known act toward the
     state it has visited least.

When the game has ended, RESET. What ACTION6 may click is each thing on the
grid: a region of one colour, joined side to side, at the cell nearest its
middle — at most MAX_CLICK_TARGETS of them, smallest first, none larger than MAX_THING_SHARE of
the grid (a region that large is taken for the ground). Declared, not
measured, and naming no game: that a grid shows things is this mind's reading of
any grid.

Each choice is written (`kind: choice`): what it chose, why, the odds it gave the
grid changing, and what it was built from — the frame it stands on, the
transitions its path runs through, the task. So every change in what it does can
be read back from the store and `[event]`.

WHAT IT DOES NOT DO. It does not read the store back for what it holds: it holds
what it learned, as the language mind holds its program, and writes it as it
learns it. It asks the store once, for its task. The onlooker's remark reaches
it and is written with the choice it met; a path it follows it keeps to.

The seam is the language mind's: `learning_rule(mind)` is T5's PredictRule; the
mind commands through T5's test, and the body carries it out (`command.py`).
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Final

from dil.loop.layers.t3 import STORE_CHANNEL
from dil.loop.layers.t5 import Expecting, WriteRequest, persistence
from dil.loop.types import InfoUnit

from .action import COMPLEX_ACTION, RESET
from .command import can_carry_out
from .frame import TERMINAL_STATES
from .mind import Transition, _content_value, _fingerprint, _no_change, expected_status, transition_of
from .observe import FRAME_CHANNEL, FRAME_KIND, ONLOOKER_CHANNEL, STATUS_CHANNEL
from .task import TASK_CUE, TASK_DOMAIN

Grid = list[list[int]]
Act = tuple[int, "int | None", "int | None"]

LEARNED_TAGS: Final = {"domain": "mind", "kind": "transition", "object": FRAME_KIND, "source": "mind"}
CHOICE_TAGS: Final = {"domain": "mind", "kind": "choice", "source": "mind"}
CLOCK_TAGS: Final = {"domain": "mind", "kind": "clock", "object": FRAME_KIND, "source": "mind"}

# The clock: rows that changed in every one of the last CLOCK_WINDOW steps, under
# at least CLOCK_KINDS kinds of act, by at most CLOCK_CELLS cells a row each step;
# a step that changed more than BIG_CHANGE cells (a new level, a reset) is no
# evidence of a clock. DECLARED, not measured: on ls20 a looser rule took the
# rows a moving piece crossed for the clock (LOG.md).
CLOCK_WINDOW: Final = 6
CLOCK_KINDS: Final = 3
CLOCK_CELLS: Final = 2
BIG_CHANGE: Final = 64 * 64 // 4

# The aim, as this mind reads the task it is told (`prior:mind-task`). DECLARED.
AIM: Final = {"aim": "gain a level", "source": "the task, as this mind reads it",
              "reached_when": {"status": {"levelsDelta": 1}}}

# What ACTION6 may click. DECLARED, not measured.
MAX_CLICK_TARGETS: Final = 64
MAX_THING_SHARE: Final = 0.5
# How far it searches the grids it knows for a path. DECLARED: a bound on work.
MAX_PATH_NODES: Final = 20_000


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


@dataclass
class Edge:
    """One transition it learned: from a grid, an act, came a grid and a report.
    `source` and `to` are the grids as they came (their own keys); where the game
    stood is read from them under the clock the mind holds."""

    source: str
    act: Act
    to: str
    kind: tuple
    changed: bool
    status: dict[str, Any] | None = None
    ended: int = 0               # how many times the game ended on it
    holds: bool = True           # False once the same act from the same state gave two things
    datum_id: str | None = None
    seen: int = 1
    written: bool = False
    revise: bool = False         # a revision owed once its datum's id is known

    def payload(self, state: Callable[[str], str]) -> dict[str, Any]:
        return {"from": state(self.source), "act": list(self.act), "to": state(self.to) if self.holds else None,
                "changed": self.changed, "status": self.status, "holds": self.holds}


@dataclass
class Choice:
    """One command, for the run's report (the trace is `[event]` and the store)."""

    frame_call: int
    act: Act | None
    why: str
    odds: float | None = None


class LearningMind:
    """The one mind, learning: it expects from what it learned, is curious about
    what it has not, and commands the body's next action."""

    def __init__(self) -> None:
        self.frame_calls = 0
        self.holds: list[int] = []
        self.holds_off_clock: list[int] = []
        self.commands: list[tuple[int, Act | None]] = []
        self.thoughts: list[Choice] = []
        self.version = 0                  # transitions written
        self.code = None                  # it writes no program
        self._goal = dict(AIM)
        self._task_id: str | None = None
        self._task_asked = False
        self.clock: frozenset[int] = frozenset()
        self._recent: deque = deque(maxlen=CLOCK_WINDOW)   # (kind, rows changed) per step
        self._raw: dict[str, Grid] = {}                     # a grid, by its own key
        self._state_of: dict[str, str] = {}                 # a grid's key -> where the game stood
        self._grid_of: dict[str, str] = {}                  # a state -> a grid of it
        self._things: dict[str, list[tuple[int, int, int, int]]] = {}
        self._learned: list[Edge] = []                      # every transition, in the order learned
        self._edges: dict[tuple[str, Act], Edge] = {}
        self._out: dict[str, dict[Act, Edge]] = {}
        self._kinds: dict[tuple, list[int]] = {}   # kind -> [tried, changed, levels]
        self._actions: dict[int, list[int]] = {}   # action -> [tried, changed, levels], every kind of it
        self._kind_of: dict[tuple[str, Act], tuple] = {}
        self._by_mark: dict[str, Edge] = {}
        self._echoes: list[str] = []
        self._here: str | None = None
        self._unit: InfoUnit | None = None
        self._last: Edge | None = None
        self._last_new = False
        self._last_act: Act | None = None
        self._state: str | None = None
        self._affords: tuple[int, ...] = ()
        self._remark: dict[str, Any] | None = None
        self._status_this_cycle = False
        self._visits: dict[str, int] = {}
        self._learned_since_reset = True

    # ── what arrives ──

    def take_return(self, ret: dict[str, Any], write) -> None:
        """A store return: its task, or its own datum back with its id."""
        open_tags = ret.get("open", {})
        payload = ret.get("payload")
        entity = str(ret.get("entity"))
        if open_tags.get("domain") == TASK_DOMAIN and self._task_id is None:
            self._task_id = entity
            return
        mark = _fingerprint(payload)
        if mark in self._echoes:
            self._echoes.remove(mark)
            edge = self._by_mark.pop(mark, None)
            if edge is not None and edge.datum_id is None:
                edge.datum_id = entity
                if edge.revise and write is not None:
                    edge.revise = False
                    self._write(write, WriteRequest(payload=edge.payload(self._state_key), datum_id=entity,
                                                    built_from=()))

    def _write(self, write, request: WriteRequest, edge: Edge | None = None) -> None:
        mark = _fingerprint(request.payload)
        self._echoes.append(mark)
        if edge is not None:
            self._by_mark[mark] = edge
        write(request)

    # ── where the game stands ──

    def _meet(self, grid: Grid) -> str:
        """A grid met: kept by its own key; returns where the game stands."""
        raw = grid_key(grid)
        if raw not in self._raw:
            self._raw[raw] = grid
            state = grid_key(grid, self.clock)
            self._state_of[raw] = state
            self._grid_of.setdefault(state, raw)
        return raw

    def _state_key(self, raw: str) -> str:
        return self._state_of[raw]

    def _learn_clock(self, t: Transition, kind: tuple, observed: InfoUnit, write) -> None:
        """Rows that changed in every recent step, under two kinds of act or more,
        are the clock's."""
        per_row = {r: sum(1 for a, b in zip(t.before[r], t.after[r]) if a != b)
                   for r in range(min(len(t.before), len(t.after))) if t.before[r] != t.after[r]}
        if t.action == RESET or sum(per_row.values()) > BIG_CHANGE:
            return
        self._recent.append((kind, frozenset(r for r, n in per_row.items() if n <= CLOCK_CELLS)))
        if len(self._recent) < CLOCK_WINDOW or len({k for k, _ in self._recent}) < CLOCK_KINDS:
            return
        always = frozenset.intersection(*(r for _, r in self._recent))
        if not always or always <= self.clock:
            return
        self.clock = self.clock | always
        self._reindex(write, (observed,))
        if write is not None:
            self._write(write, WriteRequest(payload={"rows": sorted(self.clock), "cycle": self.frame_calls},
                                            open=dict(CLOCK_TAGS), built_from=(observed,)))

    def _reindex(self, write, built_from) -> None:
        """Every grid met, read again under the clock; the transitions indexed again.
        Two that now start from the same state with the same act and disagree no
        longer hold."""
        self._state_of = {raw: grid_key(g, self.clock) for raw, g in self._raw.items()}
        self._grid_of = {}
        for raw, state in self._state_of.items():
            self._grid_of.setdefault(state, raw)
        self._things = {}
        self._edges, self._out = {}, {}
        for edge in self._learned:
            key = (self._state_of[edge.source], edge.act)
            first = self._edges.get(key)
            if first is None:
                self._edges[key] = edge
                self._out.setdefault(key[0], {})[edge.act] = edge
            elif first.holds and self._state_of[first.to] != self._state_of[edge.to]:
                first.holds = False
                self._revise(first, write, built_from)
        if self._here is not None and self._last is not None:
            self._here = self._state_of[self._last.to]

    # ── the expectation, and learning ──

    def on_frame(self, t: Transition, observed: InfoUnit, content: dict[str, Any], payload: dict[str, Any],
                 window, contribute, ask, write) -> InfoUnit | Expecting:
        self.frame_calls += 1
        self._status_this_cycle = False
        if not self._task_asked and ask is not None:
            ask(dict(TASK_CUE))
            self._task_asked = True
        if self._last is not None and self._last_new and not self._last.written and write is not None:
            self._write_edge(self._last, write, ())  # a step whose report never came
        source_raw = self._meet(t.before)
        source = self._state_of[source_raw]
        act: Act = (t.action, t.x, t.y) if t.action == COMPLEX_ACTION else (t.action, None, None)
        known = self._edges.get((source, act))
        if known is not None and known.holds:
            expected = [row[:] for row in self._raw[known.to]]
            held = (known.datum_id,) if known.datum_id else ()
        else:
            expected, held = [row[:] for row in t.before], ()
        predicted = InfoUnit(content={**content, "value": {**payload, "grids": [expected]}},
                             ref_frame=observed.ref_frame, t=observed.t)
        self.holds.append(int(expected == t.after))
        to_raw = self._meet(t.after)
        self.holds_off_clock.append(int(grid_key(expected, self.clock) == self._state_of[to_raw]))

        # Learn what came.
        kind = known.kind if known is not None else (self._kind_of.get((source, act)) or ("act", act[0]))
        to = self._state_of[to_raw]
        changed = to != source
        if act[0] != RESET:
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
                self._revise(edge, write, (observed,))
        self._last, self._last_act = edge, act
        self._here, self._unit = to, observed
        self._visits[to] = self._visits.get(to, 0) + 1
        if act[0] == RESET:
            self._learned_since_reset = False
        elif known is None:
            self._learned_since_reset = True
        self._learn_clock(t, kind, observed, write)
        return Expecting(predicted=predicted, held_by=held) if held else predicted

    def on_status(self, observed: InfoUnit, content: dict[str, Any], payload: dict[str, Any],
                  window, contribute, ask, write, test) -> InfoUnit | Expecting:
        self._status_this_cycle = True
        standing_unit = window[-1] if window else observed
        standing = _content_value(standing_unit)
        status_now = payload.get("status") if isinstance(payload.get("status"), dict) else None
        self._affords = tuple(int(a) for a in payload.get("affords") or ())
        self._state = (status_now or {}).get("stateTo")
        base = standing if isinstance(standing, dict) else dict(payload)
        base = {**base, "context": payload.get("context")} if "context" in payload else base
        edge = self._last
        value, held = base, ()
        if edge is not None and not self._last_new and edge.holds and edge.status and status_now is not None:
            value = {**base, "status": expected_status(dict(edge.status), _no_change(status_now))}
            held = (edge.datum_id,) if edge.datum_id else ()
        if value == standing:
            predicted = standing_unit
        else:
            base_content = standing_unit.content if isinstance(standing_unit.content, dict) else {}
            predicted = InfoUnit(content={**base_content, "value": value}, ref_frame=standing_unit.ref_frame,
                                 t=standing_unit.t)
        # Learn what the region reported of the step.
        if edge is not None and status_now is not None:
            said = {k: status_now.get(k) for k in ("stateTo", "levelsDelta", "depthDelta")}
            built = (self._unit, observed) if self._unit is not None else (observed,)
            if edge.status is None:
                edge.status = said
            elif (edge.status.get("levelsDelta") or 0) != (said.get("levelsDelta") or 0) and edge.holds:
                # A level from one and none from the other: the act does not hold.
                # The game ending one time and not another is the clock's doing
                # (a budget of acts), not the act's.
                edge.holds = False
                self._revise(edge, write, built)
            if said.get("stateTo") == "GAME_OVER":
                edge.ended += 1
            if self._last_new and (said.get("levelsDelta") or 0) > 0 and edge.act[0] != RESET:
                self._kinds.setdefault(edge.kind, [0, 0, 0])[2] += 1
                self._actions.setdefault(edge.act[0], [0, 0, 0])[2] += 1
            if self._last_new and not edge.written and write is not None:
                self._write_edge(edge, write, built)
        self.command(ask, write, test)
        holders: tuple[object, ...] = (standing_unit,) if window else ()
        return Expecting(predicted=predicted, held_by=(*holders, *held))

    def on_remark(self, observed: InfoUnit, payload: dict[str, Any], window, contribute, ask, write,
                  test=None) -> InfoUnit:
        """What the onlooker says: kept, and written with the choice it meets."""
        predicted = persistence("onlooker", window, observed, contribute, ask, write)
        self._remark = {k: v for k, v in payload.items() if k != "entity"} if payload.get("remark") else None
        if not self._status_this_cycle:
            self.command(ask, write, test)
        self._status_this_cycle = False
        return predicted

    def _write_edge(self, edge: Edge, write, built_from: tuple[object, ...]) -> None:
        edge.written = True
        self.version += 1
        self._write(write, WriteRequest(payload=edge.payload(self._state_key), open=dict(LEARNED_TAGS),
                                        built_from=built_from), edge)

    def _revise(self, edge: Edge, write, built_from: tuple[object, ...]) -> None:
        if write is None or not edge.written:
            return
        if edge.datum_id is None:
            edge.revise = True
            return
        self._write(write, WriteRequest(payload=edge.payload(self._state_key), datum_id=edge.datum_id,
                                        built_from=built_from))

    # ── commanding ──

    def _odds(self, kind: tuple) -> tuple[float, float]:
        """The odds it gives a kind of act: of a level, and of the state changing."""
        return self._odds_of(self._kinds.get(kind, (0, 0, 0)))

    @staticmethod
    def _odds_of(counts) -> tuple[float, float]:
        tried, changed, levels = counts
        return (levels + 1) / (tried + 2) if levels else 0.0, (changed + 1) / (tried + 2)

    def _action_curiosity(self, action: int) -> tuple[float, float]:
        """How much it wants to try an action at all, over every kind of it: the
        first of the two choices (then, for ACTION6, which thing to click). A
        click that never did anything anywhere makes clicking itself less
        wanted, however many things are left unclicked (LOG.md: ar25 and sk48
        spent two steps in three on clicks that changed nothing)."""
        level, change = self._odds_of(self._actions.get(action, (0, 0, 0)))
        tried = self._actions.get(action, (0, 0, 0))[0]
        total = sum(a[0] for a in self._actions.values())
        return level, change + math.sqrt(2 * math.log(total + 1) / (tried + 1))

    def _curiosity(self, kind: tuple) -> tuple[float, float]:
        """How much it wants to try a kind of act: the odds of a level first; then
        the odds of a change, raised by how little it knows the kind — the less
        tried, the more (UCB1). A kind never tried outranks one tried and found to
        change nothing, and one that changes things is tried again, less and
        less for its novelty. DECLARED: the rule is UCB1's, not measured here."""
        level, change = self._odds(kind)
        tried = self._kinds.get(kind, (0, 0, 0))[0]
        total = sum(k[0] for k in self._kinds.values())
        return level, change + math.sqrt(2 * math.log(total + 1) / (tried + 1))

    def _candidates(self, here: str) -> list[tuple[Act, tuple]]:
        out: list[tuple[Act, tuple]] = []
        for a in sorted(self._affords):
            if a == RESET:
                continue
            if a == COMPLEX_ACTION:
                if here not in self._things:
                    self._things[here] = things(self._raw[self._grid_of[here]])
                for colour, size, x, y in self._things[here]:
                    out.append(((a, x, y), ("click", colour, size)))
            else:
                out.append(((a, None, None), ("act", a)))
        return out

    def _open_here(self, here: str) -> list[tuple[Act, tuple]]:
        return [(act, kind) for act, kind in self._candidates(here) if (here, act) not in self._edges]

    def _path(self, start: str, goal: Callable[[str], bool]) -> list[Edge] | None:
        """The shortest path it knows from `start` to a state `goal` holds of, by
        transitions that hold and did not end the game; None if it knows none."""
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
                if edge.holds and edge.ended < edge.seen and edge.act[0] != RESET and to not in prev:
                    prev[to] = edge
                    queue.append(to)
        return None

    def command(self, ask, write, test) -> None:
        here = self._here
        if here is None:
            return
        through: list[Edge] = []
        odds: float | None = None
        act: Act | None = None
        if self._state in TERMINAL_STATES:
            act, why = (RESET, None, None), f"the game has ended ({self._state})"
        else:
            def gains(e: Edge) -> bool:
                return e.holds and bool(e.status) and (e.status.get("levelsDelta") or 0) > 0
            gained = {self._state_of[e.source] for e in self._edges.values() if gains(e)}
            level_here = [e for e in self._out.get(here, {}).values() if gains(e)]
            path = None if level_here or not gained else self._path(here, lambda n: n in gained)
            opened = self._open_here(here)
            if level_here:
                act, why, through = level_here[0].act, "an act that gained a level before", [level_here[0]]
            elif path:
                act, why, through = path[0].act, f"toward a level gained before ({len(path)} steps)", path
            elif opened:
                # First which action, over every kind of it; then which of its kinds.
                action = max({a for (a, _, _), _ in opened}, key=lambda a: (self._action_curiosity(a), -a))
                best = max((ak for ak in opened if ak[0][0] == action), key=lambda ak: self._curiosity(ak[1]))
                act, odds = best[0], self._odds(best[1])[1]
                self._kind_of[(here, act)] = best[1]
                why = "not yet taken from here"
            else:
                path = self._path(here, lambda n: n in self._grid_of and bool(self._open_here(n)))
                if path:
                    act, why, through = path[0].act, f"toward a state with an act not yet taken ({len(path)} steps)", path
                elif self._learned_since_reset:
                    act, why = (RESET, None, None), "nothing left to try from anywhere it can reach"
                else:
                    known = [e for e in self._out.get(here, {}).values()
                             if e.act[0] in self._affords and e.act[0] != RESET]
                    if known:
                        least = min(known, key=lambda e: (self._visits.get(self._state_of[e.to], 0), e.seen,
                                                          e.act[0], e.act[1] or 0, e.act[2] or 0))
                        act, why, through = least.act, "all known; toward the state visited least", [least]
                    else:
                        why = "nothing it can do here"
        if act is not None and not can_carry_out(*act, self._state, self._affords):
            why, act = f"{why}; the body cannot carry out {act}", None
        self.commands.append((self.frame_calls, act))
        self.thoughts.append(Choice(self.frame_calls, act, why, odds))
        if write is not None:
            choice: dict[str, Any] = {"cycle": self.frame_calls, "here": here, "chose": list(act) if act else None,
                                      "why": why, "aim": AIM["aim"]}
            if odds is not None:
                choice["odds_of_change"] = round(odds, 3)
            if self._remark:
                choice["onlooker"] = self._remark
            built: list[object] = [self._unit] if self._unit is not None else []
            built += [e.datum_id for e in through if e.datum_id]
            if self._task_id:
                built.append(self._task_id)
            self._write(write, WriteRequest(payload=choice, open=dict(CHOICE_TAGS), built_from=tuple(built)))
        if act is not None and test is not None:
            test({"kind": "move", "actionId": act[0], "x": act[1], "y": act[2]})


def learning_rule(mind: LearningMind) -> Callable[..., InfoUnit | Expecting]:
    """The learning mind at T5's seam (`PredictRule`): one rule, one mind, every arrival."""

    def rule(entity_id: str, window, observed: InfoUnit, contribute=None, ask=None, write=None, test=None):
        content = observed.content if isinstance(observed.content, dict) else {}
        channel = content.get("channel")
        payload = _content_value(observed)
        window = tuple(window or ())
        if channel == STORE_CHANNEL:
            if isinstance(payload, dict):
                mind.take_return(payload, write)
            return observed
        if channel == FRAME_CHANNEL and isinstance(payload, dict):
            t = transition_of(payload)
            if t is not None:
                return mind.on_frame(t, observed, content, payload, window, contribute, ask, write)
        if channel == STATUS_CHANNEL and isinstance(payload, dict):
            return mind.on_status(observed, content, payload, window, contribute, ask, write, test)
        if channel == ONLOOKER_CHANNEL and isinstance(payload, dict):
            return mind.on_remark(observed, payload, window, contribute, ask, write, test)
        return persistence(entity_id, window, observed, contribute, ask, write)

    return rule


def create_learning_mind() -> LearningMind:
    return LearningMind()


__all__ = ["AIM", "BIG_CHANGE", "CHOICE_TAGS", "CLOCK_CELLS", "CLOCK_KINDS", "CLOCK_TAGS", "CLOCK_WINDOW", "LEARNED_TAGS", "MAX_CLICK_TARGETS", "MAX_PATH_NODES", "MAX_THING_SHARE",
           "Choice", "Edge", "LearningMind", "create_learning_mind", "grid_key", "learning_rule", "things"]
