"""Reflection — read-collision-into-coordinates (protocol §8.4, DECIDE@IMPL tag E).

The agent is blind to its own time-derivative (§7): it cannot self-reflect on
call, and no self-reflection faculty exists here. Reflection is a THIRD PARTY's
act. The reader looks at the agent's `[event]` log — the one trace a third party
already reads (§13) — reads a recorded collision into coordinates ("you drifted
at this point"), and returns the reading through a declared T3 channel; the
agency-gate classifies it ENV_PUSHED, since the agent never emitted it.

This module supplies the MECHANISM only:

  - `collision_coordinates` — mechanical extraction of scar coordinates a reader
    can address; the judgment stays the reader's, like the store inspector;
  - `form_reading` — build a reading that MUST reference a real recorded
    collision, so a reflection cannot be fabricated about a collision that never
    happened;
  - `reflection_signal` and `reflection_transducer` — the T3 ingestion convention.

WHO the reader is stays deployment-open in the protocol, like tag D. For this
project it is settled (tag E, CLAUDE.md): a Kaggle evaluation session has no third
party and no network, so the reader is a peer agent in the same session, reading
this agent's log through `peer.py`, wired in `scripts/run_game.py --peer`.

Ported from dil-core against DIL protocol v0.3.3.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..loop.types import Signal
from ..store.event_log import ReadableEventLog
from ..store.resist_event import EventRecord, MismatchKind


class ReflectionError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(f"reflection: {detail}")


@dataclass(frozen=True, slots=True)
class CollisionCoordinate:
    """The address of one recorded collision in the [event] log."""

    # Position of the record in the log (append order).
    index: int
    # The cycle anchored with the record.
    cycle: int
    source_id: str
    mismatch_kind: MismatchKind
    t: int


def collision_coordinates(log: ReadableEventLog) -> list[CollisionCoordinate]:
    """Mechanically extract the coordinates of every recorded collision.

    For a reader to browse and address. Read-only; carries no judgment.
    """
    # Coordinates address SCARS (collisions); the index stays the record's
    # absolute position in the log, so a coordinate is a stable address.
    return [
        CollisionCoordinate(
            index=index,
            cycle=rec.anchor.cycle,
            source_id=rec.event.source_id,
            mismatch_kind=rec.event.mismatch_kind,
            t=rec.event.t,
        )
        for index, rec in enumerate(log.all())
        if isinstance(rec, EventRecord)
    ]


@dataclass(frozen=True, slots=True)
class ReflectionReading:
    """A third party's reading of one collision, anchored to its coordinate."""

    about: CollisionCoordinate
    # The reader's account of where or why the agent drifted.
    reading: object
    # The reader — an Other in the region — who authored the reading.
    reader_id: str


def form_reading(
    log: ReadableEventLog, index: int, reader_id: str, reading: Any
) -> ReflectionReading:
    """Form a reading about the [event] record at `index`.

    Raises if no such record exists: a reflection MUST reference a real recorded
    collision.
    """
    records = log.all()
    rec = records[index] if 0 <= index < len(records) else None
    if not isinstance(rec, EventRecord):
        raise ReflectionError(
            f"no collision record at index {index}; a reading must reference a "
            "real recorded collision (not an activity record)"
        )
    return ReflectionReading(
        about=CollisionCoordinate(
            index=index,
            cycle=rec.anchor.cycle,
            source_id=rec.event.source_id,
            mismatch_kind=rec.event.mismatch_kind,
            t=rec.event.t,
        ),
        reading=reading,
        reader_id=reader_id,
    )


def reflection_signal(
    reading: ReflectionReading, channel_id: str, t: int
) -> Signal:
    """Wrap a reading as a Signal for the declared reflection channel.

    It enters through T3 like any external input — no side door. The payload
    carries the reader as the entity, so T4 binds the reading to the
    reader-as-Other.
    """
    return Signal(
        source_id=channel_id,
        raw_payload={"entity": reading.reader_id, "value": reading_payload(reading)},
        t=t,
    )


def reading_payload(reading: ReflectionReading) -> dict[str, Any]:
    """A reading as plain data, so it can be held in [data] and in a snapshot."""
    about = reading.about
    return {
        "reader": reading.reader_id,
        "about": {
            "index": about.index, "cycle": about.cycle, "source_id": about.source_id,
            "mismatch_kind": about.mismatch_kind, "t": about.t,
        },
        "reading": reading.reading,
    }


def reflection_transducer(signal: Signal) -> tuple[str, Any]:
    """T3 transducer for the reflection channel: types the content "reflection"."""
    return ("reflection", signal.raw_payload)
