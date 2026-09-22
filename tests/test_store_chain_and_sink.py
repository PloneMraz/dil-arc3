"""The hash chain, the segmented JSONL sink, and the durable [event] log.

Ported from dil-core's hash-chain.test.ts, event-sink.test.ts and
durable-event-log.test.ts.
"""

import json
import tempfile
import unittest
from pathlib import Path

from dil.store import (
    CHAIN_GENESIS,
    ChainBroken,
    ChainOk,
    ContextAnchor,
    EventRecord,
    FixedTags,
    ResistEvent,
    TaggedDatum,
    create_durable_event_log,
    create_event_log,
    create_jsonl_file_sink,
    deserialize_event_record,
    list_segments,
    read_log_records,
    record_crystallization,
    record_emission,
    record_expectation,
    record_layer_exit,
    record_manifest,
    record_resistance_reading,
    record_scar,
    serialize_event_record,
    verify_jsonl_sink,
)
from dil.store.resist_event import ActivityEvent, record_activity

TAGS = {"domain": "arc", "grid": "64x64", "object": "cell"}


def scar_datum(cycle: int = 1) -> TaggedDatum:
    return TaggedDatum(
        payload={"v": cycle},
        fixed=FixedTags(timestamp=1_700_000_000_000, cycle_mark=cycle, provenance="scar", floor_tag=5),
        open=dict(TAGS),
    )


def a_scar(source: str = "region", cycle: int = 1) -> EventRecord:
    return record_scar(
        scar_datum(cycle),
        ResistEvent(source, cycle, cycle + 1, "value-mismatch", cycle),
        ContextAnchor(cycle=cycle, field_state={"gain": 1}),
    )


class ChainVerification(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp())

    def _sink(self, **kw):
        kw.setdefault("date_stamp", lambda: "20260922")
        return create_jsonl_file_sink(self.dir, **kw)

    def _lines(self) -> list[str]:
        seg = list_segments(self.dir)[0].file
        return [l for l in seg.read_text(encoding="utf-8").split("\n") if l]

    def _rewrite(self, lines: list[str]) -> None:
        list_segments(self.dir)[0].file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_an_intact_chained_directory_verifies_with_a_64_hex_head(self) -> None:
        s = self._sink()
        for i in range(3):
            s.write(a_scar(cycle=i + 1))
        s.close()
        result = verify_jsonl_sink(self.dir)
        self.assertIsInstance(result, ChainOk)
        self.assertEqual(result.count, 3)
        self.assertRegex(result.head, r"^[0-9a-f]{64}$")

    def test_altering_one_byte_of_a_middle_line_is_detected_at_that_line(self) -> None:
        s = self._sink()
        for i in range(3):
            s.write(a_scar(cycle=i + 1))
        s.close()
        lines = self._lines()
        obj = json.loads(lines[1])
        obj["record"]["payload"] = {"v": 999}
        lines[1] = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
        self._rewrite(lines)
        result = verify_jsonl_sink(self.dir)
        self.assertIsInstance(result, ChainBroken)
        self.assertEqual(result.at_line, 1)
        self.assertIn("content break", result.reason)

    def test_removing_a_line_is_detected_as_a_sequence_break(self) -> None:
        s = self._sink()
        for i in range(3):
            s.write(a_scar(cycle=i + 1))
        s.close()
        lines = self._lines()
        self._rewrite([lines[0], lines[2]])
        result = verify_jsonl_sink(self.dir)
        self.assertIsInstance(result, ChainBroken)
        self.assertEqual(result.at_line, 1)
        self.assertIn("sequence break", result.reason)

    def test_reordering_two_lines_is_detected(self) -> None:
        s = self._sink()
        for i in range(3):
            s.write(a_scar(cycle=i + 1))
        s.close()
        lines = self._lines()
        self._rewrite([lines[1], lines[0], lines[2]])
        result = verify_jsonl_sink(self.dir)
        self.assertIsInstance(result, ChainBroken)
        self.assertEqual(result.at_line, 0)

    def test_each_line_carries_its_schema_version_folded_into_the_hash(self) -> None:
        s = self._sink()
        s.write(a_scar())
        s.close()
        obj = json.loads(self._lines()[0])
        self.assertEqual(obj["schemaVersion"], 2)
        obj["schemaVersion"] = 3
        self._rewrite([json.dumps(obj, separators=(",", ":"), ensure_ascii=False)])
        result = verify_jsonl_sink(self.dir)
        self.assertIsInstance(result, ChainBroken)
        self.assertIn("content break", result.reason)

    def test_a_pre_versioning_line_is_rejected_by_version(self) -> None:
        s = self._sink()
        s.write(a_scar())
        s.close()
        obj = json.loads(self._lines()[0])
        del obj["schemaVersion"]
        self._rewrite([json.dumps(obj, separators=(",", ":"), ensure_ascii=False)])
        result = verify_jsonl_sink(self.dir)
        self.assertIsInstance(result, ChainBroken)
        self.assertIn("pre-versioning", result.reason)
        self.assertNotIn("content break", result.reason)

    def test_a_forged_appended_line_with_a_wrong_prev_is_detected(self) -> None:
        s = self._sink()
        s.write(a_scar(cycle=1))
        s.write(a_scar(cycle=2))
        s.close()
        lines = self._lines()
        obj = json.loads(lines[1])
        obj["prev"] = "f" * 64
        lines[1] = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
        self._rewrite(lines)
        result = verify_jsonl_sink(self.dir)
        self.assertIsInstance(result, ChainBroken)
        self.assertEqual(result.at_line, 1)
        self.assertIn("chain break", result.reason)

    def test_the_chain_resumes_across_a_reopen(self) -> None:
        s1 = self._sink()
        s1.write(a_scar(cycle=1))
        head1 = s1.head()
        s1.close()
        s2 = self._sink()
        self.assertEqual(s2.head(), head1, "a reopened sink resumes from the stored head")
        s2.write(a_scar(cycle=2))
        s2.close()
        result = verify_jsonl_sink(self.dir)
        self.assertIsInstance(result, ChainOk)
        self.assertEqual(result.count, 2)

    def test_an_empty_sink_has_the_genesis_head_and_verifies_vacuously(self) -> None:
        s = self._sink()
        self.assertEqual(s.head(), CHAIN_GENESIS)
        s.close()
        result = verify_jsonl_sink(self.dir)
        self.assertIsInstance(result, ChainOk)
        self.assertEqual(result.count, 0)
        self.assertEqual(result.head, CHAIN_GENESIS)

    def test_opening_on_an_unparsable_tail_refuses(self) -> None:
        s = self._sink()
        s.write(a_scar())
        s.close()
        self._rewrite([*self._lines(), '{"not":"a chained line"}'])
        with self.assertRaises(RuntimeError) as caught:
            self._sink()
        self.assertIn("refusing to append past corruption", str(caught.exception))


class SinkRoundTrips(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp())

    def _round_trip(self, record):
        return deserialize_event_record(serialize_event_record(record))

    def test_a_scar_round_trips_with_tags_intact_and_in_fixed_order(self) -> None:
        rec = a_scar()
        back = self._round_trip(rec)
        self.assertEqual(back, rec)
        keys = list(serialize_event_record(rec).keys())
        self.assertEqual(
            keys[:7],
            ["form", "timestamp", "cycleMark", "provenance", "floorTag", "open", "payload"],
        )

    def test_a_cycle_seal_round_trips_with_the_same_fixed_order_tag_set(self) -> None:
        datum = TaggedDatum(
            payload="p",
            fixed=FixedTags(1, 2, "running", 8),
            open=dict(TAGS),
        )
        rec = record_activity(
            "cycle-2",
            datum,
            ActivityEvent(cycle=2, flow="single-threaded", emitted={"a": 1}, observed=("e1",), scars=0, t=9),
            ContextAnchor(cycle=2),
        )
        self.assertEqual(self._round_trip(rec), rec)

    def test_a_lean_layer_exit_round_trips(self) -> None:
        rec = record_layer_exit("cycle-1", 1, 3, 10)
        back = self._round_trip(rec)
        self.assertEqual(back, rec)
        self.assertNotIn("anchor", serialize_event_record(rec))

    def test_an_emission_round_trips_with_register_and_issuing_layer(self) -> None:
        rec = record_emission("cycle-1", 1, 8, {"kind": "respond"}, 11)
        back = self._round_trip(rec)
        self.assertEqual(back, rec)
        self.assertEqual(back.register, "↔")
        self.assertEqual(back.issuing_layer, 8)

    def test_a_crystallization_round_trips(self) -> None:
        rec = record_crystallization("cycle-0", 0, 12)
        self.assertEqual(self._round_trip(rec), rec)

    def test_an_expectation_round_trips(self) -> None:
        rec = record_expectation("cycle-3", 3, "e1", "e1", 0.75, 4, 0.25, 13)
        back = self._round_trip(rec)
        self.assertEqual(back, rec)
        self.assertEqual(back.source, back.entity, "the join key to a scar's source_id")

    def test_a_resistance_reading_round_trips(self) -> None:
        rec = record_resistance_reading("cycle-3", 3, "region", "e1", "absence", 2, 1.0, "-", 14)
        self.assertEqual(self._round_trip(rec), rec)

    def test_a_manifest_round_trips(self) -> None:
        rec = record_manifest("DIL v0.3.2", 2, {"COMMIT_EVERY": 9, "H_COUNT": 3}, 15)
        self.assertEqual(self._round_trip(rec), rec)

    def test_records_survive_a_sink_reopen(self) -> None:
        s = create_jsonl_file_sink(self.dir, date_stamp=lambda: "20260922")
        s.write(a_scar())
        s.close()
        s2 = create_jsonl_file_sink(self.dir, date_stamp=lambda: "20260922")
        s2.write(record_layer_exit("cycle-1", 1, 2, 3))
        s2.close()
        self.assertEqual(len(read_log_records(self.dir)), 2)

    def test_the_sink_surface_exposes_no_mutation_path(self) -> None:
        s = create_jsonl_file_sink(self.dir, date_stamp=lambda: "20260922")
        for forbidden in ("update", "delete", "truncate", "remove", "rewrite"):
            self.assertFalse(hasattr(s, forbidden))
        s.close()

    def test_event_log_mirrors_every_appended_record_to_the_sink(self) -> None:
        s = create_jsonl_file_sink(self.dir, date_stamp=lambda: "20260922")
        log = create_event_log(s)
        log.append(a_scar())
        log.append(record_layer_exit("cycle-1", 1, 2, 3))
        s.close()
        self.assertEqual(len(read_log_records(self.dir)), 2)

    def test_event_log_without_a_sink_stays_in_memory_only(self) -> None:
        log = create_event_log()
        log.append(a_scar())
        self.assertEqual(log.size(), 1)
        self.assertEqual(list_segments(self.dir), [])

    def test_segments_rotate_on_the_size_cap_without_splitting_a_record(self) -> None:
        s = create_jsonl_file_sink(self.dir, max_segment_bytes=900, date_stamp=lambda: "20260922")
        for i in range(6):
            s.write(a_scar(cycle=i + 1))
        s.close()
        segs = list_segments(self.dir)
        self.assertGreater(len(segs), 1, "the cap must have rotated at least once")
        self.assertEqual(segs[0].file.name, "event-log-20260922.jsonl")
        self.assertEqual(segs[1].file.name, "event-log-20260922-002.jsonl")
        for seg in segs:
            for line in seg.file.read_text(encoding="utf-8").split("\n"):
                if line:
                    json.loads(line)  # every line is whole
        self.assertIsInstance(verify_jsonl_sink(self.dir), ChainOk)

    def test_a_date_change_opens_a_new_daily_segment_and_the_chain_spans_both(self) -> None:
        day = {"v": "20260922"}
        s = create_jsonl_file_sink(self.dir, date_stamp=lambda: day["v"])
        s.write(a_scar(cycle=1))
        day["v"] = "20260923"
        s.write(a_scar(cycle=2))
        s.close()
        names = [seg.file.name for seg in list_segments(self.dir)]
        self.assertEqual(names, ["event-log-20260922.jsonl", "event-log-20260923.jsonl"])
        result = verify_jsonl_sink(self.dir)
        self.assertIsInstance(result, ChainOk)
        self.assertEqual(result.count, 2)


class DurableLog(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp())

    def test_serialize_deserialize_round_trips_losslessly(self) -> None:
        rec = a_scar()
        self.assertEqual(deserialize_event_record(serialize_event_record(rec)), rec)

    def test_records_read_back_from_disk_and_size_is_a_counter(self) -> None:
        log = create_durable_event_log(self.dir, date_stamp=lambda: "20260922")
        log.append(a_scar(cycle=1))
        log.append(record_layer_exit("cycle-1", 1, 2, 3))
        self.assertEqual(log.size(), 2)
        self.assertEqual(len(log.all()), 2)
        log.close()

    def test_a_reopened_log_resumes_prior_records_and_the_chain(self) -> None:
        log = create_durable_event_log(self.dir, date_stamp=lambda: "20260922")
        log.append(a_scar(cycle=1))
        head = log.head()
        log.close()
        log2 = create_durable_event_log(self.dir, date_stamp=lambda: "20260922")
        self.assertEqual(log2.size(), 1, "the counter resumes from the substrate")
        self.assertEqual(log2.head(), head)
        log2.append(a_scar(cycle=2))
        self.assertEqual(log2.size(), 2)
        log2.close()
        self.assertIsInstance(verify_jsonl_sink(self.dir), ChainOk)

    def test_by_source_id_reads_matching_scars_from_disk(self) -> None:
        log = create_durable_event_log(self.dir, date_stamp=lambda: "20260922")
        log.append(a_scar(source="a", cycle=1))
        log.append(a_scar(source="b", cycle=2))
        log.append(a_scar(source="a", cycle=3))
        log.close()
        reopened = create_durable_event_log(self.dir, date_stamp=lambda: "20260922")
        self.assertEqual(len(reopened.by_source_id("a")), 2)
        self.assertEqual(len(reopened.by_source_id("b")), 1)
        reopened.close()


if __name__ == "__main__":
    unittest.main()
