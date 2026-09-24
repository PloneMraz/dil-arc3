"""Every record takes the clock at the moment it happens. Ported from dil-core 9073ddf.

§9: the `[event]` log "records each transition as it occurs", and a datum's
timestamp is set "when the datum is first stamped". One clock reading per cycle
hid where a cycle's time went — the minutes a model spends thinking in T5 — and
stamped a datum written at the end of a cycle with the time it began.
"""

from __future__ import annotations

from dil.loop.cycle import HostCycleInput, Layers, create_cycle
from dil.loop.glob_mod import create_glob_mod
from dil.loop.layers.t1 import create_t1
from dil.loop.layers.t2 import Emission, create_t2
from dil.loop.layers.t3 import create_t3
from dil.loop.layers.t4 import create_t4
from dil.loop.layers.t5 import WriteRequest, create_t5, persistence
from dil.loop.layers.t6 import create_t6
from dil.loop.layers.t7 import create_t7
from dil.loop.layers.t8 import create_t8
from dil.loop.types import Signal
from dil.store.data_store import create_data_store
from dil.store.event_log import create_event_log
from dil.store.event_sink import deserialize_event_record, serialize_event_record
from dil.store.resist_event import CycleSealActivity, EventRecord, ManifestRecord

THINKING = 1000


def sig(value: str) -> Signal:
    return Signal(source_id="ch", raw_payload={"entity": "weather", "value": value}, t=0)


def loop():
    clock = [1_000_000]

    def now() -> int:
        clock[0] += 1
        return clock[0]

    wrote = [False]

    def rule(entity_id, window, observed, contribute=None, ask=None, write=None):
        if not wrote[0]:
            clock[0] += THINKING  # the thinking takes a while
            write(WriteRequest(built_from=(), payload={"thought": 1},
                               open={"domain": "world-model", "kind": "program", "source": "mind"}))
            wrote[0] = True
        return persistence(entity_id, window, observed, contribute, ask, write)

    data, events = create_data_store(), create_event_log()
    cycle = create_cycle(
        layers=Layers(t1=create_t1(), t2=create_t2(), t3=create_t3(), t4=create_t4(),
                      t5=create_t5(predict=rule), t6=create_t6(), t7=create_t7(), t8=create_t8()),
        glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=data, events=events,
        initial_emission=Emission(action="boot"), now=now,
    )
    return cycle, data, events


def time_of(r) -> int | None:
    if isinstance(r, ManifestRecord):
        return r.t
    if isinstance(r, EventRecord):
        return r.event.t
    if isinstance(r, CycleSealActivity):
        return r.activity.closed_at
    return getattr(r, "t", None)


def exits(events, datum_id: str, cycle: int):
    return [r for r in events.all()
            if getattr(r, "activity_kind", None) == "layer-exit" and r.datum_id == datum_id and r.cycle_mark == cycle]


def seals(events):
    return [r for r in events.all() if isinstance(r, CycleSealActivity)]


def test_each_layer_exit_takes_its_own_time_and_the_thinking_shows_between_t4_and_t5():
    cycle, _, events = loop()
    cycle.run(HostCycleInput(signals=(sig("sun"),)))
    times = [r.t for r in exits(events, "cycle-0", 0)]
    assert len(times) == 8
    assert all(b > a for a, b in zip(times, times[1:]))
    assert times[4] - times[3] >= THINKING, "the time T5 took is where it was spent"
    assert times[3] - times[0] < THINKING


def test_a_datum_is_stamped_when_it_is_stamped():
    cycle, data, events = loop()
    cycle.run(HostCycleInput(signals=(sig("sun"),)))
    seal = seals(events)[0]
    t5 = exits(events, "cycle-0", 0)[4].t
    assert data.get("cycle-0").fixed.timestamp == seal.activity.t
    assert data.get("written-0-0").fixed.timestamp > t5
    assert data.get("signal-0-0").fixed.timestamp >= seal.activity.t


def test_the_seal_brackets_its_cycle_and_times_never_run_backwards():
    cycle, _, events = loop()
    for v in ("sun", "rain", "rain"):
        cycle.run(HostCycleInput(signals=(sig(v),)))
    for s in seals(events):
        inside = [r for r in events.all()
                  if not isinstance(r, CycleSealActivity) and getattr(r, "cycle_mark", None) == s.activity.cycle]
        assert all(s.activity.t <= time_of(r) <= s.activity.closed_at for r in inside)
    assert seals(events)[0].activity.closed_at - seals(events)[0].activity.t >= THINKING
    last = None
    for r in events.all():
        t = time_of(r)
        if t is None:
            continue
        assert last is None or t >= last
        last = t
    for rec in events.all():
        assert deserialize_event_record(serialize_event_record(rec)) == rec
