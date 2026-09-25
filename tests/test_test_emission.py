"""T5 emits a test (protocol §6.4): "an action that pushes to the region to see
whether the return matches the Expectation just built". Ported from dil-core
a8ef7ce. The rule thinks; it does not act: `test` records the action as an
emission from T5, register ↔, handed to the host as `CycleResult.tests` and to
link 5 as `RespondContext.tests`.
"""

from __future__ import annotations

from dil.conformance.checker import check_conformance
from dil.loop.cycle import HostCycleInput, Layers, create_cycle
from dil.loop.glob_mod import create_glob_mod
from dil.loop.layers.t1 import create_t1
from dil.loop.layers.t2 import Emission, create_t2
from dil.loop.layers.t3 import create_t3
from dil.loop.layers.t4 import create_t4
from dil.loop.layers.t5 import create_t5, persistence, region_test
from dil.loop.layers.t6 import create_t6
from dil.loop.layers.t7 import create_t7
from dil.loop.layers.t8 import create_t8
from dil.loop.types import Signal
from dil.store.data_store import create_data_store
from dil.store.event_log import create_event_log
from dil.store.event_sink import deserialize_event_record, serialize_event_record


def pushing_rule():
    seen = {"t": None}

    def rule(entity_id, window, observed, contribute=None, ask=None, write=None, test=None):
        if observed.t != seen["t"]:
            seen["t"] = observed.t
            test({"kind": "move", "to": "up", "at": observed.t})
        return persistence(entity_id, window, observed, contribute, ask, write)

    return rule


def loop(rule, respond=None):
    events = create_event_log()
    cycle = create_cycle(
        layers=Layers(t1=create_t1(), t2=create_t2(), t3=create_t3({}), t4=create_t4(),
                      t5=create_t5(predict=rule), t6=create_t6(), t7=create_t7(), t8=create_t8()),
        glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=create_data_store(), events=events,
        initial_emission=Emission(action="boot"), **({"respond": respond} if respond else {}),
    )
    return cycle, events


def sig(v, t):
    return Signal(source_id="ch", raw_payload={"entity": "weather", "value": v}, t=t)


def from_t5(events):
    return [r for r in events.all() if getattr(r, "activity_kind", None) == "emission" and r.issuing_layer == 5]


def test_a_test_is_recorded_from_t5_and_reaches_link_5_in_the_same_cycle():
    seen = []

    def respond(ctx):
        seen.append(ctx.tests)
        return "done"

    cycle, events = loop(pushing_rule(), respond)
    result = cycle.run(HostCycleInput(signals=(sig("sun", 100),)))
    action = {"kind": "move", "to": "up", "at": 100}
    assert result.tests == (action,)
    assert seen == [(action,)], "link 5 sees this cycle's test, not last cycle's"
    assert [(r.action, r.register) for r in from_t5(events)] == [(region_test(action), "↔")]


def test_a_rule_written_before_test_existed_still_runs_and_tests_nothing():
    old = lambda e, w, o, c=None, a=None, wr=None: persistence(e, w, o, c, a, wr)  # noqa: E731
    cycle, events = loop(old)
    assert cycle.run(HostCycleInput(signals=(sig("sun", 100),))).tests == ()
    assert from_t5(events) == []


def test_the_trace_with_tests_is_accepted_and_survives_the_sink():
    cycle, events = loop(pushing_rule())
    for i, v in enumerate(["sun", "rain", "sun"]):
        cycle.run(HostCycleInput(signals=(sig(v, 100 + i),)))
    assert [f"{r.id}: {r.detail}" for r in check_conformance(events).results if r.verdict == "fail"] == []
    for rec in events.all():
        assert deserialize_event_record(serialize_event_record(rec)) == rec
