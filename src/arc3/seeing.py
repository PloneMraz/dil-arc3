"""Seeing individuals — the mind's perceptual stage, with memory.

`perceive.py` finds pieces in one frame. This follows them from frame to frame,
learns which pieces are parts of one thing, and reads, for each thing, what lies
ahead of it on every side. It is the mind's sensing, not the body's: the body
receives the grid and carries what this makes of it inward, the way a nerve
carries what the eye has already processed.

WHY INDIVIDUALS, AND NOT STUFF. Identity used to be a kind of stuff — every cell
of value 9 was one Other — chosen by measurement because it held churn at 1.0x.
It had a declared cost, and a later measurement found where the cost fell. In
`ls20` value 9 is FIVE separate pieces, one of which moves. Any reading of what
surrounds "thing:9" is the union over all five, so the four that never move
swamp the one that does, and whether the mover is about to be blocked becomes
unreadable. Curiosity then fixed on exactly the action whose outcome depended on
that, and never left it.

Tracked piece by piece, the picture changes (316 real transitions):

    identity                     churn   prediction ls20   prediction vc33
    stuff (value)                1.0x         93%               85%
    tracked piece, what's ahead  1.5x         98%               94%

The leading part of the moving object is then predicted 100% under the action
that moves it: it can see the wall.

WHY PIECES ARE GROUPED BY COMMON FATE. The same measurement found the trailing
part at 67%, and why: the object is drawn in two colours, segmentation splits it
in two, and a ray cast from the back part stops at its own front part and never
sees the wall. Pieces that keep moving together, by the same displacement, are
parts of one thing — a grouping read off what they DO, learned from the agent's
own observations and never configured.

ORDER, AND WHY IT IS INV-8. Grouping learns from how pieces moved; the situation
a thing is read in is used to predict how it will move. If this cycle's movement
formed the groups this cycle's situation is read with, the answer would leak into
the question. So the scene is read with the groups the PAST formed, and only then
is this cycle's co-movement accrued.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Final

from .frame import Frame
from .interpret import ThingChange
from .perceive import NEIGHBOURS, Region, background_of, segment

DIRECTIONS: Final = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}

# How often two pieces must have moved together, by the same displacement, before
# they are read as one thing (DECLARED, tunable). One co-movement can be a
# coincidence; two cannot be ruled one as easily. Any occasion on which both were
# present and moved differently vetoes the grouping outright.
MIN_COMOVEMENTS: Final = 2

# What a ray meets when it leaves the grid.
EDGE: Final = "edge"


@dataclass(frozen=True, slots=True)
class Thing:
    """One individual, as seen in a transition."""

    # Stable while the thing persists: its values and its oldest piece id.
    entity: str
    change: ThingChange
    # What lies ahead of it on every side, read off the frame BEFORE the move.
    ahead: str


@dataclass(frozen=True, slots=True)
class Scene:
    things: tuple[Thing, ...]
    # Contacts made or broken between two things: (a, b, "contact-made" | ...).
    interactions: tuple[tuple[str, str, str], ...]
    # Entities present in the frame AFTER the move.
    present: frozenset[str]


class Seeing:
    """Follows pieces across frames and groups the ones that move as one."""

    __slots__ = ("_next_id", "_tracked", "_last_frame", "_last_ids", "_together", "_apart")

    def __init__(self) -> None:
        self._next_id = 0
        # The pieces of the last frame assigned, as (id, value, centroid).
        self._tracked: list[tuple[int, int, tuple[float, float]]] = []
        # The last frame assigned, and its pieces' ids, so a contiguous run does
        # not re-match a frame it has already seen.
        self._last_frame: Frame | None = None
        self._last_ids: list[int] = []
        # Evidence for grouping, accrued (INV-5), never reloaded.
        self._together: Counter[tuple[int, int]] = Counter()
        self._apart: Counter[tuple[int, int]] = Counter()

    # ── identity ──

    def _assign(self, pieces: tuple[Region, ...]) -> list[int]:
        """Give each piece the id of the nearest tracked piece of its value."""
        free = list(self._tracked)
        ids: list[int] = []
        for piece in pieces:
            same = [t for t in free if t[1] == piece.value]
            if same:
                best = min(same, key=lambda t: math.dist(t[2], piece.centroid))
                free.remove(best)
                ids.append(best[0])
            else:
                ids.append(self._next_id)
                self._next_id += 1
        self._tracked = [(i, p.value, p.centroid) for i, p in zip(ids, pieces)]
        return ids

    def _ids_for(self, frame: Frame, pieces: tuple[Region, ...]) -> list[int]:
        if frame is self._last_frame:
            return list(self._last_ids)
        return self._assign(pieces)

    # ── grouping by common fate ──

    def _groups(self, ids: set[int]) -> dict[int, int]:
        """Each id's group leader, from evidence accrued BEFORE this cycle."""
        parent = {i: i for i in ids}

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for (a, b), n in self._together.items():
            if a in parent and b in parent and n >= MIN_COMOVEMENTS and not self._apart[(a, b)]:
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[max(ra, rb)] = min(ra, rb)
        return {i: find(i) for i in ids}

    def _accrue(self, moves: dict[int, tuple[int, int]]) -> None:
        """Record which pieces moved together this cycle — AFTER the scene."""
        items = sorted(moves.items())
        for x, (a, da) in enumerate(items):
            for b, db in items[x + 1 :]:
                if da == db and da != (0, 0):
                    self._together[(a, b)] += 1
                elif da != db:
                    self._apart[(a, b)] += 1

    # ── reading a transition ──

    def look(self, prev: Frame, now: Frame) -> Scene:
        before = segment(prev)
        after = segment(now)
        ids_before = self._ids_for(prev, before)
        ids_after = self._assign(after)
        self._last_frame, self._last_ids = now, list(ids_after)

        by_id_before = dict(zip(ids_before, before))
        by_id_after = dict(zip(ids_after, after))

        # Groups formed by the past only (see ORDER in the module docstring).
        leader = self._groups(set(by_id_before) | set(by_id_after))
        members: dict[int, set[int]] = {}
        for i, lead in leader.items():
            members.setdefault(lead, set()).add(i)

        def entity_of(lead: int) -> str:
            values = sorted(
                {r.value for i in members[lead] for r in (by_id_before.get(i), by_id_after.get(i)) if r}
            )
            return f"thing:{'+'.join(map(str, values))}#{lead}"

        label_before = _labels(before, ids_before, leader)
        label_after = _labels(after, ids_after, leader)

        things: list[Thing] = []
        for lead in sorted(members):
            was = [by_id_before[i] for i in members[lead] if i in by_id_before]
            is_ = [by_id_after[i] for i in members[lead] if i in by_id_after]
            things.append(
                Thing(
                    entity=entity_of(lead),
                    change=_change(was, is_),
                    ahead=_ahead(prev, was, lead, label_before) if was else "",
                )
            )

        interactions = _interactions(
            _contacts(prev, label_before, entity_of), _contacts(now, label_after, entity_of)
        )
        present = frozenset(
            entity_of(lead) for lead in members if any(i in by_id_after for i in members[lead])
        )

        # Only now does this cycle's movement become evidence for grouping.
        moves: dict[int, tuple[int, int]] = {}
        for i in by_id_before.keys() & by_id_after.keys():
            (r0, c0), (r1, c1) = by_id_before[i].centroid, by_id_after[i].centroid
            moves[i] = (round(r1 - r0), round(c1 - c0))
        self._accrue(moves)

        return Scene(things=tuple(things), interactions=interactions, present=present)


def _labels(
    pieces: tuple[Region, ...], ids: list[int], leader: dict[int, int]
) -> dict[int, dict[tuple[int, int], int]]:
    """Per channel, which thing (by group leader) owns each non-background cell."""
    out: dict[int, dict[tuple[int, int], int]] = {}
    for piece, i in zip(pieces, ids):
        grid = out.setdefault(piece.channel, {})
        for cell in piece.cells:
            grid[cell] = leader[i]
    return out


def _change(was: list[Region], is_: list[Region]) -> ThingChange:
    if was and is_:
        return ThingChange(
            persisted=True,
            appeared=False,
            vanished=False,
            moved=_displacement(was, is_),
            grew=sum(r.size for r in is_) - sum(r.size for r in was),
            pieces=len(is_) - len(was),
        )
    return ThingChange(
        persisted=False,
        appeared=bool(is_),
        vanished=bool(was),
        moved=None,
        grew=sum(r.size for r in is_) - sum(r.size for r in was),
        pieces=len(is_) - len(was),
    )


def _displacement(was: list[Region], is_: list[Region]) -> tuple[int, int]:
    def centre(regions: list[Region]) -> tuple[float, float]:
        total = sum(r.size for r in regions)
        return (
            sum(r.centroid[0] * r.size for r in regions) / total,
            sum(r.centroid[1] * r.size for r in regions) / total,
        )

    (r0, c0), (r1, c1) = centre(was), centre(is_)
    return (round(r1 - r0), round(c1 - c0))


def _ahead(
    frame: Frame,
    pieces: list[Region],
    lead: int,
    labels: dict[int, dict[tuple[int, int], int]],
) -> str:
    """What each side of this thing faces first, at any distance.

    A ray leaves every cell on the thing's boundary on that side, passes over
    background and over the thing's OWN cells — all its pieces, whatever their
    value, which is what grouping bought — and records the value of the first
    other thing it meets, or the grid's edge. No distance constant, and nothing
    about what any action does: only what is there to be met.
    """
    seen: dict[str, set[str]] = {d: set() for d in DIRECTIONS}
    for piece in pieces:
        grid = frame.grids[piece.channel]
        rows, cols = len(grid), len(grid[0])
        background = background_of(grid)
        owner = labels.get(piece.channel, {})
        for d, (dr, dc) in DIRECTIONS.items():
            for r, c in piece.cells:
                nr, nc = r + dr, c + dc
                # Start only where this side of the cell is not the thing itself.
                if 0 <= nr < rows and 0 <= nc < cols and owner.get((nr, nc)) == lead:
                    continue
                while (
                    0 <= nr < rows
                    and 0 <= nc < cols
                    and (grid[nr][nc] == background or owner.get((nr, nc)) == lead)
                ):
                    nr += dr
                    nc += dc
                seen[d].add(str(grid[nr][nc]) if 0 <= nr < rows and 0 <= nc < cols else EDGE)
    return "|".join(f"{d}:{','.join(sorted(seen[d]))}" for d in DIRECTIONS)


def _contacts(frame: Frame, labels, entity_of) -> frozenset[tuple[str, str]]:
    """Which things touch which, edge to edge, on the same channel."""
    pairs: set[tuple[str, str]] = set()
    for channel, owner in labels.items():
        for (r, c), a in owner.items():
            for dr, dc in NEIGHBOURS[1::2]:  # down and right: each edge once
                b = owner.get((r + dr, c + dc))
                if b is not None and b != a:
                    x, y = sorted((entity_of(a), entity_of(b)))
                    pairs.add((x, y))
    return frozenset(pairs)


def _interactions(before: frozenset, after: frozenset) -> tuple[tuple[str, str, str], ...]:
    """Contacts made or broken — Other-to-Other, no self present (§6.3 SocialEdge).

    A contact that merely persists is not an interaction; measured, standing
    contacts were near-constant and would have said nothing.
    """
    return tuple(
        [(a, b, "contact-made") for a, b in sorted(after - before)]
        + [(a, b, "contact-broken") for a, b in sorted(before - after)]
    )


def create_seeing() -> Seeing:
    return Seeing()
