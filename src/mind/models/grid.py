"""The grid inducer — the model the mind learns with where a state is a grid.

It reads grids, and suggests from each experience the hypotheses that reach past
where it was met. What an experience itself says — that the act gives there
what it gave — is the mind's own (`mind/learning.py`, its experiences); the
mind holds these too, weighs them against the store, and expects from the one
right at the highest rate (FIT_LAW). It stands on its own: every computing of
it is in this file (Plone, 2026-10-06).

HOW IT READS A GRID — declared, not measured, naming no game:

- **Things.** A region of one colour joined side to side, at its cell nearest its
  middle — every one, smallest first, none larger than MAX_THING_SHARE of the
  grid (that large is taken for the ground). They are where an act that takes a
  place may be put; which to try is the mind's curiosity, not a cut made here
  (Plone, 2026-09-29: a cap of 64 left lp85's second level's arrows unseen).
- **Kinds.** Putting an act on a thing is of the kind (colour, size), within the
  coarser kind of its colour (`coarse`): what a colour did is read first, so
  what was learned of it carries to a thing of that colour at another size
  (Plone, 2026-09-29).
- **The clock.** A bar the region keeps whatever is done — it counts steps — is
  not where it stands (ls20's rows 61-62, vc33's row 0, lp85's column 0; LOG.md).
  A line is taken for it three ways. A row that changed in every one of the last
  CLOCK_WINDOW steps, under CLOCK_KINDS kinds of act or more, by no more than
  CLOCK_CELLS cells each time, no cell of it twice: a bar counts a cell once and
  moves on, and a cell that blinks back and forth as the acts alternate —
  r11l's mark of what is chosen — is not one (2026-10-04). Or a row or a column
  that, in every one of those steps, whatever the act, changed by 1 to
  CLOCK_CELLS cells, each time the same way and next to the cells it changed the
  step before. Or a row or a column within COUNTER_EDGE lines of the grid's edge
  whose last COUNTER_TICKS changes — the steps it changed in, not every step: a
  bar may count only some acts — were each of 1 to COUNTER_CELLS cells, all the
  same way (one colour into one other), each next to the cells of the change
  before: a bar growing or shrinking at the edge (Plone, 2026-09-29; every public
  game draws one, by a public notebook's survey — LOG.md, 2026-10-04). A thing
  that moves along a line changes it two ways (its colour into the ground's, and
  back), so it is not taken for one. Two grids are one situation when they agree
  off the clock's rows and columns. The clock only grows; when it does, every
  situation is read again under it. The clock is not predicted.
- **What a step made** (`made`): each part of the cells it changed off the clock,
  where it lies, as left (B1).
- **How alike** two grids are (`similarity`): the share of cells, off the clock,
  of one colour in both (attention).

ITS HYPOTHESES, in a language declared, not measured, naming no game:

- **Still** — "this act changes nothing (off the clock)": for an act that takes
  a place, put on a cell of this colour; for any other, anywhere.
- **Rewrite** — "this act rewrites, in each part of the grid it changes, the
  cells L into R": a part is changed cells near one another; its L is every cell
  of the box around them, as it was, and R the cells that changed, as they
  became. An act that takes a place must be put on the colour it was put on
  then. Each part is found on its own — two parts need not keep their distance
  (a piece moves, and a counter elsewhere ticks): at the place the act is put,
  when that lies in or next to the part; else at the one place L lies, or, where
  it lies at several, the one whose ring — the cells around the box, the grid's
  edge among them — is as it was. Never where it cannot tell which. The rewrite
  applies when every part is found. What lies in the way is in L: a move whose
  landing is blocked finds no L, and the rewrite says nothing there.
- **Aim** — "this act, taken where these cells lie, brings the aim": suggested
  when the region's report says the aim came (S4). Each part is what the act was
  to change — what the region showed before its last grid, else what the mind
  expected of the step, or, for an act that takes a place, the thing it was put
  on — with the ring around it, as it was. It says nothing of the state; where
  every part lies, box and ring alike, it says the region will report what it
  reported then.

The clock's rows and columns are no part of any of them: what lies there matches
anything.
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



# A rewrite over more cells than this is not suggested: it would be the grid
# itself, met again or not at all. DECLARED, a bound on work.
MAX_REWRITE_CELLS: Final = 1024


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


@dataclass(frozen=True)
class Part:
    """One part of a rewrite: its box `lhs` as it was, the `ring` around it, and
    the cells `rhs` it changes into — each (row, column, colour) from the box's
    corner; `place`, the corner from where the act was put, when that lies in or
    next to the box."""

    lhs: tuple[tuple[int, int, int], ...]
    ring: tuple[tuple[int, int, int], ...]
    rhs: tuple[tuple[int, int, int], ...]
    place: tuple[int, int] | None


@dataclass(eq=False)
class RewriteForm:
    """This act rewrites each of its parts."""

    act: int
    placed: bool
    parts: tuple[Part, ...]
    colour: int | None = None     # for an act that takes a place: the colour it was put on

    @property
    def key(self) -> tuple:
        return ("rewrite", self.act, self.placed, self.colour, self.parts)


@dataclass(eq=False)
class AimForm:
    """This act brings the aim, taken where its parts lie: the region then reports
    `status`. Each part is what the act was to change and what lay around it, as
    it was (`rhs` empty) — for an act that takes a place, the thing it was put on."""

    act: int
    placed: bool
    parts: tuple[Part, ...]
    colour: int | None
    status: dict

    @property
    def key(self) -> tuple:
        return ("aim", self.act, self.placed, self.colour, self.parts)




class GridInducer:
    """Still, rewrite and aim hypotheses, over its reading of grids."""

    kind = "grid"
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
        # (situation, part) -> (the part, where it lies): the part is kept, so its id is not reused.
        self._found: dict[tuple[str, int], tuple[Part, tuple[int, int] | None]] = {}

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
        if report is not None:
            return self._aim(act, before, expected, report, through)
        forms: list[Any] = []
        rows = min(len(before), len(after))
        changed = [(r, c) for r in range(rows) if r not in self.clock
                   for c in range(min(len(before[r]), len(after[r]))) if before[r][c] != after[r][c] and c not in self.clock_columns]
        placed = act[0] in self.organs.placed and act[1] is not None and act[2] is not None
        if not changed:
            forms.append(StillForm(act[0], before[act[2]][act[1]] if placed else None))
            return forms
        if len(changed) > BIG_CHANGE:
            return forms
        found, size = [], 0
        for part in parts(changed):
            r0, r1 = min(r for r, _ in part), max(r for r, _ in part)
            c0, c1 = min(c for _, c in part), max(c for _, c in part)
            box = [(r, c) for r in range(r0, r1 + 1) if r not in self.clock for c in range(c0, c1 + 1)
                   if c not in self.clock_columns]
            ring = [(r, c) for r in range(r0 - 1, r1 + 2) if r not in self.clock for c in range(c0 - 1, c1 + 2)
                    if not (r0 <= r <= r1 and c0 <= c <= c1) and c not in self.clock_columns]
            size += len(box)

            def at(r: int, c: int) -> int:
                return before[r][c] if 0 <= r < len(before) and 0 <= c < len(before[r]) else OFF_GRID

            place = None
            if placed and r0 - 1 <= act[2] <= r1 + 1 and c0 - 1 <= act[1] <= c1 + 1:
                place = (r0 - act[2], c0 - act[1])
            # Its rarest colours first: where it does not lie, that is seen soonest.
            seen = {}
            for r, c in box:
                seen[before[r][c]] = seen.get(before[r][c], 0) + 1
            box.sort(key=lambda rc: (seen[before[rc[0]][rc[1]]], rc))
            found.append(Part(lhs=tuple((r - r0, c - c0, before[r][c]) for r, c in box),
                              ring=tuple((r - r0, c - c0, at(r, c)) for r, c in ring),
                              rhs=tuple((r - r0, c - c0, after[r][c]) for r, c in sorted(part)),
                              place=place))
        if size > MAX_REWRITE_CELLS:
            return forms
        forms.append(RewriteForm(act=act[0], placed=placed, parts=tuple(found),
                                 colour=before[act[2]][act[1]] if placed else None))
        return forms

    def _aim(self, act: Act, before: Grid, expected: Grid | None, report: dict, through: tuple = ()) -> list[Any]:
        """What reaching the aim suggests (S4, Plone, 2026-09-28): that this act,
        taken where the same cells lie again, brings it again. The step's last
        grid says nothing of where: the region comes back changed nearly whole (a
        level over, 715 to 2,872 of 4,096 cells in the runs measured). So what
        the act was to change is, for an act that takes a place, the thing it was
        put on; for another, what the region showed last before its last grid —
        the act's doing before the next level came (2026-10-05) — or, where it
        showed nothing between, what the mind expected of the step; with none of
        them, nothing is suggested."""
        placed = act[0] in self.organs.placed and act[1] is not None and act[2] is not None
        if placed:
            x, y = act[1], act[2]
            if not (0 <= y < len(before) and 0 <= x < len(before[y])):
                return []
            cells = self._thing_at(before, x, y)
        else:
            done = through[-1] if through else expected
            if done is None:
                return []
            rows = min(len(before), len(done))
            cells = [(r, c) for r in range(rows) if r not in self.clock
                     for c in range(min(len(before[r]), len(done[r]))) if before[r][c] != done[r][c] and c not in self.clock_columns]
        if not cells or len(cells) > MAX_REWRITE_CELLS:
            return []
        found = []
        for part in parts(cells):
            r0, r1 = min(r for r, _ in part), max(r for r, _ in part)
            c0, c1 = min(c for _, c in part), max(c for _, c in part)

            def at(r: int, c: int) -> int:
                return before[r][c] if 0 <= r < len(before) and 0 <= c < len(before[r]) else OFF_GRID
            box = [(r, c) for r in range(r0, r1 + 1) if r not in self.clock for c in range(c0, c1 + 1)
                   if c not in self.clock_columns]
            ring = [(r, c) for r in range(r0 - 1, r1 + 2) if r not in self.clock for c in range(c0 - 1, c1 + 2)
                    if not (r0 <= r <= r1 and c0 <= c <= c1) and c not in self.clock_columns]
            seen: dict[int, int] = {}
            for r, c in box:
                seen[before[r][c]] = seen.get(before[r][c], 0) + 1
            box.sort(key=lambda rc: (seen[before[rc[0]][rc[1]]], rc))
            place = (r0 - act[2], c0 - act[1]) if placed else None
            found.append(Part(lhs=tuple((r - r0, c - c0, before[r][c]) for r, c in box),
                              ring=tuple((r - r0, c - c0, at(r, c)) for r, c in ring), rhs=(), place=place))
        return [AimForm(act=act[0], placed=placed, parts=tuple(found),
                        colour=before[act[2]][act[1]] if placed else None, status=dict(report))]

    def _thing_at(self, grid: Grid, x: int, y: int) -> list[tuple[int, int]]:
        """The cells of one colour joined side to side to the cell at (x, y)."""
        colour, cells, stack, seen = grid[y][x], [], [(y, x)], {(y, x)}
        while stack and len(cells) <= MAX_REWRITE_CELLS:
            r, c = stack.pop()
            cells.append((r, c))
            for q in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if q not in seen and 0 <= q[0] < len(grid) and 0 <= q[1] < len(grid[q[0]]) \
                        and grid[q[0]][q[1]] == colour:
                    seen.add(q)
                    stack.append(q)
        return cells

    def key(self, form: Any) -> tuple:
        """What a hypothesis says, as one value: two that say the same are one."""
        return form.key

    def scope(self, form: Any, situation_of) -> tuple:
        """Where a hypothesis applies: wherever its act is taken."""
        if isinstance(form, AimForm):
            return ("aim", form.act)
        return ("act", form.act)

    def scopes(self, situation: str, act: Act) -> list[tuple]:
        """The scopes a situation and act fall in."""
        return [("act", act[0]), ("aim", act[0])]

    def predict(self, form: Any, situation: str, state: Grid, act: Act, situation_of) -> Prediction | None:
        if act[0] != form.act:
            return None
        placed = act[0] in self.organs.placed and act[1] is not None and act[2] is not None
        if isinstance(form, AimForm):
            return self._aim_predict(form, placed, situation, state, act)
        if isinstance(form, StillForm):
            if placed != (form.colour is not None):
                return None
            if placed and not (0 <= act[2] < len(state) and 0 <= act[1] < len(state[act[2]])
                               and state[act[2]][act[1]] == form.colour):
                return None
            return Prediction(state=state)
        if placed != form.placed:
            return None
        if placed and not (0 <= act[2] < len(state) and 0 <= act[1] < len(state[act[2]])
                           and state[act[2]][act[1]] == form.colour):
            return None
        corners = {}
        # The parts at the place first: they are one look each.
        for i, part in sorted(enumerate(form.parts), key=lambda ip: ip[1].place is None):
            if part.place is not None:
                corner = (act[2] + part.place[0], act[1] + part.place[1])
                if not self._fits(part.lhs, corner, state):
                    return None
            else:
                corner = self._lies(part, situation, state)
                if corner is None:
                    return None
            corners[i] = corner
        out = [row[:] for row in state]
        for i, part in enumerate(form.parts):
            ar, ac = corners[i]
            for dr, dc, colour in part.rhs:
                r, c = ar + dr, ac + dc
                if 0 <= r < len(out) and 0 <= c < len(out[r]):
                    out[r][c] = colour
        return Prediction(state=out)

    def _aim_predict(self, form: AimForm, placed: bool, situation: str, state: Grid,
                     act: Act) -> Prediction | None:
        """Where every part of an aim hypothesis lies, it says the region will report
        what it reported when the aim came; of the state it says nothing."""
        if placed != form.placed:
            return None
        if placed and not (0 <= act[2] < len(state) and 0 <= act[1] < len(state[act[2]])
                           and state[act[2]][act[1]] == form.colour):
            return None
        for part in form.parts:
            if part.place is not None:
                corner = (act[2] + part.place[0], act[1] + part.place[1])
            else:
                corner = self._lies(part, situation, state)
                if corner is None:
                    return None
            # What lay around it is part of what brought the aim: it must lie so
            # too, not only tell one place from another as in a rewrite.
            if not (self._fits(part.lhs, corner, state) and self._fits(part.ring, corner, state)):
                return None
        return Prediction(state=None, fields=dict(form.status))

    def _fits(self, cells, anchor: tuple[int, int], state: Grid) -> bool:
        ar, ac = anchor
        for dr, dc, colour in cells:
            r, c = ar + dr, ac + dc
            if r in self.clock or c in self.clock_columns:
                continue
            inside = 0 <= r < len(state) and 0 <= c < len(state[r])
            if (state[r][c] if inside else OFF_GRID) != colour:
                return False
        return True

    def _lies(self, part: Part, situation: str, state: Grid) -> tuple[int, int] | None:
        """The one place a part lies on the grid — by its box, or where the box
        lies at several, by its ring; None if nowhere, or it cannot tell which."""
        known = self._found.get((situation, id(part)))
        if known is not None and known[0] is part:
            return known[1]
        lhs = part.lhs
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
        # Sought from its cell of the colour the grid holds fewest of.
        pr, pc, colour = min(lhs, key=lambda cell: len(where.get(cell[2], ())))
        found = [(r - pr, c - pc) for r, c in where.get(colour, ()) if self._fits(lhs, (r - pr, c - pc), state)]
        if len(found) > 1:
            found = [corner for corner in found if self._fits(part.ring, corner, state)]
        corner = found[0] if len(found) == 1 else None
        self._found[(situation, id(part))] = (part, corner)
        return corner

    def describe(self, form: Any, situation_of) -> dict[str, Any]:
        if isinstance(form, StillForm):
            return {"form": "still", "act": form.act, "colour": form.colour}
        if isinstance(form, AimForm):
            return {"form": "aim", "act": form.act, "placed": form.placed, "colour": form.colour,
                    "status": form.status,
                    "parts": [{"from": [list(c) for c in p.lhs], "ring": [list(c) for c in p.ring],
                               "place": list(p.place) if p.place else None} for p in form.parts]}
        return {"form": "rewrite", "act": form.act, "placed": form.placed, "colour": form.colour,
                "parts": [{"from": [list(c) for c in p.lhs], "ring": [list(c) for c in p.ring],
                           "to": [list(c) for c in p.rhs], "place": list(p.place) if p.place else None}
                          for p in form.parts]}

    def keep(self, form: Any, recall: Any) -> None:
        """It computes with no form it said again: the mind's memory holds them."""

    def restore(self, payload: dict[str, Any]) -> Any:
        """A still, rewrite or aim hypothesis from its datum alone."""
        form = payload.get("form")
        if form == "still":
            return StillForm(act=payload["act"], colour=payload["colour"])
        parts_ = tuple(_part(p) for p in payload["parts"])
        if form == "aim":
            return AimForm(act=payload["act"], placed=payload["placed"], parts=parts_, colour=payload["colour"],
                           status=dict(payload["status"]))
        return RewriteForm(act=payload["act"], placed=payload["placed"], parts=parts_, colour=payload["colour"])


def _part(said: dict[str, Any]) -> Part:
    """A part as `describe` said it."""
    return Part(lhs=tuple(tuple(c) for c in said["from"]), ring=tuple(tuple(c) for c in said["ring"]),
                rhs=tuple(tuple(c) for c in said.get("to", ())),
                place=tuple(said["place"]) if said["place"] is not None else None)



__all__ = ["BIG_CHANGE", "CLOCK_CELLS", "CLOCK_KINDS", "CLOCK_TAGS", "CLOCK_WINDOW", "COUNTER_CELLS", "COUNTER_EDGE",
           "COUNTER_TICKS", "MAX_REWRITE_CELLS", "MAX_THING_SHARE", "OFF_GRID", "PART_GAP", "AimForm", "GridInducer",
           "Part", "RewriteForm", "StillForm", "grid_key", "parts", "things"]
