"""The absorption measure (protocol §8.3) — a REAL brake, or only deceleration?

§8.3 ranks anchors: a fixed, memorizable source reaches only content-degradation
— "a fixed test is memorizable, so a systematic lens-bias passes through" — while
a live Mode-B "can always deliver a collision NEW IN KIND". New in kind is not a
taxonomy of mismatches; it is novelty, resistance the agent cannot re-author away.

The trace-measurable proxy is ABSORPTION: for a source seen many times, does it
still produce prediction error — not absorbed, a real brake — or has the error
gone to zero, memorized, deceleration only?

This reads the resistance readings a run already records: `expectation` lines for
value-mismatch sources and `resistance-reading` lines for absence sources,
grouped by the resisting subject. The signal fires when EVERY sufficiently-probed
source has been absorbed, so nothing delivers a collision new in kind. It is an
OBSERVABILITY signal, not a §13 conformance criterion — §13 mandates source
diversity (§13.7), not absorption — and a third party can recompute it from the
log.

Ported from dil-core against DIL protocol v0.3.2.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, TypeAlias

from ..loop.decisions import SUFFICIENT_RECURRENCE
from ..store.resist_event import (
    ExpectationActivity,
    LogRecord,
    ResistanceReadingActivity,
)

# One source's absorption state, read from its high-recurrence readings.
SourceAbsorption: TypeAlias = Literal["resisting", "absorbed", "insufficient"]


@dataclass(frozen=True, slots=True)
class AbsorptionReport:
    # Per resisting subject: still resisting, absorbed (memorized), or under-probed.
    per_source: dict[str, SourceAbsorption]
    # The absorption-loss signal, or None. Fires when at least one source is
    # sufficiently probed and EVERY sufficiently-probed source has been absorbed —
    # no collision new in kind remains, a deceleration-only regime (§8.3).
    signal: str | None


@dataclass(frozen=True, slots=True)
class _Reading:
    recurrence: float
    delta: float


def measure_absorption(
    records: Sequence[LogRecord],
    recurrence_threshold: float = SUFFICIENT_RECURRENCE,
) -> AbsorptionReport:
    """Measure absorption from the trace.

    A source is `absorbed` if, once probed at least `recurrence_threshold` times,
    its prediction error is always zero — memorized. It is `resisting` if it
    still errs at that exposure, so new in kind still arrives. It is
    `insufficient` if never probed that many times.
    """
    # Group readings by the resisting SUBJECT. A value-mismatch reading and an
    # absence reading about the same entity are the same source resisting by
    # different means.
    by_entity: dict[str, list[_Reading]] = {}

    for r in records:
        if isinstance(r, (ExpectationActivity, ResistanceReadingActivity)):
            by_entity.setdefault(r.entity, []).append(
                _Reading(recurrence=r.recurrence, delta=r.delta)
            )

    per_source: dict[str, SourceAbsorption] = {}
    for entity, readings in by_entity.items():
        probed = [x for x in readings if x.recurrence >= recurrence_threshold]
        if not probed:
            per_source[entity] = "insufficient"
        else:
            # Still a real brake if it errs at high exposure; absorbed if never.
            per_source[entity] = (
                "resisting" if any(x.delta > 0 for x in probed) else "absorbed"
            )

    qualified = [v for v in per_source.values() if v != "insufficient"]
    all_absorbed = bool(qualified) and all(v == "absorbed" for v in qualified)

    signal = (
        (
            f"absorption: every sufficiently-probed resistance source "
            f"(≥{recurrence_threshold} exposures) has been memorized (prediction "
            "error → 0); no collision new in kind — deceleration only, not a real "
            "brake (§8.3)"
        )
        if all_absorbed
        else None
    )

    return AbsorptionReport(per_source=per_source, signal=signal)
