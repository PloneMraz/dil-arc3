"""The loop topology (protocol §6.2, INV-1).

The canonical loop is six links over eight layers closing into a cycle: T1→T2→…
→T8, and T8 back to T1. INV-1 requires every layer output to have a path back to
some layer's input — no dead branches, no terminal sink. T8 closes back into the
loop, not into a sink.

Ported from dil-core, first against DIL protocol v0.3.3 (the package
implements `dil.DIL_PROTOCOL_VERSION`).
"""

from ..invariants.guards import assert_closed_loop
from ..invariants.types import LoopEdge


def canonical_loop_topology() -> list[LoopEdge]:
    """The canonical T1→T8→T1 closed-loop edge set."""
    return [
        LoopEdge(1, 2),
        LoopEdge(2, 3),
        LoopEdge(3, 4),
        LoopEdge(4, 5),
        LoopEdge(5, 6),
        LoopEdge(6, 7),
        LoopEdge(7, 8),
        LoopEdge(8, 1),  # closes the loop (INV-1) — not a sink
    ]


def validate_loop_topology(edges: list[LoopEdge]) -> None:
    """INV-1: validate the topology closes; halts on any dead branch or sink."""
    assert_closed_loop(edges)
