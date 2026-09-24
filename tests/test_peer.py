"""The peer reader (tag E): another agent's reading of this one's collisions.

A Kaggle session has no third party, so the reader is a peer agent in the same
session. Its readings arrive through T3 on their own channel, are kept as data
(`domain: reflection`), and can resist like any Other's return — which is what
gives an agent playing one game a second resistance source (§11, C5 and C7).
"""

from __future__ import annotations

import pytest

from arc3.observe import admit, transducers
from dil.conformance.checker import check_conformance
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
from dil.runtime.host_source import scripted_source
from dil.runtime.peer import PeerLog, peer_reflecting_source, read_only
from dil.runtime.reflection import ReflectionError, form_reading
from dil.store.data_store import create_data_store
from dil.store.event_log import create_event_log
from dil.store.event_sink import deserialize_event_record, serialize_event_record


def weather(value: str, t: int) -> Signal:
    return Signal(source_id="ch", raw_payload={"entity": "weather", "value": value}, t=t)


def inputs(n: int) -> list[HostCycleInput]:
    """A region that changes every cycle: one Other, resisting every time."""
    return [HostCycleInput(signals=(weather("sun" if t % 2 else "rain", t),),
                           afforded=frozenset({"weather"})) for t in range(n)]


def make_cycle(data, events):
    layers = Layers(
        t1=create_t1(), t2=create_t2(stability_threshold=1), t3=create_t3(transducers()),
        t4=create_t4(), t5=create_t5(), t6=create_t6(), t7=create_t7(), t8=create_t8(),
    )
    return create_cycle(layers=layers, glob=create_glob_mod({"appraisalGain": 1.0}, 0),
                        data=data, events=events, initial_emission=Emission(action="boot"),
                        admit=admit)


def play(source, data, events) -> list[HostCycleInput]:
    cycle, seen = make_cycle(data, events), []
    while (inp := source.next()) is not None:
        seen.append(inp)
        cycle.run(inp)
    return seen


def peer_log(n: int = 12):
    """Agent B's log after it has played: collisions a reader can address."""
    events = create_event_log()
    play(scripted_source(inputs(n)), create_data_store(), events)
    return events


def sources(events) -> set[str]:
    return {r.event.source_id for r in events.all() if type(r).__name__ == "EventRecord"}


def verdict(events, criterion: str) -> str:
    return next(r.verdict for r in check_conformance(events).results if r.id == criterion)


def test_alone_one_source_and_diversity_loss_is_established():
    events = create_event_log()
    play(scripted_source(inputs(12)), create_data_store(), events)
    assert sources(events) == {"weather"}
    assert verdict(events, "5") == "partial"
    assert verdict(events, "7") == "fail"


def test_with_a_peer_its_readings_are_data_that_resist_and_diversity_holds():
    b = peer_log()
    data, events = create_data_store(), create_event_log()
    source = peer_reflecting_source(scripted_source(inputs(12)), [PeerLog("peer:B", read_only(b))])
    seen = play(source, data, events)

    assert all(inp.afforded == frozenset({"weather"}) for inp in seen), "presence survives the wrapper"
    readings = [(k, d) for k, d in data.entries() if d.open.get("domain") == "reflection"]
    assert readings and all(d.open["kind"] == "peer-reading" for _, d in readings)
    first = readings[0][1].payload["value"]
    assert first["reader"] == "peer:B" and first["about"]["source_id"] == "weather"
    assert sources(events) == {"weather", "peer:B"}
    assert verdict(events, "5") == "pass"
    assert verdict(events, "7") == "pass"
    for rec in events.all():
        assert deserialize_event_record(serialize_event_record(rec)) == rec


def test_a_cycle_reads_at_most_two_readings_per_peer_and_each_collision_once():
    b = peer_log()
    source = peer_reflecting_source(scripted_source(inputs(3)), [PeerLog("peer:B", read_only(b))])
    about = []
    while (inp := source.next()) is not None:
        readings = [s for s in inp.signals if s.source_id == "peer-reflection"]
        assert len(readings) <= 2
        about += [s.raw_payload["value"]["about"]["index"] for s in readings]
    assert len(about) == len(set(about)) == 6


def test_the_peer_can_read_and_not_write_and_reads_a_log_made_later():
    later = {}
    view = read_only(lambda: later["log"])
    assert not hasattr(view, "append")
    later["log"] = peer_log(4)
    assert view.size() == later["log"].size()
    with pytest.raises(ReflectionError):
        form_reading(view, 0, "peer:B", {})  # the first record is no collision
