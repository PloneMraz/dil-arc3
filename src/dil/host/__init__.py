"""The host's structural self-description.

Per the sovereign principle, DIL does not build adapters the host must conform
to. The host *declares* where its faculties are and what structural capacities it
affords; DIL reads this declaration. This module fixes the shape of that
declaration.

Each field maps to exactly one precondition checked by the gate (protocol §4):
the gate's job is to read these structural facts — all answerable *before* the
loop runs — and answer qualify or non-start.

Ported from dil-core against DIL protocol v0.3.3.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class ChannelDeclaration:
    """A declared channel in the host's region.

    E2 is measured on the pair (agent, region): the test is whether the region
    can return *anything at all*, not whether an Other is present.
    """

    # Stable identifier for this channel.
    id: str
    # Can this channel return anything other than silence? A region whose
    # channels never return is a void field (protocol §4, E2).
    can_return: bool


@runtime_checkable
class StoreProbe(Protocol):
    """Optional probe handle for E3/P(b).

    The host declares how its store can be written and read back, and the GATE
    performs the round-trip — the host does not attest its own probe result. An
    absent handle means the condition is graded `declared` instead of `probed`.
    """

    def write(self, key: str, value: str) -> None: ...
    def read(self, key: str) -> str | None: ...


@runtime_checkable
class TraceProbe(Protocol):
    """Optional probe handle for E4.

    The host declares how a trace can be left and read back externally; the gate
    leaves a marker and reads for it.
    """

    def leave(self, marker: str) -> None: ...
    def read(self) -> list[str]: ...


@dataclass(frozen=True, slots=True)
class PreexistingItem:
    """One item of the host's pre-existing content, offered for admission at startup.

    DIL does NOT import host content wholesale: on startup it scans this and
    forces every item through the tagging-gate — vetted and stamped provenance
    `prior` — before anything enters the store (§9, no side door). The host
    supplies the raw payload and its *descriptive* open tags, which must satisfy
    the gate: include `domain`, at least three tags, no verdict. DIL owns the
    stamping.
    """

    # A stable id/key this item takes in `[data]`.
    id: str
    payload: object
    # Descriptive open tags (must satisfy the tagging-gate).
    open: dict[str, str] = field(default_factory=dict)
    # The admitting layer (T1 ingestion by default).
    admitting_layer: int = 1


@runtime_checkable
class PreexistingMemory(Protocol):
    """The host's pre-existing memory, declared so DIL can scan it at startup.

    DIL reads the host's declaration of *where* its content is; it does not
    assume the host's storage format. Every scanned item is vetted and stamped
    `prior`.
    """

    def scan(self) -> Iterable[PreexistingItem]: ...


@dataclass(frozen=True, slots=True)
class BoundaryDeclaration:
    """E1 — Differentiability.

    A boundary permitting an internal/external distinction to be drawn. The
    drawing itself is T2's work, not the host's; the host need only afford the
    boundary.
    """

    present: bool


@dataclass(frozen=True, slots=True)
class StoreDeclaration:
    """E3 — Temporal accumulation, and P(b), the same condition restated for bootstrap.

    State held across cycles so history accrues — accrual, not loading (INV-5).
    """

    persists_across_cycles: bool
    probe: StoreProbe | None = None
    # The host's *raw durable substrate* location — a directory or partition on
    # its native storage that DIL requisitions and imposes its store law on. This
    # is NOT a store abstraction DIL conforms to; it is raw physical memory DIL
    # rules. Absent means DIL runs on an in-memory fixture, never a real
    # deployment.
    root: str | None = None
    # The host's pre-existing content, scanned at startup and admitted through
    # the tagging-gate as `prior` (no side door). Absent means nothing pre-exists.
    preexisting: PreexistingMemory | None = None


@dataclass(frozen=True, slots=True)
class TraceDeclaration:
    """E4 — Observable projection. Every action leaves an externally readable trace."""

    externally_readable: bool
    probe: TraceProbe | None = None


@dataclass(frozen=True, slots=True)
class EmitterDeclaration:
    """P(a) — emission.

    Can the host emit a first action at cycle-0 at all? This checks the *capacity
    to emit*, not whether the emission is distinguishable from ambient
    fluctuation — that is T2's later work.
    """

    can_emit_first_action: bool


@dataclass(frozen=True, slots=True)
class ResilienceDeclaration:
    """P(c) — no self-wipe.

    The host must lack the defect of wiping its own state clean on every
    mismatch; otherwise no scar survives. `True` here names the defect being
    present — a stateless-reset-per-call host — which fails P(c).
    """

    wipes_state_on_mismatch: bool


@dataclass(frozen=True, slots=True)
class HostDeclaration:
    """What the host declares about itself, read once by the gate before the loop runs."""

    boundary: BoundaryDeclaration
    channels: tuple[ChannelDeclaration, ...]
    store: StoreDeclaration
    trace: TraceDeclaration
    emitter: EmitterDeclaration
    resilience: ResilienceDeclaration


__all__ = [
    "BoundaryDeclaration",
    "ChannelDeclaration",
    "EmitterDeclaration",
    "HostDeclaration",
    "PreexistingItem",
    "PreexistingMemory",
    "ResilienceDeclaration",
    "StoreDeclaration",
    "StoreProbe",
    "TraceDeclaration",
    "TraceProbe",
]
