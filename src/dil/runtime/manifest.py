"""Collect the run's DECIDE@IMPL constitution into a genesis manifest (§9, §8.5).

The runtime ring is the one place that can see every ring's declared choices, so
it gathers them here — reading the ACTUAL declared constants, never re-stating
values, so the manifest cannot drift from the decisions files — and builds the
one-time manifest record the daemon writes as the first `[event]` line. A third
party then reads the law the run operated under from the trusted log alone.

Tag A (Signal / InfoUnit / RefFrame representation) is a TYPE-level choice, not a
runtime value; it is described, not snapshotted. Every other declared choice that
governs behaviour is captured verbatim from its declaration.

Ported from dil-core, first against DIL protocol v0.3.3 (the package
implements `dil.DIL_PROTOCOL_VERSION`).
"""

from ..conformance.decisions import (
    CONFORMANCE_DIVERSITY_WINDOW,
    CONFORMANCE_MIN_DISTINCT_SOURCES,
)
from ..loop.decisions import (
    APPRAISAL_ANCHOR_ID,
    APPRAISAL_ANCHOR_KIND,
    BASELINE_WINDOW,
    MATCHING_WINDOW,
    STABILITY_THRESHOLD,
    SUFFICIENT_RECURRENCE,
)
from ..store.decisions import (
    COMMIT_EVERY,
    CONTEXT_ANCHOR_DEPTH,
    FIT_MEASURE,
    H_COUNT,
    SCHEMA_VERSION,
    STORE_REPRESENTATION,
)
from ..store.resist_event import ManifestRecord, record_manifest
from ..store.substrate import DIL_CLAIM
from .decisions import (
    DIVERSITY_WINDOW,
    MIN_DIVERSITY_SOURCES,
    MODE_B_SOURCE,
    REFLECTION_MECHANISM,
)


def collect_manifest(t: int) -> ManifestRecord:
    """Build the genesis manifest from the declared DECIDE@IMPL choices, stamped at `t`."""
    return record_manifest(
        DIL_CLAIM["protocol"],
        SCHEMA_VERSION,
        {
            "tagA_representation": (
                "Signal/InfoUnit/RefFrame shapes — a type-level choice "
                "(loop/decisions.py), not a runtime value"
            ),
            "tagB_thresholds": {
                "MATCHING_WINDOW": MATCHING_WINDOW,
                "STABILITY_THRESHOLD": STABILITY_THRESHOLD,
                "BASELINE_WINDOW": BASELINE_WINDOW,
                "SUFFICIENT_RECURRENCE": SUFFICIENT_RECURRENCE,
            },
            "tagC_appraisalAnchor": {
                "kind": APPRAISAL_ANCHOR_KIND,
                "id": APPRAISAL_ANCHOR_ID,
            },
            "tagD_modeBSource": MODE_B_SOURCE,
            "tagE_reflection": REFLECTION_MECHANISM,
            "tagF_storeRepresentation": STORE_REPRESENTATION,
            "tagG_contextAnchorDepth": CONTEXT_ANCHOR_DEPTH,
            "tagH_forwardBuilding": {"H_COUNT": H_COUNT, "FIT_MEASURE": FIT_MEASURE},
            "diversity": {
                "window": DIVERSITY_WINDOW,
                "minSources": MIN_DIVERSITY_SOURCES,
            },
            "conformanceDiversity": {
                "window": CONFORMANCE_DIVERSITY_WINDOW,
                "minSources": CONFORMANCE_MIN_DISTINCT_SOURCES,
            },
            "commit": {"COMMIT_EVERY": COMMIT_EVERY},
        },
        t,
    )
