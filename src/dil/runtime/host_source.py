"""HostSource — the requisition boundary.

The host declares where its IO is; the daemon threads its mechanism through. A
HostSource supplies each cycle's input — the region's returns — and accepts the
agent's response. **The agent acts through `deliver`.** DIL is the condition, not
the actor: `deliver` is the host's channel, not DIL speaking to the world.

A scripted source stands in for tests; a real deployment supplies a live source,
the Mode-B Other of decisions.py tag D.

Ported from dil-core against DIL protocol v0.3.2.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from ..loop.cycle import HostCycleInput
from ..loop.layers.t2 import Emission


@runtime_checkable
class HostSource(Protocol):
    def next(self) -> HostCycleInput | None:
        """The next cycle's input, or None when none is available right now."""
        ...

    def deliver(self, response: Emission) -> None:
        """Deliver the agent's response back to the region (the agent acts)."""
        ...


class ScriptedSource:
    """A finite scripted source over a list of inputs.

    Records delivered responses so a test can inspect what the agent acted.
    """

    __slots__ = ("_inputs", "_i", "delivered")

    def __init__(self, inputs: Sequence[HostCycleInput]) -> None:
        self._inputs = list(inputs)
        self._i = 0
        self.delivered: list[Emission] = []

    def next(self) -> HostCycleInput | None:
        if self._i < len(self._inputs):
            out = self._inputs[self._i]
            self._i += 1
            return out
        return None

    def deliver(self, response: Emission) -> None:
        self.delivered.append(response)


def scripted_source(inputs: Sequence[HostCycleInput]) -> ScriptedSource:
    return ScriptedSource(inputs)
