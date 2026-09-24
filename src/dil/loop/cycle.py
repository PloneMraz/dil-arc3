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

Ported from dil-core against DIL protocol v0.3.3.
"""

from __future__ import annotations

import time
import weakref
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
    WrittenTags,
    ResistEvent,
    record_activity,
    record_crystallization,
    record_emission,
    record_expectation,
    record_layer_exit,
    record_provenance,
    record_resistance_reading,
    record_revision,
    record_scar,
)
from ..store.tagging_gate import (
    HostDatum,
    TaggingGateError,
    admit_arrival,
    admit_nascent,
)
from ..store.tags import invalid_open_tag_reason
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
from .layers.t3 import STORE_CHANNEL, is_store_query, store_query
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
    # What the rule wrote last cycle, arriving at T1 now (v0.3.3).
    pending_writes: tuple["PendingWrite", ...] = ()


@dataclass(frozen=True, slots=True)
class PendingWrite:
    """A datum the rule wrote, on its way to T1 at the next cycle (v0.3.3).

    `action` is what T2 reads as the agent's own act when the datum arrives:
    `{"kind": "write", "datum": id}`.
    """

    signal: Signal
    action: dict[str, str]


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

# What the region returns is data. An expectation is compared against it, and a
# `scar` is the datum that "collided with resistance and held" (§3, §9): if the
# return is not a datum, there is nothing for the tag to be on, and the mismatch
# does not say what it was a mismatch with. The policy is the host's declaration
# for a signal — payload and open tags (§12 tag F) — or None to keep that one out
# (§10: selective-write is DECIDE@IMPL). See `Cycle.__init__`.
AdmitPolicy: TypeAlias = Callable[[Signal], HostDatum | None]


def _format_of(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, (list, tuple)):
        return "array"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    return "object"


def admit_return(signal: Signal) -> HostDatum | None:
    """The reference admission: every return, described by what the driver can
    see of it without interpreting it — that it came from the region, by which
    channel, in what form. A host with a vocabulary of its own declares its own.
    """
    return HostDatum(
        payload=signal.raw_payload,
        admitting_layer=1,
        open={"domain": "region", "source": signal.source_id, "format": _format_of(signal.raw_payload)},
    )


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
    # DEVIATION from dil-core, declared: how many data the agent wrote this
    # cycle, so the daemon can commit on it (dil-arc3's commit cadence).
    written: int = 0


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
    # T3's units, one per signal and in the signals' order: how the driver finds
    # which admitted datum a T5 observation came from.
    units: tuple[InfoUnit, ...] = ()


class Cycle:
    """One pass of the loop per `run`."""

    __slots__ = (
        "_layers", "_glob", "_data", "_events", "_channel", "_now",
        "_cycle", "_last_emission", "_cycle_t", "_respond", "_recollection",
        "_pending", "_recalled", "_unasked", "_last_lateral", "_running_recalled",
        "_admit", "_running_admitted", "_pending_writes", "_running_written",
        "_unit_datum",
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
        admit: AdmitPolicy | None = None,
    ) -> None:
        # How each return from the region enters `[data]` (see `AdmitPolicy`):
        # through the tagging-gate, running as `running`, leaving its own line at
        # every layer it exits, and — when the expectation about it fails —
        # moving to `scar` itself, the scar record naming it. Defaults to
        # `admit_return`, which keeps every one. Ported from dil-core 276f30a.
        self._admit = admit if admit is not None else admit_return
        self._running_admitted: tuple[str, ...] = ()
        # What the rule wrote last cycle, arriving at T1 this cycle (v0.3.3).
        self._pending_writes: list[PendingWrite] = (
            list(resume.pending_writes) if resume is not None else []
        )
        # Data the rule wrote last cycle, running now: their exits are theirs too.
        self._running_written: tuple[str, ...] = ()
        # The datum each observation unit came from, for as long as anything
        # holds the unit — T5 keeps a window of them per entity — so what a
        # written datum was built from can be recorded by id (v0.3.4 §9). Keyed
        # by the unit's identity; each entry leaves with its unit.
        self._unit_datum: dict[int, str] = {}
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
        # Wall-clock at which the cycle currently running began: the cycle datum's
        # timestamp and the seal's `t`. Every record takes the clock at the moment
        # it is appended instead (§9: "records each transition as it occurs").
        # Ported from dil-core 9073ddf.
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

    def _remember_unit(self, unit: InfoUnit, datum_id: str) -> None:
        """Map an observation unit to its datum until the unit is gone."""
        key = id(unit)
        if key in self._unit_datum:
            return
        self._unit_datum[key] = datum_id
        weakref.finalize(unit, self._unit_datum.pop, key, None)

    def _datum_id(self) -> str:
        """The id the cycle datum takes in `[data]`; also its key in the path."""
        return f"cycle-{self._cycle}"

    def _log_exit(self, layer: LayerIndex) -> None:
        """Log one `layer-exit` line as the cycle datum leaves a layer (§9)."""
        at = self._now()
        self._events.append(
            record_layer_exit(self._datum_id(), self._cycle, layer, at)
        )
        for datum_id in (*self._running_recalled, *self._running_admitted, *self._running_written):
            self._events.append(
                record_layer_exit(datum_id, self._cycle, layer, at)
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
                self._datum_id(), self._cycle, issuing_layer, action, self._now()
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
            units=tuple(t3.output.units),
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
            units=tuple(t3.output.units),
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
            pending_writes=tuple(self._pending_writes),
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
        # What the rule wrote last cycle arrives now too, and runs every layer;
        # its change is the agent's own write, which T2 matches to the write it
        # made (v0.3.3 §9: SELF_WRITTEN at the next cycle).
        written_back = [w for w in self._pending_writes if self._data.has(w.action["datum"])]
        self._pending_writes = []
        arriving = {returned_entity(s) for s in returned} | {
            w.action["datum"] for w in written_back
        }
        # Like a recalled datum, a written one returns only when it is written:
        # not arriving later is no absence.
        self._recalled |= arriving
        self._unasked = frozenset(self._recalled - arriving)
        # Each return is also a change the agent's own query produced: its value
        # is the query that asked, so T2 matches it to that emission and tags it
        # SELF_WRITTEN — §6.4's closure. The datum's CONTENT is still not the
        # agent's own; agency and provenance are two different questions.
        host = (
            region_input
            if not returned and not written_back
            else replace(
                region_input,
                signals=(*region_input.signals, *returned, *(w.signal for w in written_back)),
                changes=(
                    *region_input.changes,
                    *(
                        ObservedChange(
                            id=returned_entity(s),
                            value=store_query(s.raw_payload["cue"]),
                        )
                        for s in returned
                    ),
                    *(
                        ObservedChange(id=w.action["datum"], value=w.action)
                        for w in written_back
                    ),
                ),
            )
        )
        flow: FlowMode = "single-threaded" if self._cycle == 0 else "multi-stream"
        # The host server clock at this cycle, for [event] timestamps.
        self._cycle_t = self._now()

        # The cycle datum, threaded T1→T8 so it accrues a floor-tag at each
        # layer; the flow mode rides along as an open tag (trace-visible, §13.3).
        # It is the loop's own, in use the moment it exists, so it passes the
        # tagging-gate at `running` (v0.3.3 §9); its entry is the cycle seal that
        # embeds it with its tags.
        admitted = admit_arrival(
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
            self._cycle,
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
                        datum_id, self._cycle, "prior", "running", self._now()
                    )
                )
        self._running_recalled = tuple(
            returned_entity(s) for s in returned if self._data.has(returned_entity(s))
        )

        # nascent → running, for each datum the rule wrote anew last cycle: it
        # runs now, keeping the mark of the cycle that wrote it (v0.3.3 §9). A
        # revised datum arrives too, its provenance untouched.
        for w in written_back:
            written_id = w.action["datum"]
            held = self._data.get(written_id)
            if held.fixed.provenance == "nascent":
                self._data.put(written_id, to_running(held, self._cycle))
                self._events.append(
                    record_provenance(
                        written_id, self._cycle, "nascent", "running", self._now()
                    )
                )
        self._running_written = tuple(dict.fromkeys(w.action["datum"] for w in written_back))

        # Each return from the region enters through the tagging-gate at
        # `running` (see `AdmitPolicy`, v0.3.3 §9): in use the moment it arrives,
        # it takes this cycle's mark, and its entry is its tag set in this
        # cycle's record. The region's signals come first in `host.signals`, so
        # index i is the i-th T3 unit too.
        admitted_ids: dict[int, str] = {}
        for i, signal in enumerate(region_input.signals):
            declared = self._admit(signal)
            if declared is None:
                continue
            datum_id = f"signal-{self._cycle}-{i}"
            self._data.put(datum_id, admit_arrival(declared, self._now(), self._cycle))
            admitted_ids[i] = datum_id
        self._running_admitted = tuple(admitted_ids.values())
        admitted_now = frozenset(self._running_admitted)

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

        # The same for each admitted region return: it left T8 with the cycle
        # datum, and its tag set — never its content — goes into the record.
        admitted_tags: list[RecalledTags] = []
        for datum_id in self._running_admitted:
            ran = stamp_layer(self._data.get(datum_id), 8)
            self._data.put(datum_id, ran)
            admitted_tags.append(
                RecalledTags(datum_id=datum_id, fixed=ran.fixed, open=dict(ran.open))
            )
        self._running_admitted = ()
        # And each datum the rule wrote, running now.
        for written_id in self._running_written:
            self._data.put(written_id, stamp_layer(self._data.get(written_id), 8))
        self._running_written = ()
        # Which admitted datum each observation came from, by the unit itself:
        # T4 and T5 carry T3's units through unchanged.
        datum_of = {
            id(pass_.units[i]): datum_id
            for i, datum_id in admitted_ids.items()
            if i < len(pass_.units)
        }
        for i, datum_id in admitted_ids.items():
            if i < len(pass_.units):
                self._remember_unit(pass_.units[i], datum_id)
        # What came back from the store, recalled or written, is a datum too.
        for i in range(len(region_input.signals), min(len(host.signals), len(pass_.units))):
            payload = host.signals[i].raw_payload
            entity = payload.get("entity") if isinstance(payload, dict) else None
            if isinstance(entity, str):
                self._remember_unit(pass_.units[i], entity)

        # ── §7 crystallization: T2 drew the self/environment distinction ──
        # The one-time act where the from-within standpoint begins. Recorded as a
        # lean trace line — the ACT of distinguishing, never a persistent or
        # continuing self, which §7 forbids claiming. A resumed line has already
        # crystallized and T2 does not re-signal.
        if pass_.crystallized:
            self._events.append(
                record_crystallization(self._datum_id(), self._cycle, self._now())
            )

        # ── Lateral emissions raised during the pass (§6.4) ──
        # Any layer MAY have pushed a committed action to the region during its
        # work. Each is recorded as one activity record naming its issuing layer,
        # register ↔. The capability is afforded, not fabricated; with no live
        # region to push to, the buffer is empty.
        for e in pass_.emissions:
            self._emit(e.issuing_layer, e.action)

        # ── The store answers the queries raised this cycle (§6.4, §9 open layer) ──
        # Answered now, ingested at T1 next cycle. Answering changes nothing in
        # `[data]`; the datum moves only when it runs. Memory is what the store
        # held before the cycle that asks: what arrived this cycle is already
        # running in it, and answering with it would recall what is being seen.
        for e in pass_.emissions:
            if not is_store_query(e.action):
                continue
            for s in answer_query(self._data, e.action["cue"], self._now()):
                if returned_entity(s) in admitted_now:
                    continue
                if all(returned_entity(p) != returned_entity(s) for p in self._pending):
                    self._pending.append(s)

        # ── What the rule wrote (v0.3.3 §9) ──
        # A datum written anew enters through the tagging-gate at `nascent`,
        # bearing this cycle's mark. A revision rewrites a datum already held: its
        # content changes, its provenance does not, and a bare `revision` line is
        # recorded. Either way the datum's tags go into this cycle's record, and
        # it arrives at T1 next cycle, where T2 reads the write as the agent's
        # own. Taken after the store has answered: what is written now is not
        # memory yet.
        written_tags: dict[str, WrittenTags] = {}
        write_actions: dict[str, dict[str, str]] = {}
        anew = 0
        for w in pass_.t5.writes:
            # What it was built from, by id: every unit must be one that came
            # from a datum, every id a datum the store holds.
            if w.built_from is None:
                raise ValueError(
                    "write: a datum written must say what it was built from "
                    "(built_from; () for nothing held)"
                )
            built_from: list[str] = []
            for source in w.built_from:
                source_id = source if isinstance(source, str) else self._unit_datum.get(id(source))
                if source_id is None or not self._data.has(source_id):
                    raise ValueError(
                        f'write: built_from names "{source}", which is no datum'
                        if isinstance(source, str)
                        else "write: built_from names a unit that came from no datum"
                    )
                if source_id not in built_from:
                    built_from.append(source_id)
            if w.datum_id is not None:
                held = self._data.get(w.datum_id)
                if held is None:
                    raise ValueError(
                        f'write: there is no datum "{w.datum_id}" to revise; '
                        "a datum written anew carries no datum_id"
                    )
                if w.open is not None:
                    bad = invalid_open_tag_reason(w.open)
                    if bad is not None:
                        raise TaggingGateError(bad)
                written_id = w.datum_id
                self._data.put(
                    written_id,
                    replace(held, payload=w.payload,
                            open=dict(w.open) if w.open is not None else held.open),
                )
                self._events.append(
                    record_revision(written_id, self._cycle, 5, self._now())
                )
            else:
                if w.open is None:
                    raise TaggingGateError("a datum written anew must carry its open tags")
                written_id = f"written-{self._cycle}-{anew}"
                anew += 1
                self._data.put(
                    written_id,
                    admit_nascent(
                        HostDatum(payload=w.payload, admitting_layer=5, open=dict(w.open)),
                        self._now(),
                        self._cycle,
                    ),
                )
            d = self._data.get(written_id)
            action = {"kind": "write", "datum": written_id}
            written_tags.pop(written_id, None)
            written_tags[written_id] = WrittenTags(
                datum_id=written_id, fixed=d.fixed, open=dict(d.open),
                built_from=tuple(built_from),
            )
            write_actions.setdefault(written_id, action)
            self._pending_writes = [
                p for p in self._pending_writes if p.action["datum"] != written_id
            ]
            self._pending_writes.append(
                PendingWrite(
                    signal=Signal(
                        source_id=STORE_CHANNEL,
                        # The same form a store return takes (store_query.py),
                        # so it snapshots as data like any other arrival.
                        raw_payload={
                            "entity": written_id,
                            "payload": d.payload,
                            "fixed": {
                                "timestamp": d.fixed.timestamp,
                                "cycleMark": d.fixed.cycle_mark,
                                "provenance": d.fixed.provenance,
                                "floorTag": d.fixed.floor_tag,
                            },
                            "open": dict(d.open),
                        },
                        t=self._now(),
                    ),
                    action=action,
                )
            )

        # ── Expectation readings: the observable signature of accumulation ──
        # One lean line per observed entity: its prediction confidence and the
        # recurrence that drove it. A third party reads these grouped by entity
        # and measures the ramp (§13.4) — an accruing self makes confidence and
        # recurrence climb together; a reloading impostor cannot.
        # ── What each expectation is (v0.3.5 §9, `held_by`) ──
        # The held data an expectation is, by id: named by the rule, or the datum
        # a unit it took from its window came from. A name the rule gave that is
        # no datum is refused, as a `built_from` would be; a unit the rule
        # returned that came from no datum is simply nothing held. Ported from
        # dil-core 4f5da8f.
        held_of: dict[int, tuple[str, ...]] = {}
        for r in pass_.t5.results:
            ids: list[str] = []
            for h in r.expectation.held_by:
                if isinstance(h, str):
                    hid = h if self._data.has(h) else None
                else:
                    hid = self._unit_datum.get(id(h))
                if hid is None:
                    if r.expectation.held_by_declared:
                        raise ValueError(
                            "expectation: held_by names "
                            + (f'"{h}", which is no datum' if isinstance(h, str) else "a unit that came from no datum")
                        )
                    continue
                if hid not in ids:
                    ids.append(hid)
            held_of[id(r)] = tuple(ids)
        # An expectation built that a datum is, is that datum in use: a scar used
        # again returns to `running` (§9 `scar → running`), once, before it is
        # compared — so a program that keeps failing circulates between the two.
        in_use: set[str] = set()
        for ids in held_of.values():
            for hid in ids:
                if hid in in_use:
                    continue
                in_use.add(hid)
                held = self._data.get(hid)
                if held is not None and held.fixed.provenance in ("scar", "prior"):
                    self._data.put(hid, to_running(held, self._cycle))
                    self._events.append(
                        record_provenance(hid, self._cycle, held.fixed.provenance, "running", self._now())
                    )
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
                    self._now(),
                    held_of.get(id(r), ()),
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
                    self._now(),
                )
            )

        # ── Scars that returned as material (§9, `scar → running`) ──
        # A recalled scar is "data in use"; §9 is explicit that a scar is not a
        # resting place. The datum key is the recalled scar's own (`cycle-N`),
        # not this cycle's: it is that datum which moved, not this one.
        if self._recollection is not None:
            # The move is the datum's own and happens once: a scar recalled
            # again once it is back in use does not move again, and `[data]`
            # follows the log. Ported from dil-core dc7a9a7.
            for recalled in self._recollection.drain():
                held = self._data.get(recalled.datum_id)
                if held is None or held.fixed.provenance != "scar":
                    continue
                self._data.put(recalled.datum_id, to_running(held, self._cycle))
                self._events.append(
                    record_provenance(
                        recalled.datum_id,
                        self._cycle,
                        "scar",
                        "running",
                        self._now(),
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
        # The entities whose outcome the cycle datum cast: what it carries into collision.
        cast: frozenset[str] = frozenset()

        if material:
            # running → simulated: the loop takes the datum up into building.
            datum = to_simulated(datum)
            self._events.append(
                record_provenance(
                    self._datum_id(), self._cycle, "running", "simulated", self._now()
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
                    self._now(),
                )
            )
            projected_units = tuple(r.expectation.predicted for r in situations)
            cast = frozenset(r.entity_id for r in situations)
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
            t=self._now(),
        )
        response = Emission(action=directive.committed_action)

        # ── Collisions that hold → scars in [event] ──
        # Each collision is sourced: a value-mismatch by the entity that resisted,
        # an absence by the region. The source set drives diversity monitoring.
        # The expecting side is scarred only against what the region returned:
        # an arrival from the store — the agent's own revision coming back — is
        # not the region resisting (INV-6).
        collisions: list[tuple[str, Any, tuple[str, ...]]] = [
            *(
                (
                    r.entity_id,
                    r.pred_err,
                    held_of.get(id(r), ()) if id(r.pred_err.observed) in datum_of else (),
                )
                for r in pass_.t5.results
                if r.pred_err.delta > 0
            ),
            *(("region", a, ()) for a in pass_.t7.absences),
        ]
        anchor = ContextAnchor(
            cycle=self._cycle,
            field_state=dict(field.params),
            depth=CONTEXT_ANCHOR_DEPTH,
        )

        scars = 0
        collision_sources: list[str] = []

        # The cycle datum collides only when what it carries does (§9): an
        # outcome it cast — `projected → scar`, "the emission was made, the region
        # returned, and the datum collided and held" — or a collision that has no
        # return of its own to hold the scar (an absence, where nothing returned;
        # a return the host kept out; a store arrival), for which it stands.
        # Otherwise the region's return is the datum that collided, and a cast
        # that did not collide returns to use: `projected → running`. Ported from
        # dil-core 6c74f0c; settled with Plone.
        def return_of(e) -> str | None:
            return datum_of.get(id(e.observed)) if e.observed is not None else None

        cycle_collides = any(
            return_of(e) is None or (forward_built and source_id in cast)
            for source_id, e, _ in collisions
        )
        scar_datum = to_scar(datum, True) if cycle_collides else None
        if cycle_collides:
            # → scar: from `projected` if a cast preceded the collision, else a
            # direct running → scar (reflex, §5, §8.7).
            self._events.append(
                record_provenance(
                    self._datum_id(),
                    self._cycle,
                    "projected" if forward_built else "running",
                    "scar",
                    self._now(),
                )
            )
        if collisions:
            for source_id, e, held_ids in collisions:
                # What collided is the return the expectation was compared
                # against: that datum moves to `scar` (§9 `running → scar`), and
                # the record embeds and names it. Where there is no such return,
                # the cycle datum stands for the collision.
                collided_id = return_of(e)
                collided = scar_datum
                if collided_id is not None:
                    held = self._data.get(collided_id)
                    collided = to_scar(held, True)
                    self._data.put(collided_id, collided)
                    self._events.append(
                        record_provenance(
                            collided_id,
                            self._cycle,
                            held.fixed.provenance,
                            "scar",
                            self._now(),
                        )
                    )
                self._events.append(
                    record_scar(
                        collided,
                        ResistEvent(
                            source_id=source_id,
                            expected=e.predicted.content,
                            received=e.observed.content if e.observed is not None else None,
                            mismatch_kind=(
                                "absence" if e.observed is None else "value-mismatch"
                            ),
                            t=self._now(),
                        ),
                        anchor,
                        datum_id=collided_id,
                    )
                )
                if source_id not in collision_sources:
                    collision_sources.append(source_id)
                scars += 1
                # The expecting side met the mismatch too (v0.3.5 §9): each datum
                # the expectation is moves to `scar` with its own record, carrying
                # the same ResistEvent. The rest of the window met nothing.
                for hid in held_ids:
                    if hid == collided_id:
                        continue
                    held = self._data.get(hid)
                    if held is None or held.fixed.provenance not in ("running", "simulated", "projected"):
                        continue
                    scarred = to_scar(held, True)
                    self._data.put(hid, scarred)
                    self._events.append(
                        record_provenance(hid, self._cycle, held.fixed.provenance, "scar", self._now())
                    )
                    self._events.append(
                        record_scar(
                            scarred,
                            ResistEvent(
                                source_id=source_id,
                                expected=e.predicted.content,
                                received=e.observed.content if e.observed is not None else None,
                                mismatch_kind="value-mismatch",
                                t=self._now(),
                            ),
                            anchor,
                            datum_id=hid,
                        )
                    )
                    scars += 1
        if scar_datum is not None:
            datum = scar_datum
        elif forward_built:
            # projected → running: the cast produced no scar; the datum returns
            # to use — a datum is never a conclusion at rest (§9).
            datum = to_running(datum, self._cycle)
            self._events.append(
                record_provenance(
                    self._datum_id(), self._cycle, "projected", "running", self._now()
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
                    closed_at=self._now(),
                    recalled=tuple(recalled_tags),
                    admitted=tuple(admitted_tags),
                    written=tuple(written_tags.values()),
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
        self._last_lateral = (
            *(e.action for e in pass_.emissions),
            *write_actions.values(),
        )
        self._cycle += 1

        return CycleResult(
            cycle=self._cycle - 1,
            flow=flow,
            appraisal=appraisal,
            response=response,
            scars=scars,
            absences=len(pass_.t7.absences),
            collision_sources=tuple(collision_sources),
            written=len(written_tags),
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
    admit: AdmitPolicy | None = None,
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
        admit=admit,
    )
