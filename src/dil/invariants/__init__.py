"""Invariants — the eight hard runtime guards (protocol §5).

Everything else runs *inside* these.
"""

from .guards import (
    assert_accrual,
    assert_agency_classified,
    assert_appraisal_independence,
    assert_closed_loop,
    assert_correlational,
    assert_glob_mod_update,
    assert_meaning_channel_order,
    assert_referred,
)
from .types import (
    AgencyTag,
    AppraisalCriteria,
    Change,
    GlobModUpdate,
    LayerIndex,
    LoopEdge,
    ReferredUnit,
    Register,
    RunningOutput,
    TemporalWrite,
)
from .violation import InvariantId, InvariantViolation, halt

__all__ = [
    "AgencyTag",
    "AppraisalCriteria",
    "Change",
    "GlobModUpdate",
    "InvariantId",
    "InvariantViolation",
    "LayerIndex",
    "LoopEdge",
    "ReferredUnit",
    "Register",
    "RunningOutput",
    "TemporalWrite",
    "assert_accrual",
    "assert_agency_classified",
    "assert_appraisal_independence",
    "assert_closed_loop",
    "assert_correlational",
    "assert_glob_mod_update",
    "assert_meaning_channel_order",
    "assert_referred",
    "halt",
]
