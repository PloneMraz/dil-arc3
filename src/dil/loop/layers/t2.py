"""T2 — Agency Differentiation (protocol §6.3, §7).

Builds the self-written versus environment-pushed distinction by matching what
the agent just emitted against the observed change. This is where the
self/environment difference is FIRST drawn and the from-within standpoint begins
— the crystallization of §7. The self is the consequence of T2 running, not a
thing built here; this module makes no claim of self-continuity, which is
forbidden.

State accrues across cycles (INV-5): the matching window and the cycle counter
accumulate, they are never reloaded. Postcondition (INV-6): once sufficient
matching cycles have run, nothing leaves UNDECIDED — enforced on the output.

MATCHING_WINDOW and STABILITY_THRESHOLD are DECIDE@IMPL tag B, declared in
decisions.py.

Ported from dil-core against DIL protocol v0.3.3.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field as dc_field
from typing import Any

from ...invariants.guards import assert_agency_classified
from ...invariants.types import AgencyTag, Change
from ..decisions import MATCHING_WINDOW, STABILITY_THRESHOLD
from ..layer import BaseLayer, ContributeFn, EmitFn
from ..types import ActivityEnvironment, ModField


@dataclass(frozen=True, slots=True)
class Emission:
    """What the agent emitted this cycle."""

    action: object


@dataclass(frozen=True, slots=True)
class ObservedChange:
    """A change observed in the region after the emission."""

    id: str
    value: object


@dataclass(frozen=True, slots=True)
class TaggedChange:
    """A change with its agency classification."""

    change: ObservedChange
    agency: AgencyTag


@dataclass(frozen=True, slots=True)
class T2Input:
    env: ActivityEnvironment
    emitted: Emission
    changes: tuple[ObservedChange, ...] = dc_field(default_factory=tuple)
    # The actions layers emitted laterally last cycle (§6.4) — a T3 query, a T5
    # test. Every emission "MUST be readable by T2 at the next cycle as 'the
    # action just emitted'", not only the committed response; without these,
    # what a query brought back could never be matched to the query (INV-6).
    lateral: tuple[object, ...] = dc_field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class T2Output:
    tagged: tuple[TaggedChange, ...]
    # True on the ONE run where T2 first draws the self/environment distinction —
    # the crystallization of §7, where the from-within standpoint begins. It
    # marks the *act* of distinguishing, not the self's persistence; a resumed T2,
    # restored with an accrued cycle count, has already crystallized and never
    # re-signals.
    crystallized: bool


def _json_equal(a: object, b: object) -> bool:
    """Default match: structural equality. A chosen representation, overridable.

    `default=str` keeps a value the reference would have serialised happily from
    raising here; JSON.stringify never throws on an unserialisable value, it
    drops or stringifies it, and a match test must not halt the loop.
    """
    return json.dumps(a, sort_keys=True, default=str) == json.dumps(
        b, sort_keys=True, default=str
    )


class T2(BaseLayer):
    index = 2
    consumes: tuple[int, ...] = (1,)

    def __init__(
        self,
        window: int | None = None,
        stability_threshold: int | None = None,
        matches: Callable[[object, object], bool] | None = None,
    ) -> None:
        self._window = window if window is not None else MATCHING_WINDOW
        self._stability = (
            stability_threshold if stability_threshold is not None else STABILITY_THRESHOLD
        )
        self._matches = matches if matches is not None else _json_equal
        # Accruing state (INV-5): accumulated, never reloaded.
        self._recent_emissions: list[object] = []
        self._cycles_run = 0

    # §9 snapshot surface; `restore` is recovery-only (see Snapshottable).

    def snapshot(self) -> dict[str, Any]:
        return {
            "recentEmissions": list(self._recent_emissions),
            "cyclesRun": self._cycles_run,
        }

    def restore(self, state: Any) -> None:
        self._recent_emissions = list(state["recentEmissions"])
        self._cycles_run = state["cyclesRun"]

    def process(  # noqa: A002
        self,
        input: T2Input,
        field: ModField,
        emit: EmitFn,
        contribute: ContributeFn,
    ) -> T2Output:
        # The crystallization of §7: T2 first drawing the self/environment
        # distinction. Zero cycles run is true only on the very first run — after
        # recovery it is false, because a restored count means the self already
        # crystallized in the line being resumed.
        crystallized = self._cycles_run == 0

        # Accrue this cycle's emission into the bounded matching window.
        self._recent_emissions.append(input.emitted.action)
        self._recent_emissions.extend(input.lateral)
        while len(self._recent_emissions) > self._window:
            self._recent_emissions.pop(0)
        self._cycles_run += 1

        stable = self._cycles_run >= self._stability

        tagged: list[TaggedChange] = []
        for change in input.changes:
            if not stable:
                # The self/environment line is not yet trusted.
                agency: AgencyTag = "UNDECIDED"
            elif any(self._matches(a, change.value) for a in self._recent_emissions):
                agency = "SELF_WRITTEN"
            else:
                agency = "ENV_PUSHED"
            tagged.append(TaggedChange(change=change, agency=agency))

        return T2Output(tagged=tuple(tagged), crystallized=crystallized)

    def post(self, output: T2Output) -> None:
        # INV-6 postcondition: once stable, nothing leaves UNDECIDED.
        if self._cycles_run >= self._stability:
            for t in output.tagged:
                assert_agency_classified(Change(agency=t.agency))

    def info_units(self, output: Any) -> Sequence[Any]:
        return ()


def create_t2(
    window: int | None = None,
    stability_threshold: int | None = None,
    matches: Callable[[object, object], bool] | None = None,
) -> T2:
    return T2(window=window, stability_threshold=stability_threshold, matches=matches)
