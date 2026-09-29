"""The precondition gate — check before the king sits down.

Before DIL starts, it checks whether the host can be reigned over at all. If the
host does not qualify → a *clean non-start* (protocol §4): report the reason, do
nothing further. Not a half-running degraded DIL. Presiding over a room of the
unresponsive is no reign.

Every check here is static — answerable purely by reading the host declaration,
before the loop runs. The gate evaluates all conditions, so the report is
complete, and then decides: pass all → qualify; fail any → non-start.

This module is intentionally independent of the loop, the store, and the
invariants.

Ported from dil-core, first against DIL protocol v0.3.3 (the package
implements `dil.DIL_PROTOCOL_VERSION`).
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Literal, TypeAlias

from ..host import HostDeclaration
from .decisions import PROBE_NONCE_PREFIX

# The seven structural conditions of protocol §4.
ConditionId: TypeAlias = Literal["E1", "E2", "E3", "E4", "P_a", "P_b", "P_c"]

# How a condition's verdict was reached:
#   `probed`   — the gate exercised a host-declared handle and observed the result
#   `declared` — the gate read the host's declaration (the designed mechanism of
#                requisition; graded honestly rather than dressed up as a
#                measurement)
ConditionBasis: TypeAlias = Literal["declared", "probed"]


@dataclass(frozen=True, slots=True)
class ConditionResult:
    id: ConditionId
    passed: bool
    # How this verdict was reached.
    basis: ConditionBasis
    # Human-readable account of why this condition passed or failed.
    detail: str


@dataclass(frozen=True, slots=True)
class Qualify:
    checks: tuple[ConditionResult, ...]
    outcome: Literal["qualify"] = "qualify"


@dataclass(frozen=True, slots=True)
class NonStart:
    checks: tuple[ConditionResult, ...]
    failed: tuple[ConditionId, ...]
    reason: str
    outcome: Literal["non-start"] = "non-start"


GateResult: TypeAlias = Qualify | NonStart


def _probe_nonce() -> str:
    """A per-run nonce so a stale value or an echoing handle cannot fake a pass."""
    return f"{PROBE_NONCE_PREFIX}:{int(time.time() * 1000)}:{secrets.token_hex(8)}"


def _check_e1(host: HostDeclaration) -> ConditionResult:
    """E1 — Differentiability."""
    passed = host.boundary.present
    return ConditionResult(
        id="E1",
        passed=passed,
        basis="declared",
        detail=(
            "boundary present: an internal/external distinction can be drawn"
            if passed
            else "no boundary: nothing affords an internal/external distinction"
        ),
    )


def _check_e2(host: HostDeclaration) -> ConditionResult:
    """E2 — Interaction.

    At least one channel can return something other than silence. Zero channels,
    or all channels silent, is a void field.
    """
    returning = [c for c in host.channels if c.can_return]
    passed = len(returning) >= 1
    if passed:
        detail = (
            f"{len(returning)} of {len(host.channels)} channel(s) can return a "
            "non-silent response"
        )
    elif len(host.channels) == 0:
        detail = "void field: no channels declared"
    else:
        detail = "void field: no declared channel can return anything other than silence"
    return ConditionResult(id="E2", passed=passed, basis="declared", detail=detail)


def _check_e3(host: HostDeclaration) -> tuple[bool, ConditionBasis, str]:
    """E3 — Temporal accumulation.

    When the host declares a store probe handle, the gate performs a marker
    round-trip: evidence beats claim — a failed or throwing probe fails the
    condition even if declared true. A negative declaration fails regardless: a
    momentary round-trip cannot overrule the host's own admission about its
    across-cycle behaviour.
    """
    if not host.store.persists_across_cycles:
        return (False, "declared", "no cross-cycle persistence: history cannot accrue")

    probe = host.store.probe
    if probe is None:
        return (
            True,
            "declared",
            "state persists across cycles: history can accrue (declared; no probe handle)",
        )

    try:
        nonce = _probe_nonce()
        probe.write("__dil_probe_e3__", nonce)
        back = probe.read("__dil_probe_e3__")
    except Exception as exc:  # noqa: BLE001 — any host failure refutes the claim
        return (
            False,
            "probed",
            f"probe refuted the declaration: store handle raised ({exc})",
        )

    if back == nonce:
        return (True, "probed", "marker round-trip held through the declared store handle")
    return (
        False,
        "probed",
        "probe refuted the declaration: wrote a nonce, read back "
        + ("nothing" if back is None else "a different value"),
    )


def _check_e4(host: HostDeclaration) -> ConditionResult:
    """E4 — Observable projection.

    When the host declares a trace probe handle, the gate leaves a marker and
    reads the trace back for it; same evidence-beats-claim rules as E3.
    """
    if not host.trace.externally_readable:
        return ConditionResult(
            id="E4",
            passed=False,
            basis="declared",
            detail="actions leave no externally readable trace",
        )

    probe = host.trace.probe
    if probe is None:
        return ConditionResult(
            id="E4",
            passed=True,
            basis="declared",
            detail="actions leave an externally readable trace (declared; no probe handle)",
        )

    try:
        nonce = _probe_nonce()
        probe.leave(nonce)
        found = nonce in probe.read()
    except Exception as exc:  # noqa: BLE001
        return ConditionResult(
            id="E4",
            passed=False,
            basis="probed",
            detail=f"probe refuted the declaration: trace handle raised ({exc})",
        )

    return ConditionResult(
        id="E4",
        passed=found,
        basis="probed",
        detail=(
            "marker left through the declared trace handle and read back externally"
            if found
            else "probe refuted the declaration: the left marker was not readable back"
        ),
    )


def _check_pa(host: HostDeclaration) -> ConditionResult:
    """P(a) — emission: capacity to emit a first action."""
    passed = host.emitter.can_emit_first_action
    return ConditionResult(
        id="P_a",
        passed=passed,
        basis="declared",
        detail=(
            "host can emit a first action at cycle-0"
            if passed
            else "host cannot emit a first action: T2 never rises to FIRST"
        ),
    )


def _check_pc(host: HostDeclaration) -> ConditionResult:
    """P(c) — no self-wipe on mismatch, else no scar survives."""
    passed = not host.resilience.wipes_state_on_mismatch
    return ConditionResult(
        id="P_c",
        passed=passed,
        basis="declared",
        detail=(
            "host does not wipe its state on mismatch: scars can survive"
            if passed
            else "self-wipe defect: host resets on every mismatch, no scar survives"
        ),
    )


def check_precondition(host: HostDeclaration) -> GateResult:
    """Run the precondition gate over a host declaration.

    Evaluates all seven conditions, then decides. Pass all → qualify (the king
    sits, the loop may start). Fail any → non-start, with the failing condition
    ids and a reason assembled from their details.
    """
    # P(b) is E3 restated for bootstrap: it inherits the same outcome — and the
    # same probe evidence — rather than re-deriving it.
    e3_passed, e3_basis, e3_detail = _check_e3(host)

    checks: tuple[ConditionResult, ...] = (
        _check_e1(host),
        _check_e2(host),
        ConditionResult(id="E3", passed=e3_passed, basis=e3_basis, detail=e3_detail),
        _check_e4(host),
        _check_pa(host),
        ConditionResult(
            id="P_b",
            passed=e3_passed,
            basis=e3_basis,
            detail=(
                "host holds state across cycles for bootstrap accrual (INV-5) — "
                f"{e3_basis}"
                if e3_passed
                else f"bootstrap accrual impossible: {e3_detail}"
            ),
        ),
        _check_pc(host),
    )

    failed_checks = [c for c in checks if not c.passed]

    if not failed_checks:
        return Qualify(checks=checks)

    reason = "host does not qualify; clean non-start. Failed: " + "; ".join(
        f"{c.id} ({c.detail})" for c in failed_checks
    )
    return NonStart(
        checks=checks,
        failed=tuple(c.id for c in failed_checks),
        reason=reason,
    )
