"""The meaning-channel (protocol §6.2, INV-3).

The up-channel: a layer makes its output available and each higher layer reads
what falls within its dependency set. "The mechanism is consumption, not
dispatch." Reads are guarded by INV-3 — a consumer may read only layers ≤ its own
index; reading a higher layer halts the loop.

This is deliberately separate from the modulatory field, the down-channel of
INV-7. The two channels are never collapsed into one.

Ported from dil-core against DIL protocol v0.3.3.
"""

from typing import Any

from ..invariants.guards import assert_meaning_channel_order
from ..invariants.types import LayerIndex


class MeaningChannel:
    """Published layer outputs for one cycle."""

    __slots__ = ("_outputs",)

    def __init__(self) -> None:
        self._outputs: dict[LayerIndex, Any] = {}

    def publish(self, layer: LayerIndex, output: Any) -> None:
        """A layer publishes its output, making it available to higher layers."""
        self._outputs[layer] = output

    def read(self, consumer: LayerIndex, from_: LayerIndex) -> Any:
        """A consumer reads a lower layer's output.

        Halts (INV-3) if `from_` is above `consumer`.
        """
        assert_meaning_channel_order(consumer, from_)
        return self._outputs.get(from_)

    def has(self, layer: LayerIndex) -> bool:
        """Whether a layer has published this cycle."""
        return layer in self._outputs

    def clear(self) -> None:
        """Clear all published outputs (between cycles)."""
        self._outputs.clear()


def create_meaning_channel() -> MeaningChannel:
    return MeaningChannel()
