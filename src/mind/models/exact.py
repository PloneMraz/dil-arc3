"""The exact inducer — a model the mind learns with: the part of it that computes,
with no trained weights (Plone, 2026-09-28: learning is the mind's; a model is
its replaceable computing).

What the mind asks of an inducer is computing, never the learning itself:

- **perception** — what a state is to it (its own identity, and where the region
  stands, read off it), and what its perception learns from a step (here, the
  clock a region keeps whatever is done);
- **what can be done** — the acts it can take in a state, each with its kind;
- **hypotheses** — what an experience suggests (`induce`), and what a hypothesis
  predicts in a situation for an act (`predict`), and how it is said as data
  (`describe`).

The mind holds the experiences, holds the hypotheses as data, weighs them against
the store, keeps or drops them, expects, is curious, chooses (`mind/learning.py`).

THIS INDUCER'S HYPOTHESES ARE EXACT: "from this situation, this act gives that
situation, and the region reports this of itself" — one per experience, applying
nowhere but where it was met. It generalises nothing. It is the reference the
others are measured against.

ITS PERCEPTION OF A GRID — declared, not measured, naming no game:

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
  r11l's mark of what is chosen — is not one (2026-10-04). Or a row or a column that, in every one of those
  steps, whatever the act, changed by 1 to CLOCK_CELLS cells, each time the same
  way and next to the cells it changed the step before. Or a row or a column within COUNTER_EDGE lines of
  the grid's edge whose last COUNTER_TICKS changes — the steps it changed in,
  not every step: a bar may count only some acts — were each of 1 to
  COUNTER_CELLS cells, all the same way (one colour into one other), each next
  to the cells of the change before: a bar growing or shrinking at the edge
  (Plone, 2026-09-29; every public game draws one, by a public notebook's survey
  — LOG.md, 2026-10-04). A thing that moves along a line changes it two ways
  (its colour into the ground's, and back), so it is not taken for one. Two grids are one situation when they
  agree off the clock's rows and columns. The clock only grows; when it does,
  every situation is read again under it. The clock is not predicted.
"""

from __future__ import annotations

import hashlib
from collections import deque
from dataclasses import dataclass
from typing import Any, Final

from ..organs import Act, Organs, Step

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


@dataclass(frozen=True)
class Perceived:
    """What its perception learned from a step: a datum to write, and that every
    situation must be read again."""

    payload: dict[str, Any]
    tags: dict[str, str]


@dataclass(eq=False)
class ExactForm:
    """An exact hypothesis: from the situation of `source`, `act` gives the grid
    `to`, and the region reports `status` (learned when its report comes)."""

    source: str
    act: Act
    to: Grid
    status: dict[str, Any] | None = None
    # It applies at one situation only: the mind indexes it there.
    situated: bool = True


@dataclass(frozen=True)
class Prediction:
    """What a hypothesis says will come back."""

    state: Any
    fields: dict[str, Any] | None = None


class ExactInducer:
    """Exact hypotheses, over a grid's perception."""

    kind = "exact"
    # Its hypotheses apply where they were met and nowhere else.
    general = False

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

    # ── perception ──

    def identity(self, state: Grid) -> str:
        """A state's own identity, as it came."""
        return grid_key(state)

    def situation(self, state: Grid) -> str:
        """Where the region stands in a state, read by its perception now."""
        return grid_key(state, self.clock, self.clock_columns)

    def perceive(self, step: Step, kind: tuple) -> Perceived | None:
        """What its perception learns from a step: the clock, when it grows."""
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
        self._things, self._masks = {}, {}
        payload: dict[str, Any] = {"rows": sorted(self.clock)}
        if self.clock_columns:
            payload["columns"] = sorted(self.clock_columns)
        return Perceived(payload=payload, tags=dict(CLOCK_TAGS))

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

    def reported(self, form: Any, said: dict[str, Any]) -> None:
        """What the region reported the first time a hypothesis's step was met: a
        form that says what the region reports takes it."""
        if hasattr(form, "status"):
            form.status = said

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

    def induce(self, source: str, act: Act, before: Grid, after: Grid, *, foreseen: bool = False,
               evidence: tuple = (), report: dict | None = None, expected: Grid | None = None,
               through: tuple = ()) -> list[ExactForm]:
        """What one experience suggests: that it will happen again, exactly. It
        costs nothing, so whether the step was foreseen, and the steps before it,
        change nothing here. Asked again when the aim came (`report`), it has
        nothing more to say: its exact hypothesis takes the report as it comes."""
        if report is not None:
            return []
        return [ExactForm(source=source, act=act, to=after)]

    def said(self) -> list[Perceived]:
        """What it said in computing, to be kept whole as data: nothing — it says
        nothing but its hypotheses."""
        return []

    def receive_prior(self, name: str, payload: Any) -> None:
        """A prior the mind recalled: it reads no words."""

    def hold_aim(self, aim: dict[str, Any]) -> None:
        """The aim the mind holds: it computes the same whatever it is for."""

    def key(self, form: ExactForm) -> tuple:
        """What a hypothesis says, as one value: two that say the same are one."""
        return ("exact", form.source, form.act, grid_key(form.to))

    def scope(self, form: ExactForm, situation_of) -> tuple:
        """Where a hypothesis applies: the situation it was met in, and its act."""
        return ("at", situation_of(form.source), form.act)

    def scopes(self, situation: str, act: Act) -> list[tuple]:
        """The scopes a situation and act fall in."""
        return [("at", situation, act)]

    def predict(self, form: ExactForm, situation: str, state: Grid, act: Act, situation_of) -> Prediction | None:
        """What an exact hypothesis predicts: what came, where and when it came."""
        if act != form.act or situation_of(form.source) != situation:
            return None
        return Prediction(state=form.to)

    def fields(self, form: ExactForm) -> dict[str, Any] | None:
        """What it says the region will report of itself: what it reported then."""
        return form.status

    def describe(self, form: ExactForm, situation_of) -> dict[str, Any]:
        source = situation_of(form.source)
        to = self.situation(form.to)
        return {"from": source, "act": list(form.act), "to": to, "changed": to != source, "status": form.status}

    def keep(self, form: Any, recall: Any) -> None:
        """It computes with no form it said again: the mind's memory holds them."""

    def restore(self, payload: dict[str, Any], step: Step) -> ExactForm:
        """An exact hypothesis from its datum, which names situations only: the
        state it came from and the grid it says comes are the step's."""
        return ExactForm(source=self.identity(step.before), act=tuple(payload["act"]), to=step.after,
                         status=payload.get("status"))


__all__ = ["BIG_CHANGE", "PART_GAP", "parts", "CLOCK_CELLS", "CLOCK_KINDS", "CLOCK_TAGS", "CLOCK_WINDOW", "COUNTER_CELLS", "COUNTER_EDGE",
           "COUNTER_TICKS", "MAX_THING_SHARE", "ExactForm", "ExactInducer", "Perceived", "Prediction", "grid_key", "things"]
