"""T4 — Context Binding (protocol §6.3).

Binds content to context, by entity id or STRANGER. An InfoUnit that can be
attributed to a known entity is bound to it; one that cannot is bound to
STRANGER — a positional unknown, not an error. The resolver is pluggable with a
declared default.

Ported from dil-core against DIL protocol v0.3.3.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field as dc_field
from typing import Any, Final

from ..layer import BaseLayer, ContributeFn, EmitFn
from ..types import InfoUnit, ModField

# The positional "unknown entity" binding.
STRANGER: Final = "STRANGER"

# The share of arriving units that bound to STRANGER (INV-7, up-channel).
STRANGENESS: Final = "strangeness"

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

    def process(  # noqa: A002
        self,
        input: T4Input,
        field: ModField,
        emit: EmitFn,
        contribute: ContributeFn,
    ) -> T4Output:
        bound = tuple(
            BoundInfo(unit=unit, entity_id=self._resolve(unit))
            for unit in input.units
        )
        # A FACT T4 can see and no other layer can: how much of what arrived
        # could not be attributed to a known entity. Context novelty, reported
        # and not interpreted.
        strangers = sum(1 for b in bound if b.entity_id == STRANGER)
        contribute({STRANGENESS: strangers / len(bound) if bound else 0.0})
        return T4Output(bound=bound)

    def info_units(self, output: T4Output) -> Sequence[InfoUnit]:
        return tuple(b.unit for b in output.bound)


def create_t4(resolve: ContextResolver | None = None) -> T4:
    return T4(resolve)
