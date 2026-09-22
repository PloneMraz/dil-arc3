"""The layer scaffold (protocol §6.3).

A uniform contract every layer T1–T8 plugs into. Each layer maps to one link and
satisfies an Input/Output/Precondition/Postcondition contract. The scaffold wires
three invariants at the points the loop touches them:

  - **INV-3** (meaning-channel): a layer may declare it consumes only layers ≤ its
    own index — `validate_layer_spec` halts otherwise.
  - **INV-4** (meaning as relation): every InfoUnit a layer emits MUST carry a
    reference frame — `run_layer` asserts it, defence in depth atop the
    construction-level guarantee.
  - The **floor-tag** stamping every layer performs (§9): `run_layer` calls
    `stamp_layer` so the datum's floor-tag names the layer it just exited. The
    path itself is not kept on the datum — each exit is recorded as a lean line in
    the `[event]` log.

The modulatory field is passed to `process` as read-only background — the
down-channel, INV-7 — and is a separate argument from the meaning-channel inputs,
the up-channel, INV-3. The two channels are never collapsed.

Ported from dil-core against DIL protocol v0.3.2.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from ..invariants.guards import assert_meaning_channel_order, assert_referred
from ..invariants.types import LayerIndex
from ..store.data_store import stamp_layer
from ..store.tags import TaggedDatum
from .types import InfoUnit, ModField

# The lateral emission capability (§6.4) handed to a layer's `process`: pushing a
# committed action out to the region. It is the structural MIRROR of the
# modulatory field (INV-7) — the field descends INTO `process` as read-only
# background, `emit` projects OUT from it — and neither is a station on the
# meaning-channel (INV-3). A layer calls it when its own work requires pushing to
# the region: a T2 probe, a T3 query, a T5 test, a T6 model-test. The issuing
# layer is bound by `run_layer` to the layer's own index; the layer never states
# it. Each declared action is buffered and handed back to the driver, which
# records exactly one activity record naming the issuing layer (§9); the layer
# itself never writes to `[event]`. Register is always ↔ (INV-2) and correctness
# is judged only by the next cycle's return (§6.4).
EmitFn = Callable[[Any], None]


@runtime_checkable
class LayerSpec(Protocol):
    """The uniform layer contract."""

    index: LayerIndex
    # Meaning-channel dependencies: layer indices this layer consumes (≤ index).
    consumes: tuple[LayerIndex, ...]

    def pre(self, input: Any) -> None:
        """Precondition — raises if the input does not satisfy the contract."""
        ...

    def process(self, input: Any, field: ModField, emit: EmitFn) -> Any:
        """The layer's work.

        Reads the modulatory field as read-only background (down-channel), and
        MAY invoke `emit` to push a committed action to the region (§6.4,
        lateral). Most layers never emit and ignore the argument.
        """
        ...

    def post(self, output: Any) -> None:
        """Postcondition — raises if the output does not satisfy the contract."""
        ...

    def info_units(self, output: Any) -> Sequence[InfoUnit]:
        """The InfoUnits this output carries, for INV-4 enforcement."""
        ...


class BaseLayer:
    """Default no-op pre/post/info_units, so a layer states only what it needs.

    The reference makes these optional properties of an object literal; Python
    reaches the same place with a base class, which also keeps `index` and
    `consumes` in one declared spot.
    """

    index: LayerIndex
    consumes: tuple[LayerIndex, ...] = ()

    def pre(self, input: Any) -> None:  # noqa: A002 — mirrors the reference's name
        return None

    def post(self, output: Any) -> None:
        return None

    def info_units(self, output: Any) -> Sequence[InfoUnit]:
        return ()

    def process(self, input: Any, field: ModField, emit: EmitFn) -> Any:  # noqa: A002
        raise NotImplementedError


def validate_layer_spec(spec: LayerSpec) -> None:
    """INV-3 at registration.

    A layer may consume only layers ≤ its own index on the meaning-channel.
    Halts if it declares otherwise.
    """
    for source in spec.consumes:
        assert_meaning_channel_order(spec.index, source)


@runtime_checkable
class Snapshottable(Protocol):
    """A stateful layer exposes its accrued state for the §9 commit snapshot.

    `restore` is RECOVERY-ONLY: it re-instates state this very loop accrued,
    resuming the causal line. It is not a within-cycle operation and never a
    pre-load of fabricated history, so INV-5 is untouched.
    """

    def snapshot(self) -> Any: ...
    def restore(self, state: Any) -> None: ...


def is_snapshottable(spec: object) -> bool:
    """Whether a layer spec exposes snapshot surfaces."""
    return callable(getattr(spec, "snapshot", None)) and callable(
        getattr(spec, "restore", None)
    )


@dataclass(frozen=True, slots=True)
class LayerEmission:
    """One action a layer emitted during its run, tagged with the layer (§6.4)."""

    issuing_layer: LayerIndex
    action: object


@dataclass(frozen=True, slots=True)
class LayerRun:
    output: Any
    # The datum after this layer stamped its floor-tag.
    datum: TaggedDatum
    # The actions this layer emitted during `process` (§6.4), each already bound
    # to this layer's index. The driver records one activity record per emission;
    # the layer itself never touches `[event]`. Empty for layers that do not emit.
    emissions: tuple[LayerEmission, ...] = ()


def run_layer(
    spec: LayerSpec,
    input: Any,  # noqa: A002 — mirrors the reference's parameter name
    field: ModField,
    datum: TaggedDatum,
) -> LayerRun:
    """Run one layer over its input under the modulatory field, against a datum.

    Order: precondition → process (with the lateral emit capability) → INV-4
    check on emitted InfoUnits → postcondition → stamp the floor-tag.

    Emissions the layer declares through `emit` are buffered here, bound to the
    layer's index so the layer never states its own issuing layer, and returned
    for the driver to record. `run_layer` never writes to `[event]`.
    """
    spec.pre(input)

    emissions: list[LayerEmission] = []

    def emit(action: Any) -> None:
        emissions.append(LayerEmission(issuing_layer=spec.index, action=action))

    output = spec.process(input, field, emit)

    for unit in spec.info_units(output):
        assert_referred(unit)  # INV-4: a reference frame is present

    spec.post(output)
    stamped = stamp_layer(datum, spec.index)
    return LayerRun(output=output, datum=stamped, emissions=tuple(emissions))
