"""InvariantViolation — the halt signal.

The eight invariants (protocol §5) are the absolute conditions of the loop:
"To overwrite one is not to edit a datum but to halt the loop." A step about to
violate an INV MUST halt the loop, not work around it.

Halting is therefore modelled as a raised exception, never a returned boolean a
caller could ignore. The loop, once built, MUST let this propagate as a halt and
MUST NOT catch-and-continue.

Ported from dil-core (TypeScript) against DIL protocol v0.3.3. Where this file
and the protocol disagree, the protocol wins.
"""

from typing import Literal, NoReturn, TypeAlias

InvariantId: TypeAlias = Literal[
    "INV-1", "INV-2", "INV-3", "INV-4", "INV-5", "INV-6", "INV-7", "INV-8"
]


class InvariantViolation(Exception):
    """Raised when a step would violate an invariant. Never caught inside the loop."""

    def __init__(self, invariant: InvariantId, detail: str) -> None:
        super().__init__(f"{invariant} violated: {detail}")
        self.invariant: InvariantId = invariant


def halt(invariant: InvariantId, detail: str) -> NoReturn:
    """Raise the halt signal for a given invariant."""
    raise InvariantViolation(invariant, detail)
