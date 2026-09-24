"""Declared DECIDE@IMPL choices for the loop (protocol §12, tags A, B, C).

Tag A — the concrete representation of Signal, InfoUnit and ActivityEnvironment —
is left open by the protocol because it depends on the environment. This file
declares the representations chosen, so nothing in types.py is a silently
invented shape. These are environment decisions, not protocol law.

HONEST STATUS for every numeric constant below: the protocol lists tag B as "not
yet derived". These are declared *starting* values, tunable, chosen for
plausibility, not fundamental constants. They are declared openly here rather
than buried in a layer.

**Carried over from dil-core's minimal host and not yet re-declared for
ARC-AGI-3.** The tag A entries in particular describe a host-shaped payload; the
ARC declarations — a stack of 64×64 grids with cells 0–15 — are the host's, in
`src/arc3/decisions.py`.

Ported from dil-core against DIL protocol v0.3.3.
"""

from typing import Final

# DECIDE@IMPL tag A — Signal.raw_payload.
# Rationale: a Signal is raw host data, not yet meaning; its payload shape is
# whatever the host emits. It stays open at the type layer and each channel's
# transducer (T3) narrows it. `source_id` is a string, `t` an epoch-millisecond
# integer, matching the store's timestamps.
SIGNAL_PAYLOAD_REPR: Final = "unknown (host-shaped raw bytes/values)"

# DECIDE@IMPL tag A — InfoUnit.content.
# Rationale: content becomes information only once referred to a frame (INV-4);
# its concrete shape is environment-specific.
INFOUNIT_CONTENT_REPR: Final = "unknown (referred content)"

# DECIDE@IMPL tag A — the reference frame an InfoUnit is referred to.
# Rationale: meaning is a function of (signal, lower-layer context), so the frame
# names the lower layer that supplies the context and an identifier of that
# context. It is a non-None structured handle, which is where INV-4 is enforced
# at the type level: a Signal, lacking a frame, is simply not an InfoUnit.
REF_FRAME_REPR: Final = "{ bound_layer, ref } (lower-layer context handle)"

# DECIDE@IMPL tag B — T2 (Agency Differentiation) thresholds (§6.3).

# Recent emissions T2 matches an observed change against.
# Rationale: a small window of the agent's recent emissions, so a change whose
# effect lags by a few cycles can still be recognised as self-written. Wide
# enough to tolerate interleaved actions, narrow enough to stay responsive.
MATCHING_WINDOW: Final = 8

# Cycles of matching before the self/environment line is trusted; until then
# agency stays UNDECIDED.
# Rationale: T2 should not commit a change to SELF_WRITTEN or ENV_PUSHED on a
# single observation; a few cycles of consistent matching must accrue first. The
# INV-6 postcondition applies only once stable.
STABILITY_THRESHOLD: Final = 3

# DECIDE@IMPL tag B — T5 (Temporal Expectation) thresholds (§6.3).

# Past observations kept per entity to build its baseline.
# Rationale: enough history to characterise an entity's behaviour, bounded so
# per-entity memory stays finite.
BASELINE_WINDOW: Final = 16

# Consistent observations before an expectation is trusted (confidence → 1).
# Rationale: an expectation earns confidence as the same return recurs; below
# this count it is held with proportionally lower confidence, not asserted.
SUFFICIENT_RECURRENCE: Final = 3

# DECIDE@IMPL — T5's expectation-update function.
# Rationale: the simplest update that satisfies conformance C2 — prediction error
# falls with repetition against a stable entity. If an entity keeps returning the
# same value, the prediction matches and the error goes to zero. A richer update
# is a later tuning, to be declared if adopted.
EXPECTATION_UPDATE_LAW: Final = (
    "persistence: predict the most recent observation for the entity"
)

# DECIDE@IMPL — the multi-stream activation schedule (§6, cycle-1+).
# Rationale: multi-stream is a FLOW-TOPOLOGY property, not OS concurrency — the
# loop advances in cycle-time, not wall-clock (INV-1 note), so no thread
# parallelism is claimed or needed. What changes at cycle-1 is the mechanism:
# consumption, not dispatch. Every layer is an active site reading its declared
# dependency set from the shared meaning-channel, a published datum is consumable
# by several higher layers at once (T5's one output is read by both T6 and T7),
# and no dependency is driver-smuggled (T6 reads T2's output itself). The switch
# at the 0→1 boundary follows §7 and §13.3: the self crystallizes at T2 of
# cycle-0, and multi-stream flow presupposes it. Each cycle's mode is recorded as
# the open tag `flow`, so it is trace-visible.
MULTI_STREAM_SCHEDULE: Final = (
    "one topological activation pass per cycle over the fixed T1..T8 dependency "
    "DAG; consumption via the meaning-channel (publish/read, INV-3-guarded); "
    "cycle-0 runs a direct hand-off pipeline"
)

# DECIDE@IMPL tag C — the kind of out-of-loop anchor for Mode-A (§8.3, §12).
APPRAISAL_ANCHOR_KIND: Final = "static"
# Identifier of the appraisal's criteria source — external to the agent's edited
# state (INV-8).
APPRAISAL_ANCHOR_ID: Final = "mode-a-static-guide"
# Rationale + HONEST CAVEAT: this uses a STATIC external anchor — a frozen guide
# — for the appraisal step. Per §8.3 a static anchor reaches only
# content-degradation: it buys time, it does not cure a systematic lens-bias,
# because a fixed test is memorizable. It satisfies INV-8, since the criteria are
# frozen against the agent's edits and external to the edited state, but it is
# NOT a real Mode-B brake. The live Mode-B source (tag D) is the host's region.

# DECIDE@IMPL — GLOB-MOD's concrete representation and update law (§12, INV-7).
GLOB_MOD_REPRESENTATION: Final = (
    "ModField.params: dict[str, float] (per-key gains/biases — how to read)"
)
GLOB_MOD_UPDATE_LAW: Final = (
    "convex per-key weighted average of a cycle's contributions; untouched keys "
    "carry over; effect at N+1"
)
# Rationale (the chosen law — no inertia constant):
#   - Each layer contributes a value and a non-negative weight for one or more
#     param keys during cycle N (INV-7: contributions blend, re-weighted each
#     cycle).
#   - At the cycle boundary, the next field's value for each contributed key is
#     the convex weighted average of that cycle's contributions naming the key,
#     Σ wᵢ·vᵢ / Σ wᵢ. A key no layer contributed simply carries over — that is
#     "no new disposition information, so no update", not a weighted self-term.
#   - The blend is applied to a *pending* buffer and becomes the active field
#     only at N+1; the active field is immutable within its own cycle (INV-7:
#     conditions the field only from N+1, never within-cycle).
#
# Why no inertia term and no constant: a previous-field inertia weight would be a
# tag-B constant with no derivation yet, which the protocol forbids inventing,
# and it would make the field partly self-constituted, softening the guarantee
# that the field is constituted by the eight layers so runaway is precluded by
# construction. A convex average of the current cycle's contributions keeps that
# exact: the result is always within the range of the contributions, so the field
# cannot amplify itself from within. No gain cap is needed.
