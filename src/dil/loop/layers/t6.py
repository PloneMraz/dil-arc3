"""T6 — Other-Model Synthesis (protocol §6.3, §8.4).

Builds an OtherModel per entity. It lives fully ONLY under Mode-B: the
independence evidence — resistance the agent could not author, plus env-pushed
changes — accrues only when there is real external resistance. Under Mode-A,
where nothing pushes back, the evidence stays zero and the model degenerates.
State accrues per entity (INV-5).

Ported from dil-core, first against DIL protocol v0.3.3 (the package
implements `dil.DIL_PROTOCOL_VERSION`).
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Final

from ..field import EXPLORATION, TRUST, axis, cast_votes, rising, share
from ..layer import BaseLayer, ContributeFn, EmitFn
from ..types import ModField, OtherModel
from .t5 import T5Result


@dataclass(frozen=True, slots=True)
class IndependenceEvidence:
    """Concrete shape of OtherModel.independence_evidence (shared with T8)."""

    # Mismatches the agent met but could not author (resistance), each weighed
    # by trust (one at NEUTRAL).
    resistances: float
    # Changes classified ENV_PUSHED for this entity (from T2), weighed the same.
    env_pushed: float


@dataclass(frozen=True, slots=True)
class T6Input:
    results: tuple[T5Result, ...] = dc_field(default_factory=tuple)
    # Entities whose change this cycle was ENV_PUSHED (from T2's agency tags).
    env_pushed: frozenset[str] = dc_field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class T6Output:
    others: tuple[OtherModel, ...] = dc_field(default_factory=tuple)


@dataclass(slots=True)
class _EntityState:
    # Counted as evidence: one each at NEUTRAL trust, more or less as the field
    # leans (dil-core 1e0a22a).
    resistances: float = 0
    env_pushed: float = 0
    observations: int = 0


class T6(BaseLayer):
    index = 6
    # T6 consumes T5's results AND T2's agency tags, the env-pushed evidence.
    # Under multi-stream it reads both from the meaning-channel itself, rather
    # than having the T2 digest smuggled in by the driver.
    consumes: tuple[int, ...] = (2, 5)

    def __init__(self) -> None:
        self._state: dict[str, _EntityState] = {}

    # §9 snapshot surface; `restore` is recovery-only.

    def snapshot(self) -> dict[str, Any]:
        return {
            "entities": [
                (k, {"resistances": v.resistances, "envPushed": v.env_pushed,
                     "observations": v.observations})
                for k, v in self._state.items()
            ]
        }

    def restore(self, state: Any) -> None:
        self._state = {
            k: _EntityState(
                resistances=v["resistances"],
                env_pushed=v["envPushed"],
                observations=v["observations"],
            )
            for k, v in state["entities"]
        }

    def process(  # noqa: A002
        self,
        input: T6Input,
        field: ModField,
        emit: EmitFn,
        contribute: ContributeFn,
    ) -> T6Output:
        others: list[OtherModel] = []
        # THE FIELD (INV-7): trust weighs how much one resistance, or one change
        # the region pushed, counts as evidence of an independent Other.
        weight = rising(axis(field, TRUST))
        first_met = 0

        for result in input.results:
            entity_id = result.entity_id
            if entity_id not in self._state:
                first_met += 1
            st = self._state.setdefault(entity_id, _EntityState())
            st.observations += 1
            if result.pred_err.delta > 0:
                st.resistances += weight  # resistance met
            if entity_id in input.env_pushed:
                st.env_pushed += weight

            evidence = IndependenceEvidence(
                resistances=st.resistances, env_pushed=st.env_pushed
            )
            observed = result.pred_err.observed
            others.append(
                OtherModel(
                    entity_id=entity_id,
                    context_map={
                        "lastContent": observed.content if observed is not None else None,
                        "observations": st.observations,
                    },
                    independence_evidence=evidence,
                )
            )

        # Its vote: how much of this cycle's Others it met for the first time.
        cast_votes(contribute, {EXPLORATION: share(first_met, len(others))})

        return T6Output(others=tuple(others))


def create_t6() -> T6:
    return T6()
