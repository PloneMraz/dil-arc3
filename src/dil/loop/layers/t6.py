"""T6 — Other-Model Synthesis (protocol §6.3, §8.4).

Builds an OtherModel per entity. It lives fully ONLY under Mode-B: the
independence evidence — resistance the agent could not author, plus env-pushed
changes — accrues only when there is real external resistance. Under Mode-A,
where nothing pushes back, the evidence stays zero and the model degenerates.
State accrues per entity (INV-5).

Ported from dil-core against DIL protocol v0.3.2.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Final

from ..layer import BaseLayer, ContributeFn, EmitFn
from ..types import ModField, OtherModel
from .t5 import T5Result


@dataclass(frozen=True, slots=True)
class IndependenceEvidence:
    """Concrete shape of OtherModel.independence_evidence (shared with T8)."""

    # Mismatches the agent met but could not author (resistance).
    resistances: int
    # Changes classified ENV_PUSHED for this entity (from T2).
    env_pushed: int


@dataclass(frozen=True, slots=True)
class T6Input:
    results: tuple[T5Result, ...] = dc_field(default_factory=tuple)
    # Entities whose change this cycle was ENV_PUSHED (from T2's agency tags).
    env_pushed: frozenset[str] = dc_field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class T6Output:
    others: tuple[OtherModel, ...] = dc_field(default_factory=tuple)


# The field parameter T6 sets: how wide attention is, given how many Others the
# loop is holding.
ATTENTION_GAIN_PARAM: Final = "attentionGain"


def attention_gain_for(n: int) -> float:
    """Attention width for N Others (DECIDE@IMPL, tunable and NOT derived).

    1/N: attending to four things is not attending to one thing four times over.
    The SHAPE is what is argued for — the false-absence load a flat expectation
    carries grows with N, so the width that answers it has to fall with N. The
    constant itself has nothing behind it but a measurement on two games, and is
    declared tunable for that reason.

    T6 is the layer that holds this, because it is the layer that ACCRUES
    Others. T8 had the job first and it did not work: T8 ranks the Others
    PRESENT this cycle, so in a host where one entity returns per cycle it saw
    N = 1 every time and the width never moved. Measured live: the gain sat at
    1.0 for 80 cycles while four affordances were being held.
    """
    return 1.0 / max(1, n)


@dataclass(slots=True)
class _EntityState:
    resistances: int = 0
    env_pushed: int = 0
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

        for result in input.results:
            entity_id = result.entity_id
            st = self._state.setdefault(entity_id, _EntityState())
            st.observations += 1
            if result.pred_err.delta > 0:
                st.resistances += 1  # resistance met
            if entity_id in input.env_pushed:
                st.env_pushed += 1

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

        # The width of attention, contributed upward into the field (INV-7).
        # It blends with every other contribution and lands at N+1.
        contribute({ATTENTION_GAIN_PARAM: attention_gain_for(len(self._state))})

        return T6Output(others=tuple(others))


def create_t6() -> T6:
    return T6()
