"""ResistEvent — the atomic unit of the experience store (protocol §3, §9).

The store's atomic unit is the registered mismatch (E2), NOT the document.
Information without collision is the root of echo-chamber drift, so what the
store accrues is collisions, not contents.

Each [event] record additionally anchors the FULL field-state of its cycle
(DECIDE@IMPL tag G = full-field-state), so a third party can re-appraise the
event later under its original context (protocol §8.5, §9).

Ported from dil-core against DIL protocol v0.3.3.
"""

from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from ..invariants.types import LayerIndex
from .tags import FixedTags, Provenance, TaggedDatum

# The kind of mismatch a ResistEvent registers.
MismatchKind: TypeAlias = Literal["value-mismatch", "absence", "unexpected-presence"]


class EventRecordError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(f"cannot build [event] record: {detail}")


@dataclass(frozen=True, slots=True)
class ResistEvent:
    """A registered mismatch between expectation and what the region returned."""

    source_id: str
    expected: object
    received: object
    mismatch_kind: MismatchKind
    t: int


@dataclass(frozen=True, slots=True)
class ContextAnchor:
    """The full field-state anchored with an event (DECIDE@IMPL tag G).

    PROVISIONAL shape: the full ModField/GLOB-MOD type lands with the loop; for
    now the anchor carries the cycle's field parameters verbatim so the depth is
    genuinely "full field-state", not a lossy trace.
    """

    cycle: int
    # The complete field parameters in force at the event's cycle.
    field_state: dict[str, object] = field(default_factory=dict)
    depth: Literal["full-field-state"] = "full-field-state"


@dataclass(frozen=True, slots=True)
class EventRecord:
    """An [event] record: the ResistEvent, the `scar` datum it recorded, and the anchor.

    Once written to the [event] log it is read-only forever.

    The record INHERITS its tags from the `[data]` datum it traced: rather than
    re-stating the fixed and open tags (which could drift), the record embeds the
    whole scar datum, so the event carries exactly that datum's four fixed tags
    and its ≥3 open tags (including `domain`, the reason audit-by-class works).
    An [event] record therefore carries the same minimum of seven tags (4 fixed +
    ≥3 open) as any datum, plus the anchor. The path the datum travelled is NOT
    among these tags — it is the stream of lean `layer-exit` lines in the log.
    """

    event: ResistEvent
    # The `[data]` datum that collided and held (provenance `scar`); its tags are
    # the event's tags.
    scar: TaggedDatum
    anchor: ContextAnchor
    kind: Literal["scar"] = "scar"
    # The `[data]` id of the datum that collided: the region's return the
    # expectation was compared against. None, and not written, when the cycle
    # datum stands for the collision instead — an absence, where the region
    # returned nothing. Ported from dil-core 276f30a.
    datum_id: str | None = None


@dataclass(frozen=True, slots=True)
class ActivityEvent:
    """One cycle's activity, for the log's AUDIT role (§9 "completeness of trace").

    What was emitted, what returned, in which flow mode. Trace, not experience —
    no layer learns from it.
    """

    cycle: int
    flow: str
    # The action the agent emitted this cycle (link 5).
    emitted: object
    # The entity ids observed this cycle.
    observed: tuple[str, ...]
    # Collisions recorded as scars this cycle.
    scars: int
    # When the cycle began (host clock, epoch-ms): the cycle datum's timestamp.
    t: int
    # The full tag set of every datum recalled from the store that ran this
    # cycle (§6.4 T3 query), as it stands after running. TAGS ONLY, NO CONTENT:
    # §9's open layer exists so the log is "auditable by data class", and §13.6
    # asks a third party to confirm "host data entered only via the
    # tagging-gate" from the trace; the content stays out because an activity
    # record is trace, not experience ("without letting uncontested information
    # into the agent's memory"). Empty when nothing was recalled, and then not
    # written at all, so every other record is byte-identical.
    recalled: tuple["RecalledTags", ...] = ()
    # The full tag set of every region return that entered `[data]` this
    # cycle, as it stands after running. What the region returns is data: it is
    # what an expectation is compared against, so without it a `scar` would name
    # nothing that collided. Tags only, never content, for the same reason as
    # `recalled`. Empty, and then not written, when nothing was admitted.
    # Ported from dil-core 276f30a.
    admitted: tuple["RecalledTags", ...] = ()
    # The full tag set of every datum the agent wrote this cycle — written anew
    # (entering at `nascent`) or revised (its provenance unchanged) — as it stands
    # once written. Tags only, never content: what a revised datum held is read
    # from the commit snapshot. Each arrives at T1 the next cycle and runs every
    # layer. Empty, and then not written, when nothing was written. Ported from
    # dil-core 44309b7 (v0.3.3).
    written: tuple["RecalledTags", ...] = ()
    # When the cycle closed, as its seal was written. With `t`, how long the
    # cycle took; with every other record's own time, where inside it the time
    # went. None on records written before it was kept. Ported from dil-core 9073ddf.
    closed_at: int | None = None


@dataclass(frozen=True, slots=True)
class RecalledTags:
    """One recalled datum's tag set, as the activity record carries it."""

    datum_id: str
    fixed: FixedTags
    open: dict[str, str]


# Activity records — the log's TRACE lines (§9: "an activity record is trace, not
# experience"; no layer learns from any of them). Every movement of a datum is a
# line, written as it occurs: it is only a log, dense but only a log.
#
# `layer-exit`/`provenance` are lean (a `datum_id` + the move) — they carry no
# embedded datum and no full anchor; the datum with its tags lives on the
# cycle-seal and scar records. `datum_id` is the key a datum takes in `[data]`,
# so a datum's whole path is read by gathering its lines from `[event]`.


@dataclass(frozen=True, slots=True)
class CycleSealActivity:
    """The per-cycle record §9 mandates (emitted/observed/flow)."""

    datum_id: str
    activity: ActivityEvent
    # The cycle datum (provenance `running`, or `scar` if the cycle collided).
    datum: TaggedDatum
    anchor: ContextAnchor
    kind: Literal["activity"] = "activity"
    activity_kind: Literal["cycle-seal"] = "cycle-seal"


@dataclass(frozen=True, slots=True)
class LayerExitActivity:
    """A datum exited one layer (lean: what/where)."""

    datum_id: str
    cycle_mark: int
    # The layer the datum just exited (T1–T8).
    layer: LayerIndex
    t: int
    kind: Literal["activity"] = "activity"
    activity_kind: Literal["layer-exit"] = "layer-exit"


@dataclass(frozen=True, slots=True)
class ProvenanceActivity:
    """A datum moved along a provenance edge (lean: from→to)."""

    datum_id: str
    cycle_mark: int
    from_: Provenance
    to: Provenance
    t: int
    kind: Literal["activity"] = "activity"
    activity_kind: Literal["provenance"] = "provenance"


@dataclass(frozen=True, slots=True)
class EmissionActivity:
    """An emission — link 5 as a lateral capability (§6.4).

    A datum's committed action pushed to the region, naming the layer that issued
    it. Trace, not experience; register is always `↔` (never `=`, INV-2). Its
    correctness is judged only by the next cycle's return, never by the emitting
    layer (no arbiter).
    """

    datum_id: str
    cycle_mark: int
    # The layer that issued this emission (§6.4, §9).
    issuing_layer: LayerIndex
    # The committed action pushed to the region.
    action: object
    t: int
    # Always `↔` — a live, revisable correlation; never `=` (INV-2).
    register: Literal["↔"] = "↔"
    kind: Literal["activity"] = "activity"
    activity_kind: Literal["emission"] = "emission"


@dataclass(frozen=True, slots=True)
class CrystallizationActivity:
    """The ONE-TIME event where T2 first draws the self/environment distinction (§7).

    It records the *act* of distinguishing self from environment — a trace a third
    party reads (E4) — NOT the self and NOT its persistence: recording a
    stable/continuing self would be the internal continuity claim §7 forbids. A
    fresh (non-recovered) self-line crystallizes exactly once; recovery resumes a
    line, it does not re-crystallize.
    """

    datum_id: str
    cycle_mark: int
    t: int
    kind: Literal["activity"] = "activity"
    activity_kind: Literal["crystallization"] = "crystallization"


@dataclass(frozen=True, slots=True)
class ExpectationActivity:
    """An expectation reading — the observable consequence of accumulation (INV-5, T5).

    Each cycle, per observed entity, T5's prediction strength: `confidence`
    (∈ [0,1]) driven by `recurrence` (observations accrued for that entity), and
    `delta` — the magnitude of the prediction error at this probe.

    Recording it makes INV-5 measurable from the log, not merely self-declared:
    over an entity's readings, an accruing self shows confidence and recurrence
    CLIMB together and confidence saturate; a reloading impostor, having no memory
    to increment, cannot make either climb. `delta` additionally gives a third
    party the per-probe prediction error for EVERY probe — including the
    non-colliding ones that leave no scar. `source` is the subject as a
    RESISTANCE-SOURCE identity — the EXPLICIT join key to a scar's `source_id`.
    """

    datum_id: str
    cycle_mark: int
    entity: str
    # The resistance-source identity — the join key to a scar's `source_id`.
    source: str
    confidence: float
    recurrence: float
    # Magnitude of the prediction error at this probe (PredErr.delta, §6.3 T5).
    delta: float
    t: int
    kind: Literal["activity"] = "activity"
    activity_kind: Literal["expectation"] = "expectation"


@dataclass(frozen=True, slots=True)
class ResistanceReadingActivity:
    """A resistance reading for an ABSENCE (§8, T7).

    The source-keyed record that the expectation line (T5, value-mismatch only)
    does not cover. A live region that keeps withholding an expected return is
    resisting by absence; recording it here, per source, lets a third party
    measure that resistance too — so it is not the case that only value-mismatch
    resistance is trace-measurable.
    """

    datum_id: str
    cycle_mark: int
    # The resistance-source identity — the join key to a scar's `source_id`.
    source: str
    # The specific entity whose absence this reads.
    entity: str
    mismatch_kind: MismatchKind
    recurrence: float
    delta: float
    signed: Literal["+", "-"]
    t: int
    kind: Literal["activity"] = "activity"
    activity_kind: Literal["resistance-reading"] = "resistance-reading"


@dataclass(frozen=True, slots=True)
class RevisionActivity:
    """A revision (v0.3.3, §9 "Revision is not entry").

    The agent rewrote the content of a datum it already holds. The datum stays
    the same datum — no provenance move, no entry. A bare record that the
    revision occurred: which datum, in which cycle, by which layer. It carries no
    content, as no `[event]` does; what the datum held is read from the commit
    snapshot.
    """

    datum_id: str
    cycle_mark: int
    issuing_layer: LayerIndex
    t: int
    kind: Literal["activity"] = "activity"
    activity_kind: Literal["revision"] = "revision"


ActivityRecord: TypeAlias = (
    CycleSealActivity
    | LayerExitActivity
    | ProvenanceActivity
    | EmissionActivity
    | CrystallizationActivity
    | ExpectationActivity
    | ResistanceReadingActivity
    | RevisionActivity
)


@dataclass(frozen=True, slots=True)
class ManifestRecord:
    """The manifest — the log's CONSTITUTION (§9, §8.5).

    A one-time genesis record, the first line of a fresh `[event]` log, declaring
    the DECIDE@IMPL configuration the run operates under. It is neither a scar
    (experience) nor a datum-activity (it belongs to no cycle or datum) — it is
    log-level metadata, so it carries no datum_id, cycle_mark, or provenance.

    Recording it makes the log self-describing about the LAW it ran under, not
    only its tag schema: a third party reading only `[event]` can re-appraise the
    trace under the very constants that governed it, and — being hash-chained like
    every line — the constitution is tamper-evident and inseparable from its run.
    """

    protocol: str
    schema_version: int
    # The declared DECIDE@IMPL constitution.
    decisions: dict[str, object]
    t: int
    kind: Literal["manifest"] = "manifest"


# What the [event] log holds: scars (experience), activity records (trace), and a
# one-time manifest (the constitution the run operates under).
LogRecord: TypeAlias = EventRecord | ActivityRecord | ManifestRecord


def record_activity(
    datum_id: str,
    datum: TaggedDatum,
    activity: ActivityEvent,
    anchor: ContextAnchor,
) -> CycleSealActivity:
    """Build the per-cycle cycle-seal activity record.

    The datum must have run (bear a cycle-mark) — it describes a cycle that
    happened.
    """
    if datum.fixed.cycle_mark is None:
        raise EventRecordError(
            "an activity record requires a datum that has run (no cycle-mark present)"
        )
    return CycleSealActivity(datum_id=datum_id, activity=activity, datum=datum, anchor=anchor)


def record_revision(
    datum_id: str, cycle_mark: int, issuing_layer: LayerIndex, t: int
) -> RevisionActivity:
    """A `revision` line: datum D was revised at cycle N by layer L (no content)."""
    return RevisionActivity(
        datum_id=datum_id, cycle_mark=cycle_mark, issuing_layer=issuing_layer, t=t
    )


def record_layer_exit(
    datum_id: str, cycle_mark: int, layer: LayerIndex, t: int
) -> LayerExitActivity:
    """Note a datum exiting a layer (a lean trace line)."""
    return LayerExitActivity(datum_id=datum_id, cycle_mark=cycle_mark, layer=layer, t=t)


def record_provenance(
    datum_id: str, cycle_mark: int, from_: Provenance, to: Provenance, t: int
) -> ProvenanceActivity:
    """Note a datum moving along a provenance edge (a lean trace line)."""
    return ProvenanceActivity(
        datum_id=datum_id, cycle_mark=cycle_mark, from_=from_, to=to, t=t
    )


def record_crystallization(
    datum_id: str, cycle_mark: int, t: int
) -> CrystallizationActivity:
    """Note a crystallization — T2 first drawing the self/environment distinction (§7).

    The act of distinguishing, recorded as a trace; never the self's persistence.
    """
    return CrystallizationActivity(datum_id=datum_id, cycle_mark=cycle_mark, t=t)


def record_expectation(
    datum_id: str,
    cycle_mark: int,
    entity: str,
    source: str,
    confidence: float,
    recurrence: float,
    delta: float,
    t: int,
) -> ExpectationActivity:
    """Note an expectation reading — the accumulation signature of INV-5 (T5)."""
    return ExpectationActivity(
        datum_id=datum_id,
        cycle_mark=cycle_mark,
        entity=entity,
        source=source,
        confidence=confidence,
        recurrence=recurrence,
        delta=delta,
        t=t,
    )


def record_resistance_reading(
    datum_id: str,
    cycle_mark: int,
    source: str,
    entity: str,
    mismatch_kind: MismatchKind,
    recurrence: float,
    delta: float,
    signed: Literal["+", "-"],
    t: int,
) -> ResistanceReadingActivity:
    """Note a resistance reading for an absence (§8, T7)."""
    return ResistanceReadingActivity(
        datum_id=datum_id,
        cycle_mark=cycle_mark,
        source=source,
        entity=entity,
        mismatch_kind=mismatch_kind,
        recurrence=recurrence,
        delta=delta,
        signed=signed,
        t=t,
    )


def record_manifest(
    protocol: str, schema_version: int, decisions: dict[str, object], t: int
) -> ManifestRecord:
    """Build the log's genesis manifest — the DECIDE@IMPL constitution (§9, §8.5)."""
    return ManifestRecord(
        protocol=protocol, schema_version=schema_version, decisions=decisions, t=t
    )


def record_emission(
    datum_id: str, cycle_mark: int, issuing_layer: LayerIndex, action: object, t: int
) -> EmissionActivity:
    """Note an emission — a layer's committed action pushed to the region (§6.4)."""
    return EmissionActivity(
        datum_id=datum_id,
        cycle_mark=cycle_mark,
        issuing_layer=issuing_layer,
        action=action,
        t=t,
    )


def record_scar(
    scar: TaggedDatum,
    event: ResistEvent,
    anchor: ContextAnchor,
    datum_id: str | None = None,
) -> EventRecord:
    """Build an [event] record from the scar datum that produced it.

    The datum MUST be a `scar` (only collision-and-hold reaches the [event] log,
    protocol §9). The event inherits the scar's full tag set by embedding it.
    """
    if scar.fixed.provenance != "scar":
        raise EventRecordError(
            f'datum is "{scar.fixed.provenance}", not a scar; '
            "only collision-and-hold reaches [event]"
        )
    return EventRecord(event=event, scar=scar, anchor=anchor, datum_id=datum_id)
