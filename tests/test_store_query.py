"""The character recalling from its own store — end to end through the driver.

Ported from dil-core's `store-query.test.ts`. §6.4: "T3 emits a query: it opens
or calls a channel to ingest actively." §9: host data enters as `prior`, "once
admitted and once it has run, bears a cycle-mark". These pin the whole road: the
cue, the query, the return arriving at T1, the move to `running`, and that
nothing floods.
"""

from __future__ import annotations

from dil.loop.cycle import HostCycleInput, Layers, create_cycle
from dil.loop.glob_mod import create_glob_mod
from dil.loop.layers.t1 import create_t1
from dil.loop.layers.t2 import Emission, create_t2
from dil.loop.layers.t3 import STORE_CHANNEL, create_t3
from dil.loop.layers.t4 import create_t4
from dil.loop.layers.t5 import create_t5
from dil.loop.layers.t6 import create_t6
from dil.loop.layers.t7 import create_t7
from dil.loop.layers.t8 import create_t8
from dil.loop.store_query import answer_query, matches_cue
from dil.loop.types import Signal
from dil.store.data_store import create_data_store
from dil.conformance.checker import check_conformance
from dil.store.event_log import create_event_log
from dil.store.event_sink import deserialize_event_record, serialize_event_record
from dil.store.resist_event import record_provenance
from dil.store.tagging_gate import HostDatum, admit_host_data

DIRECTIVE = "prior:directive"
UNRELATED = "prior:unrelated"


def status(t: int) -> Signal:
    """What the region reports each cycle: its own status, as one entity."""
    return Signal(source_id="status", raw_payload={"entity": "region", "state": "playing"}, t=t)


def described_status(signal: Signal):
    """The status channel's transducer describes what arrives on it (tag F)."""
    return ("status", signal.raw_payload, {"object": "region-status"})


def seeded_store():
    data = create_data_store()
    data.put(DIRECTIVE, admit_host_data(HostDatum(
        payload={"says": "Your goal is to win."}, admitting_layer=1,
        open={"domain": "rules", "kind": "directive", "object": "region-status"},
    ), 1))
    data.put(UNRELATED, admit_host_data(HostDatum(
        payload={"says": "Something about something else."}, admitting_layer=1,
        open={"domain": "rules", "kind": "world", "object": "things"},
    ), 1))
    return data


def cycle_over(data, events, transducers=None, t3=None):
    layers = Layers(
        t1=create_t1(), t2=create_t2(),
        t3=t3 if t3 is not None else create_t3(
            {"status": described_status} if transducers is None else transducers
        ),
        t4=create_t4(), t5=create_t5(), t6=create_t6(), t7=create_t7(), t8=create_t8(),
    )
    return create_cycle(
        layers=layers, glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=data,
        events=events, initial_emission=Emission(action="boot"),
    )


def run(cycle, t: int, **kw):
    return cycle.run(HostCycleInput(signals=(status(t),), **kw))


def queries(events):
    return [r for r in events.all()
            if getattr(r, "activity_kind", None) == "emission" and r.issuing_layer == 3]


def moves(events, datum_id: str):
    return [r for r in events.all()
            if getattr(r, "activity_kind", None) == "provenance" and r.datum_id == datum_id]


def observed_at(events, cycle: int):
    for r in events.all():
        if getattr(r, "activity_kind", None) == "cycle-seal" and r.activity.cycle == cycle:
            return tuple(r.activity.observed)
    return ()


# ── the index is the open layer ──


def test_a_datum_matches_a_cue_when_its_open_tags_carry_every_pair():
    data = seeded_store()
    assert matches_cue(data.get(DIRECTIVE), {"object": "region-status"})
    assert not matches_cue(data.get(UNRELATED), {"object": "region-status"})
    assert not matches_cue(data.get(DIRECTIVE), {}), "an empty cue asks for nothing"


def test_the_store_answers_on_the_store_channel_with_the_datum_as_it_held_it():
    (ret, *rest) = answer_query(seeded_store(), {"object": "region-status"}, 5)
    assert rest == []
    assert ret.source_id == STORE_CHANNEL
    assert ret.raw_payload["entity"] == DIRECTIVE
    assert ret.raw_payload["fixed"]["provenance"] == "prior", "not its own yet"


# ── the road through the driver ──


def test_t3_asks_the_store_about_what_arrived_traced_to_t3():
    events = create_event_log()
    run(cycle_over(seeded_store(), events), 1)
    q = queries(events)
    assert len(q) == 1
    assert q[0].action == {"kind": "query", "channel": STORE_CHANNEL,
                           "cue": {"object": "region-status"}}


def test_nothing_is_recalled_in_the_cycle_that_asks():
    data, events = seeded_store(), create_event_log()
    cycle = cycle_over(data, events)
    run(cycle, 1)
    assert moves(events, DIRECTIVE) == []
    assert data.get(DIRECTIVE).fixed.provenance == "prior"
    assert DIRECTIVE not in observed_at(events, 0)
    run(cycle, 2)
    assert DIRECTIVE in observed_at(events, 1), "it ran the layers up to T5"


def test_a_recalled_prior_moves_to_running_and_takes_the_cycle_it_ran_in():
    data, events = seeded_store(), create_event_log()
    cycle = cycle_over(data, events)
    run(cycle, 1)
    run(cycle, 2)
    (m,) = moves(events, DIRECTIVE)
    assert (m.from_, m.to, m.cycle_mark) == ("prior", "running", 1)
    assert data.get(DIRECTIVE).fixed.provenance == "running"
    assert data.get(DIRECTIVE).fixed.cycle_mark == 1


def test_memory_is_recalled_on_a_cue_never_poured_in():
    data, events = seeded_store(), create_event_log()
    cycle = cycle_over(data, events)
    for t in range(1, 6):
        run(cycle, t)
    assert len(queries(events)) == 1, "a cue already asked about is not asked again"
    assert moves(events, UNRELATED) == [], "what no cue matched stays where it is"
    assert data.get(UNRELATED).fixed.provenance == "prior"
    assert [c for c in range(5) if DIRECTIVE in observed_at(events, c)] == [1]


def test_a_memory_that_was_not_recalled_is_not_silent():
    """MEASURED in dil-core before the fix: with no presence reported, the
    recalled datum was registered absent every cycle from the second on."""
    cycle = cycle_over(seeded_store(), create_event_log())
    assert [run(cycle, t).absences for t in range(1, 7)] == [0] * 6


def test_with_presence_reported_it_is_not_absent_either():
    cycle = cycle_over(seeded_store(), create_event_log())
    afforded = frozenset({"region"})
    assert [run(cycle, t, afforded=afforded).absences for t in range(1, 5)] == [0] * 4


def test_with_no_description_t3_does_not_ask():
    events = create_event_log()
    cycle = cycle_over(seeded_store(), events, transducers={})
    run(cycle, 1)
    run(cycle, 2)
    assert queries(events) == []


def test_what_was_asked_and_what_is_in_flight_survive_a_snapshot():
    data, events = seeded_store(), create_event_log()
    t3 = create_t3({"status": described_status})
    first = cycle_over(data, events, t3=t3)
    run(first, 1)
    state = first.snapshot()
    assert len(state.pending_returns) == 1

    layers = Layers(
        t1=create_t1(), t2=create_t2(), t3=t3, t4=create_t4(), t5=create_t5(),
        t6=create_t6(), t7=create_t7(), t8=create_t8(),
    )
    resumed = create_cycle(
        layers=layers, glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=data,
        events=events, initial_emission=Emission(action="boot"), resume=state,
    )
    run(resumed, 2)
    assert len(moves(events, DIRECTIVE)) == 1, "the answer in flight still arrived"
    assert t3.snapshot() == {"asked": ['[["object", "region-status"]]']}


# ── agency closure (§6.4 rule 3) ──


def test_what_a_query_brought_back_is_tagged_self_written():
    """ "emit → region returns → T1 ingests → T2 matches." The return is a change
    the agent's own query produced, and T2 must read that query as an action just
    emitted, or it could only call the return ENV_PUSHED."""
    data, events = seeded_store(), create_event_log()
    t2 = create_t2(stability_threshold=1)
    seen = []
    inner = t2.process

    def spy(input, field, emit, contribute):  # noqa: A002
        out = inner(input, field, emit, contribute)
        seen.append(out)
        return out

    t2.process = spy
    layers = Layers(
        t1=create_t1(), t2=t2, t3=create_t3({"status": described_status}), t4=create_t4(),
        t5=create_t5(), t6=create_t6(), t7=create_t7(), t8=create_t8(),
    )
    cycle = create_cycle(layers=layers, glob=create_glob_mod({"appraisalGain": 1.0}, 0),
                         data=data, events=events, initial_emission=Emission(action="boot"))
    run(cycle, 1)
    run(cycle, 2)
    (recalled,) = [t for t in seen[1].tagged if t.change.id == DIRECTIVE]
    assert recalled.agency == "SELF_WRITTEN"


# ── one arrival, several things it is about ──


def test_an_arrival_about_several_things_asks_about_each():
    data, events = seeded_store(), create_event_log()

    def both(signal):
        return ("status", signal.raw_payload, [{"object": "region-status"}, {"object": "things"}])

    cycle = cycle_over(data, events, transducers={"status": both})
    run(cycle, 1)
    run(cycle, 2)
    assert len(queries(events)) == 2
    assert data.get(DIRECTIVE).fixed.provenance == "running"
    assert data.get(UNRELATED).fixed.provenance == "running"


# ── the recalled datum's own trace (§9, §13.6) ──


def seal_of(events, cycle: int):
    return next(r for r in events.all()
                if getattr(r, "activity_kind", None) == "cycle-seal" and r.activity.cycle == cycle)


def recalled_run():
    data, events = seeded_store(), create_event_log()
    cycle = cycle_over(data, events)
    run(cycle, 1)
    run(cycle, 2)
    return data, events, cycle


def test_a_recalled_datums_own_path_is_in_the_log():
    data, events, _ = recalled_run()
    exits = [(r.cycle_mark, r.layer) for r in events.all()
             if getattr(r, "activity_kind", None) == "layer-exit" and r.datum_id == DIRECTIVE]
    assert exits == [(1, layer) for layer in range(1, 9)]
    assert data.get(DIRECTIVE).fixed.floor_tag == 8, "it names the layer it just exited"


def test_the_activity_record_carries_the_tag_set_and_never_the_content():
    _, events, _ = recalled_run()
    (tags,) = seal_of(events, 1).activity.recalled
    assert tags.datum_id == DIRECTIVE
    assert tags.open == {"domain": "rules", "kind": "directive", "object": "region-status"}
    assert (tags.fixed.provenance, tags.fixed.cycle_mark) == ("running", 1)
    assert "Your goal is to win" not in repr(seal_of(events, 1)), (
        "uncontested content stays out of the agent's memory (§9)"
    )
    assert seal_of(events, 0).activity.recalled == ()
    assert "recalled" not in serialize_event_record(seal_of(events, 0))["activity"], (
        "a cycle that recalled nothing writes the record exactly as before"
    )


def test_the_recalled_tag_set_survives_the_durable_form():
    import json

    _, events, _ = recalled_run()
    seal = seal_of(events, 1)
    back = deserialize_event_record(json.loads(json.dumps(serialize_event_record(seal))))
    assert back.activity.recalled == seal.activity.recalled


def test_the_checker_reads_the_recalled_path_and_the_gate():
    _, events, cycle = recalled_run()
    for t in (3, 4):
        run(cycle, t)
    results = {r.id: r for r in check_conformance(events).results}
    assert any(c.claim.startswith("every recalled datum's path") and c.verdict == "pass"
               for c in results["3"].claims)
    assert any(c.claim.startswith("host data entered only via the tagging-gate")
               and c.verdict == "pass" for c in results["6"].claims)


def test_a_datum_that_ran_from_prior_with_no_tags_in_the_trace_is_caught():
    data, events = seeded_store(), create_event_log()
    run(cycle_over(data, events), 1)
    events.append(record_provenance("side-door", 0, "prior", "running", 1))
    c6 = next(r for r in check_conformance(events).results if r.id == "6")
    assert c6.verdict == "fail"
    assert "side-door" in c6.detail
