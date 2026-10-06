"""The conformance checker (protocol §13).

A system conforms if and only if a third party, reading only its externally
verifiable traces and not its internals, can confirm the seven criteria of §13.
The one trace is the `[event]` log — the same append-only, read-only log the loop
already writes. This checker reads it, plus a few observable facts a third party
can also see, and scores each criterion.

It is deliberately HONEST about the GRADE of evidence behind each verdict. §13
demands confirmation "from traces alone", but several criteria rest partly on
facts a third party CANNOT read from the log — channel separation, loop closure,
the absence of an action-arbiter, Mode-B holding no store handle. Those are
guaranteed structurally, by construction and verified by tests, not by any trace.
Others are read from a declared decision, and self-continuity (§7) is
attributable only by a third party, never machine-certified.

So each criterion decomposes into claims, each carrying its basis — `trace`,
`structural`, `declared` or `third-party` — and the criterion verdict rolls up
from them. This keeps the report from overstating what the traces alone prove: an
auditor can recompute a trace-only conformance by reading only the `trace` claims.

Ported from dil-core, first against DIL protocol v0.3.3 (the package
implements `dil.DIL_PROTOCOL_VERSION`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, fields
from typing import Literal, TypeAlias

from ..precondition.gate import GateResult, NonStart, Qualify
from ..runtime.decisions import REFLECTION_MECHANISM
from ..store.data_store import is_provenance_edge
from ..store.event_log import ReadableEventLog
from ..store.resist_event import (
    CrystallizationActivity,
    CycleSealActivity,
    EmissionActivity,
    EventRecord,
    ExpectationActivity,
    LayerExitActivity,
    LogRecord,
    ManifestRecord,
    ProvenanceActivity,
    ReadActivity,
    RevisionActivity,
)
from ..store.tags import TaggedDatum, invalid_open_tag_reason
from .decisions import CONFORMANCE_DIVERSITY_WINDOW, CONFORMANCE_MIN_DISTINCT_SOURCES

ConformanceVerdict: TypeAlias = Literal["pass", "partial", "fail", "unverifiable"]

# HOW a claim is established — the epistemic grade §13 turns on:
#   - `trace`       confirmable by a third party reading only the [event] log,
#                   the canonical §13 evidence;
#   - `structural`  guaranteed by construction, verified by tests, NOT readable
#                   from any trace. A structural PASS is trusted, not confirmed;
#   - `declared`    read from a stated DECIDE@IMPL choice or a computed gate
#                   artifact;
#   - `third-party` attributable only from outside the loop, never machine-
#                   certifiable (self-continuity, §7). Such claims cap at
#                   `partial` and can never carry a criterion to `pass`.
EvidenceBasis: TypeAlias = Literal["trace", "structural", "declared", "third-party"]


@dataclass(frozen=True, slots=True)
class ClaimCheck:
    """One sub-claim of a criterion, tagged with how it is established."""

    claim: str
    basis: EvidenceBasis
    verdict: ConformanceVerdict


@dataclass(frozen=True, slots=True)
class CriterionResult:
    id: str
    title: str
    # Rolled up from `claims` — the single source of truth.
    verdict: ConformanceVerdict
    # The criterion decomposed by evidence basis.
    claims: tuple[ClaimCheck, ...]
    # A human-readable summary: the roll-up's rationale.
    detail: str


@dataclass(frozen=True, slots=True)
class ConformanceReport:
    results: tuple[CriterionResult, ...]
    summary: dict[ConformanceVerdict, int]


@dataclass(frozen=True, slots=True)
class ObservableFacts:
    """Observable facts a third party can read alongside the [event] log.

    There is NO self-attestation flag here: a criterion satisfied by the caller's
    own claim is not a measurement. Diversity (criterion 7) is derived from the
    recorded resistance-source distribution; reflection (criterion 5) is read
    from the declared mechanism. Only the gate outcome — itself a structured
    result the system computed, not a bare boolean — is accepted here.
    """

    gate: GateResult | None = None


def _claim(text: str, basis: EvidenceBasis, verdict: ConformanceVerdict) -> ClaimCheck:
    return ClaimCheck(claim=text, basis=basis, verdict=verdict)


def _roll_up(claims: Sequence[ClaimCheck]) -> ConformanceVerdict:
    """Roll a criterion's verdict up from its claims.

    A single failing claim fails the criterion; an unverifiable claim leaves it
    unverifiable; a partial claim — limited evidence, or a third-party claim that
    never reaches pass — caps it at partial. Only when every claim passes does the
    criterion pass.
    """
    if any(c.verdict == "fail" for c in claims):
        return "fail"
    if any(c.verdict == "unverifiable" for c in claims):
        return "unverifiable"
    if any(c.verdict == "partial" for c in claims):
        return "partial"
    return "pass"


def _is_datum_bearing(rec: LogRecord) -> bool:
    """Records that embed a datum and anchor; lean lines do not."""
    return isinstance(rec, (EventRecord, CycleSealActivity))


def _datum_of(rec: EventRecord | CycleSealActivity) -> TaggedDatum:
    return rec.scar if isinstance(rec, EventRecord) else rec.datum


@dataclass(frozen=True, slots=True)
class _Accumulation:
    verdict: ConformanceVerdict
    note: str


def _measure_accumulation(readings: Sequence[ExpectationActivity]) -> _Accumulation:
    """Measure the accumulation signature of INV-5 from the expectation readings.

    The answer to "is this an accruing self or a reloading impostor?", read by a
    third party on a foreign system. Group the readings by entity, ordered by
    cycle, and inspect each entity's (recurrence, confidence) series:

      - FAIL — the reloading signature: recurrence regressed, the count reset, or
        confidence fell while recurrence rose so accrual is not driving the ramp.
        A memoryless impostor cannot avoid one of these once it must fake a series.
      - PASS — an entity's confidence ramped from below saturation up to 1 as its
        recurrence climbed: accumulation is demonstrably observable in the trace.
      - PARTIAL — readings present and non-regressing, but none has yet ramped to
        saturation: too little recurrence to establish the ramp, never a false pass.
    """
    if not readings:
        return _Accumulation(
            "partial",
            "no expectation readings — accumulation not measurable from these traces",
        )

    by_entity: dict[str, list[ExpectationActivity]] = {}
    for e in readings:
        by_entity.setdefault(e.entity, []).append(e)

    saw_ramp = False
    for series in by_entity.values():
        series.sort(key=lambda e: e.cycle_mark)
        for prev, cur in zip(series, series[1:], strict=False):
            if cur.recurrence < prev.recurrence:
                return _Accumulation(
                    "fail",
                    f'entity "{cur.entity}" recurrence regressed '
                    f"{prev.recurrence}→{cur.recurrence} — memory reset, the "
                    "reloading signature (INV-5)",
                )
            # Genuine accrual: while unsaturated, a rise in recurrence MUST lift
            # confidence. Recurrence climbing without confidence climbing — flat
            # or falling — is the broken or faked ramp of something with no real
            # memory behind the number.
            if (
                cur.recurrence > prev.recurrence
                and prev.confidence < 1
                and cur.confidence <= prev.confidence
            ):
                return _Accumulation(
                    "fail",
                    f'entity "{cur.entity}" confidence did not rise '
                    f"{prev.confidence}→{cur.confidence} though recurrence climbed "
                    "while unsaturated — accrual not driving the ramp (INV-5)",
                )

        confs = [e.confidence for e in series]
        if confs and min(confs) < max(confs) and max(confs) >= 1:
            saw_ramp = True

    if saw_ramp:
        return _Accumulation(
            "pass",
            "accumulation observable: an entity's confidence ramped with "
            "recurrence to saturation (INV-5) — a reloading impostor has no "
            "memory to make it climb",
        )
    return _Accumulation(
        "partial",
        "expectation readings present and non-regressing, but none has ramped to "
        "saturation yet — insufficient recurrence to establish accumulation",
    )


def _well_formed_store(rec: LogRecord) -> str | None:
    # The genesis manifest (§9): the run's constitution. Log-level metadata, tied
    # to no datum.
    if isinstance(rec, ManifestRecord):
        if not isinstance(rec.protocol, str) or not isinstance(rec.schema_version, int):
            return "manifest record is malformed (missing protocol/schemaVersion)"
        if not isinstance(rec.decisions, dict):
            return "manifest record carries no declared decisions"
        return None

    # Lean trace lines: only a datum id and the move.
    if not _is_datum_bearing(rec):
        datum_id = getattr(rec, "datum_id", None)
        if not isinstance(datum_id, str) or not datum_id:
            return "a trace line carries no datumId"
        if not isinstance(getattr(rec, "cycle_mark", None), int):
            return "a trace line carries no cycle-mark"
        return None

    datum = _datum_of(rec)  # type: ignore[arg-type]
    anchor = rec.anchor  # type: ignore[union-attr]

    if isinstance(rec, EventRecord):
        if not isinstance(rec.event.source_id, str) or not rec.event.mismatch_kind:
            return "record is not a ResistEvent"
        if datum.fixed.provenance != "scar":
            return "scar record embeds a non-scar datum"
    else:
        if not isinstance(rec.activity.cycle, int):  # type: ignore[union-attr]
            return "cycle-seal carries no cycle"
        if datum.fixed.provenance not in ("running", "scar"):
            return "cycle-seal embeds a datum that has not run"

    f = datum.fixed
    if not isinstance(f.timestamp, int) or not isinstance(f.floor_tag, int):
        return "missing fixed tags"
    domain = datum.open.get("domain")
    if not isinstance(domain, str) or not domain:
        return "missing mandatory open tag `domain`"
    if len(datum.open) < 3:
        return "fewer than three open tags"
    if anchor is None or anchor.depth is None or not isinstance(anchor.cycle, int):
        return "missing context anchor"
    return None


def _covers_all_layers(layers: set[int]) -> bool:
    return all(layer in layers for layer in range(1, 9))


def check_conformance(
    events: ReadableEventLog, facts: ObservableFacts | None = None
) -> ConformanceReport:
    facts = facts if facts is not None else ObservableFacts()
    records = events.all()

    scars = [r for r in records if isinstance(r, EventRecord)]
    datum_bearing = [r for r in records if _is_datum_bearing(r)]
    layer_exits = [r for r in records if isinstance(r, LayerExitActivity)]
    cycle_seals = [r for r in records if isinstance(r, CycleSealActivity)]
    provenance_lines = [r for r in records if isinstance(r, ProvenanceActivity)]
    revisions = [r for r in records if isinstance(r, RevisionActivity)]
    reads = [r for r in records if isinstance(r, ReadActivity)]
    emissions = [r for r in records if isinstance(r, EmissionActivity)]
    crystallizations = [r for r in records if isinstance(r, CrystallizationActivity)]
    expectations = [r for r in records if isinstance(r, ExpectationActivity)]

    results: list[CriterionResult] = []

    def push(id_: str, title: str, claims: Sequence[ClaimCheck], detail: str) -> None:
        results.append(
            CriterionResult(
                id=id_,
                title=title,
                verdict=_roll_up(claims),
                claims=tuple(claims),
                detail=detail,
            )
        )

    # ── C1 — Invariants (§5) ───────────────────────────────────────────────
    # No `=` emitted; four fixed tags present (trace). Channel separation is
    # structural — a third party cannot read it from the log.
    if not records:
        push(
            "1",
            "Invariants",
            [_claim("four fixed tags on every record", "trace", "unverifiable")],
            "no [event] records to read",
        )
    else:
        bad_fixed = next(
            (r for r in datum_bearing if len(fields(_datum_of(r).fixed)) != 4), None
        )
        bad_equals = next((e for e in emissions if e.register != "↔"), None)
        claims = [
            _claim(
                "four fixed tags present on every record",
                "trace",
                "fail" if bad_fixed else "pass",
            ),
            _claim(
                "no `=` emitted — every emission register is ↔ (INV-2)",
                "trace",
                "fail" if bad_equals else "pass",
            ),
            _claim(
                "meaning-channel and modulatory field implemented separately",
                "structural",
                "pass",
            ),
        ]
        if bad_fixed:
            detail = "a record lacks the four fixed tags"
        elif bad_equals:
            detail = (
                "an emission carries register `=` — INV-2 forbids a running loop "
                "emitting `=`"
            )
        else:
            detail = (
                "no `=` in traces; four fixed tags present (channel separation "
                "verified structurally, not from traces)"
            )
        push("1", "Invariants", claims, detail)

    # ── C2 — Host conditions (§4) ──────────────────────────────────────────
    # From the gate outcome: a computed artifact derived from the host's declared
    # and probed conditions.
    if facts.gate is None:
        push(
            "2",
            "Host conditions",
            [
                _claim(
                    "host conditions E1–E4 and P met (gate outcome)",
                    "declared",
                    "unverifiable",
                )
            ],
            "no gate result supplied",
        )
    else:
        probed = sum(1 for c in facts.gate.checks if c.basis == "probed")
        declared = len(facts.gate.checks) - probed
        qualified = isinstance(facts.gate, Qualify)
        push(
            "2",
            "Host conditions",
            [
                _claim(
                    "host conditions E1–E4 and P met (gate outcome)",
                    "declared",
                    "pass" if qualified else "fail",
                )
            ],
            (
                f"E1–E4 and P met; the loop qualified to run ({probed} probed, "
                f"{declared} declared)"
                if qualified
                else f"clean non-start: {facts.gate.reason}"  # type: ignore[union-attr]
            ),
        )

    # ── C3 — Loop (§6) ─────────────────────────────────────────────────────
    # Path T1→T8, flow-mode consistency and emission well-formedness are
    # trace-verifiable; loop closure (INV-1) and the absence of an action-arbiter
    # are structural — verified by construction, not readable from the log.
    if not records:
        push(
            "3",
            "Loop",
            [_claim("every cycle datum's path covers T1→T8", "trace", "unverifiable")],
            "no [event] records to read",
        )
    else:
        # The path lives in [event]: gather each datum's layer-exit lines and
        # check it traversed T1→T8 (§13.6 — read from the log, never from a tag).
        layers_by_datum: dict[str, set[int]] = {}
        for le in layer_exits:
            layers_by_datum.setdefault(le.datum_id, set()).add(le.layer)

        incomplete = next(
            (
                r
                for r in cycle_seals
                if not _covers_all_layers(layers_by_datum.get(r.datum_id, set()))
            ),
            None,
        )
        # The flow mode is the cycle's, so it is on the cycle datum each seal
        # embeds. A scar embeds the datum that collided — a return from the
        # region, which ran in a flow mode but does not carry one as a dimension
        # of its own. Ported from dil-core 276f30a.
        flow_recorded = all(
            isinstance(r.datum.open.get("flow"), str) for r in cycle_seals
        )

        def _flow_inconsistent(r: object) -> bool:
            d = _datum_of(r)  # type: ignore[arg-type]
            flow = d.open.get("flow")
            mark = d.fixed.cycle_mark
            if flow is None or mark is None:
                return False
            return flow != ("single-threaded" if mark == 0 else "multi-stream")

        flow_bad = next((r for r in datum_bearing if _flow_inconsistent(r)), None)

        # §13.3 (link 5, §6.4): every emission carries register ↔ and names a
        # valid issuing layer. The ABSENCE of an action-arbiter is not readable
        # from the trace — absence of evidence — so it is structural.
        bad_emission = next(
            (e for e in emissions if e.register != "↔" or not 1 <= e.issuing_layer <= 8),
            None,
        )

        # A datum recalled from the store runs the layers with the cycle datum,
        # and its exits are recorded under its own id and that cycle's mark (§9).
        recalled_runs = [
            (t.datum_id, r.activity.cycle)
            for r in cycle_seals
            for t in r.activity.recalled
        ]
        # So does every return the region gave that entered `[data]`.
        admitted_runs = [
            (t.datum_id, r.activity.cycle)
            for r in cycle_seals
            for t in r.activity.admitted
        ]
        recalled_gap = next(
            (
                (d, c)
                for d, c in recalled_runs
                if not _covers_all_layers(
                    {
                        le.layer
                        for le in layer_exits
                        if le.datum_id == d and le.cycle_mark == c
                    }
                )
            ),
            None,
        )
        # And a datum the rule wrote runs at the cycle after it was written
        # (v0.3.3 §9), where that cycle is in the trace.
        sealed_cycles = {r.activity.cycle for r in cycle_seals}
        written_runs = [
            (t.datum_id, r.activity.cycle + 1)
            for r in cycle_seals
            for t in r.activity.written
            if r.activity.cycle + 1 in sealed_cycles
        ]
        written_gap = next(
            (
                (d, c)
                for d, c in written_runs
                if not _covers_all_layers(
                    {
                        le.layer
                        for le in layer_exits
                        if le.datum_id == d and le.cycle_mark == c
                    }
                )
            ),
            None,
        )
        admitted_gap = next(
            (
                (d, c)
                for d, c in admitted_runs
                if not _covers_all_layers(
                    {
                        le.layer
                        for le in layer_exits
                        if le.datum_id == d and le.cycle_mark == c
                    }
                )
            ),
            None,
        )

        claims = [
            _claim(
                "every cycle datum's path covers T1→T8 (from layer-exit lines)",
                "trace",
                "fail" if incomplete else "pass",
            ),
            *(
                [
                    _claim(
                        "every recalled datum's path covers T1→T8 in the cycle it ran",
                        "trace",
                        "fail" if recalled_gap else "pass",
                    )
                ]
                if recalled_runs
                else []
            ),
            *(
                [
                    _claim(
                        "every region return's path covers T1→T8 in the cycle it arrived",
                        "trace",
                        "fail" if admitted_gap else "pass",
                    )
                ]
                if admitted_runs
                else []
            ),
            *(
                [
                    _claim(
                        "every datum the agent wrote runs T1→T8 at the next cycle",
                        "trace",
                        "fail" if written_gap else "pass",
                    )
                ]
                if written_runs
                else []
            ),
            _claim(
                "recorded flow mode matches cycle-mark (0 single-threaded, 1+ multi-stream)",
                "trace",
                "fail" if flow_bad else "pass",
            ),
            _claim(
                "every emission carries register ↔ and a valid issuing layer (1–8)",
                "trace",
                "fail" if bad_emission else "pass",
            ),
            _claim(
                "the six links close back on themselves (INV-1 topology)",
                "structural",
                "pass",
            ),
            _claim(
                "no internal action-arbiter — conflict collided as a ResistEvent (§6.4)",
                "structural",
                "pass",
            ),
        ]

        if incomplete:
            detail = (
                "a cycle datum's layer-exit lines do not cover T1–T8 "
                f"({incomplete.datum_id})"
            )
        elif flow_bad:
            d = _datum_of(flow_bad)
            detail = (
                "a record's recorded flow mode contradicts its cycle-mark "
                f"(cycle {d.fixed.cycle_mark}: {d.open.get('flow')})"
            )
        elif bad_emission:
            detail = (
                f"an emission is malformed (register {bad_emission.register}, "
                f"issuing layer {bad_emission.issuing_layer}) — must be ↔ from a "
                "layer 1–8"
            )
        else:
            detail = (
                "every cycle datum's path (from [event] layer-exit lines) covers "
                f"T1→T8; {len(emissions)} emission(s), each register ↔ naming an "
                "issuing layer, no action-arbiter; "
                + (
                    "flow mode recorded and consistent (cycle-0 single-threaded, "
                    "cycle-1+ multi-stream)"
                    if flow_recorded
                    else "flow mode not recorded in these traces"
                )
            )
        push("3", "Loop", claims, detail)

    # ── C4 — Self (§7) ─────────────────────────────────────────────────────
    # Accrual and the one-time crystallization are trace-verifiable;
    # self-continuity is attributable only by a third party.
    if not records:
        push(
            "4",
            "Self",
            [
                _claim(
                    "state accrues — cycle-marks non-decreasing (INV-5)",
                    "trace",
                    "unverifiable",
                )
            ],
            "no [event] records to read",
        )
    else:
        marks = [
            (_datum_of(r).fixed.cycle_mark if _datum_of(r).fixed.cycle_mark is not None else -1)
            for r in datum_bearing
        ]
        non_decreasing = all(
            marks[i] >= marks[i - 1] for i in range(1, len(marks))
        )

        # §7 crystallization: T2 draws the self/environment distinction ONCE, at
        # the T2 of cycle-0. The trace must show it as a one-time act — at most
        # one crystallization record, marking only cycle 0. A later
        # re-crystallization would fabricate a discontinuity the self never
        # underwent. The record is lean by construction: it carries no self datum,
        # so it asserts the *act* of distinguishing, never a persistent self.
        crystallized_once = len(crystallizations) <= 1
        crystallized_at_zero = all(c.cycle_mark == 0 for c in crystallizations)
        crystallization_ok = crystallized_once and crystallized_at_zero

        if not crystallizations:
            crystallization_note = (
                "; no crystallization recorded yet (cycle-0 T2 not reached in "
                "these traces)"
            )
        elif crystallization_ok:
            crystallization_note = (
                "; the self/environment distinction crystallized once at cycle-0 "
                "(§7), recorded as an act — no persistent self is asserted"
            )
        elif not crystallized_once:
            crystallization_note = (
                f"; self/environment distinction drawn {len(crystallizations)} "
                "times — crystallization is one-time (§7)"
            )
        else:
            crystallization_note = (
                "; a crystallization record marks a cycle other than 0 — the "
                "distinction is drawn at cycle-0 T2 (§7)"
            )

        # INV-5 accumulation, MEASURED from the expectation ramp — not the weak
        # cycle-mark proxy, which a reloading impostor also passes, and not a
        # self-declared guard, which trusts the declarer.
        accum = _measure_accumulation(expectations)

        claims = [
            _claim(
                "cycle-marks non-decreasing (basic monotonicity)",
                "trace",
                "pass" if non_decreasing else "partial",
            ),
            _claim(
                "accumulation observable — confidence ramps with recurrence to "
                "saturation (INV-5)",
                "trace",
                accum.verdict,
            ),
            _claim(
                "self/environment distinction crystallized once, at cycle-0 (§7)",
                "trace",
                "pass" if crystallization_ok else "fail",
            ),
            _claim("no internal claim of measured continuity (§7)", "structural", "pass"),
            _claim(
                "self-continuity — attributable only by a third party (§7)",
                "third-party",
                "partial",
            ),
        ]
        head = (
            "state accrues (cycle-marks non-decreasing, INV-5), no internal "
            "continuity claim; self-continuity itself is attributable only by a "
            "third party (§7)"
            if non_decreasing
            else "cycle-marks not monotonic — either a recovery fork re-entered "
            "earlier cycles (cross-check the commit DAG: fork markers carry "
            "recoveredFrom) or accrual is suspect"
        )
        push("4", "Self", claims, head + crystallization_note + "; " + accum.note)

    # ── C5 — Resistance (§8) ───────────────────────────────────────────────
    if not records:
        push(
            "5",
            "Resistance",
            [
                _claim(
                    "resistance-source diversity in traces (Mode-A not pure)",
                    "trace",
                    "unverifiable",
                )
            ],
            "no [event] records to read",
        )
    else:
        sources = {r.event.source_id for r in scars}
        mode_b_evidence = len(sources) >= 2
        # Reflection status is read from the declared decision, not a caller flag.
        reflection = REFLECTION_MECHANISM != "DEFERRED"
        # §8.4 "Mode-B returns; it does not write": the source and the reflection
        # reader hold only a read-only [event] view and the HostSource has no
        # store handle — a structural guarantee, not read from traces. Its returns
        # must be REGISTERED rather than left to pass (pure Mode-A): a registered
        # return is a scar or an observed entity in the trace.
        returns_registered = bool(scars) or any(
            len(s.activity.observed) > 0 for s in cycle_seals
        )
        claims = [
            _claim(
                "resistance-source diversity in traces (Mode-A not pure)",
                "trace",
                "pass" if mode_b_evidence else "partial",
            ),
            _claim(
                "Mode-B returns registered, not left to pass (§8.4)",
                "trace",
                "pass" if returns_registered else "partial",
            ),
            _claim(
                "Mode-B writes to no store — read-only view, no store handle (§8.4)",
                "structural",
                "pass",
            ),
            _claim(
                "reflection wired as external ENV_PUSHED input (§8.4, tag E)",
                "declared",
                "pass" if reflection else "partial",
            ),
        ]
        push(
            "5",
            "Resistance",
            claims,
            f"{len(sources)} distinct resistance source(s) in traces"
            + (" (Mode-A not pure)" if mode_b_evidence else " (limited diversity)")
            + (
                "; returns registered (not left to pass)"
                if returns_registered
                else "; returns not registered — the loop may be letting returns "
                "pass (pure Mode-A)"
            )
            + "; Mode-B writes to no store (structural: read-only view, no store handle)"
            + ("; reflection wired" if reflection else "; reflection is DEFERRED (§8.4, tag E)"),
        )

    # ── C6 — Store (§9) ────────────────────────────────────────────────────
    if not records:
        push(
            "6",
            "Store",
            [
                _claim(
                    "every record well-formed (tags, anchor, ResistEvent)",
                    "trace",
                    "unverifiable",
                )
            ],
            "no [event] records to read",
        )
    else:
        first_problem: str | None = None
        for rec in records:
            problem = _well_formed_store(rec)
            if problem:
                first_problem = problem
                break

        # §13.6: every cycle leaves an activity record — coverage must be
        # contiguous from cycle 0 to the highest cycle seen.
        activity_cycles = {r.activity.cycle for r in cycle_seals}
        coverage_gap: int | None = None
        if not activity_cycles:
            coverage_gap = 0
        else:
            for c in range(max(activity_cycles) + 1):
                if c not in activity_cycles:
                    coverage_gap = c
                    break

        # §13.6: provenance moves only along the edges of the §9 graph, so nothing
        # ever returns to `prior`, and `prior` is entered once.
        bad_edge = next(
            (r for r in provenance_lines if not is_provenance_edge(r.from_, r.to)), None
        )
        prior_entries: dict[str, int] = {}
        for r in provenance_lines:
            if r.from_ in ("prior", "nascent"):
                prior_entries[r.datum_id] = prior_entries.get(r.datum_id, 0) + 1
        double_entry = next(((k, n) for k, n in prior_entries.items() if n > 1), None)
        # §13.6: "host data entered only via the tagging-gate". Every datum that
        # leaves `prior` must show, in that cycle's activity record, a tag set the
        # gate would have admitted: the cycle datum embedded whole, a recalled
        # datum by its tags. One that ran from `prior` with no tag set in the
        # trace came in by a door the log cannot see.
        tags_seen: dict[tuple[str, int], dict[str, str]] = {}
        # Every datum whose entry shows in the trace, with the first cycle it shows.
        entered: dict[str, int] = {}
        for r in cycle_seals:
            tags_seen[(r.datum_id, r.activity.cycle)] = dict(r.datum.open)
            entered.setdefault(r.datum_id, r.activity.cycle)
            for t in (*r.activity.recalled, *r.activity.admitted, *r.activity.written):
                tags_seen[(t.datum_id, r.activity.cycle)] = dict(t.open)
                entered[t.datum_id] = min(entered.get(t.datum_id, r.activity.cycle), r.activity.cycle)

        # A datum leaving `prior` shows its tags in that cycle's record; one
        # leaving `nascent` showed them in the record of the cycle that wrote it.
        def _entry_key(r: ProvenanceActivity) -> tuple[str, int]:
            return (r.datum_id, r.cycle_mark if r.from_ == "prior" else r.cycle_mark - 1)

        unseen_entry = next(
            (
                r
                for r in provenance_lines
                if r.from_ in ("prior", "nascent")
                and (
                    _entry_key(r) not in tags_seen
                    or invalid_open_tag_reason(tags_seen[_entry_key(r)]) is not None
                )
            ),
            None,
        )
        # v0.3.3 §9: every datum entered through the gate, "its entry recorded
        # with the tag set it entered with". A datum that leaves a line in the
        # trace with no entry anywhere before it came in by a door the log
        # cannot see.
        no_entry = next(
            (
                r
                for r in (*layer_exits, *revisions)
                if r.datum_id not in entered or entered[r.datum_id] > r.cycle_mark
            ),
            None,
        )
        # v0.3.4 §9: a datum the agent writes records what it was built from —
        # the ids of data whose entry the trace shows, by the cycle it was
        # written in. Ported from dil-core c2c0cd2.
        unbuilt = next(
            (
                (w, r.activity.cycle)
                for r in cycle_seals
                for w in r.activity.written
                if any(i not in entered or entered[i] > r.activity.cycle for i in w.built_from)
            ),
            None,
        )
        # DEVIATION 7 (dil-arc3, 2026-10-05): what the agent read of `[data]` was
        # memory — data whose entry the trace shows before the cycle that read
        # them. What arrives in a cycle is met in it, not recalled.
        unremembered = next(
            (
                (r, i)
                for r in reads
                for i in r.read
                if i not in entered or entered[i] >= r.cycle_mark
            ),
            None,
        )
        # v0.3.5 §9: every datum an expectation named as what it is shows its
        # entry by then, and — when that expectation mismatched against what the
        # region returned — met the mismatch: a scar naming it at that cycle.
        # Ported from dil-core 4f5da8f.
        region_returns = {t.datum_id for r in cycle_seals for t in r.activity.admitted}
        scarred_at = {(s.datum_id, s.anchor.cycle) for s in scars}

        def _unheld(x: ExpectationActivity) -> bool:
            if any(i not in entered or entered[i] > x.cycle_mark for i in x.held_by):
                return True
            if x.delta <= 0:
                return False
            against_region = any(
                s.anchor.cycle == x.cycle_mark and s.event.source_id == x.source
                and s.datum_id in region_returns
                for s in scars
            )
            return against_region and any((i, x.cycle_mark) not in scarred_at for i in x.held_by)

        unheld = next(
            (x for x in records if isinstance(x, ExpectationActivity) and _unheld(x)),
            None,
        )

        claims = [
            _claim(
                "every record well-formed — 4 fixed + ≥3 open tags incl domain + anchor",
                "trace",
                "fail" if first_problem else "pass",
            ),
            _claim(
                "every cycle left an activity record (contiguous coverage)",
                "trace",
                "fail" if coverage_gap is not None else "pass",
            ),
            _claim(
                "provenance moves only along the §9 graph edges",
                "trace",
                "fail" if bad_edge else "pass",
            ),
            _claim(
                "`prior` and `nascent` each entered once, never re-entered (§9)",
                "trace",
                "fail" if double_entry else "pass",
            ),
            _claim(
                "host data entered only via the tagging-gate — every datum leaving "
                "`prior` or `nascent` shows its gate-admissible tag set in the trace (§13.6)",
                "trace",
                "fail" if unseen_entry else "pass",
            ),
            _claim(
                "every datum that ran or was revised shows its entry, with its tag "
                "set, in the trace (§9)",
                "trace",
                "fail" if no_entry else "pass",
            ),
            _claim(
                "every datum the agent wrote says what it was built from, each a "
                "datum whose entry the trace shows (§9)",
                "trace",
                "fail" if unbuilt else "pass",
            ),
            _claim(
                "every datum the agent read of `[data]` shows its entry in the trace "
                "before the cycle that read it (DEVIATION 7)",
                "trace",
                "fail" if unremembered else "pass",
            ),
            _claim(
                "every datum an expectation was (held_by) shows its entry, and met "
                "its mismatch against the region as a scar (§9, v0.3.5)",
                "trace",
                "fail" if unheld else "pass",
            ),
        ]

        if first_problem:
            detail = f"a record failed: {first_problem}"
        elif coverage_gap is not None:
            detail = (
                f"activity-record coverage gap: no activity record for cycle "
                f"{coverage_gap}"
            )
        elif bad_edge:
            detail = (
                f"illegal provenance move in the trace: {bad_edge.from_} → "
                f"{bad_edge.to} ({bad_edge.datum_id})"
            )
        elif double_entry:
            detail = (
                f"datum {double_entry[0]} entered `prior` more than once; prior is "
                "a one-way entry (§9)"
            )
        elif unseen_entry:
            detail = (
                f"datum {unseen_entry.datum_id} left `{unseen_entry.from_}` at cycle "
                f"{unseen_entry.cycle_mark} with no gate-admissible tag set in the "
                "trace (§13.6)"
            )
        elif no_entry:
            detail = (
                f"datum {no_entry.datum_id} appears at cycle {no_entry.cycle_mark} "
                "with no recorded entry before it (§9)"
            )
        elif unbuilt:
            detail = (
                f"datum {unbuilt[0].datum_id}, written at cycle {unbuilt[1]}, does "
                "not say what it was built from, or names data with no recorded "
                "entry (§9)"
            )
        elif unremembered:
            detail = (
                f"datum {unremembered[1]}, read at cycle {unremembered[0].cycle_mark}, "
                "shows no entry in the trace before that cycle"
            )
        elif unheld:
            detail = (
                f"the expectation for {unheld.entity} at cycle {unheld.cycle_mark} "
                "names as what it is data with no recorded entry, or data that did "
                "not scar when it mismatched against the region (§9)"
            )
        else:
            detail = (
                "scars carry the ResistEvent and every cycle left an activity "
                "record; provenance moves only along the §9 graph edges (prior "
                "and nascent each entered once); every datum that ran shows its "
                "entry; all records carry four fixed tags, ≥3 open tags "
                "incl domain, and a context anchor; the log is append-only with "
                "read-only records"
            )
        push("6", "Store", claims, detail)

    # ── C7 — Failure signals (§11) ─────────────────────────────────────────
    # Resistance-source diversity, DERIVED from the [event] log's source
    # distribution, never from a caller's claim. Over the most recent window:
    # enough evidence and diverse → pass; enough evidence and collapsed → fail;
    # not enough evidence → partial, never pass.
    window = scars[-CONFORMANCE_DIVERSITY_WINDOW:]
    if len(window) < CONFORMANCE_DIVERSITY_WINDOW:
        push(
            "7",
            "Failure signals",
            [
                _claim(
                    "resistance-source diversity established from traces",
                    "trace",
                    "partial",
                )
            ],
            f"insufficient evidence: {len(window)} recorded collision(s) < window "
            f"{CONFORMANCE_DIVERSITY_WINDOW}; diversity cannot be established from traces",
        )
    else:
        distinct = len({r.event.source_id for r in window})
        diverse = distinct >= CONFORMANCE_MIN_DISTINCT_SOURCES
        push(
            "7",
            "Failure signals",
            [
                _claim(
                    "resistance-source diversity established from traces",
                    "trace",
                    "pass" if diverse else "fail",
                )
            ],
            (
                f"resistance-source diversity established from traces: {distinct} "
                f"distinct sources over the last {CONFORMANCE_DIVERSITY_WINDOW} records"
                if diverse
                else f"diversity-loss established from traces: only {distinct} "
                f"distinct source(s) over the last {CONFORMANCE_DIVERSITY_WINDOW} "
                f"records (< {CONFORMANCE_MIN_DISTINCT_SOURCES})"
            ),
        )

    summary: dict[ConformanceVerdict, int] = {
        "pass": 0,
        "partial": 0,
        "fail": 0,
        "unverifiable": 0,
    }
    for r in results:
        summary[r.verdict] += 1

    return ConformanceReport(results=tuple(results), summary=summary)
