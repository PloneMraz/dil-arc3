"""The host's effectors carrying out the mind's command — its declared RespondPolicy.

The mind reads what the host's sensory organs took in, forms expectations, is curious and wants,
and constructs the next action; it commands it as T5's test (§6.4: "an action
that pushes to the region to see whether the return matches the Expectation just
built"). The effectors carry the command out. It weighs nothing and chooses
nothing: curiosity and want are the mind's, arising in its thinking, not a
formula here (Plone, 2026-09-25).

What they do, and nothing more:

- **The mind commanded an action the region affords** (RESET always is): it is
  committed, as commanded — ACTION6 with the cell the mind gave.
- **Cycle 0, before the mind has anything to command from**: RESET. Start-up is
  the host's (§4: "Start-up is the host's responsibility, not the loop's").
- **No command, or one the region does not afford**: the host stands still and
  waits (Plone: "Cơ thể có thể đơ để đợi"). In an informational region nothing
  comes back to a host that does not act, so the run ends there; no action is
  made up in the mind's place.

The seam is at the close of the meaning-channel, after appraisal, issuing layer
T8 — DEVIATION from dil-core, declared: dil-core carries out no command itself,
and hard-codes the terminal emission as a marker.
"""

from __future__ import annotations

from typing import Any, Callable, Final

from dil.loop.cycle import RespondContext

from .action import COMPLEX_ACTION, RESET, IllegalMove, Move
from .frame import TERMINAL_STATES
from .observe import move_from_value, move_value

# What the host commits when it stands still: no move reaches the region.
WAIT: Final = {"kind": "wait"}


def _status(ctx: RespondContext) -> dict[str, Any]:
    for signal in ctx.host.signals:
        payload = signal.raw_payload
        if isinstance(payload, dict) and isinstance(payload.get("status"), dict):
            return payload
    return {}


def _command(ctx: RespondContext) -> Move | None:
    """The mind's command this cycle: the last move T5 pushed as a test."""
    for action in reversed(ctx.tests):
        try:
            return move_from_value(action)
        except (IllegalMove, KeyError, TypeError, ValueError):
            continue
    return None


def can_carry_out(action_id: int, x: int | None, y: int | None, state: str | None,
                  affords: tuple[int, ...]) -> bool:
    """Whether the host can carry out this action: the host's one rule, which the
    mind also asks before it counts a proposal as a command. Written once, so the
    two cannot part: twice they did, when it was written in each (after
    `GAME_OVER`, and for ACTION6 with no cell; LOG.md)."""
    if action_id == RESET:
        return True
    if state in TERMINAL_STATES or action_id not in affords:
        return False
    return not (action_id == COMPLEX_ACTION and (x is None or y is None))


def carry_out(ctx: RespondContext, standing: Callable[[], tuple[str, tuple[int, ...]]] | None = None) -> Any:
    """Commit what the mind commanded, if the host can; otherwise stand still.

    What the host can do is read from the region's report this cycle. In a
    cycle the region said nothing in — the host stood still before it — the
    host goes by where it stands (`standing`: the state and the actions of the
    frame it is on), which nothing has changed since."""
    command = _command(ctx)
    if command is None:
        return move_value(Move(RESET)) if ctx.cycle == 0 else dict(WAIT)
    report = _status(ctx)
    if report:
        state = (report.get("status") or {}).get("stateTo")
        affords = tuple(int(a) for a in report.get("affords") or ())
    elif standing is not None:
        state, affords = standing()
    else:
        state, affords = None, ()
    if not can_carry_out(command.action_id, command.x, command.y, state, affords):
        return dict(WAIT)
    return move_value(command)


def carrying_out(source: Any) -> Callable[[RespondContext], Any]:
    """`carry_out` for a host over `source`, which knows the frame it stands on."""
    def respond(ctx: RespondContext) -> Any:
        return carry_out(ctx, standing=lambda: (source.frame.state, tuple(source.frame.available_actions)))
    return respond


def is_wait(action: Any) -> bool:
    return isinstance(action, dict) and action.get("kind") == WAIT["kind"]


__all__ = ["WAIT", "can_carry_out", "carry_out", "carrying_out", "is_wait"]
