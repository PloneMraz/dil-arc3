"""The [data] store and the provenance lifecycle (protocol §9).

`[data]` is mutable — overwritten each cycle — unlike the immutable `[event]`
log. It is the loop's working memory.

Lifecycle: prior → running → scar. The store records and tags origin ONLY; the
tag is mechanical (presence/absence of a cycle-mark and a resistance-stamp) and
carries no claim of correctness. Two rules are load-bearing:
  - Running many cycles does NOT wash a `prior` to tested status; only
    collision-and-hold does. So `scar` is reachable only from `running`.
  - A `prior` becomes `running` by acquiring a cycle-mark (it has run).

The four fixed tags are never overwritten as a schema: advancing provenance
produces a new datum value carrying the same four tags in order, with the
cycle-mark/provenance advanced — never stripped, reordered, or dropped.

Ported from dil-core against DIL protocol v0.3.2.
"""

from dataclasses import replace
from typing import Final, Protocol

from ..invariants.types import LayerIndex
from .tags import Provenance, TaggedDatum


class LifecycleError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(f"illegal provenance transition: {detail}")


def stamp_layer(datum: TaggedDatum, layer: LayerIndex) -> TaggedDatum:
    """Stamp a datum as it exits a layer: overwrite the floor-tag to the current layer.

    This is the operation every layer T1–T8 performs as a datum passes; there are
    no pass-through layers (protocol §9). The floor-tag slot is overwritten by
    design — the four fixed slots are never stripped or reordered, but their
    values advance under defined rules, and the floor-tag's rule is to track the
    current layer. The *path* is NOT kept here; it is recorded as a `layer-exit`
    line in the `[event]` log as it occurs (§9), and read from there.
    """
    return replace(datum, fixed=replace(datum.fixed, floor_tag=layer))


# The provenance state graph (§9): the legal moves. `prior` is a one-way entry
# (no edge returns to it); `running`, `simulated`, `projected`, `scar` circulate
# with no terminal state — a datum is never a conclusion at rest. Every
# provenance move — at runtime and in the `[event]` trace — is checked against it.
PROVENANCE_EDGES: Final[tuple[tuple[Provenance, Provenance], ...]] = (
    ("prior", "running"),       # host data admitted and run
    ("running", "simulated"),   # taken up into building a situation
    ("simulated", "projected"), # a situation yields the outcome cast from it
    ("simulated", "running"),   # built, but no emission followed; back to use
    ("projected", "simulated"), # the cast outcome does not fit; build again
    ("projected", "scar"),      # the emission was made, the region returned, it held
    ("running", "scar"),        # collided with directly, without a prior cast
    ("projected", "running"),   # an outcome that produced no scar; back to use
    ("scar", "running"),        # a scar returns to the store as data in use
    ("scar", "projected"),      # a scar enriches an outcome already cast
    ("scar", "simulated"),      # a scar re-enters the building of a situation
)

_EDGE_SET: Final[frozenset[tuple[Provenance, Provenance]]] = frozenset(PROVENANCE_EDGES)


def is_provenance_edge(from_: Provenance, to: Provenance) -> bool:
    """Whether a provenance move is a legal edge of the §9 graph."""
    return (from_, to) in _EDGE_SET


def assert_provenance_edge(from_: Provenance, to: Provenance) -> None:
    """Assert a provenance move is a legal edge; raise LifecycleError otherwise."""
    if not is_provenance_edge(from_, to):
        raise LifecycleError(f"{from_} → {to} is not an edge of the §9 provenance graph")


def to_running(datum: TaggedDatum, cycle: int) -> TaggedDatum:
    """→ running.

    A legal move to `running` (from `prior` on first run, or a re-entry from
    `simulated`/`projected`/`scar`). The cycle-mark is set once, when the datum
    first runs (§9): None → cycle; a datum that has already run keeps its mark on
    re-entry.
    """
    assert_provenance_edge(datum.fixed.provenance, "running")
    mark = datum.fixed.cycle_mark if datum.fixed.cycle_mark is not None else cycle
    return replace(datum, fixed=replace(datum.fixed, cycle_mark=mark, provenance="running"))


def to_scar(datum: TaggedDatum, held_resistance: bool) -> TaggedDatum:
    """→ scar.

    Reachable from `running` or `projected` (both valid edges), and ONLY on
    collision-and-hold (a held resistance-stamp). Raises otherwise — a `prior`
    cannot jump to `scar`, and a datum that never held a collision is not a scar.
    """
    assert_provenance_edge(datum.fixed.provenance, "scar")
    if not held_resistance:
        raise LifecycleError(
            "to scar requires a held collision (resistance-stamp); "
            "running alone does not produce a scar"
        )
    return replace(datum, fixed=replace(datum.fixed, provenance="scar"))


def to_simulated(datum: TaggedDatum) -> TaggedDatum:
    """→ simulated (§6.2, forward-building).

    The datum is taken up into the building of a situation. A legal move from
    `running`, `projected`, or `scar`. This is an on-ramp of the graph — WHEN it
    fires is a condition of the running situation, not a scheduled step.
    """
    assert_provenance_edge(datum.fixed.provenance, "simulated")
    return replace(datum, fixed=replace(datum.fixed, provenance="simulated"))


def to_projected(datum: TaggedDatum) -> TaggedDatum:
    """→ projected (§6.2).

    An outcome is cast from a built situation. A legal move from `simulated` or
    `scar` (a scar enriching an outcome already cast). Not yet collided —
    verdict-free.
    """
    assert_provenance_edge(datum.fixed.provenance, "projected")
    return replace(datum, fixed=replace(datum.fixed, provenance="projected"))


class DataStore(Protocol):
    """The mutable [data] store: overwritten each cycle, keyed by datum id."""

    def put(self, id: str, datum: TaggedDatum) -> None: ...
    def get(self, id: str) -> TaggedDatum | None: ...
    def has(self, id: str) -> bool: ...
    def delete(self, id: str) -> bool: ...
    def clear(self) -> None:
        """Clear all entries — `[data]` may be wiped each cycle."""
        ...
    def size(self) -> int: ...
    def entries(self) -> list[tuple[str, TaggedDatum]]:
        """Read-only enumeration of all entries, in insertion order."""
        ...


class InMemoryDataStore:
    """A dict-backed [data] store.

    A TEST FIXTURE, as declared in decisions.STORE_REPRESENTATION: the
    store-of-record lives on the requisitioned substrate, never in RAM.
    """

    __slots__ = ("_map",)

    def __init__(self) -> None:
        self._map: dict[str, TaggedDatum] = {}

    def put(self, id: str, datum: TaggedDatum) -> None:
        self._map[id] = datum

    def get(self, id: str) -> TaggedDatum | None:
        return self._map.get(id)

    def has(self, id: str) -> bool:
        return id in self._map

    def delete(self, id: str) -> bool:
        return self._map.pop(id, None) is not None

    def clear(self) -> None:
        self._map.clear()

    def size(self) -> int:
        return len(self._map)

    def entries(self) -> list[tuple[str, TaggedDatum]]:
        return list(self._map.items())


def create_data_store() -> DataStore:
    return InMemoryDataStore()
