"""The daemon — the loop as a long-lived run (protocol §4, §9).

Wires the loop over a declared host, with state accruing across cycles. The self
is what occurs while it runs.

Order at startup, and none of it is optional:
  1. **The precondition gate** — check before the king sits down. A host that
     does not qualify gets a clean non-start, and nothing else happens.
  2. **Requisition** — the king sits: DIL claims the host's substrate and imposes
     its store law. Without a declared substrate the daemon falls back to
     in-memory fixtures, which is a test host, never a real deployment.
  3. **Genesis** — on a fresh log the first record is the constitution: the
     DECIDE@IMPL configuration this run operates under (§9, §8.5), so a third
     party reading only `[event]` knows the law it ran under. Hash-chained like
     every line, it is tamper-evident and inseparable from the run. A resumed log
     already carries its genesis manifest and never gets a second one.
  4. **Recovery**, when asked: restore the full accrued state before the cycle
     runs, then stamp the fork immediately.

Ported from dil-core, first against DIL protocol v0.3.3 (the package
implements `dil.DIL_PROTOCOL_VERSION`).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..host import HostDeclaration
from ..loop.cycle import (
    Cycle,
    CycleResult,
    DriverState,
    HostCycleInput,
    AdmitPolicy,
    Layers,
    RespondPolicy,
    create_cycle,
)
from ..loop.decisions import (
    BASELINE_WINDOW,
    MATCHING_WINDOW,
    STABILITY_THRESHOLD,
    SUFFICIENT_RECURRENCE,
)
from ..loop.glob_mod import GlobMod
from ..loop.layers.t2 import Emission
from ..precondition import GateResult, Qualify, check_precondition
from ..store.commit_store import CommitMarker, DirCommitStore
from ..store.data_store import DataStore
from ..store.decisions import COMMIT_EVERY, SYNC_CADENCE
from ..store.event_log import EventLog
from .absorption import measure_absorption
from .commit import (
    SystemSnapshot,
    decode_snapshot_value,
    encode_snapshot_value,
    restore_snapshot,
    take_snapshot,
)
from .diversity import DiversityMonitor, create_diversity_monitor
from .host_source import HostSource
from .manifest import collect_manifest
from .requisition import RejectedItem, Requisitioned, requisition


@dataclass(frozen=True, slots=True)
class RequisitionReport:
    admitted: int
    rejected: tuple[RejectedItem, ...]


class Daemon:
    """The loop, running continuously over a requisitioned host."""

    __slots__ = (
        "_host", "_source", "_layers", "_glob", "_initial_emission", "_now",
        "_respond", "_admit", "_commit_on_write", "_sync_cadence",
        "_fixture_data", "_fixture_events", "_commit_every", "_diversity",
        "_commits", "_chain_head", "_recover_from",
        "_cycle", "_data", "_events", "_requisitioned",
        "_running", "_last", "_total_scars", "_scars_since_commit", "_encoded",
    )

    def __init__(
        self,
        host: HostDeclaration,
        source: HostSource,
        layers: Layers,
        glob: GlobMod,
        initial_emission: Emission,
        now: Callable[[], int] | None = None,
        data: DataStore | None = None,
        events: EventLog | None = None,
        diversity: DiversityMonitor | None = None,
        commits: DirCommitStore | None = None,
        chain_head: Callable[[], str] | None = None,
        commit_every: int | None = None,
        recover_from: str | None = None,
        respond: RespondPolicy | None = None,
        admit: AdmitPolicy | None = None,
        commit_on_write: bool = True,
        sync_cadence: str = SYNC_CADENCE,
    ) -> None:
        # SYNC_CADENCE (store/decisions.py; dil-core c6b8f30): "cycle" syncs
        # `[data]` and `[event]` to disk once a cycle, at its close and before any
        # commit marker; "record", the default, each write.
        if sync_cadence not in ("record", "cycle"):
            raise ValueError(f"sync_cadence is 'record' or 'cycle', not {sync_cadence!r}")
        self._sync_cadence = sync_cadence
        # DEVIATION (COMMIT_CADENCE): whether a cycle in which the agent wrote is
        # committed too. False keeps dil-core's scar rhythm alone.
        self._commit_on_write = commit_on_write
        # How each return from the region enters `[data]` — see `AdmitPolicy`
        # in cycle.py. None keeps the reference admission, `admit_return`.
        self._admit = admit
        # The host's declared terminal-response policy; None keeps dil-core's
        # marker. See cycle.py's RespondContext for why the seam exists.
        self._respond = respond
        self._host = host
        self._source = source
        self._layers = layers
        self._glob = glob
        self._initial_emission = initial_emission
        self._now = now
        self._fixture_data = data
        self._fixture_events = events
        self._commit_every = commit_every if commit_every is not None else COMMIT_EVERY
        self._diversity = diversity if diversity is not None else create_diversity_monitor()
        self._commits = commits
        self._chain_head = chain_head
        self._recover_from = recover_from

        # Resolved at STARTUP (requisition), never before.
        self._cycle: Cycle | None = None
        self._data: DataStore | None = None
        self._events: EventLog | None = None
        self._requisitioned: Requisitioned | None = None

        self._running = False
        self._last: CycleResult | None = None
        self._total_scars = 0
        self._scars_since_commit = 0
        # Each datum's snapshot encoding, kept from one commit to the next while
        # the datum is the same object (a port-side optimization, LOG.md,
        # 2026-09-28): a datum is immutable once stored, so its encoding is too.
        self._encoded: dict[int, tuple[Any, Any]] = {}

    # ── commit markers ─────────────────────────────────────────────────────

    def _write_marker(
        self, recovered_from: str | None = None, state_hash: str | None = None
    ) -> str:
        if self._cycle is None or self._events is None or self._data is None or self._commits is None:
            raise RuntimeError("commit requires a started daemon with a commit store")

        resolved_hash = state_hash
        if resolved_hash is None:
            resolved_hash = self._commits.put_state(
                _snapshot_payload(
                    take_snapshot(
                        self._layers, self._glob, self._cycle.snapshot(), self._data
                    ),
                    self._encoded,
                )
            )

        marker = CommitMarker(
            # A fork marker branches FROM the restored point: the new line's
            # parent is where you checked out, not the abandoned tip.
            parent=recovered_from if recovered_from is not None else self._commits.head(),
            recovered_from=recovered_from,
            chain_head=self._chain_head() if self._chain_head is not None else None,
            event_count=self._events.size(),
            scar_count=self._total_scars,
            cycle=self._cycle.cycle_count(),
            at=int(time.time() * 1000),
            state_hash=resolved_hash,
            config={
                "MATCHING_WINDOW": MATCHING_WINDOW,
                "STABILITY_THRESHOLD": STABILITY_THRESHOLD,
                "BASELINE_WINDOW": BASELINE_WINDOW,
                "SUFFICIENT_RECURRENCE": SUFFICIENT_RECURRENCE,
                "COMMIT_EVERY": self._commit_every,
                "SYNC_CADENCE": self._sync_cadence,
            },
        )
        self._scars_since_commit = 0
        return self._commits.put_marker(marker)

    # ── running ────────────────────────────────────────────────────────────

    def start(self) -> GateResult:
        """Run the precondition gate and, if the host qualifies, begin running."""
        # Check before the king sits down (protocol §4).
        gate = check_precondition(self._host)
        if not isinstance(gate, Qualify):
            return gate

        # The king sits: requisition the host's substrate and impose DIL's store
        # law. Without a declared substrate, fall back to the in-memory fixtures
        # — a test or throwaway host; RAM is never a real deployment's store.
        if self._host.store.root is not None:
            self._requisitioned = requisition(self._host)
            self._data = self._requisitioned.data
            self._events = self._requisitioned.events
            self._commits = self._requisitioned.commits
            if self._sync_cadence == "cycle":
                self._data.sync_each_cycle()
                self._events.sync_each_cycle()
            if self._chain_head is None:
                self._chain_head = self._requisitioned.events.head
        else:
            if self._fixture_data is None or self._fixture_events is None:
                raise RuntimeError(
                    "daemon: host declares no substrate (store.root) and no "
                    "in-memory data/events fixture was provided"
                )
            self._data = self._fixture_data
            self._events = self._fixture_events

        # Genesis: on a FRESH log the first record is the constitution.
        if self._events.size() == 0:
            stamp = self._now() if self._now is not None else int(time.time() * 1000)
            self._events.append(collect_manifest(stamp))

        # Recovery, before the cycle runs: restore the full accrued state.
        resume: DriverState | None = None
        recovered_hash: str | None = None
        recovered_marker: CommitMarker | None = None

        if self._recover_from is not None:
            if self._commits is None:
                raise RuntimeError("recover_from requires a commit store")
            recovered_marker = self._commits.get_marker(self._recover_from)
            snap = _snapshot_from_payload(
                self._commits.get_state(recovered_marker.state_hash)
            )
            resume = restore_snapshot(snap, self._layers, self._glob, self._data)
            recovered_hash = self._recover_from
            self._total_scars = recovered_marker.scar_count

        self._cycle = create_cycle(
            layers=self._layers,
            glob=self._glob,
            data=self._data,
            events=self._events,
            initial_emission=self._initial_emission,
            now=self._now,
            resume=resume,
            respond=self._respond,
            admit=self._admit,
        )
        self._running = True

        # Recovery stamps the fork instantly: parent = the marker restored from.
        if self._commits is not None and recovered_hash is not None and recovered_marker is not None:
            self._sync()
            self._write_marker(
                recovered_from=recovered_hash, state_hash=recovered_marker.state_hash
            )

        return gate

    def step(self) -> bool:
        """Run one cycle if input is available and the daemon is running."""
        if not self._running or self._cycle is None:
            return False
        host_input: HostCycleInput | None = self._source.next()
        if host_input is None:
            return False

        result = self._cycle.run(host_input)
        self._source.deliver(result.response)
        self._diversity.observe(result.collision_sources)
        self._last = result
        self._total_scars += result.scars
        self._scars_since_commit += result.scars

        # §9: the counter fires a commit after COMMIT_EVERY scars, at a cycle
        # boundary. DEVIATION from dil-core, declared (COMMIT_CADENCE): unless the
        # host turns it off (`commit_on_write`), it also
        # fires at the close of every cycle in which the agent wrote a datum, so
        # each version of what it wrote is in a snapshot the marker ties to its
        # place in `[event]` — kept for recovery: what a datum holds is in
        # `[data]` (v0.3.7 §9).
        self._sync()
        if self._commits is not None and (
            self._scars_since_commit >= self._commit_every
            or (self._commit_on_write and result.written > 0)
        ):
            self._write_marker()
        return True

    def run(self, max_cycles: int | None = None) -> None:
        """Run cycles until the source is idle, the daemon stops, or the cap is hit."""
        ran = 0
        while self._running and (max_cycles is None or ran < max_cycles):
            if not self.step():
                break  # source idle
            ran += 1

    def _sync(self) -> None:
        """At a cycle's close: sync the store to disk, when it is synced once a cycle."""
        if self._sync_cadence == "cycle":
            for store in (self._data, self._events):
                sync = getattr(store, "sync", None)
                if sync is not None:
                    sync()

    def stop(self) -> None:
        self._sync()
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def cycles_run(self) -> int:
        return self._cycle.cycle_count() if self._cycle is not None else 0

    # ── signals and reports ────────────────────────────────────────────────

    def diversity_signal(self) -> str | None:
        """The current diversity-loss signal, or None (conformance criterion 7)."""
        return self._diversity.signal()

    def absorption_signal(self) -> str | None:
        """The current absorption signal (§8.3), or None.

        Fires when every sufficiently-probed resistance source has been
        memorized — prediction error → 0 — a deceleration-only regime.
        Observability, not a §13 criterion; read from the `[event]` readings so a
        third party can recompute it from the log.
        """
        if self._events is None:
            return None
        return measure_absorption(self._events.all()).signal

    def last_result(self) -> CycleResult | None:
        """The result of the most recent cycle, or None before the first."""
        return self._last

    def commit(self) -> str | None:
        """Manual, out-of-loop commit trigger; returns the marker hash, or None."""
        if self._running and self._commits is not None:
            self._sync()
            return self._write_marker()
        return None

    def requisition_report(self) -> RequisitionReport | None:
        """Pre-existing host content admitted as `prior`, or rejected.

        None when the daemon ran on an in-memory fixture, or has not started.
        """
        if self._requisitioned is None:
            return None
        return RequisitionReport(
            admitted=self._requisitioned.admitted,
            rejected=self._requisitioned.rejected,
        )

    def close(self) -> None:
        """Release the requisitioned substrate handles and stop the daemon.

        A no-op on the in-memory fixture path. The durable log on disk is
        untouched — append-only, never rolled back.
        """
        if self._requisitioned is not None:
            self._requisitioned.close()
        self._running = False


def _encoded_data(data: list[tuple[str, Any]], held: dict[int, tuple[Any, Any]]) -> list[list[Any]]:
    """`encode_snapshot_value(data)`, each pair's encoding kept in `held` by its
    datum, and taken from there while the datum is the same object — so a
    datum stored before a commit is encoded once, not at every commit after."""
    out: list[list[Any]] = []
    seen: dict[int, tuple[Any, Any]] = {}
    for k, datum in data:
        kept = held.get(id(datum))
        if kept is not None and kept[0] is datum and kept[1][0] == k:
            pair = kept[1]
        else:
            pair = [k, encode_snapshot_value(datum)]
        seen[id(datum)] = (datum, pair)
        out.append(pair)
    held.clear()
    held.update(seen)
    return out


def _snapshot_payload(snap: SystemSnapshot, held: dict[int, tuple[Any, Any]] | None = None) -> dict[str, Any]:
    """The commit store is content-addressed over JSON, so the snapshot goes as data."""
    return {
        "layers": encode_snapshot_value(snap.layers),
        "glob": snap.glob,
        # The driver's whole state, as dil-core keeps it: a recovery that
        # dropped the returns and writes on their way to T1 would lose what the
        # agent asked for and what it wrote in the cycle before the commit.
        "driver": encode_snapshot_value(snap.driver),
        "data": encode_snapshot_value(snap.data) if held is None else _encoded_data(snap.data, held),
    }


def _snapshot_from_payload(payload: Any) -> SystemSnapshot:
    return SystemSnapshot(
        layers=decode_snapshot_value(payload["layers"]),
        glob=payload["glob"],
        driver=_driver_from_payload(payload["driver"]),
        data=[(k, v) for k, v in decode_snapshot_value(payload["data"])],
    )


def _driver_from_payload(value: Any) -> DriverState:
    """The driver state a snapshot carries.

    Snapshots written before 2026-09-24 kept only the counter and the last
    emission; those still restore, with nothing on its way to T1.
    """
    if isinstance(value, dict) and "cycle" in value and "lastEmission" in value:
        return DriverState(
            cycle=value["cycle"],
            last_emission=Emission(action=decode_snapshot_value(value["lastEmission"])),
        )
    driver = decode_snapshot_value(value)
    if not isinstance(driver, DriverState):
        raise ValueError("snapshot carries no driver state")
    return driver


def create_daemon(**kwargs: Any) -> Daemon:
    return Daemon(**kwargs)
