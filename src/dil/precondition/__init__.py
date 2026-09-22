"""The precondition gate — stage 1 of the build order.

Before DIL starts, it checks whether the host can be reigned over at all. A host
that does not qualify produces a clean non-start, never a degraded half-run.
"""

from .decisions import (
    E3_PROBE_DESIGN,
    E4_PROBE_DESIGN,
    PROBE_NONCE_PREFIX,
    PROBEABLE_CONDITIONS,
)
from .gate import (
    ConditionBasis,
    ConditionId,
    ConditionResult,
    GateResult,
    NonStart,
    Qualify,
    check_precondition,
)

__all__ = [
    "E3_PROBE_DESIGN",
    "E4_PROBE_DESIGN",
    "PROBEABLE_CONDITIONS",
    "PROBE_NONCE_PREFIX",
    "ConditionBasis",
    "ConditionId",
    "ConditionResult",
    "GateResult",
    "NonStart",
    "Qualify",
    "check_precondition",
]
