"""The eight invariant guards (protocol §5).

Each guard inspects one step and HALTS — raises InvariantViolation — when the
step would violate its invariant. A conforming step returns normally. There is
no "work around": the only responses are pass or halt.

These are structural laws, not tunable policy: no guard reads a threshold, and
none touches a DECIDE@IMPL constant.

Ported from dil-core (TypeScript) against DIL protocol v0.3.3.
"""

from collections.abc import Sequence

from .types import (
    AppraisalCriteria,
    Change,
    GlobModUpdate,
    LayerIndex,
    LoopEdge,
    ReferredUnit,
    RunningOutput,
    TemporalWrite,
)
from .violation import halt


def assert_closed_loop(edges: Sequence[LoopEdge]) -> None:
    """INV-1 — Closed loop.

    Every layer output MUST have a path back to some layer's input; no dead
    branches. Checked on topology, not per-packet timing (the INV-1 note: a
    cycle-time constraint, not wall-clock). Halts if any edge terminates in a
    SINK, or if any layer that RECEIVES output (a target) never produces onward
    (is never a source) — its output dead-ends with no path back into the loop.
    """
    # dicts, not sets: a Python set has no defined iteration order, and the
    # reference iterates JS Sets, which are insertion-ordered. Using dicts as
    # ordered sets keeps the halt message naming the same layer as the reference
    # would when a topology has more than one dead end.
    sources: dict[LayerIndex, None] = {}
    targets: dict[LayerIndex, None] = {}

    for edge in edges:
        if edge.to == "SINK":
            halt("INV-1", f"layer T{edge.from_} output terminates in a SINK (dead branch)")
        sources[edge.from_] = None
        targets[edge.to] = None  # `to` is a LayerIndex here — SINK already halted

    # A layer that receives output but has no outgoing edge is a dead branch: the
    # output that reached it has no path back into the loop. (A source always has
    # an outgoing edge by construction, so the meaningful check is over targets.)
    for layer in targets:
        if layer not in sources:
            halt("INV-1", f"layer T{layer} receives output but has no outgoing edge (dead branch)")


def assert_correlational(output: RunningOutput) -> None:
    """INV-2 — Output-register identity.

    Every running output is tagged INFO and is a correlation (↔), never a frozen
    identity (=). Committing to an action is still a ↔, so it passes; demanding
    or asserting = before the loop has stopped halts.
    """
    if output.register == "=":
        suffix = f": {output.note}" if output.note else ""
        halt("INV-2", f"running output promoted ↔ to = (identity){suffix}")


def assert_meaning_channel_order(consumer: LayerIndex, source: LayerIndex) -> None:
    """INV-3 — One-directional dependency on the meaning-channel.

    Layer N consumes only outputs of layers ≤ N. Halts if a consumer reads from a
    higher source. (The modulatory field acts downward and is governed by INV-7,
    not here.)
    """
    if source > consumer:
        halt(
            "INV-3",
            f"layer T{consumer} consumes from higher layer T{source} on the meaning-channel",
        )


def assert_referred(unit: ReferredUnit) -> None:
    """INV-4 — Meaning as relation.

    No layer assigns meaning to a signal in isolation; meaning is a function of
    (signal, lower-layer context). Halts if a unit leaves a layer without a
    reference frame.
    """
    if unit.ref_frame is None:
        halt("INV-4", "unit has null ref_frame (a signal, not yet information)")


def assert_accrual(write: TemporalWrite) -> None:
    """INV-5 — History accrues, is not loaded.

    Temporal state forms only through sequential accumulation. Halts if a
    temporal-state write loads prior state pre-formed rather than accruing it —
    a reloaded context masquerading as a self.
    """
    if write.kind == "load":
        suffix = f": {write.note}" if write.note else ""
        halt("INV-5", f"temporal state loaded instead of accrued{suffix}")


def assert_agency_classified(change: Change) -> None:
    """INV-6 — Agency-gate.

    Every change MUST be classified self-written or environment-pushed before
    interpretation. Halts if a change reaches interpretation still UNDECIDED.
    """
    if change.agency == "UNDECIDED":
        halt("INV-6", "change interpreted while still UNDECIDED (agency-gate bypassed)")


def assert_glob_mod_update(update: GlobModUpdate) -> None:
    """INV-7 — GLOB-MOD.

    Contributions blend, re-weighted each cycle, never last-write-wins; a layer's
    cycle-N contribution conditions the field only from N+1. Halts on
    last-write-wins, or on a contribution taking effect within its own cycle
    (effect must be strictly later than the contribution).
    """
    if update.mode == "last-write":
        halt("INV-7", "GLOB-MOD updated last-write-wins instead of blended")
    if update.effect_cycle <= update.contrib_cycle:
        halt(
            "INV-7",
            f"GLOB-MOD contribution at cycle {update.contrib_cycle} conditions the field "
            f"at cycle {update.effect_cycle} (must be ≥ N+1)",
        )


def assert_appraisal_independence(criteria: AppraisalCriteria) -> None:
    """INV-8 — Appraisal step.

    The appraisal MUST NOT draw its criteria from the state the agent is editing,
    otherwise it is self-scoring and hackable. Halts if the criteria source is
    the edited state.
    """
    if criteria.criteria_source == criteria.edited_state:
        halt(
            "INV-8",
            f'appraisal draws criteria from the edited state "{criteria.edited_state}" '
            f"(self-scoring)",
        )
