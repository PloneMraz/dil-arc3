"""The objects inducer — the model the mind learns with where a state is a grid,
read as things that move (Plone, 2026-10-07: tried step by step; if it does
better, grid is history).

It reads grids as grid does — the clock, the things an act may be put on, what a
step made, how alike two grids are; that reading is copied here, so this inducer
stands on its own (Plone: "cách 1") — and says what an act does to a thing,
wherever the thing lies, not to a box of cells:

- **Move** — "this act moves what lies as this pattern by (rows, columns) — as
  another pattern, if it turns as it goes — and what it leaves takes the colour
  `trail`": suggested when an act that takes no place moved something — what
  changed, read as the things that touched it, as many cells of the same colours
  before and after, shifted or turned. It applies where the pattern lies once on
  the grid, and only where the cells it moves into are of `trail` too.
- **Block** — "this act does not move that pattern where what lies in its way is
  of these colours (or the grid's edge)": suggested when an act that takes no
  place changed nothing, from the moves it suggested of that act before (held by
  the mind, had back from its memory: `keep`), where the pattern lies and what
  lies in its way now. Wherever a wall of that colour lies so, the act is
  foreseen to change nothing — not where it was met only.
- **Still** — for an act that takes a place: "put on a cell of this colour, it
  changes nothing", as grid's.

What an experience itself says — that the act gives there what it gave — is the
mind's own (its experiences).

- **Aim** — "this act brings the aim where it moves that pattern into a cell of
  these colours" (or, when it moved onto what it leaves, next to one): suggested
  when the region's report says the aim came (S4), from the act's moves had back
  from the mind's memory — a relation between things, so it may hold on another
  layout (C2c, 2026-10-07).
"""
from __future__ import annotations

import hashlib
from collections import deque
from dataclasses import dataclass
from typing import Any, Final

from ..organs import Act, Organs, Step
from .base import Note, Prediction

Grid = list[list[int]]

CLOCK_TAGS: Final = {"domain": "mind", "kind": "clock", "object": "frame", "source": "mind"}

# What an act that takes a place may be put on: no thing larger than this share
# of the grid, which is the ground. DECLARED, not measured.
MAX_THING_SHARE: Final = 0.5
# The clock. DECLARED, not measured: on ls20 a looser rule took the rows a moving
# piece crossed for the clock (LOG.md).
CLOCK_WINDOW: Final = 6
CLOCK_KINDS: Final = 3
CLOCK_CELLS: Final = 2
# A bar at the edge: how near the edge its line lies, how many cells a change of
# it may be (sp80's moves 3 at a time), how many changes in a row show it. DECLARED.
COUNTER_EDGE: Final = 2
COUNTER_CELLS: Final = 3
COUNTER_TICKS: Final = 4
BIG_CHANGE: Final = 64 * 64 // 4
# Two changed cells this close or closer are one part of what changed. DECLARED.
PART_GAP: Final = 2



def parts(cells: list[tuple[int, int]], gap: int = PART_GAP) -> list[list[tuple[int, int]]]:
    """The cells grouped into parts: two in one part when a chain of cells, each
    within `gap` rows and columns of the next, joins them."""
    left = set(cells)
    out = []
    for cell in cells:
        if cell not in left:
            continue
        left.discard(cell)
        part, stack = [], [cell]
        while stack:
            r, c = stack.pop()
            part.append((r, c))
            for dr in range(-gap, gap + 1):
                for dc in range(-gap, gap + 1):
                    q = (r + dr, c + dc)
                    if q in left:
                        left.discard(q)
                        stack.append(q)
        out.append(part)
    return out


def grid_key(grid: Grid, clock: frozenset[int] = frozenset(), columns: frozenset[int] = frozenset()) -> str:
    """A grid's identity: two grids are one situation when every cell off the
    clock's rows and columns is the same."""
    h = hashlib.blake2b(digest_size=12)
    for r, row in enumerate(grid):
        if r in clock:
            h.update(bytes(len(row)))
            continue
        try:
            cells = bytearray(row)              # a row of 0-255 at C speed: the same bytes
        except (ValueError, TypeError):
            cells = bytearray(v & 0xFF for v in row)
        for c in columns:
            if c < len(cells):
                cells[c] = 0
        h.update(cells)
    h.update(bytes([len(grid)]))
    return h.hexdigest()


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
    return out





@dataclass(eq=False)
class StillForm:
    """This act changes nothing — put on a cell of `colour`, for an act that takes a place."""

    act: int
    colour: int | None

    @property
    def key(self) -> tuple:
        return ("still", self.act, self.colour)


# What lies past the grid's edge, in a ring.
OFF_GRID: Final = -1

# A thing a move is read from is no larger than this: what is larger is the
# ground or a wall. DECLARED, a bound on work.
MAX_MOVE_CELLS: Final = 256
# How many of an act's moves a blocked step is read against, the latest first.
# DECLARED, a bound on work.
MOVES_KEPT: Final = 4


@dataclass(eq=False)
class MoveForm:
    """This act moves what lies as `pattern` — (row, column, colour) from its
    corner — by (`dr`, `dc`), as `after` if it turns as it goes; what it leaves,
    and where it goes, is `trail`."""

    act: int
    pattern: tuple[tuple[int, int, int], ...]
    dr: int
    dc: int
    trail: int
    after: tuple[tuple[int, int, int], ...] | None = None   # as it comes, if not as it was (it turns)

    @property
    def came(self) -> tuple[tuple[int, int, int], ...]:
        return self.after if self.after is not None else self.pattern

    @property
    def key(self) -> tuple:
        return ("move", self.act, self.pattern, self.dr, self.dc, self.trail, self.after)


@dataclass(eq=False)
class AimForm:
    """This act brings the aim where it moves `pattern` by (`dr`, `dc`) into a
    cell of one of `into` — or, `beside`, next to one: the region then reports
    `status`. A relation between things, not a box of cells (C2c)."""

    act: int
    pattern: tuple[tuple[int, int, int], ...]
    dr: int
    dc: int
    trail: int
    colours: frozenset[int]
    beside: bool
    status: dict
    after: tuple[tuple[int, int, int], ...] | None = None

    @property
    def came(self) -> tuple[tuple[int, int, int], ...]:
        return self.after if self.after is not None else self.pattern

    @property
    def key(self) -> tuple:
        return ("aim", self.act, self.pattern, self.dr, self.dc, self.colours, self.beside)


@dataclass(eq=False)
class BlockForm:
    """This act does not move `pattern` by (`dr`, `dc`) where what lies in its way
    is of one of `blockers` (OFF_GRID: the grid's edge)."""

    act: int
    pattern: tuple[tuple[int, int, int], ...]
    dr: int
    dc: int
    trail: int
    blockers: frozenset[int]
    after: tuple[tuple[int, int, int], ...] | None = None

    @property
    def came(self) -> tuple[tuple[int, int, int], ...]:
        return self.after if self.after is not None else self.pattern

    @property
    def key(self) -> tuple:
        return ("block", self.act, self.pattern, self.dr, self.dc, self.blockers)


class ObjectsInducer:
    """Move, block and still hypotheses, over its reading of grids as things."""

    kind = "objects"
    # Its hypotheses apply past where they were met.
    general = True

    def __init__(self, organs: Organs) -> None:
        self.organs = organs
        self.clock: frozenset[int] = frozenset()             # the clock's rows
        self.clock_columns: frozenset[int] = frozenset()     # and its columns
        self._recent: deque = deque(maxlen=CLOCK_WINDOW)   # (kind, {row changed: its cells changed}) per step
        # Per line at the edge, its last changes of 1 to COUNTER_CELLS cells: where along it, and how.
        self._ticks: dict[tuple, deque] = {}
        # Per step, each line changed by 1 to CLOCK_CELLS cells: where along it, and how.
        self._lines: deque = deque(maxlen=CLOCK_WINDOW)
        self._things: dict[str, list[tuple[int, int, int, int]]] = {}
        self._masks: dict[str, tuple[int, tuple[int, ...]]] = {}   # identity -> (cells, a bit mask per colour)
        self._where: dict[str, dict[int, list[tuple[int, int]]]] = {}   # situation -> colour -> cells
        # (situation, form) -> (the form, where its pattern lies): the form is kept, so its id is not reused.
        self._found: dict[tuple[str, int], tuple[Any, tuple[int, int] | None]] = {}
        # Each act's moves it suggested, had back from the mind's memory (`keep`).
        self._moves_of: dict[int, list[Any]] = {}

    # ── reading a grid ──

    def identity(self, state: Grid) -> str:
        """A state's own identity, as it came."""
        return grid_key(state)

    def situation(self, state: Grid) -> str:
        """Where the region stands in a state, as it reads states now."""
        return grid_key(state, self.clock, self.clock_columns)

    def learn_reading(self, step: Step, kind: tuple) -> Note | None:
        """What a step teaches it of reading states: the clock, when it grows."""
        before, after = step.before, step.after
        per_row = {r: sum(1 for a, b in zip(before[r], after[r]) if a != b)
                   for r in range(min(len(before), len(after))) if before[r] != after[r]}
        if step.act == self.organs.reset or step.act[0] == self.organs.reset[0] \
                or sum(per_row.values()) > BIG_CHANGE:
            return None
        self._recent.append((kind, {r: frozenset(c for c, (a, b) in enumerate(zip(before[r], after[r])) if a != b)
                                    for r, n in per_row.items() if n <= CLOCK_CELLS}))
        counters = self._tick(before, after, per_row)
        self._lines.append(self._changed_lines(before, after, per_row))
        counters |= {("r", i) for i in self._counters("r")} | {("c", i) for i in self._counters("c")}
        rows, columns = frozenset(), frozenset(i for axis, i in counters if axis == "c")
        if len(self._recent) == CLOCK_WINDOW and len({k for k, _ in self._recent}) >= CLOCK_KINDS:
            rows = frozenset.intersection(*(frozenset(r) for _, r in self._recent))
            rows = frozenset(r for r in rows
                             if sum(len(cells[r]) for _, cells in self._recent)
                             == len(frozenset().union(*(cells[r] for _, cells in self._recent))))
        rows = rows | frozenset(i for axis, i in counters if axis == "r")
        if rows <= self.clock and columns <= self.clock_columns:
            return None
        self.clock, self.clock_columns = self.clock | rows, self.clock_columns | columns
        self._things, self._masks, self._where, self._found = {}, {}, {}, {}
        payload: dict[str, Any] = {"rows": sorted(self.clock)}
        if self.clock_columns:
            payload["columns"] = sorted(self.clock_columns)
        return Note(payload=payload, tags=dict(CLOCK_TAGS))

    @staticmethod
    def _changed_lines(before: Grid, after: Grid, per_row: dict[int, int]) -> dict[tuple, tuple]:
        """Each row and column a step changed by 1 to CLOCK_CELLS cells: where along
        it, and how (one colour into another)."""
        cells = [(r, c, before[r][c], after[r][c]) for r in per_row
                 for c in range(min(len(before[r]), len(after[r]))) if before[r][c] != after[r][c]]
        lines: dict[tuple, list] = {}
        for r, c, a, b in cells:
            lines.setdefault(("r", r), []).append((c, (a, b)))
            lines.setdefault(("c", c), []).append((r, (a, b)))
        return {line: (frozenset(p for p, _ in got), frozenset(t for _, t in got))
                for line, got in lines.items() if len(got) <= CLOCK_CELLS}

    def _counters(self, axis: str) -> frozenset[int]:
        """The lines of an axis that counted in every one of the last CLOCK_WINDOW
        steps: one change of colour, each next to the last."""
        if len(self._lines) < CLOCK_WINDOW:
            return frozenset()
        out = set()
        for line in self._lines[-1]:
            if line[0] != axis or any(line not in step for step in self._lines):
                continue
            ways = frozenset().union(*(step[line][1] for step in self._lines))
            if len(ways) != 1:
                continue
            spots = [step[line][0] for step in self._lines]
            if all(min(abs(p - q) for p in now for q in last) == 1 for last, now in zip(spots, spots[1:])):
                out.add(line[1])
        return frozenset(out)

    def _tick(self, before: Grid, after: Grid, per_row: dict[int, int]) -> set[tuple]:
        """Keep each edge line's change of 1 to COUNTER_CELLS cells (a larger change
        ends its run); the lines whose last COUNTER_TICKS changes count like a bar."""
        rows = min(len(before), len(after))
        cols = min(len(before[0]), len(after[0])) if rows else 0
        lines: dict[tuple, list] = {}
        for r in per_row:
            for c in range(min(len(before[r]), len(after[r]))):
                if before[r][c] != after[r][c]:
                    lines.setdefault(("r", r), []).append((c, (before[r][c], after[r][c])))
                    lines.setdefault(("c", c), []).append((r, (before[r][c], after[r][c])))
        out = set()
        for line, got in lines.items():
            size = rows if line[0] == "r" else cols
            if not (line[1] < COUNTER_EDGE or line[1] >= size - COUNTER_EDGE):
                continue
            if len(got) > COUNTER_CELLS:
                self._ticks.pop(line, None)
                continue
            ticks = self._ticks.setdefault(line, deque(maxlen=COUNTER_TICKS))
            ticks.append((frozenset(p for p, _ in got), frozenset(t for _, t in got)))
            if len(ticks) < COUNTER_TICKS or len(frozenset().union(*(w for _, w in ticks))) != 1:
                continue
            spots = [p for p, _ in ticks]
            if all(min(abs(p - q) for p in now for q in last) == 1 for last, now in zip(spots, spots[1:])):
                out.add(line)
        return out

    def _mask(self, state: Grid) -> tuple[int, tuple[int, ...]]:
        """A grid off the clock as one bit mask per colour, and how many cells it has."""
        raw = grid_key(state)
        kept = self._masks.get(raw)
        if kept is None:
            masks = [0] * 16
            bit, cells = 1, 0
            for r, row in enumerate(state):
                if r in self.clock:
                    bit <<= len(row)
                    continue
                for c, v in enumerate(row):
                    if c not in self.clock_columns:
                        masks[v & 15] |= bit
                        cells += 1
                    bit <<= 1
            kept = (cells, tuple(masks))
            self._masks[raw] = kept
        return kept

    def made(self, step: Step) -> frozenset:
        """What a step made: each part of the cells it changed off the clock (cells
        PART_GAP or closer, one part), as those cells, where they lie, in the
        colours the step left them. Two steps that left a part alike made the
        same; a step that changed nothing made nothing (B1, Plone, 2026-10-05)."""
        before, after = step.before, step.after
        cells = [(r, c) for r in range(min(len(before), len(after))) if r not in self.clock and before[r] != after[r]
                 for c in range(min(len(before[r]), len(after[r])))
                 if c not in self.clock_columns and before[r][c] != after[r][c]]
        return frozenset(tuple(sorted((r, c, after[r][c]) for r, c in part)) for part in parts(cells))

    def similarity(self, a: Grid, b: Grid) -> float:
        """How alike two states are, 0 to 1: the share of their cells, off the clock,
        of one colour in both (idea (a), Plone, 2026-09-29)."""
        cells, ma = self._mask(a)
        other, mb = self._mask(b)
        if not cells or cells != other:
            return 0.0
        return sum((x & y).bit_count() for x, y in zip(ma, mb)) / cells

    # ── what can be done ──

    def learnable(self, act: Act) -> Act:
        """An act as it is learned: the place kept only for an act that takes one."""
        return act if act[0] in self.organs.placed else (act[0], None, None)

    def default_kind(self, act: Act) -> tuple:
        return ("act", act[0])

    def copy(self, state: Grid) -> Grid:
        """A state of its own, as the learning keeps what it expects."""
        return [row[:] for row in state]

    def coarse(self, kind: tuple) -> tuple | None:
        """The coarser kind a kind falls in, read first: putting an act on a thing
        of a colour, whatever its size. None for a kind with none."""
        return kind[:2] if kind[0] == "click" and len(kind) > 2 else None

    def candidates(self, situation: str, state: Grid, offers: tuple[int, ...]) -> list[tuple[Act, tuple]]:
        """The acts it can take in a state, each with its kind: an act, or for an
        act that takes a place, the colour and size of the thing it is put on."""
        out: list[tuple[Act, tuple]] = []
        for a in sorted(offers):
            if a == self.organs.reset[0]:
                continue
            if a in self.organs.placed:
                if situation not in self._things:
                    self._things[situation] = things(state)
                for colour, size, x, y in self._things[situation]:
                    out.append(((a, x, y), ("click", colour, size)))
            else:
                out.append(((a, None, None), ("act", a)))
        return out

    # ── hypotheses ──

    def said(self) -> list[Note]:
        """What it said in computing, to be kept whole as data: nothing — it says
        nothing but its hypotheses."""
        return []

    def receive_prior(self, name: str, payload: Any) -> None:
        """A prior the mind recalled: it reads no words."""

    def hold_aim(self, aim: dict[str, Any]) -> None:
        """The aim the mind holds: it computes the same whatever it is for."""

    def induce(self, source: str, act: Act, before: Grid, after: Grid, *, foreseen: bool = False,
               evidence: tuple = (), report: dict | None = None, expected: Grid | None = None,
               through: tuple = ()) -> list[Any]:
        placed = act[0] in self.organs.placed and act[1] is not None and act[2] is not None
        if report is not None:
            return [] if placed else self._aim(act[0], before, report, through)
        changed = [(r, c) for r in range(min(len(before), len(after))) if r not in self.clock
                   for c in range(min(len(before[r]), len(after[r])))
                   if c not in self.clock_columns and before[r][c] != after[r][c]]
        if placed:
            return [StillForm(act[0], before[act[2]][act[1]])] if not changed else []
        if not changed:
            return self._blocked(act[0], before)
        return self._moved(act[0], before, after, changed)

    def _thing(self, grid: Grid, start: tuple[int, int], seen: set) -> list[tuple[int, int]] | None:
        """The cells of one colour joined side to side to `start`, off the clock;
        None when larger than MAX_MOVE_CELLS (the ground, or a wall)."""
        colour, cells, stack = grid[start[0]][start[1]], [], [start]
        seen.add(start)
        while stack:
            r, c = stack.pop()
            cells.append((r, c))
            if len(cells) > MAX_MOVE_CELLS:
                return None
            for q in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if q not in seen and 0 <= q[0] < len(grid) and 0 <= q[1] < len(grid[q[0]]) \
                        and q[0] not in self.clock and q[1] not in self.clock_columns and grid[q[0]][q[1]] == colour:
                    seen.add(q)
                    stack.append(q)
        return cells

    def _touching(self, grid: Grid, changed: list[tuple[int, int]], trail: int) -> list[tuple[int, int]] | None:
        """The cells of the things on `grid` that touch what changed, of no colour
        `trail`; None when one is too large to be a thing."""
        seen: set = set()
        out: list[tuple[int, int]] = []
        for cell in changed:
            if cell in seen or grid[cell[0]][cell[1]] == trail:
                continue
            thing = self._thing(grid, cell, seen)
            if thing is None:
                return None
            out += thing
        return out

    @staticmethod
    def _pattern(grid: Grid, cells: list[tuple[int, int]]) -> tuple[tuple[tuple[int, int, int], ...], int, int]:
        r0, c0 = min(r for r, _ in cells), min(c for _, c in cells)
        return tuple(sorted((r - r0, c - c0, grid[r][c]) for r, c in cells)), r0, c0

    def _moved(self, act: int, before: Grid, after: Grid, changed: list[tuple[int, int]]) -> list[Any]:
        """A move, if what changed reads as things of as many cells, of the same
        colours, after as before — shifted, turned, or both."""
        found = self._move_from(act, before, after, changed)
        return [found[0]] if found is not None else []

    def _move_from(self, act: int, before: Grid, after: Grid,
                   changed: list[tuple[int, int]]) -> tuple[Any, tuple[int, int]] | None:
        """The move what changed reads as, and where its pattern lay; tried with
        each colour what changed most became, as what a thing leaves."""
        if not changed or len(changed) > 2 * MAX_MOVE_CELLS:
            return None
        became: dict[int, int] = {}
        for r, c in changed:
            became[after[r][c]] = became.get(after[r][c], 0) + 1
        for trail in sorted(became, key=lambda v: -became[v])[:3]:
            was = self._touching(before, changed, trail)
            now = self._touching(after, changed, trail)
            if not was or not now:
                continue
            # What it moved onto and took the place of is gone after: only the
            # colours both hold are what moved.
            both = {before[r][c] for r, c in was} & {after[r][c] for r, c in now}
            was = [(r, c) for r, c in was if before[r][c] in both]
            now = [(r, c) for r, c in now if after[r][c] in both]
            if not was or len(was) != len(now):
                continue
            p, r0, c0 = self._pattern(before, was)
            q, r1, c1 = self._pattern(after, now)
            if sorted(v for _, _, v in p) != sorted(v for _, _, v in q) or (p == q and (r1, c1) == (r0, c0)):
                continue
            return (MoveForm(act=act, pattern=p, dr=r1 - r0, dc=c1 - c0, trail=trail,
                             after=q if q != p else None), (r0, c0))
        return None

    def _blocked(self, act: int, before: Grid) -> list[Any]:
        """A block, if a move it suggested of this act before finds its pattern
        here once, and what lies in its way is of no colour `trail`."""
        situation = self.situation(before)
        for recall in reversed(self._moves_of.get(act, [])[-MOVES_KEPT:]):
            form = recall()
            corner = self._locate(form, situation, before)
            if corner is None:
                continue
            blockers = self._in_the_way(form, corner, before)
            if blockers:
                return [BlockForm(act=act, pattern=form.pattern, dr=form.dr, dc=form.dc, trail=form.trail,
                                  blockers=frozenset(blockers), after=form.after)]
        return []

    def _aim(self, act: int, before: Grid, report: dict, through: tuple = ()) -> list[Any]:
        """What brought the aim, as a relation: the move that brought it — of this
        act's moves (had back from the mind's memory), the one whose pattern lies
        here once; else the step's own, from what the region showed last before
        the next level — and where it went, the colours that lay there, other
        than what it leaves; or, if none, those that lay next to where it went
        (C2c, 2026-10-07)."""
        situation = self.situation(before)
        tries: list[tuple[Any, tuple[int, int]]] = []
        for recall in reversed(self._moves_of.get(act, [])[-MOVES_KEPT:]):
            form = recall()
            corner = self._locate(form, situation, before)
            if corner is not None:
                tries.append((form, corner))
        if not tries and through:
            done = through[-1]
            changed = [(r, c) for r in range(min(len(before), len(done))) if r not in self.clock
                       for c in range(min(len(before[r]), len(done[r])))
                       if c not in self.clock_columns and before[r][c] != done[r][c]]
            found = self._move_from(act, before, done, changed)
            if found is not None:
                tries.append(found)
        for form, corner in tries:
            own = {(corner[0] + r, corner[1] + c) for r, c, _ in form.pattern}
            went = {(corner[0] + r + form.dr, corner[1] + c + form.dc) for r, c, _ in form.came}
            inside = lambda q: 0 <= q[0] < len(before) and 0 <= q[1] < len(before[q[0]])
            into = {before[r][c] for r, c in went - own if inside((r, c)) and before[r][c] != form.trail}
            beside = False
            if not into:
                ring = {(r + dr, c + dc) for r, c in went for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))} - went - own
                mine = {v for _, _, v in form.pattern}
                into = {before[r][c] for r, c in ring if inside((r, c)) and before[r][c] not in mine
                        and before[r][c] != form.trail}
                beside = True
            if into:
                return [AimForm(act=act, pattern=form.pattern, dr=form.dr, dc=form.dc, trail=form.trail,
                                colours=frozenset(into), beside=beside, status=dict(report), after=form.after)]
        return []

    def _in_the_way(self, form: Any, corner: tuple[int, int], state: Grid) -> set[int]:
        """The colours, other than `trail`, of the cells the pattern would move
        into and does not stand on now (OFF_GRID past the edge)."""
        own = {(corner[0] + r, corner[1] + c) for r, c, _ in form.pattern}
        out: set[int] = set()
        for r, c, _ in form.came:
            rr, cc = corner[0] + r + form.dr, corner[1] + c + form.dc
            if (rr, cc) in own or rr in self.clock or cc in self.clock_columns:
                continue
            if not (0 <= rr < len(state) and 0 <= cc < len(state[rr])):
                out.add(OFF_GRID)
            elif state[rr][cc] != form.trail:
                out.add(state[rr][cc])
        return out

    def _locate(self, form: Any, situation: str, state: Grid) -> tuple[int, int] | None:
        """The one place the form's pattern lies on the grid, off the clock; None
        if nowhere, or at several."""
        known = self._found.get((situation, id(form)))
        if known is not None and known[0] is form:
            return known[1]
        where = self._where.get(situation)
        if where is None:
            where = {}
            for r, row in enumerate(state):
                if r in self.clock:
                    continue
                for c, v in enumerate(row):
                    if c not in self.clock_columns:
                        where.setdefault(v, []).append((r, c))
            self._where[situation] = where
        pr, pc, colour = min(form.pattern, key=lambda cell: len(where.get(cell[2], ())))
        found = []
        for r, c in where.get(colour, ()):
            corner = (r - pr, c - pc)
            if all(0 <= corner[0] + dr < len(state) and 0 <= corner[1] + dc < len(state[corner[0] + dr])
                   and state[corner[0] + dr][corner[1] + dc] == v for dr, dc, v in form.pattern):
                found.append(corner)
                if len(found) > 1:
                    break
        corner = found[0] if len(found) == 1 else None
        self._found[(situation, id(form))] = (form, corner)
        return corner

    def key(self, form: Any) -> tuple:
        """What a hypothesis says, as one value: two that say the same are one."""
        return form.key

    def scope(self, form: Any, situation_of) -> tuple:
        """Where a hypothesis applies: wherever its act is taken."""
        return ("aim", form.act) if isinstance(form, AimForm) else ("act", form.act)

    def scopes(self, situation: str, act: Act) -> list[tuple]:
        return [("act", act[0]), ("aim", act[0])]

    def predict(self, form: Any, situation: str, state: Grid, act: Act, situation_of) -> Prediction | None:
        if act[0] != form.act:
            return None
        placed = act[0] in self.organs.placed and act[1] is not None and act[2] is not None
        if isinstance(form, StillForm):
            if not placed or not (0 <= act[2] < len(state) and 0 <= act[1] < len(state[act[2]])
                                  and state[act[2]][act[1]] == form.colour):
                return None
            return Prediction(state=state)
        if placed:
            return None
        corner = self._locate(form, situation, state)
        if corner is None:
            return None
        in_the_way = self._in_the_way(form, corner, state)
        if isinstance(form, AimForm):
            if form.beside:
                if in_the_way:
                    return None
                went = {(corner[0] + r + form.dr, corner[1] + c + form.dc) for r, c, _ in form.came}
                own = {(corner[0] + r, corner[1] + c) for r, c, _ in form.pattern}
                ring = {(r + dr, c + dc) for r, c in went for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))} - went - own
                near = {state[r][c] for r, c in ring if 0 <= r < len(state) and 0 <= c < len(state[r])}
                return Prediction(state=None, fields=dict(form.status)) if near & form.colours else None
            return Prediction(state=None, fields=dict(form.status)) if in_the_way & form.colours else None
        if isinstance(form, BlockForm):
            return Prediction(state=state) if in_the_way & form.blockers else None
        if in_the_way:
            return None          # something lies in its way: the move says nothing
        out = [row[:] for row in state]
        for r, c, _ in form.pattern:
            out[corner[0] + r][corner[1] + c] = form.trail
        for r, c, v in form.came:
            out[corner[0] + r + form.dr][corner[1] + c + form.dc] = v
        return Prediction(state=out)

    def describe(self, form: Any, situation_of) -> dict[str, Any]:
        if isinstance(form, StillForm):
            return {"form": "still", "act": form.act, "colour": form.colour}
        name = "move" if isinstance(form, MoveForm) else "block" if isinstance(form, BlockForm) else "aim"
        said = {"form": name, "act": form.act,
                "pattern": [list(c) for c in form.pattern], "dr": form.dr, "dc": form.dc, "trail": form.trail}
        if form.after is not None:
            said["after"] = [list(c) for c in form.after]
        if isinstance(form, BlockForm):
            said["blockers"] = sorted(form.blockers)
        if isinstance(form, AimForm):
            said.update({"colours": sorted(form.colours), "beside": form.beside, "status": form.status})
        return said

    def keep(self, form: Any, recall: Any) -> None:
        """A move it said is had back from the mind's memory when a blocked step
        is read against it."""
        if isinstance(form, MoveForm):
            self._moves_of.setdefault(form.act, []).append(recall)

    def restore(self, payload: dict[str, Any]) -> Any:
        """A still, move, block or aim hypothesis from its datum alone."""
        form = payload.get("form")
        if form == "still":
            return StillForm(act=payload["act"], colour=payload["colour"])
        pattern = tuple(tuple(c) for c in payload["pattern"])
        after = tuple(tuple(c) for c in payload["after"]) if payload.get("after") is not None else None
        if form == "aim":
            return AimForm(act=payload["act"], pattern=pattern, dr=payload["dr"], dc=payload["dc"],
                           trail=payload["trail"], colours=frozenset(payload["colours"]), beside=payload["beside"],
                           status=dict(payload["status"]), after=after)
        if form == "block":
            return BlockForm(act=payload["act"], pattern=pattern, dr=payload["dr"], dc=payload["dc"],
                             trail=payload["trail"], blockers=frozenset(payload["blockers"]), after=after)
        return MoveForm(act=payload["act"], pattern=pattern, dr=payload["dr"], dc=payload["dc"],
                        trail=payload["trail"], after=after)


__all__ = ["MAX_MOVE_CELLS", "MOVES_KEPT", "AimForm", "BlockForm", "MoveForm", "ObjectsInducer", "StillForm"]
