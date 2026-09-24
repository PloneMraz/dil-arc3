"""Reflection (tag E): a third party's view, pointed at a place in the agent's trace.

Ported from dil-core `3a186b4`. A reading points at a cycle the trace recorded,
with or without a scar, and carries the reader's view — not the agent's own
recorded collision handed back. A cycle the trace never recorded is refused.
"""

from __future__ import annotations

import pytest

from dil.loop.cycle import HostCycleInput, Layers, create_cycle
from dil.loop.glob_mod import create_glob_mod
from dil.loop.layers.t1 import create_t1
from dil.loop.layers.t2 import Emission, create_t2
from dil.loop.layers.t3 import create_t3
from dil.loop.layers.t4 import create_t4
from dil.loop.layers.t5 import create_t5
from dil.loop.layers.t6 import create_t6
from dil.loop.layers.t7 import create_t7
from dil.loop.layers.t8 import create_t8
from dil.loop.types import Signal
from dil.runtime.reflection import (
    ReflectionError, form_reading, reflection_signal, reflection_transducer, trace_cycles,
)
from dil.store.data_store import create_data_store
from dil.store.event_log import create_event_log
from dil.store.resist_event import CycleSealActivity, EventRecord


def run(values):
    events = create_event_log()
    cycle = create_cycle(
        layers=Layers(t1=create_t1(), t2=create_t2(), t3=create_t3({"reflect": reflection_transducer}),
                      t4=create_t4(), t5=create_t5(), t6=create_t6(), t7=create_t7(), t8=create_t8()),
        glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=create_data_store(), events=events,
        initial_emission=Emission(action="boot"),
    )
    for t, v in enumerate(values):
        cycle.run(HostCycleInput(signals=(Signal(source_id="ch", raw_payload={"entity": "weather", "value": v}, t=t),)))
    return cycle, events


def test_the_places_a_reader_can_point_at_are_the_cycles_the_trace_recorded():
    _, events = run(["sun", "rain"])
    cycles = trace_cycles(events)
    assert [c.cycle for c in cycles] == [0, 1]
    assert all(isinstance(events.all()[c.index], CycleSealActivity) for c in cycles)


def test_a_reading_may_point_where_the_agent_recorded_no_collision():
    _, events = run(["sun", "rain"])
    scarred = {r.anchor.cycle for r in events.all() if isinstance(r, EventRecord)}
    assert 0 not in scarred, "cycle 0 held"
    reading = form_reading(events, 0, "reader-1", "you settled too early")
    assert (reading.about.cycle, reading.reader_id, reading.reading) == (0, "reader-1", "you settled too early")


def test_a_reading_cannot_point_at_a_place_the_trace_never_recorded():
    _, events = run(["sun"])
    with pytest.raises(ReflectionError):
        form_reading(events, 5, "reader-1", "you drifted")


def test_the_reading_enters_as_plain_data_bound_to_the_reader():
    cycle, events = run(["sun", "rain"])
    reading = form_reading(events, 0, "reader-1", "note")
    signal = reflection_signal(reading, "reflect", 9)
    assert signal.raw_payload == {"entity": "reader-1", "value": {
        "reader": "reader-1", "about": {"cycle": 0, "index": reading.about.index, "t": reading.about.t},
        "reading": "note"}}
    cycle.run(HostCycleInput(signals=(signal,)))
    assert trace_cycles(events)[-1].cycle == 2, "the loop took the reading and ran on"
