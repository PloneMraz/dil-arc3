"""The field's axes — what GLOB-MOD carries, and how a layer reads and feeds it
(protocol §5 INV-7; parent specification DIL-en-v7 §2, "What it carries").

WHAT THE FIELD IS. "A global interpretive prior: a single background state,
shared by every layer in a cycle, setting the disposition with which each layer
reads its input. It carries how to read, never what is read." Its params are
"scalar interpretive biases — each one modulating the gain or threshold of some
layer operation (how readily a source is trusted, how alert the loop is to
mismatch, how far it leans toward exploring rather than consolidating)". The
axes and their number are DECIDE@IMPL; their kind is fixed.

THE AXES (declared, decisions.GLOB_MOD_AXES): the three the specification
names, and no others — `trust`, `alertness`, `exploration` — each in [0, 1],
with NEUTRAL (0.5) the disposition of a field no layer has yet leaned.

HOW A LAYER READS. Each layer reads the axis that bears on its own operation,
and the axis shifts that operation's declared threshold or gain (§6: "a global
gain and bias shifting every link's parameters at once"). At NEUTRAL, and in a
field that carries no axes, every operation is exactly the declared one.

HOW A LAYER FEEDS. Each layer votes on an axis from what it alone sees this
cycle, a value in [0, 1]; the votes on a key blend convexly (INV-7) and
condition the field from N+1. A layer with nothing to see on an axis this cycle
casts no vote, and the axis carries over. What a layer sees (a count, a share)
is never put in the field itself: that would be what is read, not how to read.

Ported from dil-core 1e0a22a.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Final

from .layer import ContributeFn
from .types import ModField

# How readily a source is trusted.
TRUST: Final = "trust"
# How alert the loop is to mismatch.
ALERTNESS: Final = "alertness"
# How far the loop leans toward exploring rather than consolidating.
EXPLORATION: Final = "exploration"

AXES: Final = (TRUST, ALERTNESS, EXPLORATION)

# The disposition of an axis no layer has leaned: the declared operation, unshifted.
NEUTRAL: Final = 0.5


def axis(field: ModField | None, name: str) -> float:
    """The value of an axis in a field, in [0, 1]; NEUTRAL when the field carries none."""
    v = field.params.get(name) if field is not None else None
    if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
        return NEUTRAL
    return min(1.0, max(0.0, float(v)))


def rising(v: float) -> float:
    """The gain an axis puts on an operation that grows with it: 1 at NEUTRAL, ½ at
    0, 1½ at 1 (decisions.FIELD_READING_LAW). Never 0 and never inverted, so it
    biases an operation and never annuls it."""
    return 0.5 + v


def falling(v: float) -> float:
    """The gain on an operation that shrinks as the axis grows: 1 at NEUTRAL, 1½ at 0, ½ at 1."""
    return 1.5 - v


def round_half_up(x: float) -> int:
    # Half away from zero, as JavaScript's Math.round does for positives: the
    # port rounds as dil-core does (Python's round() rounds half to even).
    return int(math.floor(x + 0.5))


def shifted_count(base: float, gain: float) -> float:
    """A count threshold shifted by a gain: never below 1, since a threshold of 0 is no threshold."""
    if not math.isfinite(base):
        return base
    return max(1, round_half_up(base * gain))


def share(part: float, whole: float) -> float | None:
    """A share in [0, 1], or None when there is nothing to share (no vote)."""
    return min(1.0, max(0.0, part / whole)) if whole > 0 else None


def votes(cast: Mapping[str, float | None]) -> dict[str, float]:
    """A layer's votes this cycle: only the axes it saw something on."""
    out: dict[str, float] = {}
    for name in AXES:
        v = cast.get(name)
        if v is None:
            continue
        if not math.isfinite(v) or v < 0 or v > 1:
            raise ValueError(f"field vote on {name} must be in [0, 1], got {v}")
        out[name] = float(v)
    return out


def cast_votes(contribute: ContributeFn, cast: Mapping[str, float | None]) -> None:
    """Cast a layer's votes into the field, if it saw anything to vote on this cycle."""
    v = votes(cast)
    if v:
        contribute(v)


__all__ = [
    "ALERTNESS", "AXES", "EXPLORATION", "NEUTRAL", "TRUST", "round_half_up",
    "axis", "cast_votes", "falling", "rising", "share", "shifted_count", "votes",
]
