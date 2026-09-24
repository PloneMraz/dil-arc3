"""Every datum that meets a mismatch is scarred (protocol v0.3.5 §9).

Ported from dil-core 4f5da8f. A mismatch has two sides, what was expected and
what returned; the expecting side is each datum the expectation is (`held_by`):
the observation persistence repeats, or a program the rule names. Evidence in the
window the expectation is not met nothing. A scar used again returns to
`running`, so a program that keeps failing circulates between the two.
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
from dil.loop.layers.t5 import Expecting, WriteRequest, create_t5, persistence
from dil.loop.layers.t6 import create_t6
from dil.loop.layers.t7 import create_t7
from dil.loop.layers.t8 import create_t8
from dil.loop.types import InfoUnit, Signal
from dil.store.data_store import create_data_store
from dil.store.event_log import create_event_log
from dil.store.event_sink import deserialize_event_record, serialize_event_record
from dil.store.resist_event import EventRecord, ExpectationActivity
from dil.store.tagging_gate import HostDatum

RETURN_TAGS = {"domain": "observation", "kind": "weather", "source": "ch"}
PROGRAM_TAGS = {"domain": "world-model", "kind": "program", "source": "mind"}


def admit(signal):
    return HostDatum(payload=signal.raw_payload, admitting_layer=1, open=RETURN_TAGS) if signal.source_id == "ch" else None


def loop(rule=None):
    data, events = create_data_store(), create_event_log()
    cycle = create_cycle(
        layers=Layers(t1=create_t1(), t2=create_t2(), t3=create_t3({}), t4=create_t4(),
                      t5=create_t5(predict=rule) if rule else create_t5(), t6=create_t6(),
                      t7=create_t7(), t8=create_t8()),
        glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=data, events=events,
        initial_emission=Emission(action="boot"), admit=admit,
    )

    def step(i, v):
        cycle.run(HostCycleInput(signals=(Signal(source_id="ch", raw_payload={"entity": "weather", "value": v}, t=100 + i),)))

    return step, data, events


def moves(events, datum_id):
    return [f"{r.from_}→{r.to}@{r.cycle_mark}" for r in events.all()
            if getattr(r, "activity_kind", None) == "provenance" and r.datum_id == datum_id]


def scars(events):
    return [r for r in events.all() if isinstance(r, EventRecord)]


def test_persistence_scars_the_observation_it_repeated_and_not_older_evidence():
    step, data, events = loop()
    step(0, "sun")
    step(1, "sun")
    step(2, "rain")
    assert data.get("signal-2-0").fixed.provenance == "scar", "the return"
    assert data.get("signal-1-0").fixed.provenance == "scar", "the observation the expectation was"
    assert data.get("signal-0-0").fixed.provenance == "running", "evidence, not the expectation"
    assert [s.datum_id for s in scars(events)] == ["signal-2-0", "signal-1-0"]
    line = next(r for r in events.all() if isinstance(r, ExpectationActivity) and r.cycle_mark == 2)
    assert line.held_by == ("signal-1-0",)


def test_a_scar_used_again_returns_to_use_and_scars_again_if_it_fails():
    step, data, events = loop()
    step(0, "sun")
    step(1, "rain")
    step(2, "sun")
    assert moves(events, "signal-1-0") == ["running→scar@1", "scar→running@2", "running→scar@2"]
    step(3, "sun")
    assert moves(events, "signal-2-0") == ["running→scar@2", "scar→running@3"]


def program_rule():
    state = {"written": False, "seen": None}

    def rule(entity_id, window, observed, contribute=None, ask=None, write=None):
        if observed.t != state["seen"]:
            state["seen"] = observed.t
            if not state["written"]:
                state["written"] = True
                write(WriteRequest(payload={"code": "always sun"}, open=PROGRAM_TAGS, built_from=()))
                return persistence(entity_id, window, observed, contribute, ask, write)
        if entity_id != "weather":
            return persistence(entity_id, window, observed, contribute, ask, write)
        content = dict(observed.content)
        content["value"] = {"entity": "weather", "value": "sun"}
        return Expecting(predicted=InfoUnit(content=content, ref_frame=observed.ref_frame, t=observed.t),
                         held_by=("written-0-0",))

    return rule


def test_a_program_circulates_between_running_and_scar_as_its_expectations_meet_the_region():
    step, data, events = loop(program_rule())
    for i, v in enumerate(["sun", "sun", "rain", "sun", "rain"]):
        step(i, v)
    assert moves(events, "written-0-0") == ["nascent→running@1", "running→scar@2", "scar→running@3", "running→scar@4"]
    assert len([s for s in scars(events) if s.datum_id == "written-0-0"]) == 2


def test_a_name_that_is_no_datum_or_a_unit_from_no_datum_is_refused():
    ghost = lambda e, w, o, c=None, a=None, wr=None: Expecting(predicted=o, held_by=("ghost",))  # noqa: E731
    with pytest.raises(ValueError, match='held_by names "ghost", which is no datum'):
        loop(ghost)[0](0, "sun")
    made = InfoUnit(content={"invented": True}, ref_frame=None, t=0)
    orphan = lambda e, w, o, c=None, a=None, wr=None: Expecting(predicted=o, held_by=(made,))  # noqa: E731
    with pytest.raises(ValueError, match="a unit that came from no datum"):
        loop(orphan)[0](0, "sun")


def test_the_checker_accepts_it_as_run_and_fails_a_forged_expectation():
    step, data, events = loop(program_rule())
    for i, v in enumerate(["sun", "sun", "rain", "sun", "rain"]):
        step(i, v)
    report = check_conformance(events)
    assert [f"{r.id}: {r.detail}" for r in report.results if r.verdict == "fail"] == []
    for rec in events.all():
        assert deserialize_event_record(serialize_event_record(rec)) == rec

    forged = create_event_log()
    for r in events.all():
        if isinstance(r, EventRecord) and r.datum_id == "written-0-0" and r.anchor.cycle == 2:
            continue
        forged.append(r)
    c6 = next(r for r in check_conformance(forged).results if r.id == "6")
    assert c6.verdict == "fail"
    assert "did not scar when it mismatched against the region" in c6.detail
