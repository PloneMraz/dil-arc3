"""The diversity-loss monitor (protocol §11, conformance criterion 7).

A conforming implementation MUST emit the diversity-loss signal when its
resistance-source set loses diversity. Over a sliding window of cycles, if the
distinct resistance sources fall below a minimum, the signal fires. This catches
single-source domination — a Sybil-ish external flood, §11 — and resistance
depletion, the Mode-A collapse risk. The cure lives outside the loop; the
protocol carries only this early signal.

Thresholds are DECIDE@IMPL (decisions.py), declared as tunable.

**Worth knowing before the conformance table is written**: an agent playing one
ARC-AGI-3 game at a time has one resistance source, so this signal will fire and
criterion 7 will render `partial` — as it does in dil-core for the same reason.

Ported from dil-core, first against DIL protocol v0.3.3 (the package
implements `dil.DIL_PROTOCOL_VERSION`).
"""

from collections.abc import Sequence

from .decisions import DIVERSITY_WINDOW, MIN_DIVERSITY_SOURCES


class DiversityMonitor:
    """A sliding window over the resistance sources each cycle produced."""

    __slots__ = ("_window", "_min_sources", "_recent")

    def __init__(self, window: int | None = None, min_sources: int | None = None) -> None:
        self._window = window if window is not None else DIVERSITY_WINDOW
        self._min_sources = (
            min_sources if min_sources is not None else MIN_DIVERSITY_SOURCES
        )
        self._recent: list[list[str]] = []

    def observe(self, sources: Sequence[str]) -> None:
        """Record the distinct resistance sources observed in a cycle."""
        self._recent.append(list(dict.fromkeys(sources)))
        while len(self._recent) > self._window:
            self._recent.pop(0)

    def diversity_lost(self) -> bool:
        """Whether diversity has been lost over the current window."""
        if len(self._recent) < self._window:
            return False  # not enough history yet
        distinct = {s for cycle_sources in self._recent for s in cycle_sources}
        return len(distinct) < self._min_sources

    def signal(self) -> str | None:
        """The diversity-loss signal string, or None if diversity is intact."""
        if not self.diversity_lost():
            return None
        return (
            f"diversity-loss: fewer than {self._min_sources} distinct resistance "
            f"sources over {self._window} cycles"
        )


def create_diversity_monitor(
    window: int | None = None, min_sources: int | None = None
) -> DiversityMonitor:
    return DiversityMonitor(window=window, min_sources=min_sources)
