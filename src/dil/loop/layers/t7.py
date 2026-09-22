"""T7 — Absence Registration (protocol §6.3).

Emits a signed PredErr for registered absence (ABS-INV): when an entity that was
expected fails to return this cycle, its absence is registered as a NEGATIVE
PredErr — no observation, signed "-". A single silence against a background of
returns is a valid mismatch (§4); unbroken silence is a void field, handled by
the precondition gate, not here.

DEVIATION from dil-core, declared: `T7Input.present` lets the host report which
entities the region says are there this cycle, and an absence is registered only
against those. Silence presupposes the chance to speak. `None` — the default —
restores the original behaviour exactly.

T7 accrues which entities are expected to recur (INV-5): an entity seen at least
`min_observations_to_expect` times is expected next cycle.

Ported from dil-core against DIL protocol v0.3.2.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field as dc_field
from typing import Any, Literal

from ..layer import BaseLayer, EmitFn
from ..types import InfoUnit, ModField


@dataclass(frozen=True, slots=True)
class ExpectedEntity:
    """One entity's expectation as T7 receives it this cycle."""

    entity_id: str
    predicted: InfoUnit


@dataclass(frozen=True, slots=True)
class T7Input:
    # This cycle's expectations (entity → predicted), used to update memory.
    expectations: tuple[ExpectedEntity, ...] = dc_field(default_factory=tuple)
    # Entities that actually returned this cycle.
    observed: frozenset[str] = dc_field(default_factory=frozenset)
    # Entities the region reports PRESENT this cycle — able to return if they
    # are going to. See HostCycleInput.afforded for why this exists and what it
    # measured. `None` restores dil-core's behaviour exactly.
    present: frozenset[str] | None = dc_field(default=None)


@dataclass(frozen=True, slots=True)
class AbsenceReading:
    """A registered absence — a signed-negative PredErr naming who fell silent.

    It additionally records how many times the entity had been expected, so a
    third party can read the absent source's resistance per-source in the trace.
    It is still a prediction error, usable everywhere one is.
    """

    entity_id: str
    # How many times this entity had been expected (T7's `seen`).
    recurrence: int
    predicted: InfoUnit
    delta: float
    observed: None = None
    signed: Literal["-"] = "-"


@dataclass(frozen=True, slots=True)
class T7Output:
    absences: tuple[AbsenceReading, ...] = dc_field(default_factory=tuple)


@dataclass(slots=True)
class _ExpectState:
    predicted: InfoUnit
    seen: int = 0


class T7(BaseLayer):
    index = 7
    consumes: tuple[int, ...] = (5,)

    def __init__(self, min_observations_to_expect: int = 1) -> None:
        self._min_seen = min_observations_to_expect
        self._expected: dict[str, _ExpectState] = {}

    # §9 snapshot surface; `restore` is recovery-only.

    def snapshot(self) -> dict[str, Any]:
        return {
            "expected": [
                (k, {"predicted": v.predicted, "seen": v.seen})
                for k, v in self._expected.items()
            ]
        }

    def restore(self, state: Any) -> None:
        self._expected = {
            k: _ExpectState(predicted=v["predicted"], seen=v["seen"])
            for k, v in state["expected"]
        }

    def process(self, input: T7Input, field: ModField, emit: EmitFn) -> T7Output:  # noqa: A002
        # Accrue this cycle's expectations into memory.
        for e in input.expectations:
            st = self._expected.get(e.entity_id)
            if st is None:
                st = _ExpectState(predicted=e.predicted, seen=0)
                self._expected[e.entity_id] = st
            st.predicted = e.predicted
            st.seen += 1

        # Register absence for expected entities that did not return, naming
        # which entity fell silent and how many times it had been expected, so
        # the absent source's resistance is readable per-source in the trace.
        absences = tuple(
            AbsenceReading(
                entity_id=entity_id,
                recurrence=st.seen,
                predicted=st.predicted,
                delta=1.0,
            )
            for entity_id, st in self._expected.items()
            if st.seen >= self._min_seen
            and entity_id not in input.observed
            # Silence presupposes the chance to speak: an entity the region says
            # is not present this cycle is not silent, it is simply not there.
            and (input.present is None or entity_id in input.present)
        )
        return T7Output(absences=absences)

    def info_units(self, output: T7Output) -> Sequence[InfoUnit]:
        # INV-4: the predicted unit of each absence is an InfoUnit.
        return tuple(a.predicted for a in output.absences)


def create_t7(min_observations_to_expect: int = 1) -> T7:
    return T7(min_observations_to_expect)
