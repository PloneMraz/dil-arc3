"""T3 — Channel Ingestion (protocol §6.3).

Ingests external and internal channels. Channel content-typing preserves the
distinction between information-type and physical-channel: each ingested unit
records BOTH which physical channel it arrived on and what information-type it
is. The per-channel transducer is DECIDE@IMPL — pluggable, with a declared
default.

**The query (§6.4).** "T3 emits a *query*: it opens or calls a channel to ingest
actively, rather than only receiving what streams in." The channel it calls is
the agent's own store. What T3 asks with is the arrival's own description, on
the open-tag dimensions the implementation declares (§9 open layer; §12 tag F):
a key denotes the same dimension wherever it appears, so a description of what
just arrived and the tags of a datum in `[data]` can be matched without any new
mechanism. T3 does not read the store — it emits, and the return comes back
through T1 next cycle like any other query-return.

T3 asks about a description it has not asked about before. Memory is recalled
by the character on a cue, never poured in: the store does not flood the loop,
and a cue already asked about has already been answered.

Ported from dil-core against DIL protocol v0.3.3.
"""

import json
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field as dc_field
from typing import Any, Final

from ..decisions import T3_REASK_AFTER
from ..field import EXPLORATION, NEUTRAL, axis, cast_votes, falling, share, shifted_count
from ..layer import BaseLayer, ContributeFn, EmitFn
from ..types import InfoUnit, ModField, RefFrame, Signal

# Maps a channel's raw signal into a typed value (DECIDE@IMPL, per channel).
# Returns (info_type, value), or (info_type, value, description) where the
# description is what the arrival is on the declared open-tag dimensions — the
# cue T3 asks the store with. It may be a list of descriptions when one arrival
# is about several things. No description: nothing to ask with, and no ask.
ChannelTransducer = Callable[[Signal], tuple[Any, ...]]

# The open-tag description of an arrival: registry key → value (§9, tag F).
Description = Mapping[str, str]


# The internal channel a query to the agent's own store opens, and on which its
# return arrives. A return is an answer, not a new cue: T3 never asks about what
# arrived on this channel.
STORE_CHANNEL: Final = "store"


def store_query(cue: Description) -> dict[str, Any]:
    """The action T3 emits to call the store (§6.4)."""
    return {"kind": "query", "channel": STORE_CHANNEL, "cue": dict(cue)}


def is_store_query(action: Any) -> bool:
    return (
        isinstance(action, dict)
        and action.get("kind") == "query"
        and action.get("channel") == STORE_CHANNEL
        and isinstance(action.get("cue"), dict)
    )


def _cue_key(cue: Description) -> str:
    """A description's stable key, so the same cue is recognised however ordered."""
    return json.dumps(sorted(cue.items()))


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
    """THE FIELD (INV-7). T3 reads `exploration`: leaning to explore, it asks again
    a cue it asked long enough ago (T3_REASK_AFTER), since the store may hold more
    under it by now; at NEUTRAL or below it never asks again, the reference
    behaviour. It votes `exploration` from what only it sees: the share of this
    cycle's cues it had never asked before (dil-core 1e0a22a)."""

    index = 3
    consumes: tuple[int, ...] = (1,)

    def __init__(self, transducers: dict[str, ChannelTransducer] | None = None) -> None:
        self._transducers = dict(transducers or {})
        # Every cue T3 has asked the store about, and the cycle it last asked
        # (INV-5: accrued, never reloaded). T3 runs once a cycle: its call count
        # is its clock.
        self._asked: dict[str, int] = {}
        self._tick = 0

    # §9 snapshot surface (recovery-only restore).
    def snapshot(self) -> dict[str, Any]:
        return {"asked": [[k, v] for k, v in sorted(self._asked.items())], "tick": self._tick}

    def restore(self, state: Any) -> None:
        # A snapshot from before the field was read keeps only the cues: each
        # restores as asked at cycle 0.
        self._asked = {}
        for k in state["asked"]:
            if isinstance(k, str):
                self._asked[k] = 0
            else:
                self._asked[k[0]] = k[1]
        self._tick = state.get("tick", 0)

    def process(  # noqa: A002
        self,
        input: T3Input,
        field: ModField,
        emit: EmitFn,
        contribute: ContributeFn,
    ) -> T3Output:
        self._tick += 1
        # How long ago a cue must have been asked for T3 to ask it again: never
        # at NEUTRAL or below.
        exploration = axis(field, EXPLORATION)
        reask_after = (
            shifted_count(T3_REASK_AFTER, falling(exploration)) if exploration > NEUTRAL else math.inf
        )
        cue_count = 0
        fresh = 0

        units: list[InfoUnit] = []
        for signal in input.signals:
            transduce = self._transducers.get(signal.source_id, default_transducer)
            typed = transduce(signal)
            info_type, value = typed[0], typed[1]
            describe = typed[2] if len(typed) > 2 else None

            if signal.source_id != STORE_CHANNEL and describe:
                cues = describe if isinstance(describe, (list, tuple)) else [describe]
                for cue in cues:
                    if not cue:
                        continue
                    key = _cue_key(cue)
                    cue_count += 1
                    last = self._asked.get(key)
                    if last is None:
                        fresh += 1
                    elif self._tick - last < reask_after:
                        continue
                    self._asked[key] = self._tick
                    emit(store_query(cue))

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
        cast_votes(contribute, {EXPLORATION: share(fresh, cue_count)})
        return T3Output(units=tuple(units))

    def info_units(self, output: T3Output) -> Sequence[InfoUnit]:
        return output.units


def create_t3(transducers: dict[str, ChannelTransducer] | None = None) -> T3:
    return T3(transducers)
