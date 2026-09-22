"""Smoke test — the precondition gate.

The fixed check this stage must satisfy: a non-qualifying host declaration yields
a *clean non-start*, not a degraded run. These cases pin that down condition by
condition, plus the two design properties that bite:
  - P(b) is E3 restated (a store that does not persist fails both);
  - the gate evaluates all conditions before deciding (no short-circuit).

Ported case for case from dil-core's gate.test.ts.
"""

import unittest
from dataclasses import replace

from dil.host import (
    BoundaryDeclaration,
    ChannelDeclaration,
    EmitterDeclaration,
    HostDeclaration,
    ResilienceDeclaration,
    StoreDeclaration,
    TraceDeclaration,
)
from dil.precondition import GateResult, NonStart, Qualify, check_precondition


def valid_host() -> HostDeclaration:
    """A fully valid host. Bad cases override exactly one field."""
    return HostDeclaration(
        boundary=BoundaryDeclaration(present=True),
        channels=(ChannelDeclaration(id="ch0", can_return=True),),
        store=StoreDeclaration(persists_across_cycles=True),
        trace=TraceDeclaration(externally_readable=True),
        emitter=EmitterDeclaration(can_emit_first_action=True),
        resilience=ResilienceDeclaration(wipes_state_on_mismatch=False),
    )


class WorkingStoreProbe:
    def __init__(self) -> None:
        self.cells: dict[str, str] = {}

    def write(self, key: str, value: str) -> None:
        self.cells[key] = value

    def read(self, key: str) -> str | None:
        return self.cells.get(key)


class LyingStoreProbe(WorkingStoreProbe):
    """Accepts the write and returns something else."""

    def read(self, key: str) -> str | None:
        return "not-the-nonce"


class ThrowingStoreProbe(WorkingStoreProbe):
    def write(self, key: str, value: str) -> None:
        raise RuntimeError("store handle is broken")


class WorkingTraceProbe:
    def __init__(self) -> None:
        self.marks: list[str] = []

    def leave(self, marker: str) -> None:
        self.marks.append(marker)

    def read(self) -> list[str]:
        return list(self.marks)


class SwallowingTraceProbe(WorkingTraceProbe):
    """Accepts the marker and never shows it again."""

    def leave(self, marker: str) -> None:
        pass


class Gate(unittest.TestCase):
    def expect_non_start(self, result: GateResult) -> tuple[str, ...]:
        """Assert non-start and return the failed-condition list."""
        self.assertIsInstance(result, NonStart)
        assert isinstance(result, NonStart)
        return result.failed

    def basis_of(self, result: GateResult, condition: str) -> str:
        return next(c.basis for c in result.checks if c.id == condition)

    # 1 — fully valid host qualifies; every check passed.

    def test_valid_host_qualifies_with_all_checks_passed(self) -> None:
        result = check_precondition(valid_host())
        self.assertIsInstance(result, Qualify)
        self.assertTrue(all(c.passed for c in result.checks))
        self.assertEqual(len(result.checks), 7)

    # One condition at a time.

    def test_missing_boundary_fails_e1(self) -> None:
        host = replace(valid_host(), boundary=BoundaryDeclaration(present=False))
        self.assertIn("E1", self.expect_non_start(check_precondition(host)))

    def test_zero_channels_is_a_void_field(self) -> None:
        host = replace(valid_host(), channels=())
        result = check_precondition(host)
        self.assertIn("E2", self.expect_non_start(result))
        self.assertIn("no channels declared", next(c.detail for c in result.checks if c.id == "E2"))

    def test_all_silent_channels_is_a_void_field(self) -> None:
        host = replace(
            valid_host(),
            channels=(
                ChannelDeclaration(id="a", can_return=False),
                ChannelDeclaration(id="b", can_return=False),
            ),
        )
        self.assertIn("E2", self.expect_non_start(check_precondition(host)))

    def test_one_returning_channel_satisfies_e2_amid_silence(self) -> None:
        host = replace(
            valid_host(),
            channels=(
                ChannelDeclaration(id="a", can_return=False),
                ChannelDeclaration(id="b", can_return=True),
                ChannelDeclaration(id="c", can_return=False),
            ),
        )
        self.assertIsInstance(check_precondition(host), Qualify)

    def test_no_cross_cycle_persistence_fails_both_e3_and_pb(self) -> None:
        host = replace(valid_host(), store=StoreDeclaration(persists_across_cycles=False))
        failed = self.expect_non_start(check_precondition(host))
        self.assertIn("E3", failed)
        self.assertIn("P_b", failed)

    def test_no_externally_readable_trace_fails_e4(self) -> None:
        host = replace(valid_host(), trace=TraceDeclaration(externally_readable=False))
        self.assertIn("E4", self.expect_non_start(check_precondition(host)))

    def test_cannot_emit_a_first_action_fails_pa(self) -> None:
        host = replace(valid_host(), emitter=EmitterDeclaration(can_emit_first_action=False))
        self.assertIn("P_a", self.expect_non_start(check_precondition(host)))

    def test_self_wipe_on_mismatch_fails_pc(self) -> None:
        host = replace(valid_host(), resilience=ResilienceDeclaration(wipes_state_on_mismatch=True))
        self.assertIn("P_c", self.expect_non_start(check_precondition(host)))

    def test_the_gate_evaluates_every_condition_before_deciding(self) -> None:
        # Every condition broken at once: the report must name all of them, not
        # stop at the first.
        host = HostDeclaration(
            boundary=BoundaryDeclaration(present=False),
            channels=(),
            store=StoreDeclaration(persists_across_cycles=False),
            trace=TraceDeclaration(externally_readable=False),
            emitter=EmitterDeclaration(can_emit_first_action=False),
            resilience=ResilienceDeclaration(wipes_state_on_mismatch=True),
        )
        result = check_precondition(host)
        failed = self.expect_non_start(result)
        self.assertEqual(len(result.checks), 7, "all seven are still evaluated")
        for condition in ("E1", "E2", "E3", "E4", "P_a", "P_b", "P_c"):
            self.assertIn(condition, failed)

    # Probe grading.

    def test_without_probe_handles_every_condition_is_declared(self) -> None:
        result = check_precondition(valid_host())
        self.assertTrue(all(c.basis == "declared" for c in result.checks))

    def test_a_working_store_probe_grades_e3_and_pb_probed(self) -> None:
        host = replace(
            valid_host(),
            store=StoreDeclaration(persists_across_cycles=True, probe=WorkingStoreProbe()),
        )
        result = check_precondition(host)
        self.assertIsInstance(result, Qualify)
        self.assertEqual(self.basis_of(result, "E3"), "probed")
        self.assertEqual(self.basis_of(result, "P_b"), "probed")

    def test_evidence_beats_claim_a_failing_store_probe_fails_e3_and_pb(self) -> None:
        host = replace(
            valid_host(),
            store=StoreDeclaration(persists_across_cycles=True, probe=LyingStoreProbe()),
        )
        result = check_precondition(host)
        failed = self.expect_non_start(result)
        self.assertIn("E3", failed)
        self.assertIn("P_b", failed)
        self.assertEqual(self.basis_of(result, "E3"), "probed")

    def test_a_throwing_store_probe_refutes_the_declaration(self) -> None:
        host = replace(
            valid_host(),
            store=StoreDeclaration(persists_across_cycles=True, probe=ThrowingStoreProbe()),
        )
        result = check_precondition(host)
        self.assertIn("E3", self.expect_non_start(result))
        detail = next(c.detail for c in result.checks if c.id == "E3")
        self.assertIn("raised", detail)

    def test_a_working_trace_probe_grades_e4_probed(self) -> None:
        host = replace(
            valid_host(),
            trace=TraceDeclaration(externally_readable=True, probe=WorkingTraceProbe()),
        )
        result = check_precondition(host)
        self.assertIsInstance(result, Qualify)
        self.assertEqual(self.basis_of(result, "E4"), "probed")

    def test_a_trace_probe_whose_marker_cannot_be_read_back_fails_e4(self) -> None:
        host = replace(
            valid_host(),
            trace=TraceDeclaration(externally_readable=True, probe=SwallowingTraceProbe()),
        )
        result = check_precondition(host)
        self.assertIn("E4", self.expect_non_start(result))
        self.assertEqual(self.basis_of(result, "E4"), "probed")

    def test_a_negative_declaration_fails_even_with_a_working_probe(self) -> None:
        host = replace(
            valid_host(),
            store=StoreDeclaration(persists_across_cycles=False, probe=WorkingStoreProbe()),
        )
        result = check_precondition(host)
        self.assertIn("E3", self.expect_non_start(result))
        self.assertEqual(
            self.basis_of(result, "E3"),
            "declared",
            "a momentary round-trip cannot overrule the host's own admission",
        )


if __name__ == "__main__":
    unittest.main()
