"""The peer mechanism ported from dil-core: its plumbing, not its use.

This host does not use a peer (tag E is the onlooker, `arc3/onlooker.py`): a
peer that relays another agent's recorded collisions only retells them, and the
diversity it gave C7 was the peers echoing each other (LOG.md, 2026-09-25).
What is pinned here is that the mechanism, if used, keeps the region's presence,
carries plain data, and reads without being able to write.
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
from dil.runtime.host_source import scripted_source
from dil.runtime.peer import PEER_REFLECTION_CHANNEL, PeerLog, peer_reflecting_source, read_only
from dil.runtime.reflection import ReflectionError, form_reading, reflection_transducer
from dil.store.tagging_gate import HostDatum
from dil.store.data_store import create_data_store
from dil.store.event_log import create_event_log
from dil.store.event_sink import deserialize_event_record, serialize_event_record


def weather(value: str, t: int) -> Signal:
    return Signal(source_id="ch", raw_payload={"entity": "weather", "value": value}, t=t)


def inputs(n: int) -> list[HostCycleInput]:
    """A region that changes every cycle: one Other, resisting every time."""
    return [HostCycleInput(signals=(weather("sun" if t % 2 else "rain", t),),
                           afforded=frozenset({"weather"})) for t in range(n)]


def admit(signal):
    """Keep a reading as data, so the test can see what it carries."""
    if signal.source_id != PEER_REFLECTION_CHANNEL:
        return None
    return HostDatum(payload=signal.raw_payload, admitting_layer=1,
                     open={"domain": "reflection", "kind": "peer-reading", "source": signal.source_id})


def make_cycle(data, events):
    layers = Layers(
        t1=create_t1(), t2=create_t2(stability_threshold=1),
        t3=create_t3({PEER_REFLECTION_CHANNEL: reflection_transducer}),
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


def test_the_readings_keep_presence_and_are_plain_data_kept_as_data():
    b = peer_log()
    data, events = create_data_store(), create_event_log()
    source = peer_reflecting_source(scripted_source(inputs(12)), [PeerLog("peer:B", read_only(b))])
    seen = play(source, data, events)

    assert all(inp.afforded == frozenset({"weather"}) for inp in seen), "presence survives the wrapper"
    readings = [d for _, d in data.entries() if d.open.get("domain") == "reflection"]
    assert readings, "a reading can be held in [data]"
    first = readings[0].payload["value"]
    assert first["reader"] == "peer:B" and first["about"]["source_id"] == "weather"
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
