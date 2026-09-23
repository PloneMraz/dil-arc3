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

Ported from dil-core against DIL protocol v0.3.2.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field as dc_field
from typing import Any

from collections.abc import Callable

from ..decisions import BASELINE_WINDOW, SUFFICIENT_RECURRENCE
from ..layer import BaseLayer, ContributeFn, EmitFn
from ..types import Expectation, HistoryWindow, InfoUnit, ModField, PredErr
from .t4 import BoundInfo

# Builds the expectation for one entity (DECIDE@IMPL, host-declared).
#
# DEVIATION from dil-core, declared. dil-core hard-codes persistence because its
# minimal host has no model; **this is the seam the thinking organ plugs into**.
# A model supplies the EXPECTATION here and nothing else — it never sees the
# afforded set and never reaches the emission, so it cannot choose. That is the
# settled architecture in the type: the model thinks, the self acts.
#
# It receives the entity, the accrued window for that entity, and this cycle's
# observation — which carries the context the move was made under. It must NOT
# read the observation's effect: that is the answer it is being asked to
# predict, and using it would make the prediction error self-scoring (INV-8).
PredictRule = Callable[[str, HistoryWindow, InfoUnit], InfoUnit]


def persistence(entity_id: str, window: HistoryWindow, observed: InfoUnit) -> InfoUnit:
    """dil-core's declared update law: predict the most recent observation.

    Satisfies conformance C2 — against a stable entity the prediction matches
    and the error falls to zero with repetition — and stays the default, so a
    host that declares no model behaves exactly as the reference does.
    """
    return window[-1] if window else observed


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

        for b in input.bound:
            entity_id = b.entity_id
            observed = b.unit
            window = self._windows.get(entity_id, [])
            count = self._counts.get(entity_id, 0)

            # The declared prediction rule. dil-core's default is persistence;
            # a host with a thinking organ declares its own. Whatever the rule,
            # what leaves here is an expectation and never a choice.
            predicted = self._predict(entity_id, tuple(window), observed)
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

        return T5Output(results=tuple(results))

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
