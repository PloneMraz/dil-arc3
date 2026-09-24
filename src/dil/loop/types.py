"""Shared types of the loop (protocol §6.1).

The notation in §6.1 is abstract; concrete representation is DECIDE@IMPL tag A.
This module fixes the shapes the eight layers consume and produce.

Reconciliation with the inner rings — invariants are innermost, the loop is
outer, so the loop depends on them and never the reverse:
  - `LayerIndex` and `AgencyTag` are owned by the invariants ring and imported
    here, not redefined.
  - `ResistEvent` and `MismatchKind` are owned by the store and re-used here: the
    loop writes into the store, so it shares the store's shapes rather than
    duplicating them.

There is no layer trace: v0.3.2 §6.1 drops the path from the running types. It
lives only in `[event]`.

**INV-4 at the type level.** An `InfoUnit` has a non-None `ref_frame`; a `Signal`
has none at all. That difference is the type-level enforcement of "meaning is a
function of (signal, lower-layer context)": a signal without a frame is simply
not yet an InfoUnit.

Ported from dil-core against DIL protocol v0.3.3.
"""

from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from ..invariants.types import AgencyTag, LayerIndex
from ..store.resist_event import MismatchKind, ResistEvent

__all__ = [
    "ActivityEnvironment",
    "AgencyTag",
    "Appraisal",
    "Directive",
    "Expectation",
    "HistoryWindow",
    "InfoUnit",
    "LayerIndex",
    "MismatchKind",
    "ModField",
    "OtherModel",
    "PredErr",
    "RefFrame",
    "RelValue",
    "ResistEvent",
    "Sign",
    "Signal",
    "SocialEdge",
]


@dataclass(frozen=True, slots=True)
class RefFrame:
    """The reference frame an InfoUnit is referred to (DECIDE@IMPL tag A).

    A non-None structured handle: the lower layer that supplies the context, plus
    an identifier of that context. Its presence is INV-4 at the type level.
    """

    # The lower layer whose output supplies the context (INV-3: ≤ consumer).
    bound_layer: LayerIndex
    # Identifier of the context frame within that layer.
    ref: str


@dataclass(frozen=True, slots=True)
class Signal:
    """Raw data, not yet meaning (no ref_frame)."""

    source_id: str
    raw_payload: object
    t: int


@dataclass(frozen=True, slots=True)
class InfoUnit:
    """Information = content referred to a frame.

    `ref_frame` is non-None by construction (INV-4). The path a datum has
    travelled is NOT carried here: v0.3.2 §6.1 drops it from the running types —
    it duplicated, in a mutable type, the path the append-only `[event]` log
    already records, and no layer read it.
    """

    content: object
    ref_frame: RefFrame
    t: int


# Presence confirmed, not yet a self/environment line (T1 output). It is an
# InfoUnit: the root reference frame.
ActivityEnvironment: TypeAlias = InfoUnit

# The window of prior information an Expectation was built from.
HistoryWindow: TypeAlias = tuple[InfoUnit, ...]


@dataclass(frozen=True, slots=True)
class Expectation:
    """A prediction about what a stable entity will return (T5)."""

    predicted: InfoUnit
    # Strength of the prediction (a value, not a threshold). Ramps with
    # `recurrence` (INV-5).
    confidence: float
    # How many observations of this entity have accrued so far — the count that
    # drives `confidence`. Recorded in `[event]` (§9) so a third party can
    # measure the accumulation signature: rising confidence with rising
    # recurrence (INV-5). A reloading impostor has no memory to make either climb.
    recurrence: float
    built_from: HistoryWindow = ()


# The sign a PredErr carries; absence registers as negative (T7).
Sign: TypeAlias = Literal["+", "-"]


@dataclass(frozen=True, slots=True)
class PredErr:
    """Prediction error — where resistance (E2) becomes information (T5/T7).

    `observed` is None when the expected event failed to occur (absence, T7);
    `signed` records direction, `delta` the magnitude.
    """

    observed: InfoUnit | None
    predicted: InfoUnit
    delta: float
    signed: Sign


@dataclass(frozen=True, slots=True)
class OtherModel:
    """A model of an Other; lives fully under Mode-B (T6)."""

    entity_id: str
    context_map: dict[str, object] = field(default_factory=dict)
    independence_evidence: object = None


@dataclass(frozen=True, slots=True)
class RelValue:
    """Relative value of an entity; exists only when N ≥ 2 (T8)."""

    entity_id: str
    relative_rank: float
    comparison_basis: str


@dataclass(frozen=True, slots=True)
class SocialEdge:
    """An Other↔Other interaction observed with no self present (T8)."""

    a_id: str
    b_id: str
    observed_interaction: object


@dataclass(frozen=True, slots=True)
class ModField:
    """GLOB-MOD, the modulatory field, reaching every layer field-to-layer (INV-7).

    `params` carries how to read — gains and biases — never what is read. The
    update law (blend, never last-write; effect at N+1) lives in glob_mod.py.
    """

    params: dict[str, float] = field(default_factory=dict)
    t: int = 0


@dataclass(frozen=True, slots=True)
class Appraisal:
    """Output of the appraisal step (link 4, INV-8)."""

    # Reference to the appraised information.
    info_ref: str
    # Direction/value assigned, relative to the cycle's context, not a fixed scale.
    valence: float
    goal_relevance: float


@dataclass(frozen=True, slots=True)
class Directive:
    """An emitted action — link 5 as a lateral capability (§6.4).

    Emission belongs to no single layer; any layer MAY invoke it when its work
    requires pushing to the region. Whatever layer issues it, an emission carries
    register `↔` — a revisable best-current-guess read against the next cycle's
    consequence — and NEVER `=` (INV-2): committing to an action is not promoting
    a correlation to an identity. Its correctness is never scored by the emitting
    layer; only the next cycle's return judges it, because there is no internal
    action-arbiter (§6.4).

    The capability is genuinely afforded, not merely typed: `process` receives a
    layer-bound `emit`, so any layer CAN raise an emission and the driver records
    it against that layer. Affording the capability is not fabricating behaviour
    for it.
    """

    # The committed action pushed to the region.
    committed_action: object
    # The layer that issued this emission.
    issuing_layer: LayerIndex
    t: int
    # The appraisal(s) this action was built from.
    built_from: tuple[Appraisal, ...] = ()
    # Always `↔` — a live, revisable correlation; never `=` (INV-2).
    register: Literal["↔"] = "↔"
