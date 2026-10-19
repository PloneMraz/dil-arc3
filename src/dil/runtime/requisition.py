"""Requisition — DIL imposes its store law on the host's substrate at startup.

This is "the king sits down": run once at startup, after the precondition gate
qualifies, it takes the host's raw durable substrate and imposes DIL's entire
store law on it. In order:

  1. claim the substrate, lay out store/{memory,event-log,commits} and the
     DIL-CLAIM, refusing a foreign or incompatible claim;
  2. bind the durable stores DIL rules on it: `[data]` as SQLite under memory/,
     `[event]` as append-only hash-chained JSONL under event-log/, and the commit
     DAG under commits/;
  3. SCAN the host's pre-existing memory and force every item through the
     tagging-gate — vetted and stamped `prior` — before it enters `[data]`.
     Nothing enters the store untagged (§9, no side door); an item that cannot be
     admitted cleanly is rejected and reported, not smuggled in.

DIL does not import host content wholesale and does not conform to the host's
storage format — it requisitions raw physical memory and rules it.

Ported from dil-core, first against DIL protocol v0.3.3 (the package
implements `dil.DIL_PROTOCOL_VERSION`).
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field as dc_field

from ..host import HostDeclaration
from ..store.commit_store import DirCommitStore, create_dir_commit_store
from ..store.event_log import DurableEventLog, create_durable_event_log
from ..store.sqlite_data_store import SqliteDataStore, create_sqlite_data_store
from ..store.substrate import StoreLayout, claim_substrate
from ..store.tagging_gate import HostDatum, admit_host_data


class RequisitionError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(f"DIL cannot requisition the host: {detail}")


@dataclass(frozen=True, slots=True)
class RejectedItem:
    id: str
    reason: str


@dataclass(frozen=True, slots=True)
class Requisitioned:
    """The durable stores DIL rules on the substrate, plus the scan report."""

    layout: StoreLayout
    data: SqliteDataStore
    events: DurableEventLog
    commits: DirCommitStore
    # Pre-existing host items admitted as `prior`.
    admitted: int = 0
    # Items the host offered that failed vetting — reported, not smuggled.
    rejected: tuple[RejectedItem, ...] = dc_field(default_factory=tuple)

    def close(self) -> None:
        """Release the durable handles (SQLite and the [event] sink)."""
        self.data.close()
        self.events.close()


def requisition(host: HostDeclaration, now: int | None = None) -> Requisitioned:
    """Requisition the host's substrate and impose DIL's store law.

    Raises RequisitionError if the host declares no substrate, and
    SubstrateClaimError if the substrate carries a foreign or incompatible claim.
    Both surface as a clean non-start at the daemon.
    """
    root = host.store.root
    if root is None:
        raise RequisitionError(
            "host declares no durable substrate (store.root); DIL requisitions "
            "physical memory, it does not run its store in RAM"
        )

    stamp = now if now is not None else int(time.time() * 1000)

    layout = claim_substrate(root)
    data = create_sqlite_data_store(os.path.join(layout.memory, "data.sqlite"))
    events = create_durable_event_log(layout.event_log)
    commits = create_dir_commit_store(layout.commits)

    # Scan the host's pre-existing memory; admit each through the tagging-gate as
    # `prior`. No side door: an item that cannot be honestly tagged is rejected.
    admitted = 0
    rejected: list[RejectedItem] = []
    pre = host.store.preexisting

    if pre is not None:
        for item in pre.scan():
            try:
                datum = admit_host_data(
                    HostDatum(
                        payload=item.payload,
                        admitting_layer=item.admitting_layer,
                        open=item.open,
                    ),
                    stamp,
                )
            except Exception as exc:  # noqa: BLE001 — any rejection is reported
                rejected.append(RejectedItem(id=item.id, reason=str(exc)))
            else:
                data.put(item.id, datum)
                admitted += 1

    return Requisitioned(
        layout=layout,
        data=data,
        events=events,
        commits=commits,
        admitted=admitted,
        rejected=tuple(rejected),
    )
