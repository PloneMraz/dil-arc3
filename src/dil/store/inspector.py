"""The inspector — a READ-ONLY human-readable view of the store.

Lets a person see what is in `[data]` and `[event]` when they access the store,
using the derived display_name projection. It only reads — it calls the stores'
read methods (`entries()`, `all()`) and never mutates — so inspecting can never
alter the store or an `[event]` record.

This renders to a string; the caller decides where to send it. It is a standalone
read-only view; the loop itself never depends on it.

Ported from dil-core, first against DIL protocol v0.3.3 (the package
implements `dil.DIL_PROTOCOL_VERSION`).
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from .data_store import DataStore
from .display_name import display_name, event_display_name
from .event_log import ReadableEventLog
from .resist_event import (
    ReadActivity,
    ReadRecordActivity,
    RevisionActivity,
    CrystallizationActivity,
    CycleSealActivity,
    EmissionActivity,
    EventRecord,
    ExpectationActivity,
    LayerExitActivity,
    ManifestRecord,
    ProvenanceActivity,
    ResistanceReadingActivity,
)

_WS = re.compile(r"\s+")


def _clock(ts: int) -> str:
    """Render an epoch-ms timestamp as HH:mm:ss UTC (the wall-clock of the event)."""
    d = datetime.fromtimestamp(ts / 1000, tz=UTC)
    return f"{d.hour:02d}:{d.minute:02d}:{d.second:02d}"


def _preview(value: Any, max_len: int = 40) -> str:
    """A short, safe one-line preview of an arbitrary payload value."""
    if isinstance(value, str):
        s = value
    else:
        try:
            s = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
        except (TypeError, ValueError):
            s = str(value)
    s = _WS.sub(" ", s)
    return f"{s[: max_len - 1]}…" if len(s) > max_len else s


def inspect_data(store: DataStore) -> str:
    """Render the `[data]` store: one line per datum, with its derived name."""
    entries = store.entries()
    lines = [
        f"  {id_}  {display_name(d)}  payload={_preview(d.payload)}" for id_, d in entries
    ]
    return "\n".join([f"[data] — {len(entries)} item(s)", *lines])


def inspect_event_log(log: ReadableEventLog) -> str:
    """Render the `[event]` log: one line per activity/scar (the datum's diary)."""
    records = log.all()
    lines: list[str] = []

    for i, r in enumerate(records):
        if isinstance(r, EventRecord):
            lines.append(
                f"  #{i}  {event_display_name(r)}  "
                f"{_preview(r.event.expected)}→{_preview(r.event.received)}"
            )
        elif isinstance(r, ManifestRecord):
            keys = ", ".join(r.decisions.keys())
            lines.append(
                f"  #{i}  [manifest] protocol={r.protocol} schema={r.schema_version} "
                f"· DECIDE@IMPL: {keys} {_clock(r.t)}"
            )
        elif isinstance(r, CycleSealActivity):
            observed = ",".join(r.activity.observed) or "-"
            lines.append(
                f"  #{i}  {display_name(r.datum)}_[cycle-seal]  "
                f"cycle={r.activity.cycle} flow={r.activity.flow} "
                f"observed={observed} scars={r.activity.scars}"
            )
        elif isinstance(r, LayerExitActivity):
            lines.append(
                f"  #{i}  [layer-exit] {r.datum_id} @T{r.layer} (c{r.cycle_mark}) {_clock(r.t)}"
            )
        elif isinstance(r, ProvenanceActivity):
            lines.append(
                f"  #{i}  [provenance] {r.datum_id} {r.from_}→{r.to} "
                f"(c{r.cycle_mark}) {_clock(r.t)}"
            )
        elif isinstance(r, EmissionActivity):
            lines.append(
                f"  #{i}  [emission] {r.datum_id} @T{r.issuing_layer} {r.register} "
                f"{_preview(r.action)} (c{r.cycle_mark}) {_clock(r.t)}"
            )
        elif isinstance(r, RevisionActivity):
            lines.append(
                f"  #{i}  [revision] {r.datum_id} @T{r.issuing_layer} "
                f"(c{r.cycle_mark}) {_clock(r.t)}"
            )
        elif isinstance(r, ReadActivity):
            lines.append(
                f"  #{i}  [read] {r.datum_id} @T{r.issuing_layer} for {r.purpose}: "
                f"{len(r.read)} datum(s) (c{r.cycle_mark}) {_clock(r.t)}"
            )
        elif isinstance(r, ReadRecordActivity):
            lines.append(
                f"  #{i}  [read-record] {r.datum_id} @T{r.issuing_layer} for {r.purpose}: "
                f"{len(r.records)} record(s) (c{r.cycle_mark}) {_clock(r.t)}"
            )
        elif isinstance(r, CrystallizationActivity):
            lines.append(
                f"  #{i}  [crystallization] {r.datum_id} self|env "
                f"(c{r.cycle_mark}) {_clock(r.t)}"
            )
        elif isinstance(r, ExpectationActivity):
            lines.append(
                f"  #{i}  [expectation] {r.entity} conf={r.confidence:.2f} "
                f"rec={r.recurrence} err={r.delta} (c{r.cycle_mark}) {_clock(r.t)}"
            )
        elif isinstance(r, ResistanceReadingActivity):
            lines.append(
                f"  #{i}  [resistance-reading] {r.source}/{r.entity} {r.mismatch_kind} "
                f"rec={r.recurrence} err={r.delta}{r.signed} (c{r.cycle_mark}) {_clock(r.t)}"
            )

    return "\n".join([f"[event-log] — {len(records)} record(s)", *lines])
