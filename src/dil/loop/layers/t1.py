"""T1 — Activity-Environment Confirmation (protocol §6.3).

Confirms the presence of an activity-environment, the root reference frame. It
draws NO self/environment line — that is T2's work.

In: the host's signals for the cycle. Out: an `ActivityEnvironment`, an InfoUnit
whose frame is the root. Precondition: none. Postcondition: presence confirmed
for T2.

THE FIELD (INV-7). T1 reads `trust`: how many silent cycles it holds the
environment confirmed through (T1_GRACE_MAX) — none at NEUTRAL, the reference
behaviour. A silence against a background of returns is a mismatch (§4), not the
environment gone. It votes `trust` from what only it sees: whether the region
said anything at all this cycle.

Ported from dil-core against DIL protocol v0.3.3; the field from dil-core 1e0a22a.
"""

from collections.abc import Sequence
from typing import Any

from ..decisions import T1_GRACE_MAX
from ..field import TRUST, round_half_up, axis, cast_votes
from ..layer import BaseLayer, ContributeFn, EmitFn
from ..types import ActivityEnvironment, InfoUnit, ModField, RefFrame, Signal

# The root reference frame every higher layer ultimately refers to.
ROOT_FRAME = RefFrame(bound_layer=1, ref="activity-environment")


def _latest_t(signals: Sequence[Signal]) -> int:
    return max((s.t for s in signals), default=0)


def grace_of(trust: float) -> int:
    """How many silent cycles trust holds the environment through: 0 at NEUTRAL or below."""
    return round_half_up(T1_GRACE_MAX * max(0.0, 2 * trust - 1))


class T1(BaseLayer):
    index = 1
    consumes: tuple[int, ...] = ()

    def __init__(self) -> None:
        # Silent cycles in a row, accrued (INV-5).
        self._silent_for = 0

    def snapshot(self) -> dict[str, Any]:
        return {"silentFor": self._silent_for}

    def restore(self, state: Any) -> None:
        self._silent_for = (state or {}).get("silentFor", 0)

    def process(  # noqa: A002
        self,
        input: Sequence[Signal],
        field: ModField,
        emit: EmitFn,
        contribute: ContributeFn,
    ) -> ActivityEnvironment:
        # Presence confirmed as the root reference frame. No self/environment
        # line is drawn here; the content only digests what is present.
        said = len(input) > 0
        self._silent_for = 0 if said else self._silent_for + 1
        held = not said and self._silent_for <= grace_of(axis(field, TRUST))
        cast_votes(contribute, {TRUST: 1.0 if said else 0.0})
        content: dict[str, Any] = {
            "present": said or held,
            "count": len(input),
            "sources": [s.source_id for s in input],
        }
        if held:
            content["heldThroughSilence"] = self._silent_for
        return InfoUnit(
            content=content,
            ref_frame=ROOT_FRAME,
            t=_latest_t(input),
        )

    def info_units(self, output: Any) -> Sequence[InfoUnit]:
        # INV-4: the ActivityEnvironment is an InfoUnit leaving the layer.
        return (output,)


def create_t1() -> T1:
    return T1()
