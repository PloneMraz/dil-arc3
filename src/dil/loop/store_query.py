"""Answering a store query (§6.4 T3 query; §9 open layer; §12 tag F).

T3 asks with a description of what just arrived. The store answers with every
datum whose open tags carry that same description — each cue key present, with
the same value. That is the whole index: §9 already requires a key to denote the
same dimension wherever it appears, "so the `[event]` log is filterable", and a
filter is what this is.

One key reads the fixed layer instead: `provenance`, the position a datum
occupies now. "What collided" is a question about position, not about what a
datum is, so a cue may carry it — `{"kind": "frame", "provenance": "scar"}` —
and no open tag may use that key, since open tags never overwrite the fixed
layer. Ported from dil-core 44309b7 (v0.3.3).

The answer is a set of Signals on the store channel, ingested at T1 the next
cycle like any query-return (§6: "input channels: query returns"). Nothing is
read into any layer here, and nothing is changed in `[data]`: the provenance move
happens when the datum actually runs, and the driver records it then.

Ported from dil-core, first against DIL protocol v0.3.3 (the package
implements `dil.DIL_PROTOCOL_VERSION`).
"""

from __future__ import annotations

from typing import Any

from ..store.data_store import DataStore
from ..store.tags import TaggedDatum
from .layers.t3 import STORE_CHANNEL, Description
from .types import Signal


# The one cue key read from the fixed layer rather than the open layer.
PROVENANCE_CUE = "provenance"


def _value_for(datum: TaggedDatum, key: str) -> str | None:
    return datum.fixed.provenance if key == PROVENANCE_CUE else datum.open.get(key)


def matches_cue(datum: TaggedDatum, cue: Description) -> bool:
    """Whether a datum carries every pair of the cue: open tags, and provenance for that key."""
    return len(cue) > 0 and all(_value_for(datum, k) == v for k, v in cue.items())


def returned_entity(signal: Signal) -> str:
    """The datum key a query-return carries; also the entity T4 binds it to."""
    return str(signal.raw_payload["entity"])


def answer_query(data: DataStore, cue: Description, t: int) -> list[Signal]:
    """The Signals a store query returns, in the store's own order.

    Each carries the datum as the store held it when it answered — its payload
    and both tag layers — so what arrives says, among other things, that the
    datum is still a `prior`: not the agent's own, not yet tested.
    """
    out: list[Signal] = []
    for datum_id, datum in data.entries():
        if not matches_cue(datum, cue):
            continue
        ret: dict[str, Any] = {
            "entity": datum_id,
            "payload": datum.payload,
            "fixed": {
                "timestamp": datum.fixed.timestamp,
                "cycleMark": datum.fixed.cycle_mark,
                "provenance": datum.fixed.provenance,
                "floorTag": datum.fixed.floor_tag,
            },
            "open": dict(datum.open),
            # The cue this return answers — so T2 can match it to the query.
            "cue": dict(cue),
        }
        out.append(Signal(source_id=STORE_CHANNEL, raw_payload=ret, t=t))
    return out


__all__ = ["answer_query", "matches_cue", "returned_entity"]
