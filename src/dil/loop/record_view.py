"""The cycle's view of `[event]` for T5 (v0.3.9 §9, "Reading the record").

Ported from dil-core c258f43. The whole store is the agent's history: `[data]`
its memory, which it revises, and `[event]` the record of what happened to it,
which it reads and never alters. This is the reading. It is an open link, not a
switch: the driver builds one every cycle and hands it to the rule, and whether
to read is the rule's.

It takes a ReadableEventLog and nothing more, so it cannot append to the log,
reach into `[data]` or correct the store. It sees what the log held before the
cycle that reads (`before`, a place in the chain): what is being appended in
this cycle is met in it, not yet history. Each way of reading goes back from
there, newest first, through at most `scan` records, and returns at most
`limit`; what it returns is what was read, and `on_read` is told, by purpose, so
the driver records it — a layer does not write the log.
"""

from __future__ import annotations

from typing import Callable

from ..store.event_log import ReadableEventLog
from ..store.event_sink import SeqRecord
from ..store.resist_event import CycleSealActivity, EventRecord, LogRecord, ManifestRecord
from .decisions import RECORD_SCAN
from .layers.t5 import RecordView


def _datum_of(record: LogRecord) -> str | None:
    """The datum a record is of: the one it names, or for a scar with none — an
    absence — the cycle datum that stood for it. The manifest is of none."""
    if isinstance(record, EventRecord):
        return record.datum_id if record.datum_id is not None else f"cycle-{record.anchor.cycle}"
    if isinstance(record, ManifestRecord):
        return None
    return record.datum_id


def create_record_view(
    log: ReadableEventLog,
    before: int,
    on_read: Callable[[str, tuple[int, ...]], None],
    scan: int = RECORD_SCAN,
) -> RecordView:
    def read(purpose: str, keep: Callable[[LogRecord], bool], limit: int | None) -> list[SeqRecord]:
        cap = scan if limit is None else limit
        out: list[SeqRecord] = []
        if cap <= 0:
            return out
        records = log.iter_back(before, scan) if hasattr(log, "iter_back") else log.back(before, scan)
        for r in records:
            if not keep(r.record):
                continue
            out.append(r)
            if len(out) >= cap:
                break
        if out:
            on_read(purpose, tuple(r.seq for r in out))
        return out

    def recent(purpose: str, limit: int | None = None) -> list[SeqRecord]:
        return read(purpose, lambda r: True, limit)

    def about(datum_id: str, purpose: str, limit: int | None = None) -> list[SeqRecord]:
        return read(purpose, lambda r: _datum_of(r) == datum_id, limit)

    def scars(source_id: str, purpose: str, limit: int | None = None) -> list[SeqRecord]:
        return read(
            purpose,
            lambda r: isinstance(r, EventRecord) and r.event.source_id == source_id,
            limit,
        )

    def cycles(purpose: str, limit: int | None = None) -> list[SeqRecord]:
        # DEVIATION (proposed, for measurement; Plone, 2026-10-25): the seals of
        # the latest cycles — what each admitted, emitted and wrote — so what
        # happened is read cycle by cycle without reading every line between.
        return read(purpose, lambda r: isinstance(r, CycleSealActivity), limit)

    return RecordView(recent=recent, about=about, scars=scars, cycles=cycles)
