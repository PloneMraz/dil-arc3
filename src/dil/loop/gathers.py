"""Consumption-side input assembly for multi-stream flow (protocol §6, cycle-1+).

"The mechanism is consumption, not dispatch: a layer makes its output available,
and each higher layer reads what falls within its dependency set." Each gather
builds one layer's input by READING the meaning-channel — every read passes the
INV-3 guard, so a consumer may read only layers at or below its own index — and
the driver never hands an output to a consumer.

Fan-out is real: T5's single published output is read by both T6 and T7, and T6
reads T2's output itself, its declared dependency, instead of a driver-smuggled
digest.

T1 and T3 ingest the HOST's input — external ingest, not a channel read. T2
additionally takes the previous cycle's emission, the feedback of INV-1, and the
observed changes.

Ported from dil-core against DIL protocol v0.3.2.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..invariants.types import LayerIndex
from .layers.t2 import Emission, T2Input, T2Output
from .layers.t3 import T3Input, T3Output
from .layers.t4 import T4Input, T4Output
from .layers.t5 import T5Input, T5Output
from .layers.t6 import T6Input, T6Output
from .layers.t7 import ExpectedEntity, T7Input
from .layers.t8 import T8Input
from .meaning_channel import MeaningChannel

if TYPE_CHECKING:
    from .cycle import HostCycleInput


class MultiStreamError(Exception):
    """A declared dependency was consumed before its producer published."""

    def __init__(self, detail: str) -> None:
        super().__init__(f"multi-stream: {detail}")


def _must_read(ch: MeaningChannel, consumer: LayerIndex, from_: LayerIndex) -> Any:
    """Read a dependency that MUST have been published (INV-3 guarded by the channel)."""
    out = ch.read(consumer, from_)
    if out is None:
        raise MultiStreamError(
            f"layer T{consumer} consumed T{from_}, but T{from_} has published "
            "nothing this cycle"
        )
    return out


def gather_t2(ch: MeaningChannel, host: HostCycleInput, emitted: Emission) -> T2Input:
    return T2Input(
        env=_must_read(ch, 2, 1),
        emitted=emitted,
        changes=tuple(host.changes),
    )


def gather_t3(host: HostCycleInput) -> T3Input:
    return T3Input(signals=tuple(host.signals))


def gather_t4(ch: MeaningChannel) -> T4Input:
    t3: T3Output = _must_read(ch, 4, 3)
    return T4Input(units=t3.units)


def gather_t5(ch: MeaningChannel) -> T5Input:
    t4: T4Output = _must_read(ch, 5, 4)
    return T5Input(bound=t4.bound)


def gather_t6(ch: MeaningChannel) -> T6Input:
    t2: T2Output = _must_read(ch, 6, 2)
    t5: T5Output = _must_read(ch, 6, 5)
    return T6Input(
        results=t5.results,
        env_pushed=frozenset(
            t.change.id for t in t2.tagged if t.agency == "ENV_PUSHED"
        ),
    )


def gather_t7(ch: MeaningChannel) -> T7Input:
    t5: T5Output = _must_read(ch, 7, 5)
    return T7Input(
        expectations=tuple(
            ExpectedEntity(entity_id=r.entity_id, predicted=r.expectation.predicted)
            for r in t5.results
        ),
        observed=frozenset(r.entity_id for r in t5.results),
    )


def gather_t8(ch: MeaningChannel, host: HostCycleInput) -> T8Input:
    t6: T6Output = _must_read(ch, 8, 6)
    return T8Input(others=t6.others, interactions=tuple(host.interactions))
