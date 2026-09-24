"""The host — the body the loop runs inside, over a live ARC-AGI-3 game.

`HostSource` says it plainly: *the agent acts through `deliver`*. DIL is the
condition, not the actor. So this ring holds the game, reports what the region
returned through `next`, and executes what the self committed through `deliver`.
Nothing here chooses a move — the choice arrives already made, in the emission.

Order within a cycle is the daemon's: `next()` → `cycle.run()` → `deliver()`. So
`deliver` acts and the FOLLOWING `next` reports what that act did. That is INV-1
closing against a real region rather than against a script.

**The first cycle.** `reset()` produces the opening frame out of nothing, and
there is no earlier frame to difference it against, so cycle 0 reports the RESET
with a null effect. That is not a placeholder standing in for a real observation:
the agent has not yet done anything observable, and saying so is accurate. It
costs one cycle, and it binds an `action:0` entity the game never affords —
which is also the check that T7's presence filter works, since an affordance the
region does not offer must never be registered absent.

The SDK is not imported here. The environment and the engine's action class both
arrive as arguments, so the body stays testable with the game uninstalled — the
same stance `frame.py` takes at the sense boundary.
"""

from __future__ import annotations

from typing import Any, Final

from dil.host import (
    BoundaryDeclaration,
    ChannelDeclaration,
    EmitterDeclaration,
    HostDeclaration,
    PreexistingMemory,
    ResilienceDeclaration,
    StoreDeclaration,
    TraceDeclaration,
)
from dil.loop.cycle import HostCycleInput
from dil.loop.layers.t2 import Emission

from .action import RESET, IllegalMove, Move, check_afforded, to_engine
from .frame import Frame, read_frame
from .observe import FRAME_CHANNEL, ONLOOKER_CHANNEL, STATUS_CHANNEL, move_from_value, observe
from .prior import ArcRules

# How many state-changing actions a run may spend. RHAE scores
# (human_baseline / ai_actions)^2, so every action is paid for; deliberation is
# free and this is not.
DEFAULT_ACTION_BUDGET: Final = 200

# How many RESETs to spend trying to get an opening frame before giving up.
OPEN_ATTEMPTS: Final = 3


class StepFailed(Exception):
    """The engine returned nothing for a committed action."""


class Arc3Source:
    """A `HostSource` over one live game."""

    __slots__ = (
        "_env", "_ga", "_frame", "_prev", "_pending", "_t", "_budget", "_spent",
        "delivered",
    )

    def __init__(
        self,
        env: Any,
        game_action_cls: Any,
        action_budget: int = DEFAULT_ACTION_BUDGET,
    ) -> None:
        # The host holds no model and computes nothing from what it takes in: it
        # reads the engine's frame, carries it inward, and executes what the self
        # committed. Working out what the grid means is the mind's.
        self._env = env
        self._ga = game_action_cls
        self._frame: Frame | None = None
        self._prev: Frame | None = None
        self._pending: Move | None = None
        self._t = 0
        self._budget = action_budget
        self._spent = 0
        # What the self committed, in order — the run's own record of its acts.
        self.delivered: list[Move] = []

    @property
    def frame(self) -> Frame | None:
        """The frame currently on the region's side. Read-only."""
        return self._frame

    @property
    def spent(self) -> int:
        return self._spent

    def next(self) -> HostCycleInput | None:
        """What the region returned, as the loop consumes it."""
        if self._spent >= self._budget:
            return None

        if self._frame is None:
            # Opening the game. See the module docstring on cycle 0.
            self._frame = read_frame(self._open())
            self._prev = self._frame
            self._pending = Move(RESET)

        if self._pending is None or self._prev is None:
            # `deliver` has not run since the last report; nothing new happened.
            return None

        host_input = observe(
            self._prev, self._pending, self._frame, t=self._t
        )
        self._t += 1
        self._pending = None
        return host_input

    def _open(self) -> Any:
        """Get the first real frame out of the engine.

        MEASURED, not assumed: `env.reset()` returns a populated frame for
        `ls20` and an EMPTY one for `vc33`, which needs RESET sent as an action
        before the game starts. The boundary gate refused the empty frame — as
        it should, an empty stack is not an observation — and that refusal is
        what exposed this. The retry is bounded, because a reset that never
        yields a frame is a failure to report, not a condition to sit in.
        """
        raw = self._env.reset()
        for _ in range(OPEN_ATTEMPTS):
            if getattr(raw, "frame", None):
                return raw
            action, _data = to_engine(Move(RESET), self._ga)
            raw = self._env.step(action, None)
            self._spent += 1
            if raw is None:
                raise StepFailed("the engine returned nothing while opening the game")
        raise StepFailed(
            f"the game gave no frame after {OPEN_ATTEMPTS} resets"
        )

    def deliver(self, response: Emission) -> None:
        """Execute what the self committed. **This is where the agent acts.**

        A move the current frame does not afford is refused rather than
        substituted. Quietly swapping in a legal action would put the choice in
        the body, and the body does not choose.
        """
        move = move_from_value(response.action)
        if self._frame is None:
            raise StepFailed("deliver before the game was opened")
        check_afforded(move, self._frame)

        action, data = to_engine(move, self._ga)
        if data:
            action.set_data(data)
        raw = self._env.step(action, data or None)
        if raw is None:
            raise StepFailed(f"the engine returned nothing for {move}")

        self._prev = self._frame
        self._frame = read_frame(raw)
        self._pending = move
        self._spent += 1
        self.delivered.append(move)


def declaration(
    game_id: str,
    store_root: str | None = None,
    prior: PreexistingMemory | None = None,
    onlooker: bool = False,
) -> HostDeclaration:
    """What this host declares about itself, read once by the precondition gate.

    Every field is a claim about this deployment that the gate checks before the
    loop is allowed to run, so each is stated from what the code actually does.

    `prior` is what the character may know before it has lived a cycle — by
    default the directive and the published rules, `ArcRules`. It reaches the
    store only through the runtime's tagging-gate, and only when the host
    declares a real substrate (`store_root`): the in-memory fixture a test runs
    on has no requisition step, so nothing is admitted there.

    `onlooker` declares the third channel, when the onlooker (tag E) stands by.
    """
    return HostDeclaration(
        # A frame arrives, a move goes out: the boundary is real and crossable.
        boundary=BoundaryDeclaration(present=True),
        channels=(
            ChannelDeclaration(
                id=FRAME_CHANNEL,
                # The game returns, and it resists: it is the Mode-B source of
                # tag D. An agent cannot write a frame.
                can_return=True,
            ),
            ChannelDeclaration(
                # The region's own status is a separate kind of signal, so it is
                # a separate channel — which is what T3's content-typing is for.
                id=STATUS_CHANNEL,
                can_return=True,
            ),
            *((ChannelDeclaration(
                # An Other outside the agent, judging how it behaves: it returns,
                # and the agent does not control what it says.
                id=ONLOOKER_CHANNEL,
                can_return=True,
            ),) if onlooker else ()),
        ),
        store=StoreDeclaration(
            persists_across_cycles=True,
            root=store_root,
            preexisting=prior if prior is not None else ArcRules(),
        ),
        # The `[event]` log is the one trace §13 turns on, and it is a plain
        # append-only file a third party can read without this code.
        trace=TraceDeclaration(externally_readable=True),
        # The host can act before the region says anything: RESET opens the game.
        emitter=EmitterDeclaration(can_emit_first_action=True),
        # A refused move raises; it does not reset the run or discard accrued
        # state. Wiping on mismatch would destroy the accrual INV-5 rests on.
        resilience=ResilienceDeclaration(wipes_state_on_mismatch=False),
    )


def create_source(
    env: Any,
    game_action_cls: Any,
    action_budget: int = DEFAULT_ACTION_BUDGET,
) -> Arc3Source:
    return Arc3Source(env, game_action_cls, action_budget)


__all__ = [
    "DEFAULT_ACTION_BUDGET",
    "OPEN_ATTEMPTS",
    "Arc3Source",
    "IllegalMove",
    "StepFailed",
    "create_source",
    "declaration",
]
