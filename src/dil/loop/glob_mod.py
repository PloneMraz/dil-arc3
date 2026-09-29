"""GLOB-MOD — the modulatory field (protocol §5 INV-7, §6.2).

A single background state reaching every layer field-to-layer: each layer reads
it as the disposition with which it reads its input, and contributes to it as one
competing parameter. It carries *how to read* — gains and biases — never *what is
read*.

The update law is declared in decisions.py: a convex per-key weighted average of
a cycle's contributions, untouched keys carrying over, taking effect at N+1. Two
structural guarantees:

  - **N+1, never within-cycle.** Contributions land in a pending buffer; the
    active field changes only at `advance()`, which routes through
    `assert_glob_mod_update` and halts on last-write or a within-cycle effect.
  - **No runaway by construction.** A convex combination of the contributions is
    always within their range, so the field cannot amplify itself from within.
    INV-7's note: no gain cap is needed.

Ported from dil-core, first against DIL protocol v0.3.3 (the package
implements `dil.DIL_PROTOCOL_VERSION`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType

from ..invariants.guards import assert_glob_mod_update
from ..invariants.types import GlobModUpdate, LayerIndex
from .types import ModField


class GlobModError(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(f"GLOB-MOD: {detail}")


@dataclass(frozen=True, slots=True)
class Contribution:
    """One layer's contribution to the field for the current cycle."""

    layer: LayerIndex
    params: dict[str, float]
    weight: float


def _sealed_field(params: dict[str, float], t: int) -> ModField:
    """Seal a params map so an active field cannot be mutated within its cycle.

    The reference calls Object.freeze; a MappingProxyType over a private copy is
    the closest Python offers — the copy means no caller holds a writable
    reference to it, and the proxy refuses writes through the field itself.
    """
    return ModField(params=MappingProxyType(dict(params)), t=t)  # type: ignore[arg-type]


def _blend(
    prev: dict[str, float], contributions: list[Contribution]
) -> dict[str, float]:
    """Convex per-key weighted average of the contributions, over the previous params.

    Keys with positive total weight get Σ(wᵢ·vᵢ)/Σ(wᵢ); every other key carries
    over unchanged.
    """
    weighted_sum: dict[str, float] = {}
    weight_total: dict[str, float] = {}
    for c in contributions:
        for key, value in c.params.items():
            weighted_sum[key] = weighted_sum.get(key, 0.0) + c.weight * value
            weight_total[key] = weight_total.get(key, 0.0) + c.weight

    nxt = dict(prev)
    for key, total in weight_total.items():
        if total > 0:
            nxt[key] = weighted_sum[key] / total
    return nxt


class GlobMod:
    """The modulatory field and its pending contributions."""

    __slots__ = ("_field", "_cycle", "_pending")

    def __init__(self, initial_params: dict[str, float] | None = None, cycle: int = 0) -> None:
        self._field = _sealed_field(dict(initial_params or {}), cycle)
        self._cycle = cycle
        self._pending: list[Contribution] = []

    def current(self) -> ModField:
        """The active field this cycle — immutable within the cycle."""
        return self._field

    def cycle(self) -> int:
        """The cycle the active field belongs to."""
        return self._cycle

    def contribute(
        self, layer: LayerIndex, params: dict[str, float], weight: float
    ) -> None:
        """A layer competes for one or more param keys this cycle.

        Recorded into the pending buffer; does NOT change the active field.
        """
        if not math.isfinite(weight) or weight < 0:
            raise GlobModError(
                "contribution weight must be finite and non-negative (convexity), "
                f"got {weight}"
            )
        self._pending.append(
            Contribution(layer=layer, params=dict(params), weight=weight)
        )

    def advance(self, next_cycle: int) -> ModField:
        """Close the cycle.

        Blend the pending contributions into the field for `next_cycle`, which
        MUST be later than the current cycle, clear pending, and return the new
        active field.
        """
        # INV-7: blend (never last-write) and take effect strictly later (N+1).
        assert_glob_mod_update(
            GlobModUpdate(
                mode="blend",
                contrib_cycle=self._cycle,
                effect_cycle=next_cycle,
            )
        )
        self._field = _sealed_field(_blend(dict(self._field.params), self._pending), next_cycle)
        self._cycle = next_cycle
        self._pending = []
        return self._field

    def restore(self, params: dict[str, float], at_cycle: int) -> None:
        """RECOVERY-ONLY: re-instate a field state this loop previously accrued.

        Not a within-cycle operation — INV-7's N+1 rule governs cycle
        advancement, not full-system recovery. Pending contributions are cleared.
        """
        self._field = _sealed_field(dict(params), at_cycle)
        self._cycle = at_cycle
        self._pending = []


def create_glob_mod(
    initial_params: dict[str, float] | None = None, cycle: int = 0
) -> GlobMod:
    return GlobMod(initial_params, cycle)
