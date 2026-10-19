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

Ported from dil-core, first against DIL protocol v0.3.3 (the package
implements `dil.DIL_PROTOCOL_VERSION`).
"""

from __future__ import annotations

import inspect

import json
from collections.abc import Sequence
from dataclasses import dataclass, field as dc_field
from typing import Any

from collections.abc import Callable

from ..decisions import BASELINE_WINDOW, SUFFICIENT_RECURRENCE
from ..field import ALERTNESS, EXPLORATION, axis, cast_votes, falling, shifted_count
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
#
# It returns the expected unit, or an `Expecting`: the unit with the held data it
# is (v0.3.5). A rule that returns a unit it took from its window — persistence
# does — says nothing more, since the driver knows which datum that unit came
# from. A rule that makes its expectation anew, by running a program it wrote,
# is the only thing that knows which datum it ran, so it names it.
PredictRule = Callable[..., "InfoUnit | Expecting"]


@dataclass(frozen=True, slots=True)
class Expecting:
    """An expectation, with the held data it is (v0.3.5 §6.1): units or datum ids."""

    predicted: InfoUnit
    held_by: tuple[object, ...] = ()

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


# It can READ. DEVIATION from dil-core, declared, additive and defaulted
# (dil-arc3, 2026-10-05; queued for dil-core). The whole store is the agent's
# memory (v0.3.6 §9), and what a model computes from, the mind takes from it.
# `ask` answers a cycle later and runs every layer; `read` is a view of `[data]`
# the rule reads directly, in the cycle. It is memory alone: a datum admitted in
# the cycle reading is met in it, not recalled, and the view does not
# return it — nor anything written in the cycle, which the driver takes after
# the pass. The driver records each cycle's reads in `[event]`, one `read` line
# for each purpose. `id_of` names the datum an observation unit of an earlier
# cycle came from, so the rule can read it later by its id.
@dataclass(frozen=True, slots=True)
class StoreView:
    """The rule's read-only view of `[data]`, for one cycle."""

    # read(datum_id, purpose) -> the datum as `[data]` holds it, or None.
    read: Callable[[str, str], Any]
    id_of: Callable[[InfoUnit], "str | None"]


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




@dataclass(frozen=True, slots=True)
class T5Result:
    entity_id: str
    expectation: Expectation
    pred_err: PredErr


@dataclass(frozen=True, slots=True)
class T5Input:
    bound: tuple[BoundInfo, ...] = dc_field(default_factory=tuple)
    # The cycle's view of `[data]`, from the driver (DEVIATION: READ, above).
    view: StoreView | None = None


@dataclass(frozen=True, slots=True)
class T5Output:
    results: tuple[T5Result, ...] = dc_field(default_factory=tuple)
    # What the rule wrote this cycle, in order; the driver takes each into `[data]`.
    writes: tuple[WriteRequest, ...] = dc_field(default_factory=tuple)
    # The actions the rule pushed to the region as tests this cycle, in order (§6.4).
    tests: tuple[Any, ...] = dc_field(default_factory=tuple)


# An action pushed to the region to test an expectation (§6.4): "an action that
# pushes to the region to see whether the return matches the Expectation just
# built". The rule thinks; it does not act: a test is recorded as an emission
# from T5, and it reaches the region only if the host has a body to carry it
# out. Ported from dil-core a8ef7ce.
TestFn = Callable[[Any], None]


def region_test(action: Any) -> dict[str, Any]:
    """The emission a test is recorded as: an action for the region, from T5."""
    return {"kind": "test", "action": action}


def _takes_test(rule: Callable[..., Any]) -> bool:
    """Whether a rule receives `test`: rules written before it existed do not."""
    try:
        params = inspect.signature(rule).parameters.values()
    except (TypeError, ValueError):
        return False
    return any(p.kind is p.VAR_KEYWORD or p.name == "test" for p in params) or \
        sum(p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) for p in params) >= 7


def _takes_field(rule: Callable[..., Any]) -> str | None:
    """How a rule receives the field, if it does: by name, or as its eighth argument.

    The rule — where the mind sits — receives the cycle's field as every layer
    does (INV-7): how alert to mismatch, how far to explore. A rule written
    before the field reached it does not take it (dil-core 1e0a22a)."""
    try:
        params = list(inspect.signature(rule).parameters.values())
    except (TypeError, ValueError):
        return None
    if any(p.name == "field" for p in params) or any(p.kind is p.VAR_KEYWORD for p in params):
        return "keyword"
    if sum(p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) for p in params) >= 8:
        return "positional"
    return None


def _takes_read(rule: Callable[..., Any]) -> bool:
    """Whether a rule receives the store's view, by name (DEVIATION: READ)."""
    try:
        params = inspect.signature(rule).parameters.values()
    except (TypeError, ValueError):
        return False
    return any(p.kind is p.VAR_KEYWORD or p.name == "read" for p in params)


def _content_equal(a: InfoUnit, b: InfoUnit) -> bool:
    return json.dumps(a.content, sort_keys=True, default=str) == json.dumps(
        b.content, sort_keys=True, default=str
    )


# Whether an observation fits its expectation (DECIDE@IMPL tag H, host-declared).
#
# DEVIATION from dil-core, declared, additive and defaulted: dil-core compares the
# whole content, which is what holds here when a host declares nothing. A host
# whose expectation is of one reading of what arrives — this one expects the last
# grid of a frame's stack, not the stack — declares that reading here, so the
# mismatch T5 records is the one its thinking organ met (dil-arc3, 2026-09-29).
FitRule = Callable[[InfoUnit, InfoUnit], bool]


class T5(BaseLayer):
    index = 5
    consumes: tuple[int, ...] = (4,)

    def __init__(
        self,
        baseline_window: int | None = None,
        sufficient_recurrence: int | None = None,
        predict: PredictRule | None = None,
        fit: FitRule | None = None,
        alerted_by: Callable[[InfoUnit], bool] | None = None,
    ) -> None:
        self._predict = predict if predict is not None else persistence
        # DEVIATION (dil-arc3, 2026-10-11): what its alertness vote counts, as the
        # host declares it — the returns it says can alert the loop. Every return,
        # as dil-core does, when a host declares none.
        self._alerted_by = alerted_by
        self._fit = fit if fit is not None else _content_equal
        self._predict_tests = _takes_test(self._predict)
        self._predict_field = _takes_field(self._predict)
        self._predict_read = _takes_read(self._predict)
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
        # The field's reading (INV-7): how long a baseline it keeps — exploring
        # keeps less, consolidating more. Never into confidence: §13.4 reads a
        # confidence that fails to rise with recurrence as the reloading
        # signature. What is accrued is kept whole; the field shifts how much of
        # it is read.
        window_now = int(shifted_count(self._window_size, falling(axis(field, EXPLORATION))))

        # The rule's road outward: a query to the store, issued from T5.
        def ask(cue: Description) -> None:
            emit(store_query(cue))

        # And its road into the store: what it writes, handed to the driver.
        writes: list[WriteRequest] = []

        def write(request: WriteRequest) -> None:
            writes.append(request)

        # And its road to the region: a test, recorded from T5 (§6.4).
        tests: list[Any] = []

        def test(action: Any) -> None:
            tests.append(action)
            emit(region_test(action))

        for b in input.bound:
            entity_id = b.entity_id
            observed = b.unit
            window = self._windows.get(entity_id, [])[-window_now:]
            count = self._counts.get(entity_id, 0)

            # The declared prediction rule. dil-core's default is persistence;
            # a host with a thinking organ declares its own. Whatever the rule,
            # what leaves here is an expectation and never a choice.
            # The rule may report upward into the field; the contribution is
            # bound to T5, since it is T5's declared rule that made it. It may
            # also ask the store; the query is traced to T5 for the same reason.
            args: tuple[Any, ...] = (entity_id, tuple(window), observed, contribute, ask, write)
            more: dict[str, Any] = {"read": input.view} if self._predict_read else {}
            if self._predict_field == "keyword":
                out = self._predict(*args, test, field=field, **more)
            elif self._predict_field == "positional":
                out = self._predict(*args, test, field, **more)
            elif self._predict_tests:
                out = self._predict(*args, test, **more)
            else:
                out = self._predict(*args, **more)
            declared = isinstance(out, Expecting)
            predicted = out.predicted if declared else out
            confidence = min(1.0, count / self._recurrence)

            matched = self._fit(observed, predicted)
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
                # Named by the rule, or — for a unit it took from its window —
                # that unit, which the driver resolves to its datum.
                held_by=tuple(out.held_by) if declared else (out,),
                held_by_declared=declared,
            )

            # Accrue this observation into the bounded window: kept up to the
            # longest baseline the field can ask for, read up to the one it asks
            # for now.
            next_window = [*self._windows.get(entity_id, []), observed]
            while len(next_window) > self._window_size * 2:
                next_window.pop(0)
            self._windows[entity_id] = next_window
            self._counts[entity_id] = count + 1

            results.append(
                T5Result(entity_id=entity_id, expectation=expectation, pred_err=pred_err)
            )

        # Its vote: how much of what returned did not match what it expected —
        # of the returns the host says can alert it (DEVIATION 8), all by default.
        counted = [r for r in results if self._alerted_by is None
                   or (r.pred_err.observed is not None and self._alerted_by(r.pred_err.observed))]
        cast_votes(
            contribute,
            {ALERTNESS: sum(r.pred_err.delta for r in counted) / len(counted) if counted else None},
        )
        return T5Output(results=tuple(results), writes=tuple(writes), tests=tuple(tests))

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
    fit: FitRule | None = None,
    alerted_by: Callable[[InfoUnit], bool] | None = None,
) -> T5:
    return T5(
        baseline_window=baseline_window,
        sufficient_recurrence=sufficient_recurrence,
        predict=predict,
        fit=fit,
        alerted_by=alerted_by,
    )
