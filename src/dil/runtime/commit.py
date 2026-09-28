"""Full-system snapshot and restore orchestration (protocol §9).

One whole-state payload per marker. The snapshot covers the ENTIRE system, not
just the store: the stateful layers' accrued state (T2, T5, T6, T7 through their
snapshot surfaces), the GLOB-MOD field, the cycle driver's whole state — its
counter, last emission, the store returns and writes on their way to T1, what it
has recalled, and what was emitted laterally — and the `[data]` working memory.

Restoring re-instates state this very loop accrued — resuming the causal line,
never pre-loading fabricated history (INV-5) — and rewrites ONLY memory-side
state: the `[event]` log and the markers are never touched by a restore.

Ported from dil-core against DIL protocol v0.3.3.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from typing import Any, Final

from ..loop.cycle import DriverState, Layers, PendingWrite
from ..loop.glob_mod import GlobMod
from ..loop.layer import is_snapshottable
from ..loop.layers.t2 import Emission
from ..loop.types import Expectation, InfoUnit, RefFrame, Signal
from ..store.data_store import DataStore
from ..store.tags import FixedTags, TaggedDatum

_STATEFUL: Final = ("t2", "t5", "t6", "t7")


@dataclass(frozen=True, slots=True)
class SystemSnapshot:
    """The whole-system state behind one marker's state hash."""

    layers: dict[str, Any]
    glob: dict[str, Any]
    driver: DriverState
    data: list[tuple[str, TaggedDatum]]


def take_snapshot(
    layers: Layers, glob: GlobMod, driver: DriverState, data: DataStore
) -> SystemSnapshot:
    layer_state: dict[str, Any] = {}
    for key in _STATEFUL:
        spec = getattr(layers, key)
        if is_snapshottable(spec):
            layer_state[key] = spec.snapshot()

    return SystemSnapshot(
        layers=layer_state,
        glob={"params": dict(glob.current().params), "cycle": glob.cycle()},
        driver=driver,
        data=data.entries(),
    )


def restore_snapshot(
    snap: SystemSnapshot, layers: Layers, glob: GlobMod, data: DataStore
) -> DriverState:
    """Restore everything but the driver; returns the driver state to resume with."""
    for key in _STATEFUL:
        spec = getattr(layers, key)
        state = snap.layers.get(key)
        if state is not None and is_snapshottable(spec):
            spec.restore(state)

    glob.restore(snap.glob["params"], snap.glob["cycle"])
    data.clear()
    for k, v in snap.data:
        data.put(k, v)
    return snap.driver


# ── JSON codec for the snapshot ────────────────────────────────────────────
#
# A place the reference did not need and this does. TypeScript is structurally
# typed, so `JSON.parse` hands a layer's `restore` a plain object that behaves
# like the InfoUnit it was, and nothing notices. Python reads attributes, so a
# plain dict would break the first layer that touched it. The snapshot therefore
# carries a tag naming each value's type and is rebuilt into real objects on the
# way back — the same round-trip, done explicitly because the language demands it.

_TAG: Final = "__dil__"


# Values a snapshot keeps as they are. A port-side optimization, not dil-core's
# (LOG.md, 2026-09-28): the encoder asked each cell of every grid whether it was
# a dataclass — 168 million calls in 60 cycles of sb26, two thirds of the run —
# so plain values and rows of them are now recognised first, by type, and the
# same value comes out.
_PLAIN: Final = frozenset({int, float, str, bool, type(None)})


def encode_snapshot_value(value: Any) -> Any:
    """Recursively tag the dataclasses a snapshot carries, for JSON storage."""
    t = type(value)
    if t in _PLAIN:
        return value
    if isinstance(value, dict):
        return {k: v if type(v) in _PLAIN else encode_snapshot_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        if _PLAIN.issuperset(map(type, value)):   # a row of plain values: read by type, in C
            return list(value)
        return [v if type(v) in _PLAIN else encode_snapshot_value(v) for v in value]
    if is_dataclass(value) and not isinstance(value, type):
        return {
            _TAG: t.__name__,
            "fields": {
                f.name: encode_snapshot_value(getattr(value, f.name))
                for f in fields(value)
            },
        }
    return value


def decode_snapshot_value(value: Any) -> Any:
    """Rebuild what `encode_snapshot_value` tagged."""
    if isinstance(value, dict):
        tag = value.get(_TAG)
        if isinstance(tag, str):
            cls = _SNAPSHOT_TYPES.get(tag)
            if cls is None:
                raise ValueError(f"snapshot carries an unknown type tag: {tag}")
            return cls(
                **{k: decode_snapshot_value(v) for k, v in value["fields"].items()}
            )
        return {k: decode_snapshot_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decode_snapshot_value(v) for v in value]
    return value


_SNAPSHOT_TYPES: Final[dict[str, type]] = {
    cls.__name__: cls
    for cls in (
        DriverState, Emission, Expectation, FixedTags, InfoUnit, PendingWrite,
        RefFrame, Signal, TaggedDatum,
    )
}
