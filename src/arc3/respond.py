"""How the self commits an action — the host's declared RespondPolicy.

The action worth committing is **the one whose consequences are least resolved**,
shifted by **how the region has answered it**. Curiosity is the base; want
modulates it rather than replacing it.

Where this sits matters. The policy runs at the close of the meaning-channel,
after appraisal, issuing layer T8 — so the action issues from the whole loop, not
from the thinking layer. No layer chooses the move.

IT READS THE FIELD, AND ONLY THE FIELD. Attention and want are compositions of
context, environment and GLOB-MOD, not constants — so what this policy knows
about each action arrives the way everything else reaches every link: through the
modulatory field. The mind reports, per situation, how well it predicts what
follows (`resolved:action:N`) and how the region has answered it
(`valence:action:N`); the field carries both; the policy composes them. It never
reaches into the mind, and the mind never sees this.

WHAT THIS REPLACED, AND THE REGRESSION THAT FORCED IT. The earlier policy ranked
actions by the confidence T5 held for an entity named `action:N`. When the
entity became a thing rather than an action, no entity was named `action:N` any
more, every action ranked `(0, 0, id)`, and the lowest id won for ever. Measured
on a live `ls20` run: ACTION1, forty times out of forty. The agent pressed the
same key into a wall, and the rebuild's first behaviour figures came from that.
"""

from __future__ import annotations

from typing import Any, Final

from dil.loop.cycle import RespondContext

from .action import COMPLEX_ACTION, RESET, Move
from .frame import TERMINAL_STATES
from .observe import move_value

# Resolution assumed for an action the mind has never reported on. Zero, so an
# untried action outranks every tried one: the loop reaches for what it does not
# know before what it does.
UNMET_RESOLUTION: Final = 0.0

# The field keys the mind reports under. Read as local strings rather than
# imported from the mind: the self takes nothing from the mind but what the field
# carries.
_RESOLVED: Final = "resolved:action:"
_VALENCE: Final = "valence:action:"


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


def compose(resolved: float, valence: float) -> float:
    """Curiosity shifted by want (DECLARED; lower is taken first).

    `resolved` is in [0, 1] and `valence` in [-1, 1], so where the region has
    answered an action at all, its answer outweighs how well that action is
    understood: an action the region ended the game after is avoided however
    unfamiliar it is, and one it rewarded is preferred however familiar. Where the
    region has said nothing (valence 0), curiosity decides alone.
    """
    return resolved - valence


class LeastResolved:
    """Commit the afforded action least resolved, as want shifts it.

    Ties break on how often the self has already committed each action, then on
    the lowest id, so the policy is deterministic: the same field and the same
    frame commit the same move, and a third party can replay a run.
    """

    __slots__ = ("_taken", "_coords", "_sweeps")

    def __init__(self, coords: tuple[tuple[int, int], ...] | None = None) -> None:
        # The self's own record of its acts — accrued, never loaded. Not a
        # reading of the mind: it is what this policy has itself committed.
        self._taken: dict[int, int] = {}
        # ACTION6 takes (x, y), and under this reading coordinates are CONTEXT,
        # not identity — so the loop holds no expectation about any particular
        # square and has no basis to prefer one. DECLARED LIMIT: they are swept
        # deterministically, which is not a choice the self makes. A host that
        # needs to aim has to give the loop something to aim with, and that is
        # not settled.
        self._coords = coords if coords is not None else DEFAULT_SWEEP
        self._sweeps = 0

    def __call__(self, ctx: RespondContext) -> Any:
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

        params = ctx.field.params

        def rank(action_id: int) -> tuple[float, int, int]:
            return (
                compose(
                    params.get(f"{_RESOLVED}{action_id}", UNMET_RESOLUTION),
                    params.get(f"{_VALENCE}{action_id}", 0.0),
                ),
                self._taken.get(action_id, 0),
                action_id,
            )

        action_id = min(affords, key=rank)
        self._taken[action_id] = self._taken.get(action_id, 0) + 1
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
