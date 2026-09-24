"""The tagging-gate — no side door (protocol §9).

Every datum enters the store ONLY after passing the tagging rule: the four fixed
tags plus the open-tag layer — which MUST include the mandatory `domain` tag
(protocol §9) and MUST NOT name a verdict. Untagged data MUST NOT enter the loop.
There is no other way in. What a datum is stamped depends on where it comes from
(v0.3.3):
  - host data existing before the loop ran → `prior`, no cycle-mark until it has
    run (`admit_host_data`);
  - a datum the agent writes anew → `nascent`, bearing the cycle-mark of the
    cycle that wrote it (`admit_nascent`);
  - what the region returns while the loop runs, and the loop's own per-cycle
    datum → `running`, in use the moment they arrive, told apart by `domain`
    (`admit_arrival`).

Admission failure is a halt (a raised exception), not a silent drop: data that
cannot be admitted cleanly must not slip into the store half-stamped.

Ported from dil-core against DIL protocol v0.3.3.
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


def _checked_open(open_tags: OpenTags) -> dict:
    bad = invalid_open_tag_reason(open_tags)
    if bad is not None:
        raise TaggingGateError(bad)
    return dict(open_tags)


def admit_nascent(datum: HostDatum, now: int, cycle: int) -> TaggedDatum:
    """Admit a datum the agent has written anew (v0.3.3 `nascent`).

    It bears the cycle-mark of the cycle that wrote it from the start, and moves
    `nascent → running` once it has run.
    """
    return TaggedDatum(
        payload=datum.payload,
        fixed=FixedTags(timestamp=now, cycle_mark=cycle, provenance="nascent",
                        floor_tag=datum.admitting_layer),
        open=_checked_open(datum.open),
    )


def admit_arrival(datum: HostDatum, now: int, cycle: int) -> TaggedDatum:
    """Admit what arrives while the loop runs (v0.3.3).

    A return from the region, or the loop's own per-cycle datum: in use the
    moment it arrives, so it enters at `running`, bearing the cycle it arrived
    in. Which class of data it is, is read from its `domain`, not its provenance.
    """
    return TaggedDatum(
        payload=datum.payload,
        fixed=FixedTags(timestamp=now, cycle_mark=cycle, provenance="running",
                        floor_tag=datum.admitting_layer),
        open=_checked_open(datum.open),
    )
