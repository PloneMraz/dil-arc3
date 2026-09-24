"""A datum the agent writes says what it was built from. Ported from dil-core c2c0cd2.

Protocol v0.3.4 §9: the ids of the data a written datum drew on — observations
from the rule's window and the one in front of it, and data it recalled —
never their content, as an Expectation carries `built_from`.
"""

from __future__ import annotations

import pytest

from dil.conformance.checker import check_conformance
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
from dil.loop.types import InfoUnit, RefFrame, Signal
from dil.store.data_store import create_data_store
from dil.store.event_log import create_event_log
from dil.store.event_sink import deserialize_event_record, serialize_event_record
from dil.store.resist_event import CycleSealActivity, WrittenTags

TAGS = {"domain": "world-model", "kind": "program", "source": "mind"}


def writer(at: int, pick):
    seen = {"cycle": -1, "t": None}

    def rule(entity_id, window, observed, contribute=None, ask=None, write=None):
        if observed.t != seen["t"]:
            seen["t"] = observed.t
            seen["cycle"] += 1
            if seen["cycle"] == at:
                write(WriteRequest(payload={"v": 1}, open=TAGS, built_from=pick(window, observed)))
        return persistence(entity_id, window, observed, contribute, ask, write)

    return rule


def loop(rule):
    data, events = create_data_store(), create_event_log()
    clock = [0]

    def now():
        clock[0] += 1
        return clock[0]

    cycle = create_cycle(
        layers=Layers(t1=create_t1(), t2=create_t2(), t3=create_t3(), t4=create_t4(),
                      t5=create_t5(predict=rule), t6=create_t6(), t7=create_t7(), t8=create_t8()),
        glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=data, events=events,
        initial_emission=Emission(action="boot"), now=now,
    )

    def step(i: int, v: str):
        cycle.run(HostCycleInput(signals=(Signal(source_id="ch", raw_payload={"entity": "weather", "value": v}, t=100 + i),)))

    return step, events


def written(events):
    return [w for r in events.all() if isinstance(r, CycleSealActivity) for w in r.activity.written]


def test_the_window_and_the_observation_in_front_are_recorded_by_datum_id():
    step, events = loop(writer(2, lambda window, observed: (*window, observed)))
    step(0, "sun")
    step(1, "sun")
    step(2, "rain")
    [w] = written(events)
    assert w.built_from == ("signal-0-0", "signal-1-0", "signal-2-0")
    assert "rain" not in repr(w), "ids, never content"


def test_ids_are_recorded_once_and_an_empty_tuple_says_nothing_held_went_in():
    step, events = loop(writer(1, lambda window, observed: ("signal-0-0", "signal-0-0")))
    step(0, "sun")
    step(1, "sun")
    assert written(events)[0].built_from == ("signal-0-0",)
    step2, events2 = loop(writer(0, lambda window, observed: ()))
    step2(0, "sun")
    assert written(events2)[0].built_from == ()


def test_what_it_was_built_from_must_be_data():
    step, _ = loop(writer(0, lambda window, observed: ("ghost",)))
    with pytest.raises(ValueError, match='"ghost", which is no datum'):
        step(0, "sun")
    made = InfoUnit(content={"invented": True}, ref_frame=RefFrame(bound_layer=5, ref="rule"), t=0)
    step, _ = loop(writer(0, lambda window, observed: (made,)))
    with pytest.raises(ValueError, match="a unit that came from no datum"):
        step(0, "sun")
    step, _ = loop(writer(0, lambda window, observed: None))
    with pytest.raises(ValueError, match="must say what it was built from"):
        step(0, "sun")


def test_the_checker_reads_it_and_a_forged_source_fails():
    step, events = loop(writer(1, lambda window, observed: (*window, observed)))
    step(0, "sun")
    step(1, "rain")
    report = check_conformance(events)
    assert [r.id for r in report.results if r.verdict == "fail"] == []
    c6 = next(r for r in report.results if r.id == "6")
    assert any(c.claim.startswith("every datum the agent wrote says what it was built from") and c.verdict == "pass"
               for c in c6.claims)
    for rec in events.all():
        assert deserialize_event_record(serialize_event_record(rec)) == rec

    forged = create_event_log()
    for r in events.all():
        if isinstance(r, CycleSealActivity) and r.activity.written:
            w = r.activity.written[0]
            fake = WrittenTags(datum_id=w.datum_id, fixed=w.fixed, open=w.open, built_from=("ghost",))
            r = CycleSealActivity(
                datum_id=r.datum_id, datum=r.datum, anchor=r.anchor,
                activity=type(r.activity)(**{**{f: getattr(r.activity, f) for f in r.activity.__slots__}, "written": (fake,)}),
            )
        forged.append(r)
    c6 = next(r for r in check_conformance(forged).results if r.id == "6")
    assert c6.verdict == "fail"
    assert "written at cycle 1, does not say what it was built from" in c6.detail
