"""The substrate claim, the SQLite [data] store, and the two read-only views.

Ported from dil-core's substrate.test.ts, sqlite-data-store.test.ts,
display-name.test.ts and inspector.test.ts.
"""

import json
import tempfile
import unittest
from pathlib import Path

from dil.store import (
    DIL_CLAIM,
    ContextAnchor,
    FixedTags,
    ResistEvent,
    SubstrateClaimError,
    TaggedDatum,
    claim_substrate,
    create_data_store,
    create_event_log,
    create_sqlite_data_store,
    display_name,
    event_display_name,
    inspect_data,
    inspect_event_log,
    layout_for,
    record_layer_exit,
    record_provenance,
    record_scar,
    stamp_layer,
)

TAGS = {"domain": "financial", "currency": "VND", "object": "revenue"}
# 2026-06-30T10:00:00Z
TS = 1_782_813_600_000


def a_datum(provenance="running", cycle_mark=2, floor_tag=6, ts=TS) -> TaggedDatum:
    return TaggedDatum(
        payload={"v": 1},
        fixed=FixedTags(timestamp=ts, cycle_mark=cycle_mark, provenance=provenance, floor_tag=floor_tag),
        open=dict(TAGS),
    )


class SubstrateClaim(unittest.TestCase):
    def setUp(self) -> None:
        self.root = str(Path(tempfile.mkdtemp()))

    def test_claiming_a_fresh_substrate_lays_out_three_kinds_and_writes_the_claim(self) -> None:
        layout = claim_substrate(self.root)
        for path in (layout.memory, layout.event_log, layout.commits):
            self.assertTrue(Path(path).is_dir(), f"{path} should exist")
        stored = json.loads(Path(layout.claim_file).read_text(encoding="utf-8"))
        self.assertEqual(stored["protocol"], DIL_CLAIM["protocol"])
        self.assertEqual(stored["tagSchema"], DIL_CLAIM["tagSchema"])
        self.assertEqual(stored["layout"], DIL_CLAIM["layout"])
        self.assertIn("claimedAt", stored)

    def test_layout_for_resolves_canonical_paths_under_store(self) -> None:
        layout = layout_for(self.root)
        self.assertTrue(layout.memory.endswith(str(Path("store") / "memory")))
        self.assertTrue(layout.event_log.endswith(str(Path("store") / "event-log")))
        self.assertTrue(layout.commits.endswith(str(Path("store") / "commits")))
        self.assertTrue(layout.claim_file.endswith(str(Path("store") / "DIL-CLAIM.json")))
        self.assertFalse(Path(layout.memory).exists(), "layout_for does no I/O")

    def test_resuming_with_a_matching_claim_is_accepted_and_not_rewritten(self) -> None:
        layout = claim_substrate(self.root)
        first = Path(layout.claim_file).read_text(encoding="utf-8")
        claim_substrate(self.root)
        self.assertEqual(Path(layout.claim_file).read_text(encoding="utf-8"), first)

    def test_resuming_with_a_foreign_claim_is_refused(self) -> None:
        layout = claim_substrate(self.root)
        Path(layout.claim_file).write_text(
            json.dumps({**DIL_CLAIM, "protocol": "9.9.9"}), encoding="utf-8"
        )
        with self.assertRaises(SubstrateClaimError) as caught:
            claim_substrate(self.root)
        self.assertIn("foreign/incompatible", str(caught.exception))

    def test_a_corrupt_claim_is_refused_rather_than_run(self) -> None:
        layout = claim_substrate(self.root)
        Path(layout.claim_file).write_text("{not json", encoding="utf-8")
        with self.assertRaises(SubstrateClaimError) as caught:
            claim_substrate(self.root)
        self.assertIn("corrupt", str(caught.exception))

    def test_a_pre_versioning_tag_schema_is_refused(self) -> None:
        layout = claim_substrate(self.root)
        Path(layout.claim_file).write_text(
            json.dumps({**DIL_CLAIM, "tagSchema": 1}), encoding="utf-8"
        )
        with self.assertRaises(SubstrateClaimError) as caught:
            claim_substrate(self.root)
        self.assertIn("pre-versioning", str(caught.exception))

    def test_a_newer_tag_schema_is_refused(self) -> None:
        layout = claim_substrate(self.root)
        Path(layout.claim_file).write_text(
            json.dumps({**DIL_CLAIM, "tagSchema": DIL_CLAIM["tagSchema"] + 1}), encoding="utf-8"
        )
        with self.assertRaises(SubstrateClaimError) as caught:
            claim_substrate(self.root)
        self.assertIn("newer than", str(caught.exception))


class SqliteDataStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = create_sqlite_data_store(":memory:")

    def tearDown(self) -> None:
        self.store.close()

    def test_put_get_round_trips_a_full_tagged_datum(self) -> None:
        d = a_datum()
        self.store.put("a", d)
        self.assertEqual(self.store.get("a"), d)

    def test_put_overwrites_and_has_delete_clear_size(self) -> None:
        self.store.put("a", a_datum())
        self.store.put("a", a_datum(floor_tag=8))
        self.assertEqual(self.store.size(), 1)
        self.assertEqual(self.store.get("a").fixed.floor_tag, 8)
        self.assertTrue(self.store.has("a"))
        self.assertTrue(self.store.delete("a"))
        self.assertFalse(self.store.delete("a"))
        self.store.put("b", a_datum())
        self.store.clear()
        self.assertEqual(self.store.size(), 0)

    def test_entries_preserves_insertion_order_across_updates(self) -> None:
        for key in ("a", "b", "c"):
            self.store.put(key, a_datum())
        self.store.put("a", a_datum(floor_tag=7))  # update must not move the row
        self.assertEqual([k for k, _ in self.store.entries()], ["a", "b", "c"])

    def test_get_on_a_missing_key_is_none(self) -> None:
        self.assertIsNone(self.store.get("nope"))


class DisplayName(unittest.TestCase):
    def test_renders_fixed_layer_then_keyed_open_tags_domain_first(self) -> None:
        self.assertEqual(
            display_name(a_datum()),
            "[20260630]_[10:00:00]_[c2]_[running]_[T6]"
            "_[domain:financial]_[currency:VND]_[object:revenue]",
        )

    def test_a_prior_renders_its_null_cycle_mark_as_c_dash(self) -> None:
        self.assertIn("_[c-]_", display_name(a_datum(provenance="prior", cycle_mark=None)))

    def test_open_keys_are_preserved_in_the_name(self) -> None:
        name = display_name(a_datum())
        for key in TAGS:
            self.assertIn(f"[{key}:", name)

    def test_the_name_is_derived_not_stored(self) -> None:
        d = a_datum()
        before = display_name(d)
        after = display_name(stamp_layer(d, 8))
        self.assertNotEqual(before, after)
        self.assertIn("_[T8]_", after)
        self.assertEqual(display_name(d), before, "the datum itself did not rename")

    def test_event_display_name_uses_the_scars_tags_plus_the_mismatch_kind(self) -> None:
        scar = a_datum(provenance="scar")
        rec = record_scar(scar, ResistEvent("s", 1, 2, "absence", 3), ContextAnchor(2))
        self.assertEqual(event_display_name(rec), f"{display_name(scar)}_[absence]")


class Inspector(unittest.TestCase):
    def test_inspect_data_renders_a_header_count_and_one_line_per_datum(self) -> None:
        store = create_data_store()
        store.put("d1", a_datum())
        store.put("d2", a_datum())
        out = inspect_data(store).split("\n")
        self.assertEqual(out[0], "[data] — 2 item(s)")
        self.assertEqual(len(out), 3)
        self.assertIn("d1", out[1])

    def test_inspect_data_shows_the_present_floor_tag_and_carries_no_path(self) -> None:
        store = create_data_store()
        store.put("d1", stamp_layer(a_datum(floor_tag=1), 7))
        out = inspect_data(store)
        self.assertIn("_[T7]_", out)
        self.assertNotIn("_[T1]_", out)

    def test_inspect_event_log_renders_records_with_their_derived_names(self) -> None:
        log = create_event_log()
        log.append(record_scar(a_datum(provenance="scar"), ResistEvent("s", 1, 2, "value-mismatch", 3), ContextAnchor(2)))
        out = inspect_event_log(log).split("\n")
        self.assertEqual(out[0], "[event-log] — 1 record(s)")
        self.assertIn("[value-mismatch]", out[1])
        self.assertIn("1→2", out[1])

    def test_inspect_event_log_renders_lean_layer_exit_and_provenance_lines(self) -> None:
        log = create_event_log()
        log.append(record_layer_exit("cycle-1", 1, 3, TS))
        log.append(record_provenance("cycle-1", 1, "running", "scar", TS))
        out = inspect_event_log(log)
        self.assertIn("[layer-exit] cycle-1 @T3 (c1)", out)
        self.assertIn("[provenance] cycle-1 running→scar (c1)", out)

    def test_inspecting_does_not_mutate_the_store(self) -> None:
        store = create_data_store()
        store.put("d1", a_datum())
        log = create_event_log()
        log.append(record_layer_exit("cycle-1", 1, 3, TS))
        before_data = store.entries()
        before_log = log.all()
        inspect_data(store)
        inspect_event_log(log)
        self.assertEqual(store.entries(), before_data)
        self.assertEqual(log.all(), before_log)
        self.assertEqual(store.size(), 1)
        self.assertEqual(log.size(), 1)


if __name__ == "__main__":
    unittest.main()
