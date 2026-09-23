"""How the self commits an action.

The policy runs at the close of the meaning-channel, after appraisal, and reads
what it knows about each action off the modulatory field — nowhere else. These
tests are about what the whole loop commits.
"""

from __future__ import annotations

from arc3.action import Move
from arc3.observe import move_value, observe
from arc3.respond import DEFAULT_SWEEP, UNMET_RESOLUTION, compose, least_resolved
from dil.loop.cycle import RespondContext
from dil.loop.types import Appraisal, ModField
from tests.test_arc3_perceive import framed


def ctx_for(affords, params=None, state_to="NOT_FINISHED", cycle=1):
    prev = framed({(30, 30): 9, (30, 31): 9}, actions=affords or (1,))
    if state_to == "NOT_FINISHED":
        now = framed({(25, 30): 9, (25, 31): 9}, actions=affords or (1,))
    else:
        now = framed({(25, 30): 9, (25, 31): 9}, state=state_to, actions=affords or ())
    return RespondContext(
        cycle=cycle,
        appraisal=Appraisal(info_ref="c", valence=0.0, goal_relevance=0.0),
        field=ModField(params=dict(params or {})),
        expectations=(),
        host=observe(prev, Move(1), now, t=cycle),
    )


# ── the regression this policy was rewritten to fix ──


def test_the_policy_does_not_press_one_key_for_ever():
    """MEASURED before the fix: on a live ls20 run the agent committed ACTION1
    forty times out of forty. The old policy ranked actions by the confidence
    of an entity named `action:N`; once entities became things, no such entity
    existed, every action tied, and the lowest id won every time."""
    policy = least_resolved()
    committed = [policy(ctx_for((1, 2, 3, 4)))["actionId"] for _ in range(8)]
    assert set(committed) == {1, 2, 3, 4}


# ── curiosity, read off the field ──


def test_an_action_the_mind_has_not_reported_on_is_tried_first():
    """The loop reaches for what it does not know before what it does."""
    assert UNMET_RESOLUTION == 0.0
    policy = least_resolved()
    ctx = ctx_for((1, 2), {"resolved:action:1": 0.9})
    assert policy(ctx) == move_value(Move(2))


def test_the_least_resolved_action_is_taken():
    policy = least_resolved()
    ctx = ctx_for(
        (1, 2, 3),
        {"resolved:action:1": 1.0, "resolved:action:2": 0.3, "resolved:action:3": 0.8},
    )
    assert policy(ctx) == move_value(Move(2))


# ── want modulates curiosity; it does not replace it ──


def test_an_action_the_region_ended_the_game_after_is_avoided():
    """However unfamiliar it is, an action the region answered with an ending
    ranks behind one it said nothing about."""
    policy = least_resolved()
    ctx = ctx_for(
        (1, 2),
        {
            "resolved:action:1": 0.0,
            "valence:action:1": -1.0,
            "resolved:action:2": 0.9,
        },
    )
    assert policy(ctx) == move_value(Move(2))


def test_an_action_the_region_rewarded_is_preferred_however_familiar():
    policy = least_resolved()
    ctx = ctx_for(
        (1, 2),
        {
            "resolved:action:1": 1.0,
            "valence:action:1": 1.0,
            "resolved:action:2": 0.2,
        },
    )
    assert policy(ctx) == move_value(Move(1))


def test_where_the_region_has_said_nothing_curiosity_decides_alone():
    assert compose(0.4, 0.0) == 0.4
    assert compose(0.4, -1.0) > compose(0.9, 0.0)


# ── the self's own record ──


def test_ties_break_on_what_the_self_has_already_done():
    policy = least_resolved()
    first = policy(ctx_for((1, 2)))["actionId"]
    second = policy(ctx_for((1, 2)))["actionId"]
    assert {first, second} == {1, 2}


def test_the_same_field_and_frame_commit_the_same_move():
    """Deterministic, so a third party can replay a run."""
    a, b = least_resolved(), least_resolved()
    ctx = ctx_for((1, 2, 3), {"resolved:action:2": 0.5})
    assert [a(ctx) for _ in range(4)] == [b(ctx) for _ in range(4)]


def test_the_field_is_only_read():
    params = {"resolved:action:1": 0.5}
    ctx = ctx_for((1, 2), params)
    least_resolved()(ctx)
    assert dict(ctx.field.params) == params


# ── terminal frames, and ACTION6 ──


def test_a_terminal_frame_commits_reset():
    """MEASURED: vc33 reaches GAME_OVER and KEEPS reporting available_actions
    (6,). Stepping that returns an empty frame. The state decides, not the list."""
    assert least_resolved()(ctx_for((6,), state_to="GAME_OVER")) == move_value(Move(0))


def test_a_frame_affording_nothing_commits_reset():
    assert least_resolved()(ctx_for((), state_to="GAME_OVER")) == move_value(Move(0))


def test_action6_is_given_coordinates_from_the_declared_sweep():
    policy = least_resolved()
    first = policy(ctx_for((6,)))
    assert first["actionId"] == 6
    assert (first["x"], first["y"]) == DEFAULT_SWEEP[0]
    assert policy(ctx_for((6,)))["x"] == DEFAULT_SWEEP[1][0]


def test_every_sweep_point_lies_on_the_grid():
    assert all(0 <= x <= 63 and 0 <= y <= 63 for x, y in DEFAULT_SWEEP)


def test_the_committed_shape_is_what_t2_will_match():
    """If the emission and the reported self-written change ever drift apart,
    the agent stops recognising its own act."""
    assert least_resolved()(ctx_for((1,))) == move_value(Move(1))
