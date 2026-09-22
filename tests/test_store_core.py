"""Tagging-gate, tag schema, [event] immutability and the provenance lifecycle.

Ported case for case from dil-core's store.test.ts.
"""

import unittest

from dil.store import (
    PROVENANCE_EDGES,
    ContextAnchor,
    EventRecordError,
    FixedTags,
    HostDatum,
    LifecycleError,
    ResistEvent,
    TaggedDatum,
    TaggingGateError,
    admit_host_data,
    assert_provenance_edge,
    create_data_store,
    create_event_log,
    is_provenance_edge,
    record_scar,
    stamp_layer,
    to_projected,
    to_running,
    to_scar,
    to_simulated,
)

GOOD_TAGS = {"domain": "financial", "currency": "VND", "object": "revenue"}


def a_datum(provenance="running", cycle_mark=1, floor_tag=1, open_tags=None) -> TaggedDatum:
    return TaggedDatum(
        payload={"v": 1},
        fixed=FixedTags(
            timestamp=1_700_000_000_000,
            cycle_mark=cycle_mark,
            provenance=provenance,
            floor_tag=floor_tag,
        ),
        open=dict(open_tags or GOOD_TAGS),
    )


class TaggingGate(unittest.TestCase):
    def test_host_data_is_admitted_stamped_prior(self) -> None:
        d = admit_host_data(HostDatum(payload="x", admitting_layer=1, open=GOOD_TAGS), 42)
        self.assertEqual(d.fixed.provenance, "prior")
        self.assertIsNone(d.fixed.cycle_mark)
        self.assertEqual(d.fixed.floor_tag, 1)
        self.assertEqual(d.fixed.timestamp, 42)

    def test_the_four_fixed_tags_are_present_and_in_order(self) -> None:
        d = admit_host_data(HostDatum(payload="x", admitting_layer=2, open=GOOD_TAGS), 7)
        self.assertEqual(
            [f.name for f in FixedTags.__dataclass_fields__.values()],
            ["timestamp", "cycle_mark", "provenance", "floor_tag"],
        )
        self.assertEqual(d.fixed.timestamp, 7)

    def test_gate_requires_the_mandatory_domain_tag(self) -> None:
        with self.assertRaises(TaggingGateError) as caught:
            admit_host_data(
                HostDatum(payload="x", admitting_layer=1, open={"a": "1", "b": "2", "c": "3"}), 1
            )
        self.assertIn("domain", str(caught.exception))

    def test_gate_requires_at_least_three_open_tags(self) -> None:
        with self.assertRaises(TaggingGateError) as caught:
            admit_host_data(
                HostDatum(payload="x", admitting_layer=1, open={"domain": "d", "a": "1"}), 1
            )
        self.assertIn("at least 3", str(caught.exception))

    def test_gate_rejects_open_tags_that_name_a_verdict(self) -> None:
        for verdict in ("quality", "correctness", "value", "valence", "good", "bad"):
            with self.assertRaises(TaggingGateError):
                admit_host_data(
                    HostDatum(
                        payload="x",
                        admitting_layer=1,
                        open={"domain": "d", "other": "o", verdict: "high"},
                    ),
                    1,
                )

    def test_a_compliant_open_tag_set_is_accepted(self) -> None:
        d = admit_host_data(HostDatum(payload="x", admitting_layer=1, open=GOOD_TAGS), 1)
        self.assertEqual(d.open, GOOD_TAGS)

    def test_admission_stamps_the_floor_tag_and_carries_no_path(self) -> None:
        d = admit_host_data(HostDatum(payload="x", admitting_layer=5, open=GOOD_TAGS), 1)
        self.assertEqual(d.fixed.floor_tag, 5)
        self.assertFalse(hasattr(d.fixed, "layer_trace"))

    def test_stamp_layer_overwrites_without_accumulating(self) -> None:
        d = a_datum(floor_tag=1)
        d2 = stamp_layer(stamp_layer(d, 4), 7)
        self.assertEqual(d2.fixed.floor_tag, 7)
        self.assertEqual(d.fixed.floor_tag, 1, "the original datum is untouched")


class EventLogImmutability(unittest.TestCase):
    def test_an_appended_record_cannot_be_altered_through_the_callers_reference(self) -> None:
        # dil-core deep-freezes; this deep-copies. Same guarantee from outside:
        # what the log holds cannot be reached and changed after the append.
        log = create_event_log()
        tags = dict(GOOD_TAGS)
        scar = a_datum(provenance="scar", open_tags=tags)
        log.append(record_scar(scar, ResistEvent("s", 1, 2, "value-mismatch", 3), ContextAnchor(1)))
        tags["domain"] = "TAMPERED"
        scar.open["object"] = "TAMPERED"
        stored = log.all()[0]
        self.assertEqual(stored.scar.open["domain"], "financial")
        self.assertEqual(stored.scar.open["object"], "revenue")

    def test_event_inherits_the_scars_tags(self) -> None:
        scar = a_datum(provenance="scar")
        rec = record_scar(scar, ResistEvent("s", 1, 2, "value-mismatch", 3), ContextAnchor(1))
        self.assertEqual(rec.scar.open, GOOD_TAGS)
        self.assertGreaterEqual(len(rec.scar.open), 3)
        self.assertIsNotNone(rec.scar.fixed.provenance)

    def test_a_non_scar_datum_cannot_be_recorded(self) -> None:
        for prov in ("prior", "running", "simulated", "projected"):
            with self.assertRaises(EventRecordError):
                record_scar(
                    a_datum(provenance=prov),
                    ResistEvent("s", 1, 2, "value-mismatch", 3),
                    ContextAnchor(1),
                )

    def test_the_log_exposes_no_remove_or_update_api(self) -> None:
        log = create_event_log()
        for forbidden in ("remove", "update", "delete", "truncate", "pop", "clear", "set"):
            self.assertFalse(hasattr(log, forbidden), f"log must not expose {forbidden}")

    def test_append_only_and_indexed_by_source_id(self) -> None:
        log = create_event_log()
        for i, src in enumerate(["a", "b", "a"]):
            log.append(
                record_scar(
                    a_datum(provenance="scar"),
                    ResistEvent(src, i, i + 1, "value-mismatch", i),
                    ContextAnchor(i),
                )
            )
        self.assertEqual(log.size(), 3)
        self.assertEqual(len(log.by_source_id("a")), 2)
        self.assertEqual(len(log.by_source_id("b")), 1)
        self.assertEqual(log.by_source_id("missing"), [])

    def test_each_event_anchors_the_full_field_state(self) -> None:
        anchor = ContextAnchor(cycle=4, field_state={"gain": 0.75, "mode": "b"})
        rec = record_scar(
            a_datum(provenance="scar"), ResistEvent("s", 1, 2, "absence", 3), anchor
        )
        self.assertEqual(rec.anchor.depth, "full-field-state")
        self.assertEqual(rec.anchor.field_state, {"gain": 0.75, "mode": "b"})


class ProvenanceLifecycle(unittest.TestCase):
    def test_prior_to_running_acquires_a_cycle_mark(self) -> None:
        prior = admit_host_data(HostDatum(payload="x", admitting_layer=1, open=GOOD_TAGS), 1)
        running = to_running(prior, 5)
        self.assertEqual(running.fixed.provenance, "running")
        self.assertEqual(running.fixed.cycle_mark, 5)
        # a datum that has already run keeps its mark on re-entry
        self.assertEqual(to_running(to_scar(running, True), 9).fixed.cycle_mark, 5)

    def test_running_to_scar_requires_a_held_collision(self) -> None:
        scar = to_scar(a_datum(provenance="running"), True)
        self.assertEqual(scar.fixed.provenance, "scar")

    def test_running_without_a_held_collision_cannot_become_a_scar(self) -> None:
        with self.assertRaises(LifecycleError):
            to_scar(a_datum(provenance="running"), False)

    def test_a_prior_cannot_jump_straight_to_scar(self) -> None:
        prior = admit_host_data(HostDatum(payload="x", admitting_layer=1, open=GOOD_TAGS), 1)
        with self.assertRaises(LifecycleError):
            to_scar(prior, True)

    def test_data_is_mutable_and_clearable_each_cycle(self) -> None:
        store = create_data_store()
        store.put("a", a_datum())
        store.put("b", a_datum())
        self.assertEqual(store.size(), 2)
        self.assertTrue(store.has("a"))
        store.put("a", a_datum(floor_tag=8))
        self.assertEqual(store.get("a").fixed.floor_tag, 8)
        self.assertTrue(store.delete("a"))
        self.assertFalse(store.delete("a"))
        store.clear()
        self.assertEqual(store.size(), 0)

    def test_every_one_of_the_eleven_edges_is_accepted(self) -> None:
        self.assertEqual(len(PROVENANCE_EDGES), 11)
        for frm, to in PROVENANCE_EDGES:
            self.assertTrue(is_provenance_edge(frm, to), f"{frm}→{to} should be legal")
        # prior is a one-way entry: nothing returns to it
        for prov in ("running", "simulated", "projected", "scar"):
            self.assertFalse(is_provenance_edge(prov, "prior"))

    def test_assert_provenance_edge_raises_on_a_non_edge(self) -> None:
        with self.assertRaises(LifecycleError):
            assert_provenance_edge("prior", "scar")

    def test_forward_building_on_ramps(self) -> None:
        self.assertEqual(to_simulated(a_datum(provenance="running")).fixed.provenance, "simulated")
        self.assertEqual(
            to_projected(a_datum(provenance="simulated")).fixed.provenance, "projected"
        )
        self.assertEqual(to_simulated(a_datum(provenance="scar")).fixed.provenance, "simulated")

    def test_forward_building_on_ramps_reject_illegal_from_states(self) -> None:
        prior = admit_host_data(HostDatum(payload="x", admitting_layer=1, open=GOOD_TAGS), 1)
        with self.assertRaises(LifecycleError):
            to_simulated(prior)
        with self.assertRaises(LifecycleError):
            to_projected(a_datum(provenance="running"))


if __name__ == "__main__":
    unittest.main()
