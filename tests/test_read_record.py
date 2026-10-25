"""Reading the record (protocol v0.3.9 §9; ported from dil-core c258f43).

The whole store is the agent's history: `[data]` its memory, `[event]` the
record of what happened, which the agent reads and never alters. The rule reads
it through the cycle's view — an open link, handed to it every cycle — and each
read leaves one `read-record` line for each purpose, naming the records by their
place in the chain, never their content. What the agent learns from it is
written to `[data]`, naming the record as `event:<seq>`. The checker holds both
to the record the log held before the cycle that read. Recollection, one law
over the view, recalls a scar as an expectation held by the datum that collided,
which moves `scar → running` when used again.
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
from dil.loop.recollection import recollecting
from dil.loop.types import Signal
from dil.store.data_store import create_data_store, to_running, to_scar
from dil.store.decisions import CONTEXT_ANCHOR_DEPTH
from dil.store.event_log import create_durable_event_log, create_event_log
from dil.store.event_sink import deserialize_event_record, serialize_event_record
from dil.store.resist_event import (
    ContextAnchor,
    ProvenanceActivity,
    ReadRecordActivity,
    ResistEvent,
    record_read_record,
    record_scar,
)
from dil.store.tagging_gate import HostDatum, admit_host_data

SEEDED_AT = 7


def seen(where: str, outcome: str) -> Signal:
    return Signal(source_id="ch", raw_payload={"entity": "weather", "value": {"where": where, "outcome": outcome}}, t=1)


def where_of(unit) -> str:
    return str(unit.content.get("value", {}).get("value", {}).get("where", ""))


def seeded():
    """A store as a past run left it: the scar in [event], the scarred return in [data]."""
    data, events = create_data_store(), create_event_log()
    held = to_scar(to_running(admit_host_data(HostDatum(
        payload="x", admitting_layer=1, open={"domain": "region", "source": "ch", "format": "object"},
    ), 1), SEEDED_AT), True)
    data.put("signal-7-0", held)
    events.append(record_scar(
        held,
        ResistEvent(
            source_id="weather", expected=None,
            received={"infoType": "raw", "channel": "ch",
                      "value": {"entity": "weather", "value": {"where": "hall", "outcome": "rain"}}},
            mismatch_kind="value-mismatch", t=1,
        ),
        ContextAnchor(cycle=SEEDED_AT, field_state={}, depth=CONTEXT_ANCHOR_DEPTH),
        datum_id="signal-7-0",
    ))
    return data, events


def cycle_over(data, events, rule):
    return create_cycle(
        layers=Layers(t1=create_t1(), t2=create_t2(), t3=create_t3(), t4=create_t4(),
                      t5=create_t5(predict=rule), t6=create_t6(), t7=create_t7(), t8=create_t8()),
        glob=create_glob_mod({"appraisalGain": 1.0}, 0), data=data, events=events,
        initial_emission=Emission(action="boot"),
    )


def moves(events):
    return [r for r in events.all() if isinstance(r, ProvenanceActivity) and r.from_ == "scar" and r.to == "running"]


def record_reads(events):
    return [r for r in events.all() if isinstance(r, ReadRecordActivity)]


# ── the link is open ──

def test_every_cycle_hands_the_rule_the_records_view_with_nothing_declared():
    data, events = seeded()
    got = []

    def rule(entity_id, window, observed, contribute=None, ask=None, write=None, *, record=None):
        got.append(record)
        return persistence(entity_id, window, observed)

    cycle = cycle_over(data, events, rule)
    for _ in range(3):
        cycle.run(HostCycleInput(signals=(seen("hall", "sun"),)))
    assert len(got) >= 3 and all(v is not None for v in got)


def test_the_view_holds_what_the_log_held_before_the_cycle_and_each_read_is_recorded_by_seq():
    data, events = seeded()
    got, sizes = [], []

    def rule(entity_id, window, observed, contribute=None, ask=None, write=None, *, record=None):
        got.append([r.seq for r in record.recent("look", 5)])
        return persistence(entity_id, window, observed)

    cycle = cycle_over(data, events, rule)
    for _ in range(2):
        sizes.append(events.size())
        cycle.run(HostCycleInput(signals=(seen("hall", "sun"),)))
    for seqs, size in zip(got, sizes):
        assert seqs and all(s < size for s in seqs), "nothing of the cycle that reads"
        assert seqs == sorted(seqs, reverse=True), "newest first"
    assert [(l.cycle_mark, l.purpose, list(l.records)) for l in record_reads(events)] == [
        (i, "look", g) for i, g in enumerate(got)
    ]
    for rec in events.all():
        assert deserialize_event_record(serialize_event_record(rec)) == rec


def test_what_is_learned_from_the_record_names_it_and_the_checker_passes():
    data, events = seeded()

    def rule(entity_id, window, observed, contribute=None, ask=None, write=None, *, record=None):
        lines = record.scars("weather", "learn", 1)
        if lines:
            write(WriteRequest(payload="what the record says",
                               open={"domain": "mind", "kind": "note", "source": "rule"},
                               built_from=tuple(f"event:{l.seq}" for l in lines)))
        return persistence(entity_id, window, observed)

    cycle = cycle_over(data, events, rule)
    for _ in range(3):
        cycle.run(HostCycleInput(signals=(seen("hall", "sun"),)))
    seals = [r for r in events.all() if getattr(r, "activity_kind", None) == "cycle-seal"]
    assert seals[0].activity.written[0].built_from == ("event:0",)
    c6 = next(r for r in check_conformance(events).results if r.id == "6")
    assert c6.verdict == "pass", c6.detail
    assert any(c.claim.startswith("every record read of `[event]`") and c.verdict == "pass" for c in c6.claims)


def test_a_record_the_log_did_not_hold_before_the_cycle_cannot_be_built_from():
    data, events = seeded()

    def rule(entity_id, window, observed, contribute=None, ask=None, write=None):
        write(WriteRequest(payload="x", open={"domain": "mind", "kind": "note", "source": "rule"},
                           built_from=("event:99999",)))
        return persistence(entity_id, window, observed)

    with pytest.raises(ValueError, match="did not hold before this cycle"):
        cycle_over(data, events, rule).run(HostCycleInput(signals=(seen("hall", "sun"),)))


def test_a_read_of_a_record_the_log_did_not_hold_before_the_cycle_is_caught():
    data, events = seeded()
    cycle = cycle_over(data, events, persistence)
    for _ in range(2):
        cycle.run(HostCycleInput(signals=(seen("hall", "sun"),)))
    of_cycle_1 = next(i for i, r in enumerate(events.all())
                      if getattr(r, "activity_kind", None) == "layer-exit" and r.cycle_mark == 1)
    events.append(record_read_record("cycle-1", 1, 5, "look", (of_cycle_1,), 1))
    c6 = next(r for r in check_conformance(events).results if r.id == "6")
    assert c6.verdict == "fail"
    assert f"record #{of_cycle_1}, read at cycle 1" in c6.detail


def test_a_rule_that_does_not_read_the_record_leaves_no_line_and_recalls_nothing():
    data, events = seeded()
    cycle_over(data, events, persistence).run(HostCycleInput(signals=(seen("hall", "sun"),)))
    assert record_reads(events) == []
    assert moves(events) == []


# ── recollection, one law over the view ──

def test_a_recalled_scar_is_held_by_its_datum_and_moves_on_it():
    data, events = seeded()
    cycle = cycle_over(data, events, recollecting(key=where_of))
    for _ in range(3):
        cycle.run(HostCycleInput(signals=(seen("hall", "sun"),)))
    found = moves(events)
    assert (found[0].datum_id, found[0].cycle_mark) == ("signal-7-0", 0)
    assert len({(m.cycle_mark, m.datum_id) for m in found}) == len(found), "once a cycle"
    for datum_id in {m.datum_id for m in found}:
        last = [r for r in events.all() if isinstance(r, ProvenanceActivity) and r.datum_id == datum_id][-1]
        assert data.get(datum_id).fixed.provenance == last.to, "[data] follows the log"
    assert {l.purpose for l in record_reads(events)} == {"recollection"}


def test_the_record_supplies_the_expectation_and_the_region_contradicting_it_scars():
    data, events = seeded()
    result = cycle_over(data, events, recollecting(key=where_of)).run(HostCycleInput(signals=(seen("hall", "sun"),)))
    assert result.scars > 0


def test_the_region_agreeing_with_the_record_leaves_no_new_scar():
    data, events = seeded()
    result = cycle_over(data, events, recollecting(key=where_of)).run(HostCycleInput(signals=(seen("hall", "rain"),)))
    assert result.scars == 0


def test_a_situation_the_record_has_never_met_leaves_scar_to_running_unfired():
    data, events = seeded()
    cycle_over(data, events, recollecting(key=where_of)).run(HostCycleInput(signals=(seen("cellar", "sun"),)))
    assert moves(events) == []


# ── the durable log ──

def test_the_durable_log_reads_back_from_disk_across_segments_as_in_memory(tmp_path):
    log = create_durable_event_log(tmp_path, max_segment_bytes=4096, date_stamp=lambda: "20261025")
    data, _ = seeded()

    def rule(entity_id, window, observed, contribute=None, ask=None, write=None, *, record=None):
        record.recent("look", 3)
        return persistence(entity_id, window, observed)

    cycle = cycle_over(data, log, rule)
    for i in range(6):
        cycle.run(HostCycleInput(signals=(seen("hall", "sun" if i % 2 else "rain"),)))
    log.sync()
    records = log.all()
    assert len(list(tmp_path.iterdir())) > 2, "several segments"
    for before, scan in ((len(records), 50), (len(records) - 7, 13), (40, 100), (3, 3), (0, 5)):
        expected = [(seq, records[seq]) for seq in range(min(before, len(records)) - 1, max(-1, before - 1 - scan), -1)]
        assert [(r.seq, r.record) for r in log.back(before, scan)] == expected, (before, scan)
    log.close()


def test_cycles_reads_the_seals_of_the_latest_cycles_newest_first():
    data, events = seeded()
    got = []

    def rule(entity_id, window, observed, contribute=None, ask=None, write=None, *, record=None):
        got.append([r.record.activity.cycle for r in record.cycles("what happened", 2)])
        return persistence(entity_id, window, observed)

    cycle = cycle_over(data, events, rule)
    for _ in range(4):
        cycle.run(HostCycleInput(signals=(seen("hall", "sun"),)))
    assert got == [[], [0], [1, 0], [2, 1]]
    assert [(l.cycle_mark, len(l.records)) for l in record_reads(events)] == [(1, 1), (2, 2), (3, 2)]
