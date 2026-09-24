"""EventSink — durable, write-once mirroring of the [event] log (protocol §9).

The in-memory [event] log is append-only with read-only records, but it dies with
the process. An EventSink is the persistence: an append-only, WRITE-ONCE surface
— `write` and nothing else; no update, delete, or truncate exists.

The JSONL sink writes into a DIRECTORY of daily segments:
    event-log-YYYYMMDD.jsonl, overflowing to -002, -003… when a segment would
    exceed MAX_SEGMENT_BYTES (records are never split across files). Segments are
    opened append-only and never rewritten or truncated; the hash chain continues
    ACROSS segments and restarts, so the whole directory verifies as one chain. No
    segment is ever pruned — records, once written, are never removed (§9); an
    append failure (e.g. disk full) raises, halting the loop rather than dropping a
    record.

Enforcement boundary (honest scope): durability + tamper-evidence at rest
(verify_jsonl_sink detects any altered, removed, inserted, or reordered line). A
total rewrite by a party with full write access requires anchoring the chain head
outside their reach (deployment-open). NOT the §9 full-system commit/snapshot.

WIRE FORMAT. The keys written to disk stay camelCase — cycleMark, floorTag,
datumId, issuingLayer, mismatchKind, schemaVersion, fieldState — even though the
attributes in this implementation are snake_case. That is deliberate: it keeps
the on-disk format identical to dil-core's, so a log written by either
implementation is readable and verifiable by the other. Key ORDER is equally
load-bearing, because the hash covers the serialized text; each builder below
emits its keys in the reference's order.

Ported from dil-core against DIL protocol v0.3.3.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, TypeAlias

from .decisions import MAX_SEGMENT_BYTES
from .hash_chain import (
    CHAIN_GENESIS,
    ChainedEventLine,
    ChainVerification,
    chain_next,
    verify_chain,
)
from .resist_event import (
    RecalledTags,
    ActivityEvent,
    ContextAnchor,
    CrystallizationActivity,
    CycleSealActivity,
    EmissionActivity,
    EventRecord,
    ExpectationActivity,
    LayerExitActivity,
    LogRecord,
    ManifestRecord,
    ProvenanceActivity,
    ResistanceReadingActivity,
    ResistEvent,
    RevisionActivity,
)
from .tags import FixedTags, TaggedDatum

# A serialized [event] line, discriminated by `form`. The reference models this
# as a union of interfaces; on the wire — and therefore for the hash — it is a
# JSON object, and a dict with a fixed key order is exactly that.
SerializedEventRecord: TypeAlias = dict[str, Any]


def _anchor_dict(anchor: ContextAnchor) -> dict[str, Any]:
    return {"depth": anchor.depth, "cycle": anchor.cycle, "fieldState": anchor.field_state}


def _resist_event_dict(event: ResistEvent) -> dict[str, Any]:
    return {
        "source_id": event.source_id,
        "expected": event.expected,
        "received": event.received,
        "mismatch_kind": event.mismatch_kind,
        "t": event.t,
    }


def _activity_event_dict(activity: ActivityEvent) -> dict[str, Any]:
    out: dict[str, Any] = {
        "cycle": activity.cycle,
        "flow": activity.flow,
        "emitted": activity.emitted,
        "observed": list(activity.observed),
        "scars": activity.scars,
        "t": activity.t,
    }
    if activity.closed_at is not None:
        out["closedAt"] = activity.closed_at
    # Written only when something was recalled, so every other line is exactly
    # what it was (and matches dil-core's form byte for byte).
    if activity.recalled:
        out["recalled"] = [_tags_dict(r) for r in activity.recalled]
    if activity.admitted:
        out["admitted"] = [_tags_dict(r) for r in activity.admitted]
    if activity.written:
        out["written"] = [_tags_dict(r) for r in activity.written]
    return out


def _tags_dict(r: RecalledTags) -> dict[str, Any]:
    return {
        "datumId": r.datum_id,
        "fixed": {
            "timestamp": r.fixed.timestamp,
            "cycleMark": r.fixed.cycle_mark,
            "provenance": r.fixed.provenance,
            "floorTag": r.fixed.floor_tag,
        },
        "open": dict(r.open),
    }


def _tags_of(r: dict[str, Any]) -> RecalledTags:
    return RecalledTags(
        datum_id=r["datumId"],
        fixed=FixedTags(
            timestamp=r["fixed"]["timestamp"],
            cycle_mark=r["fixed"]["cycleMark"],
            provenance=r["fixed"]["provenance"],
            floor_tag=r["fixed"]["floorTag"],
        ),
        open=dict(r["open"]),
    )


def _datum_form(
    form: str,
    datum: TaggedDatum,
    *,
    event: ResistEvent | None = None,
    activity: ActivityEvent | None = None,
    datum_id: str | None = None,
    anchor: ContextAnchor,
) -> SerializedEventRecord:
    """Serialize a datum-bearing record (`scar` or `cycle-seal`).

    Its tag set flattened in fixed order — timestamp, cycle-mark, provenance,
    floor-tag, open tags (incl. domain) — then the payload, the kind-specific
    body, and the context anchor. The path a datum travelled is NOT here (§9): it
    is the stream of lean `layer-exit`/`provenance` lines.
    """
    f = datum.fixed
    out: SerializedEventRecord = {
        "form": form,
        "timestamp": f.timestamp,
        "cycleMark": f.cycle_mark,
        "provenance": f.provenance,
        "floorTag": f.floor_tag,
        "open": datum.open,
        "payload": datum.payload,
    }
    if datum_id is not None:
        out["datumId"] = datum_id
    if event is not None:
        out["event"] = _resist_event_dict(event)
    if activity is not None:
        out["activity"] = _activity_event_dict(activity)
    out["anchor"] = _anchor_dict(anchor)
    return out


def serialize_event_record(rec: LogRecord) -> SerializedEventRecord:
    """Project a LogRecord into its serialized form (tags in fixed order)."""
    if isinstance(rec, EventRecord):
        return _datum_form(
            "scar", rec.scar, event=rec.event, datum_id=rec.datum_id, anchor=rec.anchor
        )

    if isinstance(rec, ManifestRecord):
        return {
            "form": "manifest",
            "protocol": rec.protocol,
            "schemaVersion": rec.schema_version,
            "decisions": rec.decisions,
            "t": rec.t,
        }

    if isinstance(rec, CycleSealActivity):
        return _datum_form(
            "cycle-seal",
            rec.datum,
            datum_id=rec.datum_id,
            activity=rec.activity,
            anchor=rec.anchor,
        )

    if isinstance(rec, LayerExitActivity):
        return {
            "form": "layer-exit",
            "datumId": rec.datum_id,
            "cycleMark": rec.cycle_mark,
            "layer": rec.layer,
            "t": rec.t,
        }

    if isinstance(rec, ProvenanceActivity):
        return {
            "form": "provenance",
            "datumId": rec.datum_id,
            "cycleMark": rec.cycle_mark,
            "from": rec.from_,
            "to": rec.to,
            "t": rec.t,
        }

    if isinstance(rec, EmissionActivity):
        return {
            "form": "emission",
            "datumId": rec.datum_id,
            "cycleMark": rec.cycle_mark,
            "issuingLayer": rec.issuing_layer,
            "action": rec.action,
            "register": rec.register,
            "t": rec.t,
        }

    if isinstance(rec, RevisionActivity):
        return {
            "form": "revision",
            "datumId": rec.datum_id,
            "cycleMark": rec.cycle_mark,
            "issuingLayer": rec.issuing_layer,
            "t": rec.t,
        }

    if isinstance(rec, CrystallizationActivity):
        return {
            "form": "crystallization",
            "datumId": rec.datum_id,
            "cycleMark": rec.cycle_mark,
            "t": rec.t,
        }

    if isinstance(rec, ExpectationActivity):
        return {
            "form": "expectation",
            "datumId": rec.datum_id,
            "cycleMark": rec.cycle_mark,
            "entity": rec.entity,
            "source": rec.source,
            "confidence": rec.confidence,
            "recurrence": rec.recurrence,
            "delta": rec.delta,
            "t": rec.t,
        }

    if isinstance(rec, ResistanceReadingActivity):
        return {
            "form": "resistance-reading",
            "datumId": rec.datum_id,
            "cycleMark": rec.cycle_mark,
            "source": rec.source,
            "entity": rec.entity,
            "mismatchKind": rec.mismatch_kind,
            "recurrence": rec.recurrence,
            "delta": rec.delta,
            "signed": rec.signed,
            "t": rec.t,
        }

    raise TypeError(f"unserializable [event] record: {type(rec).__name__}")


def deserialize_event_record(rec: SerializedEventRecord) -> LogRecord:
    """Reconstruct a LogRecord from its serialized form.

    The faithful inverse of `serialize_event_record` — serialization is lossless:
    the flattened tags + payload + kind-specific body + anchor rebuild the record
    exactly. This is how an auditor, and a durable disk-source-of-truth [event]
    log, reads records back from the substrate.
    """
    form = rec["form"]

    if form == "layer-exit":
        return LayerExitActivity(
            datum_id=rec["datumId"], cycle_mark=rec["cycleMark"], layer=rec["layer"], t=rec["t"]
        )

    if form == "provenance":
        return ProvenanceActivity(
            datum_id=rec["datumId"],
            cycle_mark=rec["cycleMark"],
            from_=rec["from"],
            to=rec["to"],
            t=rec["t"],
        )

    if form == "emission":
        return EmissionActivity(
            datum_id=rec["datumId"],
            cycle_mark=rec["cycleMark"],
            issuing_layer=rec["issuingLayer"],
            action=rec["action"],
            t=rec["t"],
            register=rec["register"],
        )

    if form == "revision":
        return RevisionActivity(
            datum_id=rec["datumId"], cycle_mark=rec["cycleMark"],
            issuing_layer=rec["issuingLayer"], t=rec["t"],
        )

    if form == "crystallization":
        return CrystallizationActivity(
            datum_id=rec["datumId"], cycle_mark=rec["cycleMark"], t=rec["t"]
        )

    if form == "expectation":
        return ExpectationActivity(
            datum_id=rec["datumId"],
            cycle_mark=rec["cycleMark"],
            entity=rec["entity"],
            source=rec["source"],
            confidence=rec["confidence"],
            recurrence=rec["recurrence"],
            delta=rec["delta"],
            t=rec["t"],
        )

    if form == "resistance-reading":
        return ResistanceReadingActivity(
            datum_id=rec["datumId"],
            cycle_mark=rec["cycleMark"],
            source=rec["source"],
            entity=rec["entity"],
            mismatch_kind=rec["mismatchKind"],
            recurrence=rec["recurrence"],
            delta=rec["delta"],
            signed=rec["signed"],
            t=rec["t"],
        )

    if form == "manifest":
        return ManifestRecord(
            protocol=rec["protocol"],
            schema_version=rec["schemaVersion"],
            decisions=rec["decisions"],
            t=rec["t"],
        )

    datum = TaggedDatum(
        payload=rec["payload"],
        fixed=FixedTags(
            timestamp=rec["timestamp"],
            cycle_mark=rec["cycleMark"],
            provenance=rec["provenance"],
            floor_tag=rec["floorTag"],
        ),
        open=rec["open"],
    )
    a = rec["anchor"]
    anchor = ContextAnchor(cycle=a["cycle"], field_state=a["fieldState"], depth=a["depth"])

    if form == "scar":
        e = rec["event"]
        return EventRecord(
            event=ResistEvent(
                source_id=e["source_id"],
                expected=e["expected"],
                received=e["received"],
                mismatch_kind=e["mismatch_kind"],
                t=e["t"],
            ),
            scar=datum,
            anchor=anchor,
            datum_id=rec.get("datumId"),
        )

    act = rec["activity"]
    return CycleSealActivity(
        datum_id=rec["datumId"],
        activity=ActivityEvent(
            cycle=act["cycle"],
            flow=act["flow"],
            emitted=act["emitted"],
            observed=tuple(act["observed"]),
            scars=act["scars"],
            t=act["t"],
            recalled=tuple(_tags_of(r) for r in act.get("recalled", ())),
            admitted=tuple(_tags_of(r) for r in act.get("admitted", ())),
            written=tuple(_tags_of(r) for r in act.get("written", ())),
            closed_at=act.get("closedAt"),
        ),
        datum=datum,
        anchor=anchor,
    )


class EventSinkProtocol(Protocol):
    """The append-only, write-once sink surface.

    Intentionally the ONLY method is `write` — no update, delete, or truncate
    exists to be called.
    """

    def write(self, record: LogRecord) -> None: ...


@dataclass(frozen=True, slots=True)
class Segment:
    file: Path
    date: str
    seq: int


_SEGMENT_RE = re.compile(r"^event-log-(\d{8})(?:-(\d{3}))?\.jsonl$")


def _utc_stamp() -> str:
    d = datetime.now(tz=UTC)
    return f"{d.year:04d}{d.month:02d}{d.day:02d}"


def list_segments(dir_: str | os.PathLike[str]) -> list[Segment]:
    """All segments in the directory, ordered by (date, seq)."""
    root = Path(dir_)
    if not root.is_dir():
        return []
    found: list[Segment] = []
    for entry in root.iterdir():
        m = _SEGMENT_RE.match(entry.name)
        if m is not None:
            found.append(Segment(file=entry, date=m.group(1), seq=int(m.group(2) or 1)))
    found.sort(key=lambda s: (s.date, s.seq))
    return found


def _segment_name(date: str, seq: int) -> str:
    return f"event-log-{date}.jsonl" if seq == 1 else f"event-log-{date}-{seq:03d}.jsonl"


def _read_segment_lines(file: Path) -> list[ChainedEventLine]:
    out: list[ChainedEventLine] = []
    with file.open("r", encoding="utf-8") as fh:
        for raw in fh:
            if not raw.strip():
                continue
            obj = json.loads(raw)
            out.append(
                ChainedEventLine(
                    seq=obj.get("seq"),
                    prev=obj.get("prev"),
                    # A pre-versioning line has no `schemaVersion` at all; keep it
                    # absent as None so the verifier can refuse it by version
                    # rather than mistake it for a content break.
                    schema_version=obj.get("schemaVersion"),
                    record=obj.get("record"),
                    hash=obj.get("hash"),
                )
            )
    return out


def read_chained_lines(dir_: str | os.PathLike[str]) -> list[ChainedEventLine]:
    """All chained lines across the directory's segments, in chain order."""
    lines: list[ChainedEventLine] = []
    for seg in list_segments(dir_):
        lines.extend(_read_segment_lines(seg.file))
    return lines


def read_jsonl_sink(dir_: str | os.PathLike[str]) -> list[SerializedEventRecord]:
    """All serialized records (chain envelope unwrapped), tags in fixed order."""
    return [line.record for line in read_chained_lines(dir_)]


def read_log_records(dir_: str | os.PathLike[str]) -> list[LogRecord]:
    """All LogRecords across the directory's segments, read from the substrate."""
    return [deserialize_event_record(r) for r in read_jsonl_sink(dir_)]


def verify_jsonl_sink(dir_: str | os.PathLike[str]) -> ChainVerification:
    """Verify the whole chain across all segments.

    Detects any altered, removed, inserted, or reordered line — relative to a
    trusted head, as hash_chain explains.
    """
    return verify_chain(read_chained_lines(dir_))


class JsonlFileSink:
    """The segmented JSONL sink over a directory.

    Resumes the chain from the last line of the last segment; refuses to open on
    an unparsable tail rather than appending past corruption and burying the
    evidence.
    """

    __slots__ = (
        "_cap",
        "_stamp",
        "_dir",
        "_seq",
        "_prev",
        "_fh",
        "_current_date",
        "_current_seq",
        "_current_bytes",
    )

    def __init__(
        self,
        dir_: str | os.PathLike[str],
        *,
        max_segment_bytes: int | None = None,
        date_stamp: Any = None,
    ) -> None:
        self._cap = max_segment_bytes if max_segment_bytes is not None else MAX_SEGMENT_BYTES
        self._stamp = date_stamp if date_stamp is not None else _utc_stamp
        self._dir = Path(dir_)
        self._dir.mkdir(parents=True, exist_ok=True)

        # Resume the chain from the existing segments, if any.
        self._seq = 0
        self._prev = CHAIN_GENESIS
        existing = list_segments(self._dir)
        if existing:
            lines = _read_segment_lines(existing[-1].file)
            if lines:
                last = lines[-1]
                if not isinstance(last.hash, str) or not isinstance(last.seq, int):
                    raise RuntimeError(
                        f"event sink: cannot resume chain in {existing[-1].file} — "
                        "unparsable tail; refusing to append past corruption"
                    )
                self._seq = last.seq + 1
                self._prev = last.hash

        self._fh: Any = None
        self._current_date = ""
        self._current_seq = 0
        self._current_bytes = 0

    def _open_segment(self, date: str, line_bytes: int) -> None:
        """Open (or continue) the right segment for `date`, respecting the cap."""
        if self._fh is not None:
            self._fh.close()
        todays = [s for s in list_segments(self._dir) if s.date == date]
        tail = todays[-1] if todays else None
        if tail is not None and tail.file.stat().st_size + line_bytes <= self._cap:
            target = tail
        else:
            nxt = (tail.seq if tail is not None else 0) + 1
            target = Segment(file=self._dir / _segment_name(date, nxt), date=date, seq=nxt)
        # append-only; never truncates
        self._fh = target.file.open("ab")
        self._current_date = date
        self._current_seq = target.seq
        self._current_bytes = target.file.stat().st_size

    def write(self, record: LogRecord) -> None:
        chained = chain_next(self._prev, self._seq, serialize_event_record(record))
        line = (
            json.dumps(
                {
                    "seq": chained.seq,
                    "prev": chained.prev,
                    "schemaVersion": chained.schema_version,
                    "record": chained.record,
                    "hash": chained.hash,
                },
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        )
        encoded = line.encode("utf-8")
        line_bytes = len(encoded)
        today = self._stamp()
        # Rotate on date change or when the segment would exceed the cap; a
        # record is never split across files.
        if (
            self._fh is None
            or today != self._current_date
            or self._current_bytes + line_bytes > self._cap
        ):
            self._open_segment(today, line_bytes)
        self._fh.write(encoded)
        self._fh.flush()
        os.fsync(self._fh.fileno())  # durability: flush to disk before returning
        self._current_bytes += line_bytes
        self._prev = chained.hash
        self._seq += 1

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
        self._fh = None

    def head(self) -> str:
        """The current chain head (CHAIN_GENESIS while empty).

        Read-only; a deployment anchors this outside its own write reach to make a
        total rewrite detectable.
        """
        return self._prev


def create_jsonl_file_sink(
    dir_: str | os.PathLike[str],
    *,
    max_segment_bytes: int | None = None,
    date_stamp: Any = None,
) -> JsonlFileSink:
    return JsonlFileSink(dir_, max_segment_bytes=max_segment_bytes, date_stamp=date_stamp)
