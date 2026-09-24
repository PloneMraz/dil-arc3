"""The bridge: what the host carries inward, and nothing more.

The host is the body. Like an eye it takes the signal in — the frame the engine
returns, read and gated by `frame.py` — and carries it inward; it computes
nothing from it. Working out what the grid means is the mind's, and the mind is
one: the program the model writes (`mind.py`).

Two signals travel each cycle, on two channels, through T3:

  - **the frame** — the stack of grids before the move and the stack after, and
    the move between, exactly as the engine returned them. It is what the mind
    predicts.
  - **the region's status** — the game speaking about itself: its state, the
    change in its level count, what it offers next. The agent controls none of
    it, so it is an Other's report, and the self reads from it what may be done.

WHAT THIS REPLACED, 2026-09-24. The host used to call into a computation of the
grid — `perceive.py` found pieces, `seeing.py` followed them across frames,
`interpret.py` read what became of them — and send one signal per "thing" it
found. That computation was a second mind: the grid read one way by counting
things and another by the model's program, two understandings of one world that
never met, and only the first reached the self. It was also misnamed: seeing is
the eye's; what those modules did was compute. They are gone; the host takes in,
the mind computes.
"""

from __future__ import annotations

from typing import Final

from dil.loop.cycle import HostCycleInput
from dil.loop.layers.t2 import ObservedChange
from dil.loop.types import Signal
from dil.runtime.peer import PEER_REFLECTION_CHANNEL
from dil.runtime.reflection import reflection_transducer
from dil.store.tagging_gate import HostDatum

from .action import IllegalMove, Move
from .frame import Frame

# The channel the frame arrives on: the pair of grid stacks the host took in,
# before and after the move, as they are.
FRAME_CHANNEL: Final = "arc3-frame"
FRAME_ENTITY: Final = "frame"
# The channel the region's own status arrives on. A separate channel because it
# is a separate kind of signal, which is what T3's content-typing is for.
STATUS_CHANNEL: Final = "arc3-status"
# The Other that is the game itself: its state and level counter.
REGION_ENTITY: Final = "region"

# The info-types the transducers stamp.
FRAME_INFO_TYPE: Final = "frame"
STATUS_INFO_TYPE: Final = "region-status"

# The id of the one self-written change: the agent's own move, observed back.
SELF_MOVE_CHANGE: Final = "self:move"


def action_context(move: Move) -> str:
    """What the agent just did, as the situation an arrival is read against.

    Not an entity — the agent is not an Other to itself — but the action channel,
    which names a context. ACTION6's coordinates are not part of it; they travel
    in the frame's `move`, where the mind's program reads them.
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


def frame_payload(prev: Frame, move: Move, now: Frame, context: str) -> dict[str, object]:
    """The frame signal: the two grid stacks the host took in, and the move between.

    Carried as they are — every grid of each stack, no grid chosen as "the" view
    (`Frame.top` stays a probe's accessor). Which grid the mind reads is the
    mind's reading, not the body's.
    """
    return {
        "entity": FRAME_ENTITY,
        "before": [[list(row) for row in grid] for grid in prev.grids],
        "grids": [[list(row) for row in grid] for grid in now.grids],
        "move": move_value(move),
        "context": context,
    }


def region_status(prev: Frame, now: Frame) -> dict[str, object]:
    """What the region itself reported, from the two frames it returned.

    The game's state and level counter are the region speaking about itself; the
    agent controls neither, so they belong to an Other — this one.
    """
    return {
        "stateFrom": prev.state,
        "stateTo": now.state,
        "levelsDelta": now.levels_completed - prev.levels_completed,
        "depthDelta": now.depth - prev.depth,
    }


def observe(prev: Frame, move: Move, now: Frame, t: int) -> HostCycleInput:
    """One cycle's input: the frame the region returned, and its report on itself.

    `prev` is taken as an argument rather than looked up, because a change is a
    relation between two frames and must be read from the pair the host took in.
    """
    context = action_context(move)
    status = region_status(prev, now)
    signals = (
        Signal(source_id=FRAME_CHANNEL, raw_payload=frame_payload(prev, move, now, context), t=t),
        Signal(
            source_id=STATUS_CHANNEL,
            raw_payload={
                "entity": REGION_ENTITY,
                "status": status,
                "context": context,
                "game": now.game_id,
                # What the region offers next. The respond policy reads it from
                # here, because it is the region's report.
                "affords": list(now.available_actions),
            },
            t=t,
        ),
    )
    return HostCycleInput(
        signals=signals,
        changes=(
            # The agent's own act, observed back. T2 matches this against the
            # emission it recorded and tags it SELF_WRITTEN.
            ObservedChange(id=SELF_MOVE_CHANGE, value=move_value(move)),
            # What the region did to itself.
            ObservedChange(id=REGION_ENTITY, value=status),
        ),
        # The Others the region says are there: itself, and the frame it returned.
        # T7 registers an absence only against these.
        afforded=frozenset([REGION_ENTITY, FRAME_ENTITY]),
    )


# What an arrival is about, on the open-tag dimensions this host declares (tag F,
# decisions.OPEN_TAG_KEYS). A stored datum carries the same values when it is
# about the same thing, and that shared description is how the one comes to mind
# when the other arrives (§6.4 T3 query). The prior's items are tagged with them.
THINGS_OBJECT: Final = "things"
LEVELS_OBJECT: Final = "levels"
ACTIONS_OBJECT: Final = "actions"
STATUS_OBJECT: Final = "region-status"
VISION_SENSE: Final = "vision"


def frame_transducer(signal: Signal) -> tuple[str, object, list[dict[str, str]]]:
    """T3's transducer for the frame channel. A frame came by sight."""
    return (FRAME_INFO_TYPE, signal.raw_payload, [{"sense": VISION_SENSE}])


def status_transducer(signal: Signal) -> tuple[str, object, list[dict[str, str]]]:
    """T3's transducer for the region's status channel.

    It also says what the arrival is about, which is what T3 asks the store with
    (§6.4 query). A status report carries the region's state, the change in its
    level count, and the actions it affords next — so it is about all three.
    """
    return (
        STATUS_INFO_TYPE,
        signal.raw_payload,
        [{"object": STATUS_OBJECT}, {"object": LEVELS_OBJECT}, {"object": ACTIONS_OBJECT}],
    )


def transducers() -> dict[str, object]:
    """The per-channel transducers this host declares (T3, DECIDE@IMPL).

    Three channels: the frame, the region's status, and a peer's reading of this
    agent's recorded collisions (tag E), which arrives only when a peer is wired.
    """
    return {
        FRAME_CHANNEL: frame_transducer,
        STATUS_CHANNEL: status_transducer,
        PEER_REFLECTION_CHANNEL: reflection_transducer,
    }


# The class of data a region return is, once it is a datum of its own (§9
# `domain`). The prior's is the rules it was told; this is what it met.
OBSERVATION_DOMAIN: Final = "observation"
FRAME_KIND: Final = "frame"
STATUS_KIND: Final = "status"
# A peer's reading is not the region's return: it is another agent's account of
# where this one collided (§8.4, tag E), so it is its own class of data.
REFLECTION_DOMAIN: Final = "reflection"
PEER_READING_KIND: Final = "peer-reading"


def admit(signal: Signal) -> HostDatum | None:
    """Which region returns this host keeps as data of their own (§10, DECIDE@IMPL).

    All three: what the region returned is what the character met, and a return
    it does not keep can neither be asked for later nor be the datum that
    collides when the expectation about it fails. A peer's reading is kept on the
    same ground, as `domain: reflection`.
    """
    if signal.source_id == FRAME_CHANNEL:
        open_tags = {
            "domain": OBSERVATION_DOMAIN, "kind": FRAME_KIND,
            "source": FRAME_CHANNEL, "sense": VISION_SENSE,
        }
    elif signal.source_id == STATUS_CHANNEL:
        open_tags = {
            "domain": OBSERVATION_DOMAIN, "kind": STATUS_KIND,
            "source": STATUS_CHANNEL, "object": STATUS_OBJECT,
        }
    elif signal.source_id == PEER_REFLECTION_CHANNEL:
        open_tags = {
            "domain": REFLECTION_DOMAIN, "kind": PEER_READING_KIND,
            "source": PEER_REFLECTION_CHANNEL,
        }
    else:
        return None
    return HostDatum(payload=signal.raw_payload, admitting_layer=1, open=open_tags)
