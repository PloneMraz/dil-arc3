"""How the self commits an action.

The policy runs at the close of the meaning-channel, after appraisal. No layer
chooses the move; these tests are about what the whole loop commits.
"""

from __future__ import annotations

from arc3.action import Move
from arc3.observe import move_value, observe
from arc3.respond import DEFAULT_SWEEP, UNMET_CONFIDENCE, least_resolved
from dil.loop.cycle import RespondContext
from dil.loop.types import Appraisal, Expectation, InfoUnit, ModField, RefFrame
from arc3.effect import diff
from tests.test_arc3_effect import framed, marker


class FakeResult:
    def __init__(self, entity_id: str, confidence: float, recurrence: float) -> None:
        self.entity_id = entity_id
        unit = InfoUnit(content={}, ref_frame=RefFrame(bound_layer=5, ref="x"), t=0)
        self.expectation = Expectation(
            predicted=unit, confidence=confidence, recurrence=recurrence
        )


def ctx_for(affords, expectations=(), state_to="NOT_FINISHED", cycle=1):
    prev = framed(marker(30, 30), actions=affords or (1,))
    now = framed(marker(25, 30), actions=affords or (1,), state=state_to,
                 **({} if state_to == "NOT_FINISHED" else {}))
    if state_to != "NOT_FINISHED":
        now = framed(marker(25, 30), state=state_to, actions=affords or ())
    host = observe(prev, Move(1), now, diff(prev, now), t=cycle)
    return RespondContext(
        cycle=cycle,
        appraisal=Appraisal(info_ref="c", valence=0.0, goal_relevance=0.0),
        field=ModField(),
        expectations=tuple(expectations),
        host=host,
    )


def test_an_untried_affordance_outranks_a_tried_one():
    """The loop reaches for what it does not know before what it does."""
    policy = least_resolved()
    ctx = ctx_for((1, 2), expectations=(FakeResult("action:1", 1.0, 9),))
    assert policy(ctx) == move_value(Move(2))


def test_an_unmet_affordance_is_ranked_at_zero_confidence():
    assert UNMET_CONFIDENCE == 0.0


def test_the_least_confident_affordance_wins():
    policy = least_resolved()
    ctx = ctx_for(
        (1, 2, 3),
        expectations=(
            FakeResult("action:1", 1.0, 9),
            FakeResult("action:2", 0.3, 3),
            FakeResult("action:3", 0.8, 8),
        ),
    )
    assert policy(ctx) == move_value(Move(2))


def test_ties_break_deterministically_so_a_run_can_be_replayed():
    a, b = least_resolved(), least_resolved()
    made_a = [a(ctx_for((1, 2, 3, 4))) for _ in range(4)]
    made_b = [b(ctx_for((1, 2, 3, 4))) for _ in range(4)]
    assert made_a == made_b


def test_the_policy_accrues_across_cycles_rather_than_reloading():
    """INV-5 in the host's own ring: it is told one entity per cycle and builds
    the picture from what it was told, never from a history handed back."""
    policy = least_resolved()
    policy(ctx_for((1, 2), expectations=(FakeResult("action:1", 1.0, 9),)))
    # action:1 is now known to be resolved; a later cycle that mentions nothing
    # must still prefer the affordance it has never met.
    assert policy(ctx_for((1, 2))) == move_value(Move(2))


def test_a_terminal_frame_commits_reset():
    """MEASURED: vc33 reaches GAME_OVER and KEEPS reporting available_actions
    (6,). Stepping that returns an empty frame. The state decides, not the list."""
    policy = least_resolved()
    assert policy(ctx_for((6,), state_to="GAME_OVER")) == move_value(Move(0))


def test_a_frame_affording_nothing_commits_reset():
    policy = least_resolved()
    assert policy(ctx_for((), state_to="GAME_OVER")) == move_value(Move(0))


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
    policy = least_resolved()
    committed = policy(ctx_for((1,)))
    assert committed == move_value(Move(1))


# ── the field reaches the place behaviour is constructed ──


def test_the_policy_can_read_the_modulatory_field():
    """Until this existed, the field could not reach link 5.

    §6 calls the field "a global gain and bias shifting every link's parameters
    at once", and link 5 — respond — is a link. Without the field here, anything
    the field comes to hold (attention, and whatever stands for want) could not
    affect what the agent does. Measured before the fix: the field held
    `{attentionGain: 0.2, resistance: 0.0}` after 60 live cycles and the policy
    could not see either number.
    """
    seen: list[dict[str, float]] = []

    def watching_policy(ctx):
        seen.append(dict(ctx.field.params))
        return move_value(Move(1))

    ctx = ctx_for((1,))
    object.__setattr__(ctx, "field", ModField(params={"attentionGain": 0.25}))
    watching_policy(ctx)
    assert seen == [{"attentionGain": 0.25}]


def test_the_field_is_read_only_background_here_too():
    """INV-7: the down-channel. A policy reads it and never writes it."""
    field = ModField(params={"attentionGain": 0.5})
    ctx = ctx_for((1,))
    object.__setattr__(ctx, "field", field)
    least_resolved()(ctx)
    assert field.params == {"attentionGain": 0.5}
