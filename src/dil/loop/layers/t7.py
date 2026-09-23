"""T7 — Absence Registration (protocol §6.3).

Emits a signed PredErr for registered absence (ABS-INV): when an entity that was
expected fails to return this cycle, its absence is registered as a NEGATIVE
PredErr — no observation, signed "-". A single silence against a background of
returns is a valid mismatch (§4); unbroken silence is a void field, handled by
the precondition gate, not here.

`T7Input.present` lets the host report which entities the region says are there
this cycle, and an absence is registered only against those. Silence presupposes
the chance to speak. `None` — the default — restores the original behaviour
exactly. (First written here, then carried upstream into dil-core, where the gap
actually was.)

ATTENTION (INV-7). Without it, expectation is FLAT: every entity ever seen is
expected back every cycle, for ever. With one entity that is invisible; with N
entities of which one returns per cycle it is N−1 false absences per cycle —
measured here at 444 of 481 scars over 159 real `ls20` cycles. The loop could
not tell "fell silent" from "not being attended to", having no notion of
attending.

The field supplies it: `attentionGain` scales how long an entity stays expected
after it was last seen. This is the first layer in either implementation to draw
on the modulatory field at all.

WHAT ATTENTION MUST NOT DO. §8.2 defines pure Mode-A as a loop where returns
arrive but are let go unregistered, and §8.4 adds that "a return becomes a datum
only if it is registered". So this gate touches only what is DEMANDED BACK.
Every return still arrives, is still bound, still meets its expectation, and is
still registered. Attention lowers expectation; never registration.

T7 accrues which entities are expected to recur (INV-5): an entity seen at least
`min_observations_to_expect` times is expected next cycle.

Ported from dil-core against DIL protocol v0.3.2.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field as dc_field
from typing import Any, Final, Literal

from ..layer import BaseLayer, ContributeFn, EmitFn
from ..types import InfoUnit, ModField


@dataclass(frozen=True, slots=True)
class ExpectedEntity:
    """One entity's expectation as T7 receives it this cycle."""

    entity_id: str
    predicted: InfoUnit


@dataclass(frozen=True, slots=True)
class T7Input:
    # This cycle's expectations (entity → predicted), used to update memory.
    expectations: tuple[ExpectedEntity, ...] = dc_field(default_factory=tuple)
    # Entities that actually returned this cycle.
    observed: frozenset[str] = dc_field(default_factory=frozenset)
    # Entities the region reports PRESENT this cycle — able to return if they
    # are going to. See HostCycleInput.afforded for why this exists and what it
    # measured. `None` restores dil-core's behaviour exactly.
    present: frozenset[str] | None = dc_field(default=None)


@dataclass(frozen=True, slots=True)
class AbsenceReading:
    """A registered absence — a signed-negative PredErr naming who fell silent.

    It additionally records how many times the entity had been expected, so a
    third party can read the absent source's resistance per-source in the trace.
    It is still a prediction error, usable everywhere one is.
    """

    entity_id: str
    # How many times this entity had been expected (T7's `seen`).
    recurrence: int
    predicted: InfoUnit
    delta: float
    observed: None = None
    signed: Literal["-"] = "-"


@dataclass(frozen=True, slots=True)
class T7Output:
    absences: tuple[AbsenceReading, ...] = dc_field(default_factory=tuple)


# The field parameter that scales the attention span (INV-7, down-channel).
ATTENTION_GAIN: Final = "attentionGain"

# How many expected entities stayed silent this cycle (INV-7, up-channel).
SILENCE: Final = "silence"

# Read-only names for the facts other layers report. Local string constants
# rather than imports, so T7 takes no meaning-channel dependency on T4 or T6
# (INV-3): the field is the down-channel and carries no such tie.
_OTHER_COUNT: Final = "otherCount"
_STRANGENESS: Final = "strangeness"
_CONTEXT_NOVELTY: Final = "contextNovelty"


def attention_width(params: dict[str, float]) -> float:
    """How wide attention is, read off the field (DECIDE@IMPL, tunable).

    ATTENTION IS A COMPOSITION, NOT A FORMULA IN ONE LAYER. An earlier version
    had T6 compute `1/N` and contribute the answer, which made attention a lone
    layer's constant. It is not: it is what the whole field holds. This reads the
    facts each layer reported from its own vantage and composes them —

        otherCount     (T6, accrued)  how many Others the loop is holding
        strangeness    (T4, context)  arrivals that bound to no known entity
        contextNovelty (T5's rule)    whether this SITUATION has been met before

    — so attention narrows as the loop holds more and widens again when either
    what arrives stops being attributable or the situation itself is new. A
    strange or unfamiliar moment earns a longer look; a crowded familiar one does
    not. Every input is a fact from context or environment, not a tuning knob.

    `strangeness` is ENTITY novelty and `contextNovelty` is SITUATION novelty. A
    host can have plenty of the second and none of the first, and this one does:
    it always knows which affordance it used, so `strangeness` is 0 for ever.

    An empty field composes to 1, so a host that reports nothing keeps the
    reference behaviour exactly.
    """
    others = params.get(_OTHER_COUNT, 0.0)
    strangeness = params.get(_STRANGENESS, 0.0)
    novelty = params.get(_CONTEXT_NOVELTY, 0.0)
    return (1.0 + strangeness + novelty) / max(1.0, others)


@dataclass(slots=True)
class _ExpectState:
    predicted: InfoUnit
    seen: int = 0
    # The tick this entity was last seen at — its recency, and its salience.
    last_seen: int = 0


class T7(BaseLayer):
    index = 7
    consumes: tuple[int, ...] = (5,)

    def __init__(
        self,
        min_observations_to_expect: int = 1,
        attention_span: float = float("inf"),
    ) -> None:
        self._min_seen = min_observations_to_expect
        # How many cycles an entity stays expected after it was last seen
        # (DECIDE@IMPL), scaled by the field's gain. Infinity — attend to
        # everything, for ever — is the reference behaviour.
        self._base_span = attention_span
        self._expected: dict[str, _ExpectState] = {}
        # T7 runs once per cycle, so its own call count IS a cycle clock.
        # Accrued, never loaded (INV-5).
        self._tick = 0

    # §9 snapshot surface; `restore` is recovery-only.

    def snapshot(self) -> dict[str, Any]:
        return {
            "expected": [
                (k, {"predicted": v.predicted, "seen": v.seen, "lastSeen": v.last_seen})
                for k, v in self._expected.items()
            ],
            "tick": self._tick,
        }

    def restore(self, state: Any) -> None:
        # A snapshot taken before attention existed carries no lastSeen. It
        # restores to 0 alongside a tick of 0, so the entity reads as freshly
        # seen and stays expected: recovery must not silently NARROW what the
        # loop expects. Dropping out of attention is earned by cycles passing.
        self._expected = {
            k: _ExpectState(
                predicted=v["predicted"], seen=v["seen"], last_seen=v.get("lastSeen", 0)
            )
            for k, v in state["expected"]
        }
        self._tick = state.get("tick", 0)

    def process(  # noqa: A002
        self,
        input: T7Input,
        field: ModField,
        emit: EmitFn,
        contribute: ContributeFn,
    ) -> T7Output:
        self._tick += 1
        # Accrue this cycle's expectations into memory.
        for e in input.expectations:
            st = self._expected.get(e.entity_id)
            if st is None:
                st = _ExpectState(predicted=e.predicted, seen=0, last_seen=self._tick)
                self._expected[e.entity_id] = st
            st.predicted = e.predicted
            st.seen += 1
            st.last_seen = self._tick

        # The attention span in force this cycle: the declared span under the
        # field's gain (INV-7, read as read-only background; T7 never reaches up
        # into the field).
        # The span in force this cycle: the declared span, narrowed or widened
        # by what the field holds, and finally scaled by any explicit gain a host
        # has set. INV-7 down-channel — read as background, never written.
        span = (
            self._base_span
            * attention_width(field.params)
            * field.params.get(ATTENTION_GAIN, 1.0)
        )

        # Register absence for expected entities that did not return, naming
        # which entity fell silent and how many times it had been expected, so
        # the absent source's resistance is readable per-source in the trace.
        absences = tuple(
            AbsenceReading(
                entity_id=entity_id,
                recurrence=st.seen,
                predicted=st.predicted,
                delta=1.0,
            )
            for entity_id, st in self._expected.items()
            if st.seen >= self._min_seen
            and entity_id not in input.observed
            # Silence presupposes the chance to speak: an entity the region says
            # is not present this cycle is not silent, it is simply not there.
            and (input.present is None or entity_id in input.present)
            # Out of attention: the loop is no longer demanding this one back,
            # so its not-returning is not a mismatch. The return itself, if it
            # comes, is registered as it always was.
            and self._tick - st.last_seen <= span
        )
        # A FACT T7 can see: how much of what the loop was waiting for did not
        # arrive. Reported, not interpreted.
        contribute({SILENCE: float(len(absences))})
        return T7Output(absences=absences)

    def info_units(self, output: T7Output) -> Sequence[InfoUnit]:
        # INV-4: the predicted unit of each absence is an InfoUnit.
        return tuple(a.predicted for a in output.absences)


def create_t7(
    min_observations_to_expect: int = 1, attention_span: float = float("inf")
) -> T7:
    return T7(min_observations_to_expect, attention_span)
