"""What an action DID — the effect signature, and DECIDE@IMPL tag H.

Under the settled reading, the unit of experience is the **affordance**: the loop
holds an expectation about what an action does, not about what the next frame
looks like. So the loop must be handed the *effect* of a move, and the effect has
to be described in a way that REPEATS when the same control is used again.

That rules out the obvious description. A literal diff — the set of changed
`(row, col)` cells — is different every time the player stands somewhere else, so
"move up" from two positions would look like two unrelated events, T5's
persistence rule would never match, and confidence would never ramp. The agent
would be unable to learn its own controls. The signature here is therefore
**translation-invariant**: it records *what kind* of change happened and *which
way* things moved, never *where*.

This is DECIDE@IMPL tag H, and it is a claim about the world, not a convention:
it asserts that repeating a control produces a repeating signature. That claim is
falsifiable, and it was measured on 316 real transitions rather than assumed.

What the measurement found, in both directions:

  - In `ls20` it holds, and the signature recovers the control scheme unaided:
    values 9 and 12 displace by (-5,0) under ACTION1, (+5,0) under ACTION2,
    (0,-5) under ACTION3 and (0,+5) under ACTION4 — up, down, left, right. The
    agent is not told this; it falls out of the representation.
  - A blocked move produces the SAME signature whichever direction was tried.
    That is not a defect. Walking into a wall is genuinely indistinguishable by
    its effect, and a representation that pretended otherwise would be lying.
  - In `vc33` it carries NO information: across 157 transitions the click
    position never changed the signature. Whether that is the representation
    failing or those clicks genuinely doing nothing is NOT established, and is
    not being guessed at here.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Final

from .frame import Frame

# A (from_value, to_value) pair, and how many cells made that transition.
Transitions = tuple[tuple[int, int, int], ...]
# Per value: how far the thing of that value moved, as (d_row, d_col).
Displacements = tuple[tuple[int, int, int], ...]

# Below this many changed cells of a value, its centroid is noise rather than a
# moving object, so no displacement is claimed for it.
MIN_CELLS_FOR_DISPLACEMENT: Final = 1

# Claim a displacement only when the value vanished from as many cells as it
# appeared in. A rigid translation CONSERVES the number of cells carrying that
# value; a spreading trail or a growing region does not. Without this condition
# the wobbling centroid of a non-rigid value shatters the signature: measured on
# 316 real transitions, ls20 went from 33 distinct signatures to 10, and each
# action from 8-11 signatures down to 2-4, with discrimination unchanged at 79%.
REQUIRE_RIGID_TRANSLATION: Final = True


@dataclass(frozen=True, slots=True)
class Effect:
    """A translation-invariant description of what changed between two frames.

    Equality is structural, and that is the point: two uses of the same control
    are the *same effect* exactly when these fields agree.
    """

    # Number of cells that differ, summed over the stack. Stable for a control
    # that always moves the same shape.
    cells_changed: int
    # Sorted (from, to, count) — which colours turned into which, and how often.
    transitions: Transitions
    # Sorted (value, d_row, d_col) — the displacement of each value that both
    # vanished from somewhere and appeared somewhere.
    displacements: Displacements
    # The stack grew or shrank. Structural, and worth knowing on its own.
    depth_delta: int
    # Did this action complete a level. The only channel the scorer reads.
    levels_delta: int
    # State transition, e.g. NOT_FINISHED -> GAME_OVER.
    state_from: str
    state_to: str

    @property
    def is_null(self) -> bool:
        """Nothing observable happened.

        Not a failure: an affordance that reliably does nothing is a fact about
        the game the agent is entitled to learn.
        """
        return (
            self.cells_changed == 0
            and self.depth_delta == 0
            and self.levels_delta == 0
            and self.state_from == self.state_to
        )


def _centroid(cells: list[tuple[int, int]]) -> tuple[float, float]:
    n = len(cells)
    return (sum(r for r, _ in cells) / n, sum(c for _, c in cells) / n)


def diff(prev: Frame, now: Frame) -> Effect:
    """Describe the change from `prev` to `now`, invariant to where it happened.

    Grids are compared at the same stack index. When the depths differ, only the
    overlapping indices are compared and `depth_delta` carries the rest: a stack
    that grew is a structural event, not a cell-level one.
    """
    depth = min(prev.depth, now.depth)
    changed = 0
    trans: Counter[tuple[int, int]] = Counter()
    vanished: dict[int, list[tuple[int, int]]] = {}
    appeared: dict[int, list[tuple[int, int]]] = {}

    for gi in range(depth):
        pg, ng = prev.grids[gi], now.grids[gi]
        for r, (prow, nrow) in enumerate(zip(pg, ng)):
            for c, (pv, nv) in enumerate(zip(prow, nrow)):
                if pv == nv:
                    continue
                changed += 1
                trans[(pv, nv)] += 1
                vanished.setdefault(pv, []).append((r, c))
                appeared.setdefault(nv, []).append((r, c))

    displacements: list[tuple[int, int, int]] = []
    for value in sorted(set(vanished) & set(appeared)):
        gone, came = vanished[value], appeared[value]
        if len(gone) < MIN_CELLS_FOR_DISPLACEMENT or len(came) < MIN_CELLS_FOR_DISPLACEMENT:
            continue
        if REQUIRE_RIGID_TRANSLATION and len(gone) != len(came):
            continue
        gr, gc = _centroid(gone)
        ar, ac = _centroid(came)
        displacements.append((value, round(ar - gr), round(ac - gc)))

    return Effect(
        cells_changed=changed,
        transitions=tuple(sorted((a, b, n) for (a, b), n in trans.items())),
        displacements=tuple(displacements),
        depth_delta=now.depth - prev.depth,
        levels_delta=now.levels_completed - prev.levels_completed,
        state_from=prev.state,
        state_to=now.state,
    )
