"""Reflection — a third party's view, pointed at a place in the agent's trace
(protocol §8.4, DECIDE@IMPL tag E).

The agent is blind to its own time-derivative (§7): it cannot self-reflect on
call, and no self-reflection faculty exists here. Reflection is a THIRD PARTY's
act: the reader, from its own lens, holds that the agent drifted and says where
— "you drifted at this point" — and the reading returns through a declared T3
channel; the agency-gate classifies it ENV_PUSHED, since the agent never
emitted it.

WHAT A READING IS, AND IS NOT. It is the reader's view, carrying no claim of
being right (§9): a place in the agent's trace and what the reader makes of it.
It is NOT the agent's own recorded collision handed back. A collision the agent
recorded is one it already authored — a source relaying it is compliant and
re-authorable (§8.3, §8.4) — and the drift a reader is for is the kind the agent
does not see (§8.2). So the place a reading points at need not hold a scar.
When the reading collides, the mismatch is between the agent and the reader.

This module supplies the MECHANISM only:

  - `trace_cycles` — the cycles the agent's trace recorded, the places a reader
    can point at (read-only; carries no judgment);
  - `form_reading` — anchor a reading to one of them; a cycle the trace never
    recorded is refused;
  - `reflection_signal` and `reflection_transducer` — the T3 ingestion convention.

WHO the reader is, and its lens, stay deployment-open in the protocol, like tag
D. NOT USED BY THIS HOST: kept so that `src/dil/` stays a faithful port of
dil-core. This host's reader is the onlooker (`arc3/onlooker.py`, tag E), which
does not use it: `form_reading` reads the agent's trace to check the cycle, and
the onlooker, by design, sees only the agent's moves and never its log. Its
remark enters through the host's own transducer on the `onlooker` channel.

Ported from dil-core `3a186b4`, which replaced the reading of a recorded
collision with this (Plone, 2026-09-25; LOG.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..loop.types import Signal
from ..store.event_log import ReadableEventLog
from ..store.resist_event import CycleSealActivity


class ReflectionError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(f"reflection: {detail}")


@dataclass(frozen=True, slots=True)
class TraceCoordinate:
    """A place in the agent's trace: one recorded cycle, addressed by its seal."""

    cycle: int
    # Position of the cycle's seal in the log (append order) — a stable address.
    index: int
    # When the cycle began.
    t: int


def trace_cycles(log: ReadableEventLog) -> list[TraceCoordinate]:
    """The cycles the agent's trace recorded, oldest first: the places a reader can
    point at. Read-only; carries no judgment."""
    return [
        TraceCoordinate(cycle=rec.activity.cycle, index=index, t=rec.activity.t)
        for index, rec in enumerate(log.all())
        if isinstance(rec, CycleSealActivity)
    ]


@dataclass(frozen=True, slots=True)
class ReflectionReading:
    """A third party's view of the agent, pointed at a place in its trace."""

    about: TraceCoordinate
    # The reader's view — where or why it holds the agent drifted. No verdict.
    reading: object
    # The reader — an Other — who holds that view.
    reader_id: str


def form_reading(
    log: ReadableEventLog, cycle: int, reader_id: str, reading: Any
) -> ReflectionReading:
    """Point a reading at `cycle` of the agent's trace.

    Raises if the trace recorded no such cycle: a reader cannot point at a place
    that is not there.
    """
    about = next((c for c in trace_cycles(log) if c.cycle == cycle), None)
    if about is None:
        raise ReflectionError(
            f"the trace recorded no cycle {cycle}; a reading must point at a place "
            "in the agent's trace"
        )
    return ReflectionReading(about=about, reading=reading, reader_id=reader_id)


def reflection_signal(
    reading: ReflectionReading, channel_id: str, t: int
) -> Signal:
    """Wrap a reading as a Signal for the declared reflection channel.

    It enters through T3 like any external input — no side door. The payload
    carries the reader as the entity, so T4 binds the reading to the
    reader-as-Other. The reading travels as plain data, so it can be held in
    [data] and in a snapshot.
    """
    return Signal(
        source_id=channel_id,
        raw_payload={"entity": reading.reader_id, "value": reading_payload(reading)},
        t=t,
    )


def reading_payload(reading: ReflectionReading) -> dict[str, Any]:
    """A reading as plain data."""
    about = reading.about
    return {
        "reader": reading.reader_id,
        "about": {"cycle": about.cycle, "index": about.index, "t": about.t},
        "reading": reading.reading,
    }


def reflection_transducer(signal: Signal) -> tuple[str, Any]:
    """T3 transducer for the reflection channel: types the content "reflection"."""
    return ("reflection", signal.raw_payload)
