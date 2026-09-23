"""The cycle driver (protocol §6).

Runs ONE pass of the loop per cycle, in one of two flow modes:

  - **Cycle-0 — single-threaded**: a direct hand-off pipeline T1→T8, because
    multi-stream flow presupposes a self for the streams to coordinate around,
    and at cycle-0 it does not yet exist.
  - **Cycle-1 onward — multi-stream**: the self crystallized at T2 of cycle-0
    (§7), so every layer is an active site. Each publishes its output on the
    meaning-channel and each consumer READS its declared dependency set from it —
    consumption, not dispatch, INV-3 guarded per read. Fan-out is real: T5's one
    published output is read by both T6 and T7, and T6 reads T2's output itself.
    The schedule is declared in decisions.py: one topological activation pass, in
    cycle-time not wall-clock, with no OS concurrency claimed.

Either way the cycle datum threads T1→T8, its floor-tag updating to the current
layer and each layer-exit recorded as a lean line in the `[event]` log — the path
lives there, never in a running-type field (§6.1). The mode rides along as the
open tag `flow`, trace-visible to an auditor (§13.3). Then: the appraisal step
(INV-8) under the cycle's GLOB-MOD context, a response that feeds back as the
next cycle's emission (INV-1), held collisions recorded as scars in the
append-only `[event]` log, and GLOB-MOD advanced to N+1.

This module runs one cycle correctly; it makes no self-continuity claim.

Ported from dil-core against DIL protocol v0.3.2.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field as dc_field, replace
from typing import Any, Literal, TypeAlias

from ..invariants.types import LayerIndex
from ..store.data_store import (
    DataStore,
    stamp_layer,
    to_projected,
    to_running,
    to_scar,
    to_simulated,
)
from ..store.decisions import (
    CONTEXT_ANCHOR_DEPTH,
    FIT_FLOOR,
    FIT_FLOOR_PARAM,
    H_COUNT,
)
from ..store.event_log import EventLog
from ..store.resist_event import (
    ActivityEvent,
    ContextAnchor,
    RecalledTags,
    ResistEvent,
    record_activity,
    record_crystallization,
    record_emission,
    record_expectation,
    record_layer_exit,
    record_provenance,
    record_resistance_reading,
    record_scar,
)
from ..store.tagging_gate import HostDatum, admit_host_data
from ..store.tags import TaggedDatum
from .appraisal import AppraisalInput, appraise
from .gathers import (
    gather_t2,
    gather_t3,
    gather_t4,
    gather_t5,
    gather_t6,
    gather_t7,
    gather_t8,
)
from .glob_mod import GlobMod
from .layer import LayerContribution, LayerEmission, LayerSpec, run_layer
from .layers.t2 import Emission, ObservedChange, T2Input
from .layers.t3 import is_store_query, store_query
from .layers.t4 import T4Input
from .layers.t5 import T5Input, T5Output
from .layers.t6 import T6Input
from .layers.t7 import ExpectedEntity, T7Input, T7Output
from .layers.t8 import ObservedInteraction, T8Input
from .meaning_channel import create_meaning_channel
from .store_query import answer_query, returned_entity
from .types import Appraisal, Directive, InfoUnit, ModField, PredErr, Signal

# Identifier of the agent's editable state, for the INV-8 appraisal check.
EDITED_STATE_ID = "agent-state"

# The flow mode a cycle ran in (protocol §6, §13.3).
FlowMode: TypeAlias = Literal["single-threaded", "multi-stream"]


@dataclass(frozen=True, slots=True)
class Layers:
    """The eight layer specs the driver runs. Created once; they accrue state."""

    t1: LayerSpec
    t2: LayerSpec
    t3: LayerSpec
    t4: LayerSpec
    t5: LayerSpec
    t6: LayerSpec
    t7: LayerSpec
    t8: LayerSpec


@dataclass(frozen=True, slots=True)
class DriverState:
    """The cycle driver's own accrued state (part of the §9 snapshot)."""

    cycle: int
    last_emission: Emission
    # Store query-returns answered at the close of the last cycle and not yet
    # ingested (§6.4 T3 query). They arrive at T1 of the next cycle.
    pending_returns: tuple[Signal, ...] = ()
    # Every datum ever recalled from the store — they return only when asked.
    recalled: tuple[str, ...] = ()
    # Actions layers emitted laterally last cycle, for T2 to read (§6.4).
    last_lateral: tuple[object, ...] = ()


@dataclass(frozen=True, slots=True)
class HostCycleInput:
    """What the host supplies for one cycle."""

    signals: tuple[Signal, ...] = dc_field(default_factory=tuple)
    # Observed changes after the emission; `id` is treated as the entity id.
    changes: tuple[ObservedChange, ...] = dc_field(default_factory=tuple)
    interactions: tuple[ObservedInteraction, ...] = dc_field(default_factory=tuple)
    # DEVIATION from dil-core, declared. Entity ids the region says are PRESENT
    # this cycle — able to return if they are going to. T7 registers an absence
    # only against these, because an entity the region itself says is not there
    # cannot be silent; silence presupposes the chance to speak.
    #
    # Needed because this host's entities are affordances, which return only when
    # the agent uses one, and it uses one per cycle. Without it, N-1 absences
    # were recorded every cycle for ever: measured at 444 of 481 scars over 159
    # real ls20 cycles. `None` means the host does not report presence and the
    # original behaviour holds exactly, so dil-core's semantics are unchanged.
    afforded: frozenset[str] | None = None


@dataclass(frozen=True, slots=True)
class RespondContext:
    """What the terminal response is built from (§6.4, link 5).

    Handed to the host's declared `RespondPolicy` at the close of the
    meaning-channel, after appraisal. Everything a committed action may be built
    from is here and nothing else: the appraisal that judged the cycle, the
    per-entity expectations the loop holds, and what the region supplied.
    """

    cycle: int
    appraisal: Appraisal
    # The modulatory field in force this cycle — read-only background (INV-7).
    #
    # WHY IT IS HERE. Behaviour is constructed at this point, and until now this
    # was the one place the field could not reach: the context carried the
    # appraisal, the expectations and the host's input, and not the field. So
    # anything the field came to hold — attention, and whatever stands for want —
    # could not affect what the agent did. That is the same failure found twice
    # already in this ring: a channel present in the topology that nothing draws
    # on. §6 is explicit that the field is "a global gain and bias shifting every
    # link's parameters at once", and link 5 is a link.
    field: ModField
    # The loop's expectations this cycle, entity by entity — including each
    # one's confidence and recurrence.
    expectations: tuple[Any, ...]
    # What the region supplied this cycle, including the afforded entity set.
    host: HostCycleInput


# Builds the cycle's committed action (DECIDE@IMPL, host-declared).
RespondPolicy: TypeAlias = Callable[[RespondContext], Any]


def default_respond(ctx: RespondContext) -> Any:
    """dil-core's minimal-host response: a marker, carrying no action.

    It is what a host with no region to push into can honestly commit to. A host
    with a real region declares its own policy; this stays the default so the
    reference behaviour is unchanged when none is declared.
    """
    return {"kind": "respond", "cycle": ctx.cycle, "valence": ctx.appraisal.valence}


@dataclass(frozen=True, slots=True)
class CycleResult:
    cycle: int
    # The flow mode this cycle ran in (also recorded as the `flow` open tag).
    flow: FlowMode
    appraisal: Appraisal
    # The action emitted — the next cycle's emission (feedback, INV-1).
    response: Emission
    # Collisions recorded as scars in [event] this cycle.
    scars: int
    absences: int
    # Distinct sources whose return resisted this cycle (for diversity monitoring).
    collision_sources: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _LayerPass:
    """What a layer pass hands to the cycle tail (appraisal, scars, feedback)."""

    datum: TaggedDatum
    t5: T5Output
    t7: T7Output
    # T2 first drew the self/environment distinction this pass (§7).
    crystallized: bool
    # Lateral emissions raised by any layer this pass (§6.4), each bound to its
    # issuer.
    emissions: tuple[LayerEmission, ...]
    # Field contributions declared by any layer this pass (INV-7), each bound to
    # its issuer.
    contributions: tuple[LayerContribution, ...] = ()


class Cycle:
    """One pass of the loop per `run`."""

    __slots__ = (
        "_layers", "_glob", "_data", "_events", "_channel", "_now",
        "_cycle", "_last_emission", "_cycle_t", "_respond", "_recollection",
        "_pending", "_recalled", "_unasked", "_last_lateral", "_running_recalled",
    )

    def __init__(
        self,
        layers: Layers,
        glob: GlobMod,
        data: DataStore,
        events: EventLog,
        initial_emission: Emission,
        now: Callable[[], int] | None = None,
        resume: DriverState | None = None,
        respond: RespondPolicy | None = None,
        recollection: Any = None,
    ) -> None:
        # The host's resistance-retrieval channel (§10), if one is declared. The
        # driver does not call it — T5 does, through its declared PredictRule.
        # The driver only asks which scars it returned, so their return can be
        # recorded in `[event]` (§9: every transition along a provenance edge is
        # recorded as it occurs). Without this, `scar → running` could never
        # fire and the store would stay write-only.
        self._recollection = recollection
        # DEVIATION from dil-core, declared. The content of the terminal
        # emission is host-declared, exactly as T3's transducers and T4's
        # resolver already are. dil-core hard-codes a marker because its
        # minimal host has no region to push into; a host with a real region
        # must be able to commit a real action, or INV-1 never closes.
        #
        # The seam is here — at the close of the meaning-channel, after
        # appraisal, issuing layer T8 — and NOT in a layer. A layer emitting the
        # move would make the thinking organ the actor. The action issues from
        # the whole loop.
        self._respond = respond if respond is not None else default_respond
        self._layers = layers
        self._glob = glob
        self._data = data
        self._events = events
        self._channel = create_meaning_channel()
        # The host's server clock in epoch milliseconds — the wall-clock where
        # the host operates. It stamps `[event]` timestamps so an auditor can
        # compare and sync a datum's diary. The cycle mark is recorded separately.
        self._now = now if now is not None else (lambda: int(time.time() * 1000))
        self._cycle = resume.cycle if resume is not None else 0
        self._last_emission = (
            resume.last_emission if resume is not None else initial_emission
        )
        # Wall-clock of the cycle currently running.
        self._cycle_t = 0
        # Store query-returns awaiting ingestion at the next cycle's T1 (§6.4).
        self._pending: list[Signal] = (
            list(resume.pending_returns) if resume is not None else []
        )
        # Every datum ever recalled; each returns only on a cycle it was asked for.
        self._recalled: set[str] = set(resume.recalled) if resume is not None else set()
        # Recalled data not arriving this cycle — no absence is owed by them (T7).
        self._unasked: frozenset[str] = frozenset()
        # Data recalled from the store that run this cycle. They pass the layers
        # with the cycle datum, so each exit is theirs too: "every layer a datum
        # exits MUST be recorded" (§9), and there are no pass-through layers.
        self._running_recalled: tuple[str, ...] = ()
        # What layers emitted laterally last cycle — readable by T2 now (§6.4).
        self._last_lateral: tuple[object, ...] = (
            tuple(resume.last_lateral) if resume is not None else ()
        )

    # ── identifiers and the two [event] sinks ──────────────────────────────

    def _datum_id(self) -> str:
        """The id the cycle datum takes in `[data]`; also its key in the path."""
        return f"cycle-{self._cycle}"

    def _log_exit(self, layer: LayerIndex) -> None:
        """Log one `layer-exit` line as the cycle datum leaves a layer (§9)."""
        self._events.append(
            record_layer_exit(self._datum_id(), self._cycle, layer, self._cycle_t)
        )
        for datum_id in self._running_recalled:
            self._events.append(
                record_layer_exit(datum_id, self._cycle, layer, self._cycle_t)
            )

    def _emit(self, issuing_layer: LayerIndex, action: Any) -> Any:
        """Emission — link 5 as a lateral capability (§6.4).

        The one sink through which every emission is recorded: it writes exactly
        one activity record naming the issuing layer, register ↔, never =. There
        is NO internal arbiter — a conflict among emissions is collided against
        the region, not adjudicated. Two callers reach it: any layer, via the
        bound `emit` handed to its `process`, each carrying its own issuing
        layer; and the driver, for the appraisal-driven terminal response at the
        close of the meaning-channel, issuing layer T8.
        """
        self._events.append(
            record_emission(
                self._datum_id(), self._cycle, issuing_layer, action, self._cycle_t
            )
        )
        return action

    # ── the two flow modes ─────────────────────────────────────────────────

    def _pass_single_threaded(
        self, host: HostCycleInput, field: ModField, datum0: TaggedDatum
    ) -> _LayerPass:
        """Cycle-0: direct hand-off — one thread of flow, the driver dispatches."""
        datum = datum0
        L = self._layers

        t1 = run_layer(L.t1, host.signals, field, datum)
        datum = t1.datum
        self._log_exit(1)

        t2 = run_layer(
            L.t2,
            T2Input(
                env=t1.output,
                emitted=self._last_emission,
                changes=host.changes,
                lateral=self._last_lateral,
            ),
            field,
            datum,
        )
        datum = t2.datum
        self._log_exit(2)

        env_pushed = frozenset(
            t.change.id for t in t2.output.tagged if t.agency == "ENV_PUSHED"
        )

        t3 = run_layer(L.t3, gather_t3(host), field, datum)
        datum = t3.datum
        self._log_exit(3)

        t4 = run_layer(L.t4, T4Input(units=t3.output.units), field, datum)
        datum = t4.datum
        self._log_exit(4)

        t5 = run_layer(L.t5, T5Input(bound=t4.output.bound), field, datum)
        datum = t5.datum
        self._log_exit(5)

        t6 = run_layer(
            L.t6,
            T6Input(results=t5.output.results, env_pushed=env_pushed),
            field,
            datum,
        )
        datum = t6.datum
        self._log_exit(6)

        t7 = run_layer(
            L.t7,
            T7Input(
                expectations=tuple(
                    ExpectedEntity(r.entity_id, r.expectation.predicted)
                    for r in t5.output.results
                ),
                observed=frozenset(r.entity_id for r in t5.output.results),
                unasked=self._unasked,
            ),
            field,
            datum,
        )
        datum = t7.datum
        self._log_exit(7)

        t8 = run_layer(
            L.t8,
            T8Input(others=t6.output.others, interactions=host.interactions),
            field,
            datum,
        )
        datum = t8.datum
        self._log_exit(8)

        emissions = tuple(
            e for r in (t1, t2, t3, t4, t5, t6, t7, t8) for e in r.emissions
        )
        contributions = tuple(
            c for r in (t1, t2, t3, t4, t5, t6, t7, t8) for c in r.contributions
        )
        return _LayerPass(
            datum=datum,
            t5=t5.output,
            t7=t7.output,
            crystallized=t2.output.crystallized,
            emissions=emissions,
            contributions=contributions,
        )

    def _pass_multi_stream(
        self, host: HostCycleInput, field: ModField, datum0: TaggedDatum
    ) -> _LayerPass:
        """Cycle-1+: each layer publishes; each consumer gathers from the channel."""
        datum = datum0
        L = self._layers
        ch = self._channel
        ch.clear()

        t1 = run_layer(L.t1, host.signals, field, datum)
        datum = t1.datum
        self._log_exit(1)
        ch.publish(1, t1.output)

        t2 = run_layer(
            L.t2,
            gather_t2(ch, host, self._last_emission, self._last_lateral),
            field,
            datum,
        )
        datum = t2.datum
        self._log_exit(2)
        ch.publish(2, t2.output)

        t3 = run_layer(L.t3, gather_t3(host), field, datum)
        datum = t3.datum
        self._log_exit(3)
        ch.publish(3, t3.output)

        t4 = run_layer(L.t4, gather_t4(ch), field, datum)
        datum = t4.datum
        self._log_exit(4)
        ch.publish(4, t4.output)

        t5 = run_layer(L.t5, gather_t5(ch), field, datum)
        datum = t5.datum
        self._log_exit(5)
        ch.publish(5, t5.output)

        # Fan-out: T6 and T7 both read T5's one published output; T6 also reads T2.
        t6 = run_layer(L.t6, gather_t6(ch), field, datum)
        datum = t6.datum
        self._log_exit(6)
        ch.publish(6, t6.output)

        t7 = run_layer(L.t7, gather_t7(ch, host, self._unasked), field, datum)
        datum = t7.datum
        self._log_exit(7)
        ch.publish(7, t7.output)

        t8 = run_layer(L.t8, gather_t8(ch, host), field, datum)
        datum = t8.datum
        self._log_exit(8)
        ch.publish(8, t8.output)

        emissions = tuple(
            e for r in (t1, t2, t3, t4, t5, t6, t7, t8) for e in r.emissions
        )
        contributions = tuple(
            c for r in (t1, t2, t3, t4, t5, t6, t7, t8) for c in r.contributions
        )
        return _LayerPass(
            datum=datum,
            t5=t5.output,
            t7=t7.output,
            crystallized=t2.output.crystallized,
            emissions=emissions,
            contributions=contributions,
        )

    # ── the cycle ──────────────────────────────────────────────────────────

    def cycle_count(self) -> int:
        return self._cycle

    def snapshot(self) -> DriverState:
        """The driver's accrued state, for the §9 commit snapshot."""
        return DriverState(
            cycle=self._cycle,
            last_emission=self._last_emission,
            pending_returns=tuple(self._pending),
            recalled=tuple(sorted(self._recalled)),
            last_lateral=self._last_lateral,
        )

    def run(self, region_input: HostCycleInput) -> CycleResult:
        field = self._glob.current()

        # ── Query-returns join what the region returned (§6, link 1) ──
        # "Input channels: query returns, messages from an Other, event streams,
        # the result of a prior action." What T3 asked the store for last cycle
        # arrives now, at T1, and runs every layer like anything else that
        # arrives. A return is present on the cycle it arrives, and only then: a
        # memory that was not recalled is not silent, it was not asked.
        returned = self._pending
        self._pending = []
        arriving = {returned_entity(s) for s in returned}
        self._recalled |= arriving
        self._unasked = frozenset(self._recalled - arriving)
        # Each return is also a change the agent's own query produced: its value
        # is the query that asked, so T2 matches it to that emission and tags it
        # SELF_WRITTEN — §6.4's closure. The datum's CONTENT is still not the
        # agent's own; agency and provenance are two different questions.
        host = (
            region_input
            if not returned
            else replace(
                region_input,
                signals=(*region_input.signals, *returned),
                changes=(
                    *region_input.changes,
                    *(
                        ObservedChange(
                            id=returned_entity(s),
                            value=store_query(s.raw_payload["cue"]),
                        )
                        for s in returned
                    ),
                ),
            )
        )
        flow: FlowMode = "single-threaded" if self._cycle == 0 else "multi-stream"
        # The host server clock at this cycle, for [event] timestamps.
        self._cycle_t = self._now()

        # The cycle datum, threaded T1→T8 so it accrues a floor-tag at each
        # layer; the flow mode rides along as an open tag (trace-visible, §13.3).
        admitted = to_running(
            admit_host_data(
                HostDatum(
                    payload={"signals": len(host.signals), "cycle": self._cycle},
                    admitting_layer=1,
                    open={
                        "domain": "cycle",
                        "phase": "loop",
                        "source": "driver",
                        "flow": flow,
                    },
                ),
                # Timestamp is wall-clock; the cycle number is the cycle-mark.
                self._cycle_t,
            ),
            self._cycle,
        )
        # prior → running: the admitted host datum has run this cycle.
        self._events.append(
            record_provenance(
                self._datum_id(), self._cycle, "prior", "running", self._cycle_t
            )
        )

        # prior → running, for each recalled datum that had not run before (§9):
        # "Host data, once admitted and once it has run, bears a cycle-mark." It
        # runs now, so it takes this cycle's mark, and the move is recorded as it
        # occurs. `prior` is a one-way entry: a datum already in circulation is
        # returned as it is, and no edge is recorded for being read.
        for s in returned:
            datum_id = returned_entity(s)
            held = self._data.get(datum_id)
            if held is not None and held.fixed.provenance == "prior":
                self._data.put(datum_id, to_running(held, self._cycle))
                self._events.append(
                    record_provenance(
                        datum_id, self._cycle, "prior", "running", self._cycle_t
                    )
                )
        self._running_recalled = tuple(
            returned_entity(s) for s in returned if self._data.has(returned_entity(s))
        )

        pass_ = (
            self._pass_single_threaded(host, field, admitted)
            if flow == "single-threaded"
            else self._pass_multi_stream(host, field, admitted)
        )
        datum = pass_.datum

        # Each recalled datum left T8 with the cycle datum: its floor-tag names the
        # layer it just exited (§9 fixed layer). Its tag set — never its content —
        # goes into this cycle's activity record, so the trace shows what class of
        # data entered and that it came through the gate (§9 open layer, §13.6).
        recalled_tags: list[RecalledTags] = []
        for datum_id in self._running_recalled:
            ran = stamp_layer(self._data.get(datum_id), 8)
            self._data.put(datum_id, ran)
            recalled_tags.append(
                RecalledTags(datum_id=datum_id, fixed=ran.fixed, open=dict(ran.open))
            )
        self._running_recalled = ()

        # ── §7 crystallization: T2 drew the self/environment distinction ──
        # The one-time act where the from-within standpoint begins. Recorded as a
        # lean trace line — the ACT of distinguishing, never a persistent or
        # continuing self, which §7 forbids claiming. A resumed line has already
        # crystallized and T2 does not re-signal.
        if pass_.crystallized:
            self._events.append(
                record_crystallization(self._datum_id(), self._cycle, self._cycle_t)
            )

        # ── Lateral emissions raised during the pass (§6.4) ──
        # Any layer MAY have pushed a committed action to the region during its
        # work. Each is recorded as one activity record naming its issuing layer,
        # register ↔. The capability is afforded, not fabricated; with no live
        # region to push to, the buffer is empty.
        for e in pass_.emissions:
            self._emit(e.issuing_layer, e.action)

        # ── The store answers T3's queries (§6.4, §9 open layer) ──
        # Answered now, ingested at T1 next cycle. Answering changes nothing in
        # `[data]`; the datum moves only when it runs.
        for e in pass_.emissions:
            if not is_store_query(e.action):
                continue
            for s in answer_query(self._data, e.action["cue"], self._cycle_t):
                if all(returned_entity(p) != returned_entity(s) for p in self._pending):
                    self._pending.append(s)

        # ── Expectation readings: the observable signature of accumulation ──
        # One lean line per observed entity: its prediction confidence and the
        # recurrence that drove it. A third party reads these grouped by entity
        # and measures the ramp (§13.4) — an accruing self makes confidence and
        # recurrence climb together; a reloading impostor cannot.
        for r in pass_.t5.results:
            # source == entity_id: for a value-mismatch the entity IS the
            # resistance source, recorded explicitly rather than assumed.
            self._events.append(
                record_expectation(
                    self._datum_id(),
                    self._cycle,
                    r.entity_id,
                    r.entity_id,
                    r.expectation.confidence,
                    r.expectation.recurrence,
                    r.pred_err.delta,
                    self._cycle_t,
                )
            )

        # ── Resistance readings for absences (§8, T7) ──
        # The expectation line covers value-mismatch sources; a region that
        # withholds an expected return resists by absence. Record that per-source
        # too, so no resistance source is left un-measurable in the trace.
        for a in pass_.t7.absences:
            self._events.append(
                record_resistance_reading(
                    self._datum_id(),
                    self._cycle,
                    "region",
                    a.entity_id,
                    "absence",
                    a.recurrence,
                    a.delta,
                    "-",
                    self._cycle_t,
                )
            )

        # ── Scars that returned as material (§9, `scar → running`) ──
        # A recalled scar is "data in use"; §9 is explicit that a scar is not a
        # resting place. The datum key is the recalled scar's own (`cycle-N`),
        # not this cycle's: it is that datum which moved, not this one.
        if self._recollection is not None:
            for recalled in self._recollection.drain():
                self._events.append(
                    record_provenance(
                        f"cycle-{recalled.cycle}",
                        self._cycle,
                        "scar",
                        "running",
                        self._cycle_t,
                    )
                )

        # ── Forward-building (§6.2): build situations, cast outcomes ──
        # The datum takes the running→simulated→projected road WHEN the store
        # affords material — an entity whose expectation has accrued confidence.
        # No material (a cold start) and it stays running, reflexing straight to
        # scar on collision (§5, §8.7). This is a CONDITION on the road, not a
        # scheduled step.
        # Attention over situations (INV-7): the field raises the floor a
        # situation's fit must clear before the loop builds from it. The default
        # floor is 0, which is what the loop always did. Nothing here skips an
        # expectation or alters a recorded confidence — see FIT_FLOOR for why
        # both of those are unsafe.
        fit_floor = field.params.get(FIT_FLOOR_PARAM, FIT_FLOOR)
        material = [
            r for r in pass_.t5.results if r.expectation.confidence > fit_floor
        ]
        forward_built = False
        projected_units: tuple[InfoUnit, ...] = ()

        if material:
            # running → simulated: the loop takes the datum up into building.
            datum = to_simulated(datum)
            self._events.append(
                record_provenance(
                    self._datum_id(), self._cycle, "running", "simulated", self._cycle_t
                )
            )
            # Build up to H_COUNT situations — a ceiling, not a quota. Fit is the
            # store's support for the situation (accrued confidence); the
            # closer-fitting outcomes carry, never a hard scored winner.
            situations = sorted(
                material, key=lambda r: r.expectation.confidence, reverse=True
            )[:H_COUNT]
            # simulated → projected: each situation yields the outcome cast from it.
            datum = to_projected(datum)
            self._events.append(
                record_provenance(
                    self._datum_id(),
                    self._cycle,
                    "simulated",
                    "projected",
                    self._cycle_t,
                )
            )
            projected_units = tuple(r.expectation.predicted for r in situations)
            forward_built = True

        # ── Appraisal step (INV-8), under the cycle's field context (§8.5) ──
        pred_errs: tuple[PredErr, ...] = (
            *(r.pred_err for r in pass_.t5.results),
            *pass_.t7.absences,
        )
        appraisal = appraise(
            AppraisalInput(
                info_ref=f"cycle-{self._cycle}",
                pred_errs=pred_errs,
                field=field,
                edited_state=EDITED_STATE_ID,
                # Not-yet-collided outcomes (§6.4).
                projected=projected_units,
            )
        )

        # ── Respond (link 5, §6.4): the cycle's committed action, register ↔ ──
        # The one real emission per cycle here; issued at the close of the
        # meaning-channel after appraisal, so its issuing layer is T8.
        directive = Directive(
            committed_action=self._respond(
                RespondContext(
                    cycle=self._cycle,
                    appraisal=appraisal,
                    field=field,
                    expectations=pass_.t5.results,
                    host=host,
                )
            ),
            issuing_layer=8,
            built_from=(appraisal,),
            t=self._cycle_t,
        )
        response = Emission(action=directive.committed_action)

        # ── Collisions that hold → scars in [event] ──
        # Each collision is sourced: a value-mismatch by the entity that resisted,
        # an absence by the region. The source set drives diversity monitoring.
        collisions: list[tuple[str, Any]] = [
            *((r.entity_id, r.pred_err) for r in pass_.t5.results if r.pred_err.delta > 0),
            *(("region", a) for a in pass_.t7.absences),
        ]
        anchor = ContextAnchor(
            cycle=self._cycle,
            field_state=dict(field.params),
            depth=CONTEXT_ANCHOR_DEPTH,
        )

        scars = 0
        collision_sources: list[str] = []

        if collisions:
            scar_datum = to_scar(datum, True)
            # → scar: from `projected` if a cast preceded the collision, else a
            # direct running → scar (reflex, §5, §8.7). Which road it was depends
            # on whether the store afforded a forward-cast — a situational fact.
            self._events.append(
                record_provenance(
                    self._datum_id(),
                    self._cycle,
                    "projected" if forward_built else "running",
                    "scar",
                    self._cycle_t,
                )
            )
            for source_id, e in collisions:
                self._events.append(
                    record_scar(
                        scar_datum,
                        ResistEvent(
                            source_id=source_id,
                            expected=e.predicted.content,
                            received=e.observed.content if e.observed is not None else None,
                            mismatch_kind=(
                                "absence" if e.observed is None else "value-mismatch"
                            ),
                            t=self._cycle_t,
                        ),
                        anchor,
                    )
                )
                if source_id not in collision_sources:
                    collision_sources.append(source_id)
                scars += 1
            datum = scar_datum
        elif forward_built:
            # projected → running: the cast produced no scar; the datum returns
            # to use — a datum is never a conclusion at rest (§9).
            datum = to_running(datum, self._cycle)
            self._events.append(
                record_provenance(
                    self._datum_id(), self._cycle, "projected", "running", self._cycle_t
                )
            )

        # ── Emit the cycle's committed action (link 5, §6.4) ──
        self._emit(directive.issuing_layer, directive.committed_action)

        # ── Activity record: the cycle's trace, sealing the cycle (§9) ──
        # Trace, not experience: no layer learns from it. It keeps the audit
        # trail complete across quiet stretches (E4) — one record per cycle.
        self._events.append(
            record_activity(
                self._datum_id(),
                datum,
                ActivityEvent(
                    cycle=self._cycle,
                    flow=flow,
                    emitted=response.action,
                    observed=tuple(r.entity_id for r in pass_.t5.results),
                    scars=scars,
                    t=self._cycle_t,
                    recalled=tuple(recalled_tags),
                ),
                anchor,
            )
        )

        # Persist the cycle datum in [data] (mutable working memory).
        self._data.put(f"cycle-{self._cycle}", datum)

        # ── GLOB-MOD: contribute this cycle's resistance, advance to N+1 ──
        total_resistance = sum(e.delta for e in pred_errs)
        # INV-7: "Every layer contributes to it as one competing parameter;
        # contributions blend, re-weighted each cycle, never last-write-wins."
        # Each layer's own contributions go in first, bound to its index by
        # `run_layer`; the driver adds the cycle's total resistance last, as it
        # always did. With more than one contributor the blend finally does what
        # its name says.
        for c in pass_.contributions:
            self._glob.contribute(c.layer, c.params, c.weight)
        self._glob.contribute(5, {"resistance": total_resistance}, 1.0)
        self._glob.advance(self._cycle + 1)

        # Feedback and accrual: the response becomes the next cycle's emission,
        # and every lateral emission of this cycle is readable by T2 next cycle.
        self._last_emission = response
        self._last_lateral = tuple(e.action for e in pass_.emissions)
        self._cycle += 1

        return CycleResult(
            cycle=self._cycle - 1,
            flow=flow,
            appraisal=appraisal,
            response=response,
            scars=scars,
            absences=len(pass_.t7.absences),
            collision_sources=tuple(collision_sources),
        )


def create_cycle(
    layers: Layers,
    glob: GlobMod,
    data: DataStore,
    events: EventLog,
    initial_emission: Emission,
    now: Callable[[], int] | None = None,
    resume: DriverState | None = None,
    respond: RespondPolicy | None = None,
    recollection: Any = None,
) -> Cycle:
    return Cycle(
        layers=layers,
        glob=glob,
        data=data,
        events=events,
        initial_emission=initial_emission,
        now=now,
        resume=resume,
        respond=respond,
        recollection=recollection,
    )
