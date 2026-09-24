"""T5 — Temporal Expectation (protocol §6.3).

Builds an Expectation per entity and emits a signed PredErr. **This is where
resistance (E2) becomes information**: a mismatch between what was predicted and
what the region returned enters as a signed PredErr — the precursor of a
ResistEvent, and the cycle driver decides whether it holds into a scar.

Update law (DECIDE@IMPL, declared): persistence by default — predict the most
recent observation for the entity — and host-declarable through `PredictRule`,
which is where a model plugs in. This satisfies conformance C2: against a stable
entity the prediction matches and the error falls to zero with repetition. State
accrues per entity across cycles (INV-5); the window is bounded by
BASELINE_WINDOW and confidence ramps over SUFFICIENT_RECURRENCE.

Ported from dil-core against DIL protocol v0.3.3.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field as dc_field
from typing import Any, Final

from collections.abc import Callable

from ..decisions import BASELINE_WINDOW, SUFFICIENT_RECURRENCE
from ..layer import BaseLayer, ContributeFn, EmitFn
from ..types import Expectation, HistoryWindow, InfoUnit, ModField, PredErr
from .t3 import Description, store_query
from .t4 import BoundInfo

# Builds the expectation for one entity (DECIDE@IMPL, host-declared).
#
# DEVIATION from dil-core, declared. dil-core hard-codes persistence because its
# minimal host has no model; **this is the seam the thinking organ plugs into**.
# A model supplies the EXPECTATION here and nothing else — it never sees the
# afforded set and never reaches the committed action, so it cannot choose. That
# is the settled architecture in the type: the model thinks, the self acts.
#
# It can ASK. Thinking that meets a problem goes to memory for what bears on it:
# the rule chooses what to read, and the store is not poured into it. §6.4 makes
# emission "a lateral capability any layer MAY invoke … to obtain what it lacks",
# so the rule receives `ask(cue)`, which emits a store query and nothing else —
# register ↔, one activity record naming T5, its answer arriving at T1 next
# cycle and running every layer, so what the rule read is in the trace. Nothing
# counts or limits how often it asks.
#
# It can WRITE (v0.3.3). Where the thinking is a model, what it makes — a
# program predicting the region — is data, and data not in `[data]` cannot be
# recalled, snapshotted, or read back by a third party. `write` without a
# `datum_id` writes a datum anew: it enters at `nascent`, bearing this cycle's
# mark. With a `datum_id` it revises a datum already held: the content changes,
# the provenance does not, and a `revision` line is recorded. Either way the
# datum arrives at T1 next cycle, is classified SELF_WRITTEN at T2, and runs
# every layer. The driver admits and records; the rule only says what to write.
#
# It receives the entity, the accrued window for that entity, and this cycle's
# observation — which carries the context the move was made under. It must NOT
# read the observation's effect: that is the answer it is being asked to
# predict, and using it would make the prediction error self-scoring (INV-8).
PredictRule = Callable[..., InfoUnit]

# A store query from the rule, by cue (§6.4, §9). It emits nothing else.
AskFn = Callable[[Description], None]


@dataclass(frozen=True, slots=True)
class WriteRequest:
    """What the rule asks to be written: a datum anew, or a revision of one held."""

    payload: object
    # Required for a datum written anew; for a revision, replaces its tags if given.
    open: dict[str, str] | None = None
    # The datum to revise; None to write one anew.
    datum_id: str | None = None
    # What it was built from (v0.3.4 §9): observation units — from the rule's
    # window or the one in front of it — and ids of data it recalled. The driver
    # records the ids, never the content. () says nothing held went into it;
    # None, saying nothing, is refused. Ported from dil-core c2c0cd2.
    built_from: tuple[object, ...] | None = None


# Writing from the rule into `[data]`, through the driver (v0.3.3).
WriteFn = Callable[[WriteRequest], None]


def persistence(
    entity_id: str,
    window: HistoryWindow,
    observed: InfoUnit,
    contribute: Any = None,
    ask: Any = None,
    write: Any = None,
) -> InfoUnit:
    """dil-core's declared update law: predict the most recent observation.

    Satisfies conformance C2 — against a stable entity the prediction matches
    and the error falls to zero with repetition — and stays the default, so a
    host that declares no model behaves exactly as the reference does.
    """
    return window[-1] if window else observed


# Mean prediction error over this cycle's entities (INV-7, up-channel).
SURPRISE: Final = "surprise"


@dataclass(frozen=True, slots=True)
class T5Result:
    entity_id: str
    expectation: Expectation
    pred_err: PredErr


@dataclass(frozen=True, slots=True)
class T5Input:
    bound: tuple[BoundInfo, ...] = dc_field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class T5Output:
    results: tuple[T5Result, ...] = dc_field(default_factory=tuple)
    # What the rule wrote this cycle, in order; the driver takes each into `[data]`.
    writes: tuple[WriteRequest, ...] = dc_field(default_factory=tuple)


def _content_equal(a: InfoUnit, b: InfoUnit) -> bool:
    return json.dumps(a.content, sort_keys=True, default=str) == json.dumps(
        b.content, sort_keys=True, default=str
    )


class T5(BaseLayer):
    index = 5
    consumes: tuple[int, ...] = (4,)

    def __init__(
        self,
        baseline_window: int | None = None,
        sufficient_recurrence: int | None = None,
        predict: PredictRule | None = None,
    ) -> None:
        self._predict = predict if predict is not None else persistence
        self._window_size = (
            baseline_window if baseline_window is not None else BASELINE_WINDOW
        )
        self._recurrence = (
            sufficient_recurrence
            if sufficient_recurrence is not None
            else SUFFICIENT_RECURRENCE
        )
        # Accruing per-entity state (INV-5): accumulated, never reloaded.
        self._windows: dict[str, list[InfoUnit]] = {}
        self._counts: dict[str, int] = {}

    # §9 snapshot surface; `restore` is recovery-only.

    def snapshot(self) -> dict[str, Any]:
        return {
            "windows": [(k, list(v)) for k, v in self._windows.items()],
            "counts": list(self._counts.items()),
        }

    def restore(self, state: Any) -> None:
        self._windows = {k: list(v) for k, v in state["windows"]}
        self._counts = dict(state["counts"])

    def process(  # noqa: A002
        self,
        input: T5Input,
        field: ModField,
        emit: EmitFn,
        contribute: ContributeFn,
    ) -> T5Output:
        results: list[T5Result] = []

        # The rule's road outward: a query to the store, issued from T5.
        def ask(cue: Description) -> None:
            emit(store_query(cue))

        # And its road into the store: what it writes, handed to the driver.
        writes: list[WriteRequest] = []

        def write(request: WriteRequest) -> None:
            writes.append(request)

        for b in input.bound:
            entity_id = b.entity_id
            observed = b.unit
            window = self._windows.get(entity_id, [])
            count = self._counts.get(entity_id, 0)

            # The declared prediction rule. dil-core's default is persistence;
            # a host with a thinking organ declares its own. Whatever the rule,
            # what leaves here is an expectation and never a choice.
            # The rule may report upward into the field; the contribution is
            # bound to T5, since it is T5's declared rule that made it. It may
            # also ask the store; the query is traced to T5 for the same reason.
            predicted = self._predict(
                entity_id, tuple(window), observed, contribute, ask, write
            )
            confidence = min(1.0, count / self._recurrence)

            matched = _content_equal(observed, predicted)
            pred_err = PredErr(
                observed=observed,
                predicted=predicted,
                delta=0.0 if matched else 1.0,
                # A present observation differing from prediction is a positive
                # surprise; absence — a negative — is registered at T7.
                signed="+",
            )
            expectation = Expectation(
                predicted=predicted,
                confidence=confidence,
                # Observations accrued so far, before this one; drives confidence.
                recurrence=count,
                built_from=tuple(window),
            )

            # Accrue this observation into the bounded window.
            next_window = [*window, observed]
            while len(next_window) > self._window_size:
                next_window.pop(0)
            self._windows[entity_id] = next_window
            self._counts[entity_id] = count + 1

            results.append(
                T5Result(entity_id=entity_id, expectation=expectation, pred_err=pred_err)
            )

        # A FACT T5 can see: how far the region fell from expectation, right
        # now. Reported as it is; what follows from it is not T5's to say.
        contribute(
            {
                SURPRISE: (
                    sum(r.pred_err.delta for r in results) / len(results)
                    if results
                    else 0.0
                )
            }
        )
        return T5Output(results=tuple(results), writes=tuple(writes))

    def info_units(self, output: T5Output) -> Sequence[InfoUnit]:
        # INV-4: predicted and observed are InfoUnits leaving the layer.
        units: list[InfoUnit] = []
        for r in output.results:
            units.append(r.expectation.predicted)
            if r.pred_err.observed is not None:
                units.append(r.pred_err.observed)
        return units


def create_t5(
    baseline_window: int | None = None,
    sufficient_recurrence: int | None = None,
    predict: PredictRule | None = None,
) -> T5:
    return T5(
        baseline_window=baseline_window,
        sufficient_recurrence=sufficient_recurrence,
        predict=predict,
    )
