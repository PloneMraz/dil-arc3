"""The bridge: a frame transition, as the loop consumes it.

This is the sense organ reporting inward. It turns "I made move M, and the
region came back with frame F" into the `HostCycleInput` the cycle driver takes,
and it does so under the settled reading: the unit is the **affordance**, so what
goes inward is the EFFECT of the move, not the frame.

Three things are decided here, and each is a declaration rather than a
convenience.

**The entity is the affordance, one per action id.** ACTION6 carries `(x, y)`,
and treating each coordinate as its own affordance would create 4096 entities
that each recur once — nothing would ever accrue and the agent would learn
nothing. Coordinates are therefore context, not identity. Bucketing them into
coarse regions would be tidier, but there is no measurement behind any particular
bucketing, and §12 exists to stop exactly that kind of invention. The limit is
declared instead: under ACTION6 the effect varies with a coordinate the entity id
does not carry, so the expectation for `action:6` stays unstable, and the loop
will register that as persistent resistance rather than as learning.

**The agent authors moves; it never authors frames.** So T2 sees exactly one
self-written change — the move it just made, observed back — and every change the
frame shows is environment-pushed. That is not a formality that empties INV-6: it
is the architectural line stated plainly, and it makes each affordance an Other
under T6, something that returns and resists rather than something the agent
wrote. It is also what tag D already claims about this environment.

**The loop is handed no coordinates.** Under this reading the agent learns what
its controls do and does not learn where anything is. That is a real limit of the
affordance reading, declared here rather than discovered later: knowing the
control scheme is not the same as knowing how to win a level.
"""

from __future__ import annotations

from typing import Final

from dil.loop.cycle import HostCycleInput
from dil.loop.layers.t2 import ObservedChange
from dil.loop.types import Signal

from .action import IllegalMove, Move
from .effect import Effect
from .frame import Frame

# The physical channel the game arrives on (T3 content-typing).
GAME_CHANNEL: Final = "arc3-game"
# The info-type the transducer stamps on it.
EFFECT_INFO_TYPE: Final = "affordance-effect"
# The id of the one self-written change: the agent's own move, observed back.
SELF_MOVE_CHANGE: Final = "self:move"


def affordance_key(move: Move) -> str:
    """The entity id for a move. One per action id — see the module docstring."""
    return f"action:{move.action_id}"


def effect_value(effect: Effect) -> dict[str, object]:
    """The effect as plain data.

    T5 compares expectations by `json.dumps(..., sort_keys=True)`, so the value
    has to be JSON-shaped: a dataclass would serialise through `default=str` and
    two structurally identical effects could still differ by repr. Lists rather
    than tuples, for the same reason — `json.dumps` renders both as arrays, but
    only one survives a snapshot round-trip unchanged.
    """
    return {
        "cellsChanged": effect.cells_changed,
        "transitions": [list(t) for t in effect.transitions],
        "displacements": [list(d) for d in effect.displacements],
        "depthDelta": effect.depth_delta,
        "levelsDelta": effect.levels_delta,
        "stateFrom": effect.state_from,
        "stateTo": effect.state_to,
        "null": effect.is_null,
    }


def move_value(move: Move) -> dict[str, object]:
    """The move as plain data.

    This exact shape is BOTH what the respond policy commits and what the host
    reports back as the self-written change, because T2 classifies agency by
    structural equality against the emission it recorded. If the two shapes
    drifted apart the agent's own move would be tagged ENV_PUSHED — it would
    stop recognising its own act.
    """
    return {"kind": "move", "actionId": move.action_id, "x": move.x, "y": move.y}


def move_from_value(value: object) -> Move:
    """Read a committed action back into a Move. Raises if it is not one."""
    if not isinstance(value, dict) or value.get("kind") != "move":
        raise IllegalMove(f"not a committed move: {value!r}")
    return Move(int(value["actionId"]), value.get("x"), value.get("y"))


def game_transducer(signal: Signal) -> tuple[str, object]:
    """T3's per-channel transducer for the game.

    It hands the payload through unchanged, typed. The payload already carries
    the `entity` key that T4's default resolver reads, so the affordance binding
    needs no custom resolver — the loop's own DECIDE@IMPL seam takes it as it is.
    """
    return (EFFECT_INFO_TYPE, signal.raw_payload)


def observe(prev: Frame, move: Move, now: Frame, effect: Effect, t: int) -> HostCycleInput:
    """One cycle's input: what the move was, and what the region did about it.

    `prev` is not sent inward. It is taken as an argument because the effect is a
    relation between two frames and the signature should be computed from the
    pair the caller actually observed, never from a frame this module went
    looking for.
    """
    entity = affordance_key(move)
    return HostCycleInput(
        # Which affordances the region said were there when this move was
        # chosen. T7 registers an absence only against these: an action the game
        # did not offer is not silent, it simply was not there to answer. Read
        # off `prev`, because that is the frame the move was chosen from — `now`
        # reports what is afforded for the NEXT choice.
        afforded=frozenset(
            f"action:{a}" for a in prev.available_actions
        ),
        signals=(
            Signal(
                source_id=GAME_CHANNEL,
                # `entity` is what T4's default resolver binds on; without it the
                # unit would bind to STRANGER and every affordance would collapse
                # into one.
                raw_payload={
                    "entity": entity,
                    "effect": effect_value(effect),
                    "game": now.game_id,
                    "affords": list(now.available_actions),
                },
                t=t,
            ),
        ),
        changes=(
            # The agent's own act, observed back. T2 matches this against the
            # emission it recorded and tags it SELF_WRITTEN.
            ObservedChange(id=SELF_MOVE_CHANGE, value=move_value(move)),
            # What the region did. `id` is the entity id T6 reads, so the
            # affordance accrues independence evidence as an Other.
            ObservedChange(id=entity, value=effect_value(effect)),
        ),
    )
