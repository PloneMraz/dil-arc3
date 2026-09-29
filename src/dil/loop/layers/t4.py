"""T4 — Context Binding (protocol §6.3).

Binds content to context, by entity id or STRANGER. An InfoUnit that can be
attributed to a known entity is bound to it; one that cannot is bound to
STRANGER — a positional unknown, not an error. The resolver is pluggable with a
declared default.

THE FIELD (INV-7). T4 reads `trust`: how many sightings a named entity takes
before it is bound by its name rather than STRANGER (T4_RECOGNITION) — one at
NEUTRAL, the reference; more with less trust. The arrival is registered either
way. It votes `trust` from what only it sees: the share of this cycle's
arrivals it could bind to a known entity.

Ported from dil-core, first against DIL protocol v0.3.3 (the package
implements `dil.DIL_PROTOCOL_VERSION`); the field from dil-core 1e0a22a.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field as dc_field
from typing import Any, Final

from ..decisions import T4_RECOGNITION
from ..field import TRUST, axis, cast_votes, falling, share, shifted_count
from ..layer import BaseLayer, ContributeFn, EmitFn
from ..types import InfoUnit, ModField

# The positional "unknown entity" binding.
STRANGER: Final = "STRANGER"

# Resolves which entity an InfoUnit concerns, or STRANGER (DECIDE@IMPL).
ContextResolver = Callable[[InfoUnit], str]


def default_resolver(unit: InfoUnit) -> str:
    """An `entity` field in the unit's value, else STRANGER."""
    content = unit.content
    if not isinstance(content, dict):
        return STRANGER
    value = content.get("value")
    if isinstance(value, dict):
        entity = value.get("entity")
        if isinstance(entity, str) and entity:
            return entity
    return STRANGER


@dataclass(frozen=True, slots=True)
class BoundInfo:
    unit: InfoUnit
    # The entity this unit concerns, or STRANGER.
    entity_id: str


@dataclass(frozen=True, slots=True)
class T4Input:
    units: tuple[InfoUnit, ...] = dc_field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class T4Output:
    bound: tuple[BoundInfo, ...] = dc_field(default_factory=tuple)


class T4(BaseLayer):
    index = 4
    consumes: tuple[int, ...] = (3,)

    def __init__(self, resolve: ContextResolver | None = None) -> None:
        self._resolve = resolve if resolve is not None else default_resolver
        # How often each named entity has been sighted (INV-5: accrued, never loaded).
        self._sightings: dict[str, int] = {}

    def snapshot(self) -> dict[str, Any]:
        return {"sightings": sorted(self._sightings.items())}

    def restore(self, state: Any) -> None:
        self._sightings = {k: v for k, v in (state or {}).get("sightings", [])}

    def process(  # noqa: A002
        self,
        input: T4Input,
        field: ModField,
        emit: EmitFn,
        contribute: ContributeFn,
    ) -> T4Output:
        recognition = shifted_count(T4_RECOGNITION, falling(axis(field, TRUST)))
        bound_list: list[BoundInfo] = []
        for unit in input.units:
            named = self._resolve(unit)
            if named == STRANGER:
                bound_list.append(BoundInfo(unit=unit, entity_id=STRANGER))
                continue
            seen = self._sightings.get(named, 0) + 1
            self._sightings[named] = seen
            bound_list.append(BoundInfo(unit=unit, entity_id=named if seen >= recognition else STRANGER))
        bound = tuple(bound_list)
        known = sum(1 for b in bound if b.entity_id != STRANGER)
        cast_votes(contribute, {TRUST: share(known, len(bound))})
        return T4Output(bound=bound)

    def info_units(self, output: T4Output) -> Sequence[InfoUnit]:
        return tuple(b.unit for b in output.bound)


def create_t4(resolve: ContextResolver | None = None) -> T4:
    return T4(resolve)
