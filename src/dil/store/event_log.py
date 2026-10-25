"""The [event] log — the one trusted artifact (protocol §9, §13).

`[event]` is a black box: an append-only log of read-only records. New records
may be appended to the end, but no record, once written, may be altered or
removed — by the loop, by anything, or by a third party that has compromised the
rest of the system. This is the single source an auditor can trust
unconditionally, and it doubles as the record in the agent's history and the
conformance trace (one artifact, two roles — no parallel trace channel).

IMMUTABILITY, and where this differs from the reference. dil-core calls
`Object.freeze` recursively, which makes the stored object itself unwritable.
Python has no equivalent: a dict cannot be frozen in place. The records here are
frozen dataclasses, so their fields cannot be rebound, but their nested
containers — open tags, field state, a payload — would still be reachable through
whatever reference the caller kept. `_seal` therefore takes a deep copy at append
time. The guarantee that matters is the same one: after append, nothing the
caller still holds can change what the log stored. The difference is that the
reference denies the write and this denies the shared reference.

Enforcement boundary (honest scope): this stops accidental and in-process
mutation. For DURABILITY (records surviving the process), pass an EventSink:
every appended record is mirrored to it at append time. The stronger,
tamper-EVIDENT guarantee against a compromised host is the hash chain plus the
commit markers, not the sink alone.

Ported from dil-core, first against DIL protocol v0.3.3 (the package
implements `dil.DIL_PROTOCOL_VERSION`).
"""

from __future__ import annotations

import copy
import re
import os
from dataclasses import fields, is_dataclass
from typing import Any, Protocol

from .decisions import INDEX_KEYS
from .event_sink import (
    EventSinkProtocol,
    SeqRecord,
    create_jsonl_file_sink,
    read_log_records,
    iter_log_records_back,
    read_log_records_back,
)
from .resist_event import EventRecord, LogRecord


def record_seq(id_: str) -> int | None:
    """The place in the chain an id names, when it names a record of the log —
    `event:<seq>`, as a datum built from a record read names it — rather than a
    datum; None otherwise (v0.3.9)."""
    m = re.fullmatch(r"event:(\d+)", id_) if isinstance(id_, str) else None
    return int(m.group(1)) if m else None


# Values a copy keeps as they are: immutable, so nothing can reach into them.
_PLAIN = frozenset({int, float, str, bool, type(None)})


def deep_freeze(value: Any) -> Any:
    """Return a copy nothing outside the log still holds a reference into.

    See the module docstring: this is Python's honest stand-in for the
    reference's recursive `Object.freeze`, not a transliteration of it.

    A port-side optimization, not dil-core's (LOG.md, 2026-09-28): the plain
    data a record carries — values, lists, tuples, dicts, dataclasses of them —
    is copied here directly, as `copy.deepcopy` would copy it; anything else
    still goes to `copy.deepcopy`. It was an eighth of a run's time.
    """
    return _fresh(value)


def _fresh(value: Any) -> Any:
    t = type(value)
    if t in _PLAIN:
        return value
    if t is list:
        return [v if type(v) in _PLAIN else _fresh(v) for v in value]
    if t is dict:
        return {k: v if type(v) in _PLAIN else _fresh(v) for k, v in value.items()}
    if t is tuple:
        return tuple(v if type(v) in _PLAIN else _fresh(v) for v in value)
    if is_dataclass(value) and not isinstance(value, type):
        copied = copy.copy(value)
        for f in fields(value):
            v = getattr(value, f.name)
            if type(v) not in _PLAIN:
                object.__setattr__(copied, f.name, _fresh(v))
        return copied
    return copy.deepcopy(value)


class ReadableEventLog(Protocol):
    """A READ-ONLY view of the [event] log — reads and indexed lookups only.

    A Mode-B source and the reflection reader take THIS view, so "Mode-B returns;
    it does not write" (§8.4) is a type-level guarantee: they can read the log to
    form a reading, but the type gives them no way to write it.
    """

    def all(self) -> list[LogRecord]:
        """All records, oldest first."""
        ...

    def size(self) -> int:
        """Number of records (the commit counter reads this)."""
        ...

    def by_source_id(self, source_id: str) -> list[EventRecord]:
        """Scar lookup by resistance source (activity records carry no source_id)."""
        ...

    def back(self, before: int, scan: int) -> list[SeqRecord]:
        """The records before `before` (a place in the chain), newest first, at
        most `scan` of them (v0.3.9 §9, "Reading the record").
        Bounded, so a read in a cycle costs what it scans, never the whole log."""
        ...


class EventLog(ReadableEventLog, Protocol):
    """The append-only [event] log.

    Deliberately exposes only `append`, reads, and indexed lookups — there is no
    method to alter or remove a record.
    """

    def append(self, record: LogRecord) -> None: ...


class InMemoryEventLog:
    """An [event] log held in memory, optionally mirrored to a durable sink."""

    __slots__ = ("_records", "_by_source", "_sink")

    def __init__(self, sink: EventSinkProtocol | None = None) -> None:
        self._records: list[LogRecord] = []
        self._by_source: dict[str, list[EventRecord]] = {}
        self._sink = sink

    def append(self, record: LogRecord) -> None:
        sealed = deep_freeze(record)
        self._records.append(sealed)
        # Maintain the source_id index over scars (INDEX_KEYS).
        assert "source_id" in INDEX_KEYS
        if isinstance(sealed, EventRecord):
            self._by_source.setdefault(sealed.event.source_id, []).append(sealed)
        # Mirror to the durable sink, if one is wired (append-only, write-once).
        if self._sink is not None:
            self._sink.write(sealed)

    def all(self) -> list[LogRecord]:
        return list(self._records)

    def size(self) -> int:
        return len(self._records)

    def by_source_id(self, source_id: str) -> list[EventRecord]:
        return list(self._by_source.get(source_id, ()))

    def back(self, before: int, scan: int) -> list[SeqRecord]:
        return list(self.iter_back(before, scan))

    def iter_back(self, before: int, scan: int):
        """`back`, record by record, as far as the reader goes."""
        start = min(before, len(self._records)) - 1
        for seq in range(start, max(-1, start - scan), -1):
            yield SeqRecord(seq, self._records[seq])


def create_event_log(sink: EventSinkProtocol | None = None) -> EventLog:
    """Create an [event] log.

    Pass an optional `sink` to mirror every appended record to durable storage at
    append time (DECIDE@IMPL tag F, EVENT_DURABILITY). Without a sink the log is
    in-memory only.
    """
    return InMemoryEventLog(sink)


class DurableEventLog:
    """A durable [event] log whose source of truth is the substrate (disk).

    Every record is appended to the append-only, hash-chained JSONL sink, and
    reads come back FROM the substrate. RAM holds only a monotonic counter and the
    chain head — never the record history, so it cannot grow without bound. An
    auditor trusts the durable, anchored log, not a process's RAM.

    Reads deserialize the whole live log, so they are an audit-time operation (the
    per-cycle path only appends and reads `size()`); a tiering deployment keeps
    only recent segments hot and archives older ones — never deleting (§9).
    """

    __slots__ = ("_dir", "_sink", "_count")

    def __init__(
        self,
        dir_: str | os.PathLike[str],
        *,
        max_segment_bytes: int | None = None,
        date_stamp: Any = None,
    ) -> None:
        self._dir = dir_
        self._sink = create_jsonl_file_sink(
            dir_, max_segment_bytes=max_segment_bytes, date_stamp=date_stamp
        )
        # Resume the counter from whatever the substrate already holds.
        self._count = len(read_log_records(dir_))

    def append(self, record: LogRecord) -> None:
        self._sink.write(deep_freeze(record))
        self._count += 1

    def all(self) -> list[LogRecord]:
        return read_log_records(self._dir)

    def size(self) -> int:
        return self._count

    def by_source_id(self, source_id: str) -> list[EventRecord]:
        return [
            r
            for r in read_log_records(self._dir)
            if isinstance(r, EventRecord) and r.event.source_id == source_id
        ]

    def back(self, before: int, scan: int) -> list[SeqRecord]:
        return read_log_records_back(self._dir, before, scan)

    def iter_back(self, before: int, scan: int):
        """`back`, record by record, as far as the reader goes."""
        return iter_log_records_back(self._dir, before, scan)

    def head(self) -> str:
        """The current tamper-evidence chain head (for external anchoring)."""
        return self._sink.head()

    def sync_each_cycle(self) -> None:
        """Sync to disk once a cycle, not each record (SYNC_CADENCE, declared)."""
        self._sink.sync_each = False

    def sync(self) -> None:
        """Sync what was appended to disk."""
        self._sink.sync()

    def close(self) -> None:
        """Close the underlying file handle."""
        self._sink.close()


def create_durable_event_log(
    dir_: str | os.PathLike[str],
    *,
    max_segment_bytes: int | None = None,
    date_stamp: Any = None,
) -> DurableEventLog:
    """Create a durable [event] log over a substrate directory (`store/event-log/`)."""
    return DurableEventLog(dir_, max_segment_bytes=max_segment_bytes, date_stamp=date_stamp)
