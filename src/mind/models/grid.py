"""The grid inducer — hypotheses that reach past where they were met.

It perceives a grid as the exact inducer does (`exact.py`: the clock, the things
an act that takes a place may be put on) and suggests, from each experience, the
exact hypothesis and one that generalises. The mind holds them all, weighs them
against the store, and expects from the one right at the highest rate
(`mind/learning.py`, FIT_LAW).

ITS HYPOTHESES, in a language declared, not measured, naming no game:

- **Exact** — as the exact inducer's: from this situation, this act gives that.
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
  to change — read from what the mind expected of the step, or, for an act that
  takes a place, the thing it was put on — with the ring around it, as it was.
  It says nothing of the state; where every part lies, box and ring alike, it
  says the region will report what it reported then.

The clock's rows are no part of any of them: what lies there matches anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from ..organs import Act, Step
from .exact import BIG_CHANGE, PART_GAP, ExactForm, ExactInducer, Grid, Perceived, Prediction, grid_key, parts

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


class GridInducer(ExactInducer):
    """Exact, still and rewrite hypotheses, over the exact inducer's perception."""

    kind = "grid"
    general = True

    def __init__(self, organs) -> None:
        super().__init__(organs)
        self._where: dict[str, dict[int, list[tuple[int, int]]]] = {}   # situation -> colour -> cells
        # (situation, part) -> (the part, where it lies): the part is kept, so its id is not reused.
        self._found: dict[tuple[str, int], tuple[Part, tuple[int, int] | None]] = {}

    def perceive(self, step: Step, kind: tuple) -> Perceived | None:
        perceived = super().perceive(step, kind)
        if perceived is not None:
            self._where, self._found = {}, {}
        return perceived

    # ── hypotheses ──

    def induce(self, source: str, act: Act, before: Grid, after: Grid, *, foreseen: bool = False,
               evidence: tuple = (), report: dict | None = None, expected: Grid | None = None) -> list[Any]:
        if report is not None:
            return self._aim(act, before, expected, report)
        forms: list[Any] = [ExactForm(source=source, act=act, to=after)]
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

    def _aim(self, act: Act, before: Grid, expected: Grid | None, report: dict) -> list[Any]:
        """What reaching the aim suggests (S4, Plone, 2026-09-28): that this act,
        taken where the same cells lie again, brings it again. The step itself
        says nothing of where: the region comes back changed nearly whole (a
        level over, 715 to 2,872 of 4,096 cells in the runs measured). So what
        the act was to change is read from what the mind expected of the step,
        and for an act that takes a place, from the thing it was put on; with
        neither, nothing is suggested."""
        placed = act[0] in self.organs.placed and act[1] is not None and act[2] is not None
        if placed:
            x, y = act[1], act[2]
            if not (0 <= y < len(before) and 0 <= x < len(before[y])):
                return []
            cells = self._thing_at(before, x, y)
        else:
            if expected is None:
                return []
            rows = min(len(before), len(expected))
            cells = [(r, c) for r in range(rows) if r not in self.clock
                     for c in range(min(len(before[r]), len(expected[r]))) if before[r][c] != expected[r][c] and c not in self.clock_columns]
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
        if isinstance(form, ExactForm):
            return ("exact", form.source, form.act, grid_key(form.to))
        return form.key

    def scope(self, form: Any, situation_of) -> tuple:
        if isinstance(form, ExactForm):
            return super().scope(form, situation_of)
        if isinstance(form, AimForm):
            return ("aim", form.act)
        return ("act", form.act)

    def scopes(self, situation: str, act: Act) -> list[tuple]:
        return [("at", situation, act), ("act", act[0]), ("aim", act[0])]

    def predict(self, form: Any, situation: str, state: Grid, act: Act, situation_of) -> Prediction | None:
        if isinstance(form, ExactForm):
            return super().predict(form, situation, state, act, situation_of)
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

    def fields(self, form: Any) -> dict[str, Any] | None:
        return form.status if isinstance(form, (ExactForm, AimForm)) else None

    def describe(self, form: Any, situation_of) -> dict[str, Any]:
        if isinstance(form, ExactForm):
            return {"form": "exact", **super().describe(form, situation_of)}
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

    def restore(self, payload: dict[str, Any], step: Step) -> Any:
        """A still, rewrite or aim hypothesis from its datum alone; an exact one
        from its datum and its step (`ExactInducer.restore`)."""
        form = payload.get("form")
        if form == "exact":
            return super().restore(payload, step)
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


__all__ = ["MAX_REWRITE_CELLS", "OFF_GRID", "PART_GAP", "AimForm", "GridInducer", "Part", "RewriteForm", "StillForm", "parts"]
