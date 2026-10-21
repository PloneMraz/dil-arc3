"""Minimal types the invariant guards operate on.

Deliberately narrow: each states only the structure a guard checks. The loop's
full types (`dil.loop.types`, protocol §6.1 — Signal, InfoUnit, AgencyTag,
ModField, …) carry that structure (dil-core 90518dc). They introduce no
thresholds and no DECIDE@IMPL constants; the invariants are structural laws
(protocol §5).

Naming: the reference implementation is TypeScript, so its fields are camelCase.
They are snake_case here because this is Python, and `LoopEdge.from` is spelled
`from_` because `from` is a keyword. Nothing else is renamed — a reader holding
both files open should be able to line them up.
"""

from dataclasses import dataclass
from typing import Literal, TypeAlias

# Layer index on the meaning-channel, T1..T8 (protocol §6.3).
LayerIndex: TypeAlias = Literal[1, 2, 3, 4, 5, 6, 7, 8]

# Output register (protocol §3, INV-2). `↔` is a live, revisable correlation —
# the register of every running output, including action-commitments. `=` is a
# frozen identity claim, which appears only when the loop has stopped.
Register: TypeAlias = Literal["↔", "="]

# Agency classification (protocol §6.1; INV-6).
AgencyTag: TypeAlias = Literal["SELF_WRITTEN", "ENV_PUSHED", "UNDECIDED"]


@dataclass(frozen=True, slots=True)
class RunningOutput:
    """A running output carries an INFO tag and a register (INV-2)."""

    register: Register
    tag: Literal["INFO"] = "INFO"
    note: str | None = None


@dataclass(frozen=True, slots=True)
class Change:
    """A change presented for interpretation must already carry an AgencyTag."""

    agency: AgencyTag
    note: str | None = None


@dataclass(frozen=True, slots=True)
class ReferredUnit:
    """A unit of information; meaning is relational, so ref_frame must be set (INV-4).

    `ref_frame is None` ⇒ not yet information, only a signal.
    """

    content: object
    ref_frame: object | None


@dataclass(frozen=True, slots=True)
class TemporalWrite:
    """A temporal-state write: it either accrues onto prior state or loads it (INV-5)."""

    kind: Literal["accrue", "load"]
    note: str | None = None


@dataclass(frozen=True, slots=True)
class LoopEdge:
    """A directed edge in the loop topology (INV-1). `"SINK"` is a terminal dead end."""

    from_: LayerIndex
    to: LayerIndex | Literal["SINK"]


@dataclass(frozen=True, slots=True)
class GlobModUpdate:
    """A GLOB-MOD field update (INV-7)."""

    # How contributions combine. `last-write` overwrites and is forbidden.
    mode: Literal["blend", "last-write"]
    # Cycle in which a layer's contribution was made.
    contrib_cycle: int
    # Cycle in which that contribution is allowed to condition the field.
    effect_cycle: int


@dataclass(frozen=True, slots=True)
class AppraisalCriteria:
    """The provenance of an appraisal's criteria (INV-8).

    The appraisal step MUST NOT draw criteria from the state the agent is
    editing — self-scoring is hackable.
    """

    # Identifier of where the criteria come from.
    criteria_source: str
    # Identifier of the state the agent is currently editing.
    edited_state: str
