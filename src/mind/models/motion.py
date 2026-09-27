"""How the learning model reads motion in a grid — its own perception, declared.

A thing that moves is a set of cells that turn up, all of them, a fixed
displacement away: what was at p before is at p + d after, and what was under it
is uncovered. That is read from one step alone, whatever the thing is made of
(ls20's piece is two colours, and moves five cells a step; LOG.md), and it names
no game. From it the model knows, for an act that moves something, by how much;
what the moving thing looks like; the ground it moves on; and, when the act moved
nothing, what stood where it would have gone — what blocks it. With that it can
imagine where an act would take the thing from anywhere, and search the places
it has not been before it goes there.

DECLARED, not measured: how far a displacement is looked for (MAX_SHIFT), how
much of what changed it must explain (MIN_COVER), how many changed cells are too
many to read as a thing moving (MAX_CHANGED), and — since a thing moving one way
reads, cell for cell, as its ground moving the other — that the thing is what
is rare on the grid and the ground what is common.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from typing import Callable, Final

Grid = list[list[int]]
Cell = tuple[int, int]

MAX_SHIFT: Final = 12
MIN_COVER: Final = 0.8
MAX_CHANGED: Final = 600
# How far the model searches the places it imagines. DECLARED: a bound on work.
MAX_PLACES: Final = 4096


@dataclass(frozen=True)
class Shift:
    """A thing that moved in one step: by how much, what it looks like after (its
    cells relative to its top-left, with their colours), where it is, and the
    ground it uncovered."""

    by: tuple[int, int]
    pattern: tuple[tuple[int, int, int], ...]   # (dr, dc, colour)
    at: Cell                                     # its top-left after the step
    ground: int


def changed(before: Grid, after: Grid, clock: frozenset[int]) -> list[Cell]:
    return [(r, c) for r in range(min(len(before), len(after))) if r not in clock and before[r] != after[r]
            for c in range(min(len(before[r]), len(after[r]))) if before[r][c] != after[r][c]]


def find_shift(before: Grid, after: Grid, clock: frozenset[int]) -> Shift | None:
    """The one displacement that explains what changed, if one does."""
    ch = changed(before, after, clock)
    if not ch or len(ch) > MAX_CHANGED:
        return None
    rows, cols = len(after), len(after[0]) if after else 0
    chs = set(ch)
    found: list[tuple[int, tuple[int, int], list[Cell]]] = []
    for dy in range(-MAX_SHIFT, MAX_SHIFT + 1):
        for dx in range(-MAX_SHIFT, MAX_SHIFT + 1):
            if not dy and not dx:
                continue
            src = [(r, c) for r, c in ch
                   if 0 <= r + dy < rows and 0 <= c + dx < cols and (r + dy, c + dx) in chs
                   and after[r + dy][c + dx] == before[r][c]]
            if src:
                found.append((len(src), (dy, dx), src))
    if not found:
        return None
    most = max(n for n, _, _ in found)
    # A thing moving one way reads, cell for cell, as its ground moving the other:
    # the thing is what is rare on the grid, the ground what is common.
    freq = Counter(v for row in before for v in row)
    _, (dy, dx), src = min((f for f in found if f[0] == most),
                           key=lambda f: (sum(freq[before[r][c]] for r, c in f[2]) / len(f[2]), f[1]))
    dst = {(r + dy, c + dx) for r, c in src}
    if len(set(src) | dst) < MIN_COVER * len(ch):
        return None
    uncovered = [after[r][c] for r, c in src if (r, c) not in dst]
    ground = Counter(uncovered).most_common(1)[0][0] if uncovered else after[src[0][0]][src[0][1]]
    top, left = min(r for r, _ in dst), min(c for _, c in dst)
    pattern = tuple(sorted((r - top, c - left, after[r][c]) for r, c in dst))
    return Shift(by=(dy, dx), pattern=pattern, at=(top, left), ground=ground)


def locate(grid: Grid, pattern: tuple[tuple[int, int, int], ...], near: Cell | None = None) -> Cell | None:
    """Where the thing is in a grid: a top-left at which every cell of its pattern
    matches — the nearest to `near` when there are several."""
    if not pattern:
        return None
    rows, cols = len(grid), len(grid[0]) if grid else 0
    h = max(dr for dr, _, _ in pattern) + 1
    w = max(dc for _, dc, _ in pattern) + 1
    first = pattern[0]
    found = []
    for r in range(rows - h + 1):
        row = grid[r + first[0]]
        for c in range(cols - w + 1):
            if row[c + first[1]] == first[2] and all(grid[r + dr][c + dc] == v for dr, dc, v in pattern):
                found.append((r, c))
    if not found:
        return None
    if near is None:
        return found[0]
    return min(found, key=lambda p: (abs(p[0] - near[0]) + abs(p[1] - near[1]), p))


def cells_at(pattern: tuple[tuple[int, int, int], ...], at: Cell) -> dict[Cell, int]:
    return {(at[0] + dr, at[1] + dc): v for dr, dc, v in pattern}


def blocked_by(grid: Grid, pattern, at: Cell, by: tuple[int, int], ground: int) -> tuple[bool, set[int]]:
    """Whether the thing, moved by `by` from `at`, would leave the grid; and the
    colours, other than the ground, it would move onto."""
    rows, cols = len(grid), len(grid[0]) if grid else 0
    own = cells_at(pattern, at)
    onto: set[int] = set()
    for (r, c) in own:
        q = (r + by[0], c + by[1])
        if not (0 <= q[0] < rows and 0 <= q[1] < cols):
            return True, set()
        if q not in own and grid[q[0]][q[1]] != ground:
            onto.add(grid[q[0]][q[1]])
    return False, onto


def imagine(grid: Grid, pattern, at: Cell, by: tuple[int, int], ground: int) -> Grid:
    """The grid with the thing moved: the ground where it was, the thing where it goes."""
    out = [row[:] for row in grid]
    for (r, c) in cells_at(pattern, at):
        out[r][c] = ground
    for (r, c), v in cells_at(pattern, (at[0] + by[0], at[1] + by[1])).items():
        out[r][c] = v
    return out


def search(grid: Grid, pattern, start: Cell, moves: dict[int, tuple[int, int]], ground: int,
           blocks: set[int], goal: Callable[[Cell, set[int]], bool],
           stuck: set[tuple[Cell, int]] | frozenset = frozenset()) -> list[int] | None:
    """The shortest sequence of acts that the model imagines takes the thing from
    `start` to a place `goal` holds of — `goal` is told the place and the
    colours it would move onto to get there. The grid is taken as it stands, the
    thing lifted off it; a move onto a colour that blocks, off the grid, or one
    `stuck` says moved nothing from that place, is not taken. None when no place
    it can imagine reaching will do."""
    rows, cols = len(grid), len(grid[0]) if grid else 0
    base = [row[:] for row in grid]
    for (r, c) in cells_at(pattern, start):
        base[r][c] = ground
    prev: dict[Cell, tuple[Cell, int] | None] = {start: None}
    queue = deque([start])
    while queue and len(prev) < MAX_PLACES:
        at = queue.popleft()
        for act, by in sorted(moves.items()):
            nxt = (at[0] + by[0], at[1] + by[1])
            if nxt in prev or (at, act) in stuck:
                continue
            out, onto = False, set()
            for dr, dc, _ in pattern:
                r, c = nxt[0] + dr, nxt[1] + dc
                if not (0 <= r < rows and 0 <= c < cols):
                    out = True
                    break
                if base[r][c] != ground:
                    onto.add(base[r][c])
            if out or onto & blocks:
                continue
            prev[nxt] = (at, act)
            if goal(nxt, onto):
                path = []
                node = nxt
                while prev[node] is not None:
                    node, a = prev[node][0], prev[node][1]
                    path.append(a)
                return path[::-1]
            if not onto:
                queue.append(nxt)  # onto something new, it stops there: what happens next is unknown
    return None


__all__ = ["MAX_CHANGED", "MAX_PLACES", "MAX_SHIFT", "MIN_COVER", "Shift", "blocked_by", "cells_at", "changed",
           "find_shift", "imagine", "locate", "search"]
