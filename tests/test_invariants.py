"""Smoke test — the eight invariant guards.

The fixed check this ring must satisfy: a step that violates any INV is blocked —
the guard halts (raises InvariantViolation), with no work-around. For each
invariant both halves are asserted: a violating step halts with the right INV id,
and a conforming step passes.

Ported case-for-case from dil-core's guards.test.ts, so the two suites can be
read side by side. Uses unittest from the standard library — no test dependency,
for the same reason the package has no runtime dependency.
"""

import unittest
from collections.abc import Callable

from dil.invariants import (
    AppraisalCriteria,
    Change,
    GlobModUpdate,
    InvariantId,
    InvariantViolation,
    LoopEdge,
    ReferredUnit,
    RunningOutput,
    TemporalWrite,
    assert_accrual,
    assert_agency_classified,
    assert_appraisal_independence,
    assert_closed_loop,
    assert_correlational,
    assert_glob_mod_update,
    assert_meaning_channel_order,
    assert_referred,
)


class InvariantGuards(unittest.TestCase):
    def expect_halt(self, invariant: InvariantId, fn: Callable[[], None]) -> None:
        """Assert that `fn` halts with an InvariantViolation carrying `invariant`."""
        with self.assertRaises(InvariantViolation) as caught:
            fn()
        self.assertEqual(caught.exception.invariant, invariant, f"expected {invariant} halt")

    # INV-1 — Closed loop.

    def test_inv1_halts_on_a_sink(self) -> None:
        self.expect_halt(
            "INV-1",
            lambda: assert_closed_loop([LoopEdge(1, 2), LoopEdge(8, "SINK")]),
        )

    def test_inv1_passes_a_closed_topology(self) -> None:
        # every node is both a source and a target — the cycle closes
        assert_closed_loop([LoopEdge(1, 2), LoopEdge(2, 3), LoopEdge(3, 1)])

    def test_inv1_halts_on_a_dead_end_layer(self) -> None:
        # node 3 receives output (2→3) but never produces onward — a dead branch
        # with no explicit SINK marker
        self.expect_halt(
            "INV-1",
            lambda: assert_closed_loop([LoopEdge(1, 2), LoopEdge(2, 3)]),
        )

    # INV-2 — Output-register identity.

    def test_inv2_halts_when_a_running_output_is_identity(self) -> None:
        self.expect_halt("INV-2", lambda: assert_correlational(RunningOutput(register="=")))

    def test_inv2_passes_a_correlational_output(self) -> None:
        # an action-commitment is still ↔, so it passes
        assert_correlational(RunningOutput(register="↔", note="action-commitment"))

    # INV-3 — One-directional dependency on the meaning-channel.

    def test_inv3_halts_when_consuming_from_a_higher_layer(self) -> None:
        self.expect_halt("INV-3", lambda: assert_meaning_channel_order(3, 5))

    def test_inv3_passes_consuming_from_lower_or_equal(self) -> None:
        assert_meaning_channel_order(5, 3)
        assert_meaning_channel_order(5, 5)

    # INV-4 — Meaning as relation.

    def test_inv4_halts_on_a_null_ref_frame(self) -> None:
        self.expect_halt(
            "INV-4",
            lambda: assert_referred(ReferredUnit(content="x", ref_frame=None)),
        )

    def test_inv4_passes_a_referred_unit(self) -> None:
        assert_referred(ReferredUnit(content="x", ref_frame="T2-context"))

    # INV-5 — History accrues, is not loaded.

    def test_inv5_halts_on_a_loaded_temporal_write(self) -> None:
        self.expect_halt(
            "INV-5",
            lambda: assert_accrual(TemporalWrite(kind="load", note="restored snapshot")),
        )

    def test_inv5_passes_an_accruing_temporal_write(self) -> None:
        assert_accrual(TemporalWrite(kind="accrue"))

    # INV-6 — Agency-gate.

    def test_inv6_halts_interpreting_an_undecided_change(self) -> None:
        self.expect_halt("INV-6", lambda: assert_agency_classified(Change(agency="UNDECIDED")))

    def test_inv6_passes_a_classified_change(self) -> None:
        assert_agency_classified(Change(agency="ENV_PUSHED"))
        assert_agency_classified(Change(agency="SELF_WRITTEN"))

    # INV-7 — GLOB-MOD.

    def test_inv7_halts_on_last_write_wins(self) -> None:
        self.expect_halt(
            "INV-7",
            lambda: assert_glob_mod_update(
                GlobModUpdate(mode="last-write", contrib_cycle=1, effect_cycle=2)
            ),
        )

    def test_inv7_halts_when_effect_is_within_the_contributions_own_cycle(self) -> None:
        self.expect_halt(
            "INV-7",
            lambda: assert_glob_mod_update(
                GlobModUpdate(mode="blend", contrib_cycle=4, effect_cycle=4)
            ),
        )

    def test_inv7_passes_a_blended_update_taking_effect_at_n_plus_1(self) -> None:
        assert_glob_mod_update(GlobModUpdate(mode="blend", contrib_cycle=4, effect_cycle=5))

    # INV-8 — Appraisal step.

    def test_inv8_halts_when_criteria_come_from_the_edited_state(self) -> None:
        self.expect_halt(
            "INV-8",
            lambda: assert_appraisal_independence(
                AppraisalCriteria(criteria_source="draft", edited_state="draft")
            ),
        )

    def test_inv8_passes_when_criteria_are_external(self) -> None:
        assert_appraisal_independence(
            AppraisalCriteria(criteria_source="anchor", edited_state="draft")
        )


class HaltSignal(unittest.TestCase):
    """The halt is an exception, not a returned flag a caller could ignore."""

    def test_violation_carries_its_invariant_and_message(self) -> None:
        with self.assertRaises(InvariantViolation) as caught:
            assert_referred(ReferredUnit(content=None, ref_frame=None))
        self.assertEqual(caught.exception.invariant, "INV-4")
        self.assertIn("INV-4 violated:", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
