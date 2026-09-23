"""The bridge: what the host carries inward, and nothing more.

The host is the body. It receives signals and carries them; it does not
conclude. Everything that reads the signal — finding the things in it
(`perceive.py`), reading what became of them (`interpret.py`) — is the model's
work, and the host calls into it the way a nervous system carries what the eye
has already processed. What travels inward is one signal per Other, on the
declared channels, through T3.

WHAT THIS REPLACES, AND WHY. The earlier version sent ONE signal per cycle,
carrying a finished frame-level interpretation, bound to an entity that was the
ACTION just taken. §8.4 defines an entity as "an other-entity the agent does not
control", and an action is not that. Measured, the consequences were exact:

  - T8 produced RelValue = 0 and SocialEdge = 0 over every cycle of a real run.
    `RelValue` needs N >= 2 and there was never more than one Other; two buttons
    cannot have an Other-to-Other interaction with no self present.
  - T7's absences were meaningless — 444 of 481 scars — because an affordance
    does not return on its own, so asking whether it fell silent was the wrong
    question. Attention patched the symptom.

Now: **entity is a thing, context is the action**. The Other is what is out
there; what the agent just did is the situation it is in. Measured on the same
316 transitions the old mapping was measured on, prediction went 94% -> 93% on
`ls20` and 69% -> 85% on `vc33` — and the hand-coded landing-patch feature that
carried the old `ls20` number is gone.

THE REGION IS AN OTHER TOO. Its state and level counter are the game speaking
about itself, and the agent controls neither. They are not properties of any
thing in the grid, so they travel as their own entity rather than being folded
into one.
"""

from __future__ import annotations

from typing import Final

from dil.loop.cycle import HostCycleInput
from dil.loop.layers.t2 import ObservedChange
from dil.loop.types import Signal

from .action import IllegalMove, Move
from .frame import Frame
from .interpret import REGION_ENTITY, ThingChange, change_value, changes_of, region_status

# The channel things arrive on — the agent's sight of the grid.
VISION_CHANNEL: Final = "arc3-vision"
# The channel the region's own status arrives on. A separate channel because it
# is a separate kind of signal, which is what T3's content-typing is for.
STATUS_CHANNEL: Final = "arc3-status"

# The info-types the transducers stamp.
THING_INFO_TYPE: Final = "thing-change"
STATUS_INFO_TYPE: Final = "region-status"

# The id of the one self-written change: the agent's own move, observed back.
SELF_MOVE_CHANGE: Final = "self:move"


def action_context(move: Move) -> str:
    """The situation a thing's change is read against: what the agent just did.

    This is where the affordance went. It is not an entity — the agent is not an
    Other to itself — it is the **action channel**, and an action channel names a
    context, not a thing that returns.

    ACTION6's coordinates are deliberately not part of it. Folding them in would
    make 4096 contexts that each recur once, and nothing would accrue. Declared
    cost: under ACTION6 the outcome varies with a coordinate the context does not
    carry, so its expectations stay unstable and the loop registers that as
    persistent resistance rather than as learning.
    """
    return f"action:{move.action_id}"


def move_value(move: Move) -> dict[str, object]:
    """The move as plain data.

    This exact shape is BOTH what the respond policy commits and what the host
    reports back as the self-written change, because T2 classifies agency by
    structural equality against the emission it recorded. If the two drifted
    apart the agent would stop recognising its own act.
    """
    return {"kind": "move", "actionId": move.action_id, "x": move.x, "y": move.y}


def move_from_value(value: object) -> Move:
    """Read a committed action back into a Move. Raises if it is not one."""
    if not isinstance(value, dict) or value.get("kind") != "move":
        raise IllegalMove(f"not a committed move: {value!r}")
    return Move(int(value["actionId"]), value.get("x"), value.get("y"))


def thing_payload(kind: str, change: ThingChange, context: str) -> dict[str, object]:
    return {"entity": kind, "change": change_value(change), "context": context}


def observe(prev: Frame, move: Move, now: Frame, t: int) -> HostCycleInput:
    """One cycle's input: what became of each Other, and what the agent did.

    `prev` is taken as an argument rather than looked up, because a change is a
    relation between two frames and it must be computed from the pair the caller
    actually observed.
    """
    context = action_context(move)
    changes = changes_of(prev, now)

    signals: list[Signal] = [
        Signal(
            source_id=VISION_CHANNEL,
            # `entity` is what T4's default resolver binds on. Without it every
            # thing would bind to STRANGER and collapse into one.
            raw_payload=thing_payload(kind, change, context),
            t=t,
        )
        # Sorted so a cycle's signals arrive in a stable order: two runs over the
        # same frames produce the same trace, which an auditor needs.
        for kind, change in sorted(changes.items())
    ]
    signals.append(
        Signal(
            source_id=STATUS_CHANNEL,
            raw_payload={
                "entity": REGION_ENTITY,
                "status": region_status(prev, now),
                "context": context,
                "game": now.game_id,
                # What the region offers next. The respond policy reads it from
                # here, because it is the region's report and not a thing's.
                "affords": list(now.available_actions),
            },
            t=t,
        )
    )

    return HostCycleInput(
        signals=tuple(signals),
        changes=(
            # The agent's own act, observed back. T2 matches this against the
            # emission it recorded and tags it SELF_WRITTEN.
            ObservedChange(id=SELF_MOVE_CHANGE, value=move_value(move)),
            # What the region did. `id` is the entity id T6 reads, so each Other
            # accrues its own independence evidence.
            *(
                ObservedChange(id=kind, value=change_value(change))
                for kind, change in sorted(changes.items())
            ),
            ObservedChange(id=REGION_ENTITY, value=region_status(prev, now)),
        ),
        # Which Others the region says are there. T7 registers an absence only
        # against these — and now that means something: a thing that has gone
        # from the grid is genuinely absent, which an affordance never could be.
        afforded=frozenset(
            [REGION_ENTITY, *(k for k, c in changes.items() if not c.vanished)]
        ),
    )


def thing_transducer(signal: Signal) -> tuple[str, object]:
    """T3's transducer for the vision channel."""
    return (THING_INFO_TYPE, signal.raw_payload)


def status_transducer(signal: Signal) -> tuple[str, object]:
    """T3's transducer for the region's status channel."""
    return (STATUS_INFO_TYPE, signal.raw_payload)


def transducers() -> dict[str, object]:
    """The per-channel transducers this host declares (T3, DECIDE@IMPL)."""
    return {VISION_CHANNEL: thing_transducer, STATUS_CHANNEL: status_transducer}
