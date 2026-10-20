"""The objects inducer — a model the mind learns with where a state is a grid,
made for playing games: it reads a grid as things, and its hypotheses are laws of
things (Plone, 2026-10-20: an inducer made for playing games, naming no game; the
first of the four directions queued that day).

It began as a copy of the grid inducer (`grid.py` at 9fcaafc), and stands on its own
from there: nothing here is imported from grid, and grid is left as it was — the
submission's model and the paper's. What it does otherwise than grid is said at
the end of this docstring, as it is done.

What follows is grid's own account, as it came with the copy:

The grid inducer — the model the mind learns with where a state is a grid.

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

Once the aim has first come — what the region is for now shown it — it reads
what an act that takes no place does as things that move, too (A, 2026-10-08;
before that, it suggests only the above, so what the mind does before its first
aim is as it was):

- **Move** — "this act moves what lies as this pattern by (rows, columns) — as
  another pattern, if it turns as it goes — and what it leaves takes the colour
  `trail`": what changed, read as the things that touched it, as many cells of
  the same colours before and after. It applies where the pattern lies once,
  and only where the cells it moves into are of `trail`.
- **Block** — "this act does not move that pattern where what lies in its way
  is of these colours (or the grid's edge)": an act that changed nothing, read
  against the moves it suggested of that act (had back from the mind's memory).
- **Into** — "an act brings the aim where its move takes a thing of these
  colours into a cell of those": with each aim, for an act that takes no place, from the move that brought it — a relation, of no one act and
  no one layout: any act whose move it holds takes the thing there.

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
# A thing a move is read from is no larger than this: what is larger is the
# ground or a wall. DECLARED, a bound on work.
MAX_MOVE_CELLS: Final = 256
# How many of an act's moves a blocked step is read against, the latest first.
# DECLARED, a bound on work.
MOVES_KEPT: Final = 4


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
    after: tuple[tuple[int, int, int], ...] | None = None

    @property
    def came(self) -> tuple[tuple[int, int, int], ...]:
        return self.after if self.after is not None else self.pattern

    @property
    def key(self) -> tuple:
        return ("move", self.act, self.pattern, self.dr, self.dc, self.trail, self.after)


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


@dataclass(eq=False)
class IntoForm:
    """An act brings the aim where its move takes a thing of the colours `mover`
    (each cell's, sorted), leaving `trail`, into a cell of one of `colours`: the
    region then reports `status`. Of no one act."""

    mover: tuple[int, ...]
    trail: int
    colours: frozenset[int]
    status: dict

    @property
    def key(self) -> tuple:
        return ("into", self.mover, self.trail, self.colours)


def _mover(form: Any) -> tuple[int, ...]:
    return tuple(sorted(v for _, _, v in form.pattern))


class ObjectsInducer:
    """Still, rewrite and aim hypotheses, over its reading of grids."""

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
        # (situation, part) -> (the part, where it lies): the part is kept, so its id is not reused.
        self._found: dict[tuple[str, int], tuple[Part, tuple[int, int] | None]] = {}
        # Whether the aim has come: from then it reads things as moving, too.
        self._aimed = False
        # Each act's moves it suggested, had back from the mind's memory (`keep`).
        self._moves_of: dict[int, list[Any]] = {}
        # (situation, move or block) -> (the form, where its pattern lies once, or None).
        self._lying: dict[tuple[str, int], tuple[Any, tuple[int, int] | None]] = {}

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
        if self.organs.restarts(step.act) \
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

    def unlike(self, expected: Grid, came: Grid) -> frozenset[tuple[int, int]] | None:
        """The cells, off the clock, where what came differs from what was expected."""
        cells = frozenset((r, c) for r in range(min(len(expected), len(came))) if r not in self.clock
                          for c in range(min(len(expected[r]), len(came[r])))
                          if c not in self.clock_columns and expected[r][c] != came[r][c])
        return cells or None

    def at(self, act: Act, state: Grid, where: Any) -> bool:
        """An act that takes a place lies there when the thing it is put on touches
        those cells (or is next to them); one that takes no place, nowhere."""
        if not where or act[0] not in self.organs.placed or act[1] is None or act[2] is None:
            return False
        x, y = act[1], act[2]
        if not (0 <= y < len(state) and 0 <= x < len(state[y])):
            return False
        thing = self._thing_at(state, x, y)
        return any((r + dr, c + dc) in where for r, c in thing for dr, dc in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)))

    def as_read(self, state: Grid) -> list[list[int | None]]:
        """A grid as it reads it: the clock's rows and columns left out (None)."""
        return [[None if r in self.clock or c in self.clock_columns else v for c, v in enumerate(row)]
                for r, row in enumerate(state)]

    def coarse(self, kind: tuple) -> tuple | None:
        """The coarser kind a kind falls in, read first: putting an act on a thing
        of a colour, whatever its size. None for a kind with none."""
        return kind[:2] if kind[0] == "click" and len(kind) > 2 else None

    def candidates(self, situation: str, state: Grid, offers: tuple[int, ...]) -> list[tuple[Act, tuple]]:
        """The acts it can take in a state, each with its kind: an act, or for an
        act that takes a place, the colour and size of the thing it is put on."""
        out: list[tuple[Act, tuple]] = []
        for a in sorted(offers):
            if self.organs.restarts((a, None, None)):
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

    def consider(self, situation: str, state: Grid) -> None:
        """Asked while the body waits: it reads every state's things as it meets it
        (`candidates`), so there is nothing more to consider."""
        return None

    def hold_aim(self, aim: dict[str, Any]) -> None:
        """The aim the mind holds: it computes the same whatever it is for."""

    def induce(self, source: str, act: Act, before: Grid, after: Grid, *, foreseen: bool = False,
               evidence: tuple = (), report: dict | None = None, expected: Grid | None = None,
               through: tuple = ()) -> list[Any]:
        if report is not None:
            self._aimed = True
            return self._aim(act, before, expected, report, through)
        forms = self._rewrite(act, before, after)
        placed = act[0] in self.organs.placed and act[1] is not None and act[2] is not None
        if self._aimed and not placed and not self.organs.restarts(act):
            changed = [(r, c) for r in range(min(len(before), len(after))) if r not in self.clock
                       for c in range(min(len(before[r]), len(after[r])))
                       if c not in self.clock_columns and before[r][c] != after[r][c]]
            forms += self._blocked(act[0], before) if not changed else self._moved(act[0], before, after, changed)
        return forms

    def _rewrite(self, act: Act, before: Grid, after: Grid) -> list[Any]:
        """A still or a rewrite (the module's docstring)."""
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
        aims: list[Any] = [AimForm(act=act[0], placed=placed, parts=tuple(found),
                                   colour=before[act[2]][act[1]] if placed else None, status=dict(report))]
        if not placed:
            aims += self._into(act[0], before, done, cells, report)
        return aims

    def _into(self, act: int, before: Grid, done: Grid, changed: list[tuple[int, int]],
              report: dict) -> list[Any]:
        """The move that brought the aim — read from the step, or of this act's
        moves (had back from the mind's memory) the one whose pattern lies here
        once — and the colours of the cells it moved into: an into aim."""
        tries = [self._move_read(act, before, done, changed)]
        situation = self.situation(before)
        for recall in reversed(self._moves_of.get(act, [])[-MOVES_KEPT:]):
            form = recall()
            corner = self._lies_once(form, situation, before)
            if corner is not None:
                tries.append((form, corner))
        for found in tries:
            if found is None:
                continue
            form, corner = found
            own = {(corner[0] + r, corner[1] + c) for r, c, _ in form.pattern}
            went = {(corner[0] + r + form.dr, corner[1] + c + form.dc) for r, c, _ in form.came}
            colours = {before[r][c] for r, c in went - own
                       if 0 <= r < len(before) and 0 <= c < len(before[r]) and before[r][c] != form.trail}
            if colours:
                return [IntoForm(mover=_mover(form), trail=form.trail, colours=frozenset(colours),
                                 status=dict(report))]
        return []

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
        if isinstance(form, IntoForm):
            return ("into",)
        if isinstance(form, AimForm):
            return ("aim", form.act)
        return ("act", form.act)

    def scopes(self, situation: str, act: Act) -> list[tuple]:
        """The scopes a situation and act fall in."""
        return [("act", act[0]), ("aim", act[0]), ("into",)]

    def predict(self, form: Any, situation: str, state: Grid, act: Act, situation_of) -> Prediction | None:
        placed = act[0] in self.organs.placed and act[1] is not None and act[2] is not None
        if isinstance(form, IntoForm):
            return None if placed else self._into_predict(form, situation, state, act[0])
        if act[0] != form.act:
            return None
        if isinstance(form, AimForm):
            return self._aim_predict(form, placed, situation, state, act)
        if isinstance(form, (MoveForm, BlockForm)):
            return None if placed else self._move_predict(form, situation, state)
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
        if isinstance(form, IntoForm):
            return {"form": "into", "mover": list(form.mover), "trail": form.trail,
                    "colours": sorted(form.colours), "status": form.status}
        if isinstance(form, (MoveForm, BlockForm)):
            said = {"form": "move" if isinstance(form, MoveForm) else "block", "act": form.act,
                    "pattern": [list(c) for c in form.pattern], "dr": form.dr, "dc": form.dc, "trail": form.trail}
            if form.after is not None:
                said["after"] = [list(c) for c in form.after]
            if isinstance(form, BlockForm):
                said["blockers"] = sorted(form.blockers)
            return said
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
        """A move it said is had back from the mind's memory when a blocked step is
        read against it; no other form is computed with again."""
        if isinstance(form, MoveForm):
            self._moves_of.setdefault(form.act, []).append(recall)

    # ── things that move (once the aim has come) ──

    def _moved(self, act: int, before: Grid, after: Grid, changed: list[tuple[int, int]]) -> list[Any]:
        """A move, if what changed reads as one."""
        found = self._move_read(act, before, after, changed)
        return [found[0]] if found is not None else []

    def _move_read(self, act: int, before: Grid, after: Grid,
                   changed: list[tuple[int, int]]) -> tuple[Any, tuple[int, int]] | None:
        """The move what changed reads as — things of as many cells, of the same
        colours, after as before, shifted, turned, or both — and where its
        pattern lay; tried with each colour what changed most became, as what a
        thing leaves."""
        if not changed or len(changed) > 2 * MAX_MOVE_CELLS:
            return None
        became: dict[int, int] = {}
        for r, c in changed:
            became[after[r][c]] = became.get(after[r][c], 0) + 1
        for trail in sorted(became, key=lambda v: -became[v])[:3]:
            was, now = self._touching(before, changed, trail), self._touching(after, changed, trail)
            if not was or not now:
                continue
            # What it moved onto and took the place of is gone after: only the
            # colours both hold are what moved.
            both = {before[r][c] for r, c in was} & {after[r][c] for r, c in now}
            was = [(r, c) for r, c in was if before[r][c] in both]
            now = [(r, c) for r, c in now if after[r][c] in both]
            if not was or len(was) != len(now):
                continue
            p, r0, c0 = _pattern(before, was)
            q, r1, c1 = _pattern(after, now)
            if sorted(v for _, _, v in p) != sorted(v for _, _, v in q) or (p == q and (r1, c1) == (r0, c0)):
                continue
            return MoveForm(act=act, pattern=p, dr=r1 - r0, dc=c1 - c0, trail=trail,
                            after=q if q != p else None), (r0, c0)
        return None

    def _blocked(self, act: int, before: Grid) -> list[Any]:
        """A block, if a move it suggested of this act before finds its pattern
        here once, and what lies in its way is of no colour `trail`."""
        situation = self.situation(before)
        for recall in reversed(self._moves_of.get(act, [])[-MOVES_KEPT:]):
            form = recall()
            corner = self._lies_once(form, situation, before)
            if corner is None:
                continue
            blockers = self._in_the_way(form, corner, before)
            if blockers:
                return [BlockForm(act=act, pattern=form.pattern, dr=form.dr, dc=form.dc, trail=form.trail,
                                  blockers=frozenset(blockers), after=form.after)]
        return []

    def _thing_cells(self, grid: Grid, start: tuple[int, int], seen: set) -> list[tuple[int, int]] | None:
        """The cells of one colour joined side to side to `start`, off the clock;
        None when larger than MAX_MOVE_CELLS (a ground, or a wall)."""
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
        """The cells of the things that touch what changed, of no colour `trail`;
        None when one is too large to be a thing."""
        seen: set = set()
        out: list[tuple[int, int]] = []
        for cell in changed:
            if cell in seen or grid[cell[0]][cell[1]] == trail:
                continue
            thing = self._thing_cells(grid, cell, seen)
            if thing is None:
                return None
            out += thing
        return out

    def _in_the_way(self, form: Any, corner: tuple[int, int], state: Grid) -> set[int]:
        """The colours, other than `trail`, of the cells the pattern would move
        into and does not stand on now (OFF_GRID past the edge)."""
        own = {(corner[0] + r, corner[1] + c) for r, c, _ in form.pattern}
        out: set[int] = set()
        for r, c, _ in form.came:
            rr, cc = corner[0] + r + form.dr, corner[1] + c + form.dc
            if (rr, cc) in own:
                continue
            if not (0 <= rr < len(state) and 0 <= cc < len(state[rr])):
                out.add(OFF_GRID)
            elif rr in self.clock or cc in self.clock_columns:
                continue
            elif state[rr][cc] != form.trail:
                out.add(state[rr][cc])
        return out

    def _lies_once(self, form: Any, situation: str, state: Grid) -> tuple[int, int] | None:
        """The one place a form's pattern lies, off the clock; None if nowhere or
        at several."""
        known = self._lying.get((situation, id(form)))
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
        self._lying[(situation, id(form))] = (form, corner)
        return corner

    def _into_predict(self, form: IntoForm, situation: str, state: Grid, act: int) -> Prediction | None:
        """The aim, if this act's move — of its moves had back from the mind's
        memory, the latest of the into's thing whose pattern lies here once —
        takes the thing into a cell of the into's colours."""
        for recall in reversed(self._moves_of.get(act, [])[-MOVES_KEPT:]):
            move = recall()
            if move.trail != form.trail or _mover(move) != form.mover:
                continue
            corner = self._lies_once(move, situation, state)
            if corner is None:
                continue
            own = {(corner[0] + r, corner[1] + c) for r, c, _ in move.pattern}
            for r, c, _ in move.came:
                rr, cc = corner[0] + r + move.dr, corner[1] + c + move.dc
                if (rr, cc) not in own and 0 <= rr < len(state) and 0 <= cc < len(state[rr]) \
                        and state[rr][cc] in form.colours:
                    return Prediction(state=None, fields=dict(form.status))
            return None
        return None

    def _move_predict(self, form: Any, situation: str, state: Grid) -> Prediction | None:
        """A block: nothing changes where what is in the way is of its colours. A
        move: the pattern moved, where nothing is in its way."""
        corner = self._lies_once(form, situation, state)
        if corner is None:
            return None
        in_the_way = self._in_the_way(form, corner, state)
        if isinstance(form, BlockForm):
            return Prediction(state=state) if in_the_way & form.blockers else None
        if in_the_way:
            return None
        out = [row[:] for row in state]
        for r, c, _ in form.pattern:
            out[corner[0] + r][corner[1] + c] = form.trail
        for r, c, v in form.came:
            out[corner[0] + r + form.dr][corner[1] + c + form.dc] = v
        return Prediction(state=out)

    def restore(self, payload: dict[str, Any]) -> Any:
        """A still, rewrite or aim hypothesis from its datum alone."""
        form = payload.get("form")
        if form == "still":
            return StillForm(act=payload["act"], colour=payload["colour"])
        if form == "into":
            return IntoForm(mover=tuple(payload["mover"]), trail=payload["trail"],
                            colours=frozenset(payload["colours"]), status=dict(payload["status"]))
        if form in ("move", "block"):
            pattern = tuple(tuple(c) for c in payload["pattern"])
            after = tuple(tuple(c) for c in payload["after"]) if payload.get("after") is not None else None
            if form == "block":
                return BlockForm(act=payload["act"], pattern=pattern, dr=payload["dr"], dc=payload["dc"],
                                 trail=payload["trail"], blockers=frozenset(payload["blockers"]), after=after)
            return MoveForm(act=payload["act"], pattern=pattern, dr=payload["dr"], dc=payload["dc"],
                            trail=payload["trail"], after=after)
        parts_ = tuple(_part(p) for p in payload["parts"])
        if form == "aim":
            return AimForm(act=payload["act"], placed=payload["placed"], parts=parts_, colour=payload["colour"],
                           status=dict(payload["status"]))
        return RewriteForm(act=payload["act"], placed=payload["placed"], parts=parts_, colour=payload["colour"])


def _pattern(grid: Grid, cells: list[tuple[int, int]]) -> tuple[tuple[tuple[int, int, int], ...], int, int]:
    """Cells as a pattern from their corner, and the corner."""
    r0, c0 = min(r for r, _ in cells), min(c for _, c in cells)
    return tuple(sorted((r - r0, c - c0, grid[r][c]) for r, c in cells)), r0, c0


def _part(said: dict[str, Any]) -> Part:
    """A part as `describe` said it."""
    return Part(lhs=tuple(tuple(c) for c in said["from"]), ring=tuple(tuple(c) for c in said["ring"]),
                rhs=tuple(tuple(c) for c in said.get("to", ())),
                place=tuple(said["place"]) if said["place"] is not None else None)



__all__ = ["BIG_CHANGE", "CLOCK_CELLS", "CLOCK_KINDS", "CLOCK_TAGS", "CLOCK_WINDOW", "COUNTER_CELLS", "COUNTER_EDGE",
           "COUNTER_TICKS", "MAX_REWRITE_CELLS", "MAX_THING_SHARE", "OFF_GRID", "PART_GAP", "AimForm", "ObjectsInducer",
           "BlockForm", "IntoForm", "MAX_MOVE_CELLS", "MOVES_KEPT", "MoveForm", "Part", "RewriteForm", "StillForm", "grid_key", "parts", "things"]
