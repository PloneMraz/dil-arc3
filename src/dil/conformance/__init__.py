"""The conformance checker (protocol §13) — the outermost ring.

A system conforms if and only if a third party, reading only its externally
verifiable traces, can confirm the seven criteria. This ring reads the `[event]`
log and scores them, carrying the evidence basis of every claim so the report
never overstates what the traces alone prove.
"""

from .checker import (
    ClaimCheck,
    ConformanceReport,
    ConformanceVerdict,
    CriterionResult,
    EvidenceBasis,
    ObservableFacts,
    check_conformance,
)
from .decisions import (
    CONFORMANCE_DIVERSITY_WINDOW,
    CONFORMANCE_MIN_DISTINCT_SOURCES,
)
from .render import render_conformance

__all__ = [
    "CONFORMANCE_DIVERSITY_WINDOW",
    "CONFORMANCE_MIN_DISTINCT_SOURCES",
    "ClaimCheck",
    "ConformanceReport",
    "ConformanceVerdict",
    "CriterionResult",
    "EvidenceBasis",
    "ObservableFacts",
    "check_conformance",
    "render_conformance",
]
