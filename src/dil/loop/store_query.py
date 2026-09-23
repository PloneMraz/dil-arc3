"""Answering a store query (§6.4 T3 query; §9 open layer; §12 tag F).

T3 asks with a description of what just arrived. The store answers with every
datum whose open tags carry that same description — each cue key present, with
the same value. That is the whole index: §9 already requires a key to denote the
same dimension wherever it appears, "so the `[event]` log is filterable", and a
filter is what this is.

The answer is a set of Signals on the store channel, ingested at T1 the next
cycle like any query-return (§6: "input channels: query returns"). Nothing is
read into any layer here, and nothing is changed in `[data]`: the provenance move
happens when the datum actually runs, and the driver records it then.

Ported from dil-core against DIL protocol v0.3.2.
"""

from __future__ import annotations

from typing import Any

from ..store.data_store import DataStore
from ..store.tags import TaggedDatum
from .layers.t3 import STORE_CHANNEL, Description
from .types import Signal


def matches_cue(datum: TaggedDatum, cue: Description) -> bool:
    """Whether a datum's open tags carry every pair of the cue."""
    return len(cue) > 0 and all(datum.open.get(k) == v for k, v in cue.items())


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
        }
        out.append(Signal(source_id=STORE_CHANNEL, raw_payload=ret, t=t))
    return out


__all__ = ["answer_query", "matches_cue", "returned_entity"]
