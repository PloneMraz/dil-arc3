"""T3 — Channel Ingestion (protocol §6.3).

Ingests external and internal channels. Channel content-typing preserves the
distinction between information-type and physical-channel: each ingested unit
records BOTH which physical channel it arrived on and what information-type it
is. The per-channel transducer is DECIDE@IMPL — pluggable, with a declared
default.

Ported from dil-core against DIL protocol v0.3.2.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field as dc_field
from typing import Any, Final

from ..layer import BaseLayer, ContributeFn, EmitFn
from ..types import InfoUnit, ModField, RefFrame, Signal

# Maps a channel's raw signal into a typed value (DECIDE@IMPL, per channel).
# Returns (info_type, value).
ChannelTransducer = Callable[[Signal], tuple[str, Any]]

# How many signals the region delivered this cycle (INV-7, up-channel).
CHANNEL_ACTIVITY: Final = "channelActivity"


def default_transducer(signal: Signal) -> tuple[str, Any]:
    """Pass the payload through, typed as "raw"."""
    return ("raw", signal.raw_payload)


@dataclass(frozen=True, slots=True)
class T3Input:
    signals: tuple[Signal, ...] = dc_field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class T3Output:
    units: tuple[InfoUnit, ...] = dc_field(default_factory=tuple)


class T3(BaseLayer):
    index = 3
    consumes: tuple[int, ...] = (1,)

    def __init__(self, transducers: dict[str, ChannelTransducer] | None = None) -> None:
        self._transducers = dict(transducers or {})

    def process(  # noqa: A002
        self,
        input: T3Input,
        field: ModField,
        emit: EmitFn,
        contribute: ContributeFn,
    ) -> T3Output:
        # A FACT T3 can see and no other layer can: how much the region said this
        # cycle. Not a policy number — T3 does not decide what follows from it.
        contribute({CHANNEL_ACTIVITY: float(len(input.signals))})

        units: list[InfoUnit] = []
        for signal in input.signals:
            transduce = self._transducers.get(signal.source_id, default_transducer)
            info_type, value = transduce(signal)
            units.append(
                InfoUnit(
                    # Content-typing keeps the info-type and the physical channel
                    # distinct.
                    content={
                        "infoType": info_type,
                        "channel": signal.source_id,
                        "value": value,
                    },
                    ref_frame=RefFrame(bound_layer=3, ref=f"channel:{signal.source_id}"),
                    t=signal.t,
                )
            )
        return T3Output(units=tuple(units))

    def info_units(self, output: T3Output) -> Sequence[InfoUnit]:
        return output.units


def create_t3(transducers: dict[str, ChannelTransducer] | None = None) -> T3:
    return T3(transducers)
