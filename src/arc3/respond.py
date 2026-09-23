"""How the self commits an action — the host's declared RespondPolicy.

Under the settled reading the loop holds an expectation per affordance, so the
action worth committing is **the one whose expectation is least resolved**. That
is not exploration bolted on beside a policy; it is the only thing the loop's own
state recommends, and it is where "the self picks which expectation is worth
testing" becomes code.

Where this sits matters. The policy runs at the close of the meaning-channel,
after appraisal, issuing layer T8 — so the action issues from the whole loop, not
from the thinking layer. No layer chooses the move.

**The policy accrues its own record** of how resolved each affordance is, one
cycle at a time, from what T5 published that cycle. It never reads T5's internal
state and never reloads a history: an affordance it has not met has no entry, and
an affordance it has met carries the confidence T5 last reported. That is INV-5
accrual in the host's own ring.
"""

from __future__ import annotations

from typing import Any, Final

from dil.loop.cycle import RespondContext

from .action import COMPLEX_ACTION, RESET, Move
from .frame import TERMINAL_STATES
from .observe import move_value

# Confidence assumed for an affordance the policy has never met. Zero, so an
# untried action outranks every tried one: the loop reaches for what it does not
# know before what it does.
UNMET_CONFIDENCE: Final = 0.0


def _payload(ctx: RespondContext) -> dict[str, Any] | None:
    for signal in ctx.host.signals:
        if isinstance(signal.raw_payload, dict):
            return signal.raw_payload
    return None


def _state(ctx: RespondContext) -> str:
    """The state the region is in now, read off the effect it just reported."""
    for signal in ctx.host.signals:
        payload = signal.raw_payload
        if isinstance(payload, dict):
            status = payload.get("status")
            if isinstance(status, dict):
                state = status.get("stateTo")
                if isinstance(state, str):
                    return state
    return ""


def _affords(ctx: RespondContext) -> tuple[int, ...]:
    """What the region says it offers NEXT, read off its own report.

    Not `ctx.host.afforded` — that set is what was afforded when the move being
    answered was chosen, which is what T7 needs for absence. The move about to be
    committed answers the frame that just arrived, so it reads `affords` from the
    signal the region sent.
    """
    for signal in ctx.host.signals:
        payload = signal.raw_payload
        if isinstance(payload, dict):
            affords = payload.get("affords")
            if isinstance(affords, list) and affords:
                return tuple(int(a) for a in affords)
    return ()


class LeastResolved:
    """Commit the afforded action whose expectation is least resolved.

    Ties break on the fewest observations, then on the lowest action id, so the
    policy is deterministic: the same accrued state and the same frame commit the
    same move. A run is reproducible and a third party can replay it.
    """

    __slots__ = ("_confidence", "_seen", "_coords", "_sweeps")

    def __init__(self, coords: tuple[tuple[int, int], ...] | None = None) -> None:
        # Accrued, never loaded: what the loop has reported about each
        # affordance so far.
        self._confidence: dict[str, float] = {}
        self._seen: dict[str, float] = {}
        # ACTION6 takes (x, y), and under this reading coordinates are CONTEXT,
        # not identity — so the loop holds no expectation about any particular
        # square and has no basis to prefer one. DECLARED LIMIT: they are swept
        # deterministically, which is not a choice the self makes. A host that
        # needs to aim has to give the loop something to aim with, and that is
        # not settled.
        self._coords = coords if coords is not None else DEFAULT_SWEEP
        self._sweeps = 0

    def __call__(self, ctx: RespondContext) -> Any:
        # Accrue what the loop published this cycle.
        for result in ctx.expectations:
            self._confidence[result.entity_id] = result.expectation.confidence
            self._seen[result.entity_id] = result.expectation.recurrence

        # MEASURED: `vc33` goes GAME_OVER and KEEPS reporting
        # available_actions == (6,). Stepping that action in a terminal state
        # returns an empty frame, which the boundary gate then refuses — which is
        # how this was found. So the state, not the afforded list, decides here:
        # from a terminal frame the only act that changes anything is RESET.
        if _state(ctx) in TERMINAL_STATES:
            return move_value(Move(RESET))

        affords = _affords(ctx)
        if not affords:
            # Nothing is offered: the frame is terminal, and RESET is how a
            # terminal frame is left. Still a committed action, register ↔.
            return move_value(Move(RESET))

        def rank(action_id: int) -> tuple[float, float, int]:
            key = f"action:{action_id}"
            return (
                self._confidence.get(key, UNMET_CONFIDENCE),
                self._seen.get(key, 0.0),
                action_id,
            )

        action_id = min(affords, key=rank)
        if action_id == COMPLEX_ACTION:
            x, y = self._coords[self._sweeps % len(self._coords)]
            self._sweeps += 1
            return move_value(Move(COMPLEX_ACTION, x=x, y=y))
        return move_value(Move(action_id))


def _sweep() -> tuple[tuple[int, int], ...]:
    """A coarse deterministic sweep of the grid for ACTION6.

    Declared arbitrary. It exists so the agent is not stuck clicking one square
    when a game affords nothing else, and it carries no claim of being a good
    place to click.
    """
    step = 8
    return tuple((x, y) for y in range(4, 64, step) for x in range(4, 64, step))


DEFAULT_SWEEP: Final = _sweep()


def least_resolved(coords: tuple[tuple[int, int], ...] | None = None) -> LeastResolved:
    return LeastResolved(coords)
