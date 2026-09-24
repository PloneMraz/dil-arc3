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


# How many Other↔Other interactions T8 recorded this cycle (INV-7, up-channel).
INTERACTIONS: Final = "interactions"
# The share of all resistance held by the most-resisting Other (INV-7,
# up-channel): 1 when one Other does all the resisting, 1/N when it is spread
# evenly, 0 when nothing has resisted yet.
RESISTANCE_CONCENTRATION: Final = "resistanceConcentration"


def _resistances_of(other: OtherModel) -> int:
    evidence = other.independence_evidence
    value = getattr(evidence, "resistances", None)
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


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

        # RelValue exists only when N ≥ 2.
        rel_values: tuple[RelValue, ...] = ()
        if len(input.others) >= 2:
            # Sorted by resistance, descending. Python's sort is stable, as is
            # the reference's, so equal ranks keep their arrival order.
            ranked = sorted(input.others, key=_resistances_of, reverse=True)
            rel_values = tuple(
                RelValue(
                    entity_id=other.entity_id,
                    relative_rank=i + 1,
                    comparison_basis="resistance",
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
        # loop, not into a sink"). Nothing read T8's output, so the top of the
        # meaning-channel was a dead branch. INV-3 forbids carrying it back down
        # the meaning-channel; the field carries it instead, from N+1. T8 reports
        # the two facts only it can see.
        resistances = [_resistances_of(o) for o in input.others]
        total = sum(resistances)
        contribute(
            {
                INTERACTIONS: float(len(social_edges)),
                RESISTANCE_CONCENTRATION: max(resistances) / total if total else 0.0,
            }
        )

        return T8Output(rel_values=rel_values, social_edges=social_edges)


def create_t8() -> T8:
    return T8()
