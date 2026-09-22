"""T1 — Activity-Environment Confirmation (protocol §6.3).

Confirms the presence of an activity-environment, the root reference frame. It
draws NO self/environment line — that is T2's work.

In: the host's signals for the cycle. Out: an `ActivityEnvironment`, an InfoUnit
whose frame is the root. Precondition: none. Postcondition: presence confirmed
for T2.

Ported from dil-core against DIL protocol v0.3.2.
"""

from collections.abc import Sequence
from typing import Any

from ..layer import BaseLayer, EmitFn
from ..types import ActivityEnvironment, InfoUnit, ModField, RefFrame, Signal

# The root reference frame every higher layer ultimately refers to.
ROOT_FRAME = RefFrame(bound_layer=1, ref="activity-environment")


def _latest_t(signals: Sequence[Signal]) -> int:
    return max((s.t for s in signals), default=0)


class T1(BaseLayer):
    index = 1
    consumes: tuple[int, ...] = ()

    def process(
        self, input: Sequence[Signal], field: ModField, emit: EmitFn  # noqa: A002
    ) -> ActivityEnvironment:
        # Presence confirmed as the root reference frame. No self/environment
        # line is drawn here; the content only digests what is present.
        return InfoUnit(
            content={
                "present": len(input) > 0,
                "count": len(input),
                "sources": [s.source_id for s in input],
            },
            ref_frame=ROOT_FRAME,
            t=_latest_t(input),
        )

    def info_units(self, output: Any) -> Sequence[InfoUnit]:
        # INV-4: the ActivityEnvironment is an InfoUnit leaving the layer.
        return (output,)


def create_t1() -> T1:
    return T1()
