"""T8 — Multi-Entity Abstraction (protocol §6.3).

Builds RelValue and SocialEdge as the entity count N grows, and closes the loop —
the cycle driver feeds T8 back to T1 (INV-1). RelValue exists only when N ≥ 2: a
relative rank needs something to be relative to. SocialEdge records an
Other↔Other interaction with no self present.

T8-INV (INV-2): an `=` appears only when cognition has stopped. T8's output is a
relative, revisable correlation, never a frozen identity — wired by asserting the
output register is correlational.

Ported from dil-core against DIL protocol v0.3.3.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Final

from ...invariants.guards import assert_correlational
from ...invariants.types import RunningOutput
from ..field import EXPLORATION, NEUTRAL, TRUST, axis, cast_votes, share
from ..layer import BaseLayer, ContributeFn, EmitFn
from ..types import ModField, OtherModel, RelValue, SocialEdge


@dataclass(frozen=True, slots=True)
class ObservedInteraction:
    a_id: str
    b_id: str
    observed_interaction: object


@dataclass(frozen=True, slots=True)
class T8Input:
    others: tuple[OtherModel, ...] = dc_field(default_factory=tuple)
    interactions: tuple[ObservedInteraction, ...] = dc_field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class T8Output:
    rel_values: tuple[RelValue, ...] = dc_field(default_factory=tuple)
    social_edges: tuple[SocialEdge, ...] = dc_field(default_factory=tuple)


def _evidence_of(other: OtherModel, name: str) -> float:
    # A count of evidence, weighed by trust at T6: a number, not only an integer.
    value = getattr(other.independence_evidence, name, None)
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


def _resistances_of(other: OtherModel) -> float:
    return _evidence_of(other, "resistances")


def _pushed_of(other: OtherModel) -> float:
    return _evidence_of(other, "env_pushed")


class T8(BaseLayer):
    index = 8
    consumes: tuple[int, ...] = (6,)

    def process(  # noqa: A002
        self,
        input: T8Input,
        field: ModField,
        emit: EmitFn,
        contribute: ContributeFn,
    ) -> T8Output:

        # THE FIELD (INV-7): exploration decides how deep the Others are
        # compared (decisions.T8_COMPARISON).
        deep = axis(field, EXPLORATION) > NEUTRAL
        # RelValue exists only when N ≥ 2.
        rel_values: tuple[RelValue, ...] = ()
        if len(input.others) >= 2:
            # Sorted by resistance, descending, and — exploring — then by the
            # changes each pushed. Python's sort is stable, as is the
            # reference's, so equal ranks keep their arrival order.
            key = (lambda o: (_resistances_of(o), _pushed_of(o))) if deep else _resistances_of
            ranked = sorted(input.others, key=key, reverse=True)
            rel_values = tuple(
                RelValue(
                    entity_id=other.entity_id,
                    relative_rank=i + 1,
                    comparison_basis="resistance+envPushed" if deep else "resistance",
                )
                for i, other in enumerate(ranked)
            )

        social_edges = tuple(
            SocialEdge(
                a_id=it.a_id,
                b_id=it.b_id,
                observed_interaction=it.observed_interaction,
            )
            for it in input.interactions
        )

        # T8-INV / INV-2: the abstraction is a live correlation, never an identity.
        assert_correlational(
            RunningOutput(register="↔", note="T8 multi-entity abstraction")
        )

        # T8 CLOSES BACK INTO THE LOOP (INV-1; §6.2: "T8 closes back into the
        # loop, not into a sink"). INV-3 forbids carrying relValues and
        # socialEdges back down the meaning-channel; the field can, from N+1: T8
        # votes on the dispositions the layers below it read (DIL-en-v7 §7:
        # "routed by content… to T4… to T6", both of which read trust).
        # Resistance spread evenly across the Others is Others comparable as
        # sources; resistance held by one is one source standing out. Others
        # meeting each other is more of the region to explore.
        n = len(input.others)
        resistances = [_resistances_of(o) for o in input.others]
        total = sum(resistances)
        cast_votes(
            contribute,
            {
                TRUST: 1 - max(resistances) / total if n >= 2 and total > 0 else None,
                EXPLORATION: share(len(social_edges), n) if n >= 2 else None,
            },
        )

        return T8Output(rel_values=rel_values, social_edges=social_edges)


def create_t8() -> T8:
    return T8()
