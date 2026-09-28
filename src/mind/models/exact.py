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
  middle — at most MAX_CLICK_TARGETS, smallest first, none larger than
  MAX_THING_SHARE of the grid (that large is taken for the ground). They are
  where an act that takes a place may be put.
- **The clock.** A row that changed in every one of the last CLOCK_WINDOW steps,
  under CLOCK_KINDS kinds of act or more, by no more than CLOCK_CELLS cells each
  time, is a clock the region keeps whatever is done — a bar that counts steps
  (ls20's rows 61-62, vc33's row 0; LOG.md) — not where it stands. Two grids are
  one situation when they agree off the clock. The clock only grows; when it
  does, every situation is read again under it. The clock is not predicted.
"""

from __future__ import annotations

import hashlib
from collections import deque
from dataclasses import dataclass
from typing import Any, Final

from ..organs import Act, Organs, Step

Grid = list[list[int]]

CLOCK_TAGS: Final = {"domain": "mind", "kind": "clock", "object": "frame", "source": "mind"}

# What an act that takes a place may be put on. DECLARED, not measured.
MAX_CLICK_TARGETS: Final = 64
MAX_THING_SHARE: Final = 0.5
# The clock. DECLARED, not measured: on ls20 a looser rule took the rows a moving
# piece crossed for the clock (LOG.md).
CLOCK_WINDOW: Final = 6
CLOCK_KINDS: Final = 3
CLOCK_CELLS: Final = 2
BIG_CHANGE: Final = 64 * 64 // 4


def grid_key(grid: Grid, clock: frozenset[int] = frozenset()) -> str:
    """A grid's identity: two grids are one situation when every cell off the
    clock's rows is the same."""
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
        self.clock: frozenset[int] = frozenset()
        self._recent: deque = deque(maxlen=CLOCK_WINDOW)   # (kind, rows changed) per step
        self._things: dict[str, list[tuple[int, int, int, int]]] = {}

    # ── perception ──

    def identity(self, state: Grid) -> str:
        """A state's own identity, as it came."""
        return grid_key(state)

    def situation(self, state: Grid) -> str:
        """Where the region stands in a state, read by its perception now."""
        return grid_key(state, self.clock)

    def perceive(self, step: Step, kind: tuple) -> Perceived | None:
        """What its perception learns from a step: the clock, when it grows."""
        before, after = step.before, step.after
        per_row = {r: sum(1 for a, b in zip(before[r], after[r]) if a != b)
                   for r in range(min(len(before), len(after))) if before[r] != after[r]}
        if step.act == self.organs.reset or step.act[0] == self.organs.reset[0] \
                or sum(per_row.values()) > BIG_CHANGE:
            return None
        self._recent.append((kind, frozenset(r for r, n in per_row.items() if n <= CLOCK_CELLS)))
        if len(self._recent) < CLOCK_WINDOW or len({k for k, _ in self._recent}) < CLOCK_KINDS:
            return None
        always = frozenset.intersection(*(r for _, r in self._recent))
        if not always or always <= self.clock:
            return None
        self.clock = self.clock | always
        self._things = {}
        return Perceived(payload={"rows": sorted(self.clock)}, tags=dict(CLOCK_TAGS))

    # ── what can be done ──

    def learnable(self, act: Act) -> Act:
        """An act as it is learned: the place kept only for an act that takes one."""
        return act if act[0] in self.organs.placed else (act[0], None, None)

    def default_kind(self, act: Act) -> tuple:
        return ("act", act[0])

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

    def induce(self, source: str, act: Act, before: Grid, after: Grid) -> list[ExactForm]:
        """What one experience suggests: that it will happen again, exactly."""
        return [ExactForm(source=source, act=act, to=after)]

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


__all__ = ["BIG_CHANGE", "CLOCK_CELLS", "CLOCK_KINDS", "CLOCK_TAGS", "CLOCK_WINDOW", "MAX_CLICK_TARGETS",
           "MAX_THING_SHARE", "ExactForm", "ExactInducer", "Perceived", "Prediction", "grid_key", "things"]
