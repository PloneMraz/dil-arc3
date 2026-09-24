"""Region returns as data of their own (DEVIATION from dil-core, declared).

§10 leaves store representation to the implementation, and dil-core, having no
host, keeps no region data: its one datum per cycle is the driver's own. A host
that declares `admit` has each signal it accepts become a datum — through the
tagging-gate, `running` once it runs, a line at every layer it exits — and when
the expectation about it fails, that datum is the one that collides and holds.
"""

from __future__ import annotations

from dil.conformance.checker import check_conformance
from dil.loop.cycle import HostCycleInput, Layers, create_cycle
from dil.loop.glob_mod import create_glob_mod
from dil.loop.layers.t1 import create_t1
from dil.loop.layers.t2 import Emission, create_t2
from dil.loop.layers.t3 import create_t3
from dil.loop.layers.t4 import create_t4
from dil.loop.layers.t5 import create_t5, persistence
from dil.loop.layers.t6 import create_t6
from dil.loop.layers.t7 import create_t7
from dil.loop.layers.t8 import create_t8
from dil.loop.store_query import answer_query
from dil.loop.types import Signal
from dil.store.data_store import create_data_store
from dil.store.event_log import create_event_log
from dil.store.event_sink import deserialize_event_record, serialize_event_record
from dil.store.resist_event import EventRecord
from dil.store.tagging_gate import HostDatum

FIRST = "signal-0-0"
SECOND = "signal-1-0"


def status(state: str, t: int) -> Signal:
    return Signal(source_id="status", raw_payload={"entity": "region", "state": state}, t=t)


def admit_status(signal: Signal) -> HostDatum | None:
    if signal.source_id != "status":
        return None
    return HostDatum(
        payload=signal.raw_payload,
        admitting_layer=1,
        open={"domain": "observation", "kind": "status", "source": signal.source_id},
    )


def make_cycle(data, events, admit=admit_status, predict=None):
    layers = Layers(
        t1=create_t1(), t2=create_t2(), t3=create_t3({}), t4=create_t4(),
        t5=create_t5(predict=predict), t6=create_t6(), t7=create_t7(), t8=create_t8(),
    )
    return create_cycle(
        layers=layers, glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=data,
        events=events, initial_emission=Emission(action="boot"), admit=admit,
    )


def of_kind(events, kind: str):
    return [r for r in events.all() if getattr(r, "activity_kind", None) == kind]


def test_an_admitted_return_is_a_running_datum_with_the_tags_the_host_declared():
    data, events = create_data_store(), create_event_log()
    make_cycle(data, events).run(HostCycleInput(signals=(status("playing", 1),)))

    d = data.get(FIRST)
    assert d is not None
    assert d.payload == {"entity": "region", "state": "playing"}
    assert d.fixed.provenance == "running"
    assert d.fixed.cycle_mark == 0
    assert d.fixed.floor_tag == 8, "it left T8 with the cycle datum"
    assert d.open == {"domain": "observation", "kind": "status", "source": "status"}
    moves = [r for r in of_kind(events, "provenance") if r.datum_id == FIRST]
    assert [(m.from_, m.to) for m in moves] == [("prior", "running")]


def test_every_layer_an_admitted_datum_exits_is_in_the_log():
    data, events = create_data_store(), create_event_log()
    make_cycle(data, events).run(HostCycleInput(signals=(status("playing", 1),)))

    exits = [r.layer for r in of_kind(events, "layer-exit") if r.datum_id == FIRST]
    assert exits == [1, 2, 3, 4, 5, 6, 7, 8]
    seal = of_kind(events, "cycle-seal")[0]
    assert [t.datum_id for t in seal.activity.admitted] == [FIRST]
    assert seal.activity.admitted[0].open["kind"] == "status", "tags, never content"


def test_the_datum_the_expectation_failed_on_is_the_one_that_becomes_a_scar():
    data, events = create_data_store(), create_event_log()
    cycle = make_cycle(data, events)
    cycle.run(HostCycleInput(signals=(status("playing", 1),)))
    cycle.run(HostCycleInput(signals=(status("won", 2),)))  # persistence expected "playing"

    assert data.get(SECOND).fixed.provenance == "scar"
    assert data.get(FIRST).fixed.provenance == "running", "the earlier return did not collide"
    moves = [(r.from_, r.to) for r in of_kind(events, "provenance") if r.datum_id == SECOND]
    assert moves == [("prior", "running"), ("running", "scar")]

    scars = [r for r in events.all() if isinstance(r, EventRecord)]
    assert len(scars) == 1
    assert scars[0].datum_id == SECOND
    assert scars[0].scar.payload == {"entity": "region", "state": "won"}
    assert scars[0].event.expected["value"]["state"] == "playing"


def test_the_new_fields_survive_the_sink_and_old_forms_are_unchanged():
    data, events = create_data_store(), create_event_log()
    cycle = make_cycle(data, events)
    cycle.run(HostCycleInput(signals=(status("playing", 1),)))
    cycle.run(HostCycleInput(signals=(status("won", 2),)))
    for rec in events.all():
        assert deserialize_event_record(serialize_event_record(rec)) == rec

    plain_data, plain_events = create_data_store(), create_event_log()
    plain = make_cycle(plain_data, plain_events, admit=None)
    plain.run(HostCycleInput(signals=(status("playing", 1),)))
    plain.run(HostCycleInput(signals=(status("won", 2),)))
    for rec in plain_events.all():
        form = serialize_event_record(rec)
        assert "admitted" not in form.get("activity", {})
        assert "datumId" not in form or form["form"] != "scar"
    assert plain_data.get(FIRST) is None, "without `admit`, no region datum exists"


def test_an_admitted_return_can_be_asked_for_by_its_tags():
    data, events = create_data_store(), create_event_log()
    make_cycle(data, events).run(HostCycleInput(signals=(status("playing", 1),)))

    answered = answer_query(data, {"kind": "status"}, 2)
    assert [s.raw_payload["entity"] for s in answered] == [FIRST]


def test_a_run_that_admits_leaves_a_trace_the_checker_accepts():
    data, events = create_data_store(), create_event_log()
    cycle = make_cycle(data, events)
    for t, state in enumerate(("playing", "playing", "won", "won"), start=1):
        cycle.run(HostCycleInput(signals=(status(state, t),)))

    report = check_conformance(events)
    assert [f"{r.id}: {r.detail}" for r in report.results if r.verdict == "fail"] == []
    c3 = next(r for r in report.results if r.id == "3")
    assert any(c.claim.startswith("every admitted region datum's path") and c.verdict == "pass"
               for c in c3.claims)


def test_a_rule_still_predicts_what_it_did_with_admission_on():
    """Admission changes what is stored, not what the loop expects."""
    seen = []

    def rule(entity_id, window, observed, contribute=None, ask=None):
        seen.append(entity_id)
        return persistence(entity_id, window, observed, contribute, ask)

    data, events = create_data_store(), create_event_log()
    make_cycle(data, events, predict=rule).run(HostCycleInput(signals=(status("playing", 1),)))
    assert seen == ["region"]
