"""What the agent writes (protocol v0.3.3 §9). Ported from dil-core 44309b7.

A datum the agent writes anew enters at `nascent`, bearing the cycle-mark of the
cycle that wrote it; it arrives at T1 the next cycle, is classified SELF_WRITTEN
at T2, runs every layer, and moves `nascent → running`. A revision of a datum
already held changes its content and not its provenance, and leaves a bare
`revision` line. A cue may ask by provenance.
"""

from __future__ import annotations

import json

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
from dil.loop.store_query import answer_query
from dil.loop.types import Signal
from dil.store.data_store import create_data_store
from dil.store.event_log import create_event_log
from dil.store.event_sink import deserialize_event_record, serialize_event_record
from dil.store.resist_event import record_layer_exit, record_revision
from dil.store.tagging_gate import HostDatum, TaggingGateError, admit_arrival
from dil.store.tags import FixedTags

MODEL_TAGS = {"domain": "world-model", "kind": "program", "object": "weather"}
CLOCK = {"cycle": 0}


def weather(value: str, t: int) -> Signal:
    return Signal(source_id="ch", raw_payload={"entity": "weather", "value": value}, t=t)


def writing_rule(plan: dict[int, WriteRequest], met: list):
    """Writes what the plan holds for the current cycle, once; records what it met."""
    last = [-1]

    def rule(entity_id, window, observed, contribute=None, ask=None, write=None):
        met.append(observed.content)
        if CLOCK["cycle"] != last[0]:
            last[0] = CLOCK["cycle"]
            request = plan.get(CLOCK["cycle"])
            if request is not None:
                write(request)
        return persistence(entity_id, window, observed, contribute, ask, write)

    return rule


def make_cycle(data, events, rule, agency: list | None = None, resume=None):
    # Stable from the first cycle, so the tag a write earns is visible at once.
    t2 = create_t2(stability_threshold=1)
    if agency is not None:
        inner = t2.process

        def spy(inp, field, emit, contribute):
            out = inner(inp, field, emit, contribute)
            agency.append(out)
            return out

        t2.process = spy
    layers = Layers(
        t1=create_t1(), t2=t2, t3=create_t3({}), t4=create_t4(),
        t5=create_t5(predict=rule), t6=create_t6(), t7=create_t7(), t8=create_t8(),
    )
    return create_cycle(
        layers=layers, glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=data,
        events=events, initial_emission=Emission(action="boot"), resume=resume,
    )


def step(cycle, t: int, value: str = "sun") -> None:
    CLOCK["cycle"] = t
    cycle.run(HostCycleInput(signals=(weather(value, t),)))


def of_kind(events, kind: str):
    return [r for r in events.all() if getattr(r, "activity_kind", None) == kind]


def moves(events, datum_id: str):
    return [f"{r.from_}→{r.to}@{r.cycle_mark}" for r in of_kind(events, "provenance") if r.datum_id == datum_id]


def exits_at(events, datum_id: str, cycle: int):
    return [r.layer for r in of_kind(events, "layer-exit") if r.datum_id == datum_id and r.cycle_mark == cycle]


def seal(events, cycle: int):
    return next(r for r in of_kind(events, "cycle-seal") if r.activity.cycle == cycle)


def test_a_datum_written_anew_enters_at_nascent_with_the_cycle_that_wrote_it():
    data, events = create_data_store(), create_event_log()
    step(make_cycle(data, events, writing_rule({0: WriteRequest(payload={"code": "v1"}, open=MODEL_TAGS)}, [])), 0)

    d = data.get("written-0-0")
    assert d.payload == {"code": "v1"}
    assert d.fixed.provenance == "nascent"
    assert d.fixed.cycle_mark == 0, "it bears the cycle that wrote it"
    assert d.fixed.floor_tag == 5, "written at T5"
    assert d.open == MODEL_TAGS
    assert moves(events, "written-0-0") == [], "an entry is not a move"
    assert [t.datum_id for t in seal(events, 0).activity.written] == ["written-0-0"]
    assert "v1" not in repr(seal(events, 0).activity.written), "tags, never content"


def test_next_cycle_it_arrives_is_self_written_runs_every_layer_and_moves_to_running():
    data, events = create_data_store(), create_event_log()
    met, agency = [], []
    cycle = make_cycle(data, events, writing_rule({0: WriteRequest(payload={"code": "v1"}, open=MODEL_TAGS)}, met), agency)
    step(cycle, 0)
    step(cycle, 1)

    assert exits_at(events, "written-0-0", 1) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert moves(events, "written-0-0") == ["nascent→running@1"]
    d = data.get("written-0-0")
    assert d.fixed.provenance == "running"
    assert d.fixed.cycle_mark == 0, "running keeps the mark of the cycle that wrote it"
    assert d.fixed.floor_tag == 8
    tagged = next(t for t in agency[1].tagged if t.change.id == "written-0-0")
    assert tagged.agency == "SELF_WRITTEN"
    assert any("v1" in json.dumps(c, default=str) for c in met), "the rule met what it wrote"


def test_a_revision_changes_content_not_provenance_and_leaves_a_bare_line():
    data, events = create_data_store(), create_event_log()
    agency = []
    plan = {
        0: WriteRequest(payload={"code": "v1"}, open=MODEL_TAGS),
        2: WriteRequest(payload={"code": "v2"}, datum_id="written-0-0"),
    }
    cycle = make_cycle(data, events, writing_rule(plan, []), agency)
    for t in range(4):
        step(cycle, t)

    d = data.get("written-0-0")
    assert d.payload == {"code": "v2"}
    assert d.fixed.provenance == "running", "the revision moved nothing"
    assert d.open == MODEL_TAGS, "the tags stay when none are given"
    assert moves(events, "written-0-0") == ["nascent→running@1"]
    revisions = of_kind(events, "revision")
    assert [(r.datum_id, r.cycle_mark, r.issuing_layer) for r in revisions] == [("written-0-0", 2, 5)]
    assert "v2" not in repr(revisions), "no content in the log"
    assert exits_at(events, "written-0-0", 3) == [1, 2, 3, 4, 5, 6, 7, 8], "it arrives again after the revision"
    assert next(t for t in agency[3].tagged if t.change.id == "written-0-0").agency == "SELF_WRITTEN"


def test_writing_anew_needs_tags_and_only_a_held_datum_can_be_revised():
    with pytest.raises(TaggingGateError):
        step(make_cycle(create_data_store(), create_event_log(), writing_rule({0: WriteRequest(payload=1)}, [])), 0)
    verdict = WriteRequest(payload=1, open={"domain": "x", "kind": "y", "quality": "good"})
    with pytest.raises(TaggingGateError):
        step(make_cycle(create_data_store(), create_event_log(), writing_rule({0: verdict}, [])), 0)
    with pytest.raises(ValueError, match='no datum "nope" to revise'):
        step(make_cycle(create_data_store(), create_event_log(),
                        writing_rule({0: WriteRequest(payload=1, datum_id="nope")}, [])), 0)


def test_a_cue_may_ask_by_provenance():
    data = create_data_store()
    open_tags = {"domain": "observation", "kind": "frame", "source": "ch"}
    data.put("a", admit_arrival(HostDatum(payload=1, admitting_layer=1, open=open_tags), 0, 0))
    b = admit_arrival(HostDatum(payload=2, admitting_layer=1, open=open_tags), 0, 0)
    data.put("b", type(b)(payload=b.payload, fixed=FixedTags(timestamp=0, cycle_mark=0, provenance="scar", floor_tag=8), open=b.open))

    def ids(cue):
        return [s.raw_payload["entity"] for s in answer_query(data, cue, 1)]

    assert ids({"kind": "frame"}) == ["a", "b"]
    assert ids({"kind": "frame", "provenance": "scar"}) == ["b"]
    assert ids({"provenance": "running"}) == ["a"]


def test_a_run_that_writes_and_revises_is_accepted_and_survives_the_sink():
    events = create_event_log()
    plan = {
        0: WriteRequest(payload={"code": "v1"}, open=MODEL_TAGS),
        2: WriteRequest(payload={"code": "v2"}, datum_id="written-0-0"),
    }
    cycle = make_cycle(create_data_store(), events, writing_rule(plan, []))
    for t in range(4):
        step(cycle, t, "sun" if t % 2 else "rain")

    report = check_conformance(events)
    assert [f"{r.id}: {r.detail}" for r in report.results if r.verdict == "fail"] == []
    c3 = next(r for r in report.results if r.id == "3")
    assert any(c.claim.startswith("every datum the agent wrote runs") and c.verdict == "pass" for c in c3.claims)
    for rec in events.all():
        assert deserialize_event_record(serialize_event_record(rec)) == rec


def test_a_datum_with_no_recorded_entry_is_caught_whether_it_runs_or_is_revised():
    def run():
        events = create_event_log()
        step(make_cycle(create_data_store(), events, writing_rule({}, [])), 0)
        return events

    ran = run()
    ran.append(record_layer_exit("side-door", 0, 1, 1))
    c6 = next(r for r in check_conformance(ran).results if r.id == "6")
    assert c6.verdict == "fail"
    assert "side-door" in c6.detail

    revised = run()
    revised.append(record_revision("side-door", 0, 5, 1))
    assert next(r for r in check_conformance(revised).results if r.id == "6").verdict == "fail"


def test_what_was_written_survives_a_snapshot():
    data, events = create_data_store(), create_event_log()
    first = make_cycle(data, events, writing_rule({0: WriteRequest(payload={"code": "v1"}, open=MODEL_TAGS)}, []))
    step(first, 0)
    resumed = make_cycle(data, events, writing_rule({}, []), resume=first.snapshot())
    step(resumed, 1)
    assert moves(events, "written-0-0") == ["nascent→running@1"]
