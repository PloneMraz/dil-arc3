"""The tagging-gate — no side door (protocol §9).

Host data (a pre-existing memory file, say) is admitted to the loop ONLY after
passing the tagging rule: stamped provenance `prior`, with NO cycle-mark until it
has run, plus the open-tag layer — which MUST include the mandatory `domain` tag
(protocol §9) and MUST NOT name a verdict. Untagged data MUST NOT enter the loop.
There is no other way in.

Admission failure is a halt (a raised exception), not a silent drop: data that
cannot be admitted cleanly must not slip into the store half-stamped.

Ported from dil-core against DIL protocol v0.3.2.
"""

from dataclasses import dataclass, field

from ..invariants.types import LayerIndex
from .tags import FixedTags, OpenTags, TaggedDatum, invalid_open_tag_reason


class TaggingGateError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(f"tagging-gate rejected admission: {detail}")


@dataclass(frozen=True, slots=True)
class HostDatum:
    """Raw host data offered for admission."""

    payload: object
    # The layer admitting it (T1 ingestion, normally).
    admitting_layer: LayerIndex
    # Descriptive open tags. MUST include `domain`; never verdict tags. Admission
    # fails if `domain` is missing or any key names a verdict.
    open: OpenTags = field(default_factory=dict)


def admit_host_data(datum: HostDatum, now: int) -> TaggedDatum:
    """Admit host data through the tagging-gate.

    On success the datum leaves stamped as `prior`: timestamp set, cycle-mark None
    (it has not run), floor-tag = the admitting layer, provenance = "prior".
    Raises TaggingGateError if the open tags carry a forbidden verdict dimension,
    are missing `domain`, or fall below the minimum count.
    """
    bad = invalid_open_tag_reason(datum.open)
    if bad is not None:
        raise TaggingGateError(bad)

    return TaggedDatum(
        payload=datum.payload,
        fixed=FixedTags(
            timestamp=now,
            cycle_mark=None,  # a `prior` bears no cycle-mark until it has run
            provenance="prior",
            floor_tag=datum.admitting_layer,
        ),
        open=dict(datum.open),
    )
